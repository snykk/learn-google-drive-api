import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from typing import List
from PIL import Image
import zipfile
from io import BytesIO
from googleapiclient.http import MediaFileUpload
import numpy as np
import tempfile


class DriveApiService:
    def __init__(self, client_secret_path: str, api_name: str, api_version: str, scopes: List[str], root_folder: str):
        self.__client_secret_file =  client_secret_path
        self.__api_name = api_name
        self.__api_version = api_version
        self.__scopes = scopes
        self.__root_folder = root_folder
        self.__service = None
        self.__establishConnection()

    
    def getRootFolder(self) -> str:
        return self.__root_folder


    def __establishConnection(self):
        cred = self.__loadCredentials()

        if not cred or not cred.valid:
            cred = self.__refreshCredentials(cred)

        try:
            self.__service = build(self.__api_name, self.__api_version, credentials=cred)
            print("[SYSTEM]", self.__api_name, 'service created successfully')
        except Exception as e:
            print("[SYSTEM] Unable to connect")
            print('Error:', e)


    def __loadCredentials(self):
        pickle_file = f'token_{self.__api_name}_{self.__api_version}.pickle'

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                return pickle.load(token)
        return None


    def __refreshCredentials(self, cred):
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.__client_secret_file, self.__scopes)
            cred = flow.run_local_server()

        with open(f'token_{self.__api_name}_{self.__api_version}.pickle', 'wb') as token:
            pickle.dump(cred, token)
        return cred


    def createFolders(self, folders: List[str], parent_id: str = None):
        try:
            responses = []
            for folder in folders:
                file_metadata = {
                    'name': folder,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents' : [parent_id],
                }

                response = self.__service.files().create(body=file_metadata).execute()
                responses.append(response)

            print("[SYSTEM] Folders created successfully")
            return responses
        except Exception as e:
            print("[SYSTEM] Failed when creaate a folders")
            print('Error:', e)



    def checkFolderExists(self, folder_name: str, parent_id: str = None) -> bool:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"

        response = self.__service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()

        for file in response.get('files', []):
            if file.get('name') == folder_name:
                return True  # Folder exists

        return False

    
    
    def __createZipBuf(self, metadata: dict) -> BytesIO:
        # Create BytesIO buffers to hold the images
        watermarked_image_buf = BytesIO()
        key_image_buf = BytesIO()
        block_position_buf = BytesIO()

        # Save images to BytesIO buffers
        Image.fromarray(np.uint8(metadata['file1']['image'])).save(watermarked_image_buf, format='bmp')
        Image.fromarray(np.uint8(metadata['file2']['image'])).save(key_image_buf, format='bmp')
        Image.fromarray(np.uint8(metadata['file3']['image'])).save(block_position_buf, format='bmp')

        # Reset buffer positions to start
        watermarked_image_buf.seek(0)
        key_image_buf.seek(0)
        block_position_buf.seek(0)

        # Create a BytesIO buffer for the nested zip file
        zip_buf = BytesIO()

        # Create a zip file for the nested zip and add the BMP and PNG images to it
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_STORED) as nested_zip:
            nested_zip.writestr(f'{metadata['file1']['file_name']}.bmp', watermarked_image_buf.getvalue())
            nested_zip.writestr(f'{metadata['file2']['file_name']}.bmp', key_image_buf.getvalue())
            nested_zip.writestr(f'{metadata['file3']['file_name']}.bmp', block_position_buf.getvalue())

        # Reset buffer position to start
        zip_buf.seek(0)
        return zip_buf
    

    def __uploadSingleImage(self, parent_id: str, output_name: str, image_array: np.ndarray, email: str = None):
        print(f'[SYSTEM] Uploading image \'{output_name}\' to Google Drive')
        try:
            with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as image_temp:
                Image.fromarray(np.uint8(image_array)).save(image_temp, format='bmp')
                image_temp.seek(0)
                media = MediaFileUpload(image_temp.name, mimetype='image/bmp', resumable=True)
                file_metadata = {'name': f'{output_name}.bmp', 'parents': [parent_id]}
                uploaded_file = self.__service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                # Share the file with the specified email
                if email:
                    permission = {
                        'type': 'user',
                        'role': 'reader',
                        'emailAddress': email
                    }
                    self.__service.permissions().create(fileId=uploaded_file['id'], body=permission).execute()
                
                print('[SYSTEM] File uploaded successfully')
                return uploaded_file
        except Exception as e:
            print("[SYSTEM] Failed when uploading single image")
            print('Error:', e)

    def __uploadZip(self, parent_id: str, watermarked_image: np.ndarray, key_image: np.ndarray, block_position: np.ndarray, email: str = None):
        print(f'[SYSTEM] Uploading zip to Google Drive')
        try:
            metadata = {
                'file1': {'file_name':'watermarked_image', 'image':watermarked_image},
                'file2': {'file_name':'key_image', 'image':key_image},
                'file3': {'file_name':'block_position', 'image':block_position}
            }
            # Create nested zip containing 3 images
            zip_buf = self.__createZipBuf(metadata=metadata)
            # Reset nested zip buffer position to start
            zip_buf.seek(0)
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as zip_temp:
                zip_temp.write(zip_buf.getvalue())
                zip_temp.seek(0)
                media4 = MediaFileUpload(zip_temp.name, mimetype='application/zip', resumable=True)
                file4_metadata = {'name': 'embedding.zip', 'parents': [parent_id]}
                uploaded_file = self.__service.files().create(body=file4_metadata, media_body=media4, fields='id').execute()

                # Share the file with the specified email
                if email:
                    permission = {
                        'type': 'user',
                        'role': 'reader',
                        'emailAddress': email
                    }
                    self.__service.permissions().create(fileId=uploaded_file['id'], body=permission).execute()

                print('[SYSTEM] File uploaded successfully')
                return uploaded_file
        except Exception as e:
            print("[SYSTEM] Failed when uploading a zip file")
            print('Error:', e)
            

    def uploadMixedFiles(self, parent_id: str, watermarked_image: np.ndarray, key_image: np.ndarray, block_position: np.ndarray, email: str):
        try:
            responses = {}

            responses['watermarked_image'] = self.__uploadSingleImage(parent_id=parent_id, output_name='watermarked_image', image_array=watermarked_image.copy(), email=email)
            responses['key_image'] = self.__uploadSingleImage(parent_id=parent_id, output_name='key_image', image_array=key_image.copy(), email=email)
            responses['block_position'] = self.__uploadSingleImage(parent_id=parent_id, output_name='block_position', image_array=block_position.copy(), email=email)

            responses['embedding_result_zip'] = self.__uploadZip(parent_id=parent_id, watermarked_image=watermarked_image.copy(), key_image=key_image.copy(), block_position=block_position.copy(), email=email)

            print("Uploaded all files successfully")

            return responses
        except Exception as e:
            print("[SYSTEM] Failed to upload mixed files")
            print('Error:', e)


    def getFileLinks(self, file_id: str):
        try:
            # Retrieve file metadata including webViewLink and downloadUrl
            file = self.__service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()

            # Extract links
            web_view_link = file.get('webViewLink')
            download_link = file.get('webContentLink')

            return web_view_link, download_link
        except Exception as e:
            print("[SYSTEM] Failed to retrieve file links")
            print('Error:', e)
        
    
    def getFilesInFolder(self, folder_id: str):
        try:
            # Query to retrieve all files in the folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            response = self.__service.files().list(q=query, fields='files(id, name)').execute()
            
            files_in_folder = response.get('files', [])
                        
            return files_in_folder
        except Exception as e:
            print("[SYSTEM] Failed to retrieve files in folder")
            print('Error:', e)
            return []

