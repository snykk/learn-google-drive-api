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
        self.__establish_connection()

    
    def getRootFolder(self) -> str:
        return self.__root_folder


    def __establish_connection(self):
        cred = self.__load_credentials()

        if not cred or not cred.valid:
            cred = self.__refresh_credentials(cred)

        try:
            self.__service = build(self.__api_name, self.__api_version, credentials=cred)
            print("[SYSTEM]", self.__api_name, 'service created successfully')
        except Exception as e:
            print("[SYSTEM] Unable to connect")
            print('Error:', e)


    def __load_credentials(self):
        pickle_file = f'token_{self.__api_name}_{self.__api_version}.pickle'

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                return pickle.load(token)
        return None


    def __refresh_credentials(self, cred):
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.__client_secret_file, self.__scopes)
            cred = flow.run_local_server()

        with open(f'token_{self.__api_name}_{self.__api_version}.pickle', 'wb') as token:
            pickle.dump(cred, token)
        return cred


    def create_folders(self, folders: List[str], parent_id: str = None):
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



    def check_folder_exists(self, folder_name: str, parent_id: str = None) -> bool:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"

        response = self.__service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()

        for file in response.get('files', []):
            if file.get('name') == folder_name:
                return True  # Folder exists

        return False

    
    
    def __create_nested_zip(self, metadata: dict) -> BytesIO:
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
        nested_zip_buf = BytesIO()

        # Create a zip file for the nested zip and add the BMP and PNG images to it
        with zipfile.ZipFile(nested_zip_buf, 'w', zipfile.ZIP_STORED) as nested_zip:
            nested_zip.writestr('image1.bmp', watermarked_image_buf.getvalue())
            nested_zip.writestr('image2.bmp', key_image_buf.getvalue())
            nested_zip.writestr('image3.bmp', block_position_buf.getvalue())

        # Reset buffer position to start
        nested_zip_buf.seek(0)
        return nested_zip_buf
    

    def __upload_single_image(self, parent_id: str, output_name: str, image_array: np.ndarray):
        print(f'[SYSTEM] Uploading image \'{output_name}\' to google drive')
        try:
            with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as image_temp:
                Image.fromarray(np.uint8(image_array)).save(image_temp, format='bmp')
                image_temp.seek(0)
                media = MediaFileUpload(image_temp.name, mimetype='image/bmp', resumable=True)
                file_metadata = {'name': f'{output_name}.bmp', 'parents': [parent_id]}
                return self.__service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        except Exception as e:
            print("[SYSTEM] Failed when upload single image")
            print('Error:', e)
        

    def __upload_zip(self, parent_id: str, watermarked_image: np.ndarray, key_image: np.ndarray, block_position: np.ndarray):
        print(f'[SYSTEM] Uploading zip to google drive')
        try:
            metadata = {
                'file1': {
                    'file_name':'watermarked_image',
                    'image':watermarked_image
                },
                'file2': {
                    'file_name':'key_image',
                    'image':key_image
                },
                'file3': {
                    'file_name':'block_position',
                    'image':block_position
                }
                
            }
            # Create nested zip containing 3 images
            nested_zip_buf = self.__create_nested_zip(metadata=metadata)
            # Reset nested zip buffer position to start
            nested_zip_buf.seek(0)
            

            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as zip_temp:
                zip_temp.write(nested_zip_buf.getvalue())
                zip_temp.seek(0)
                media4 = MediaFileUpload(zip_temp.name, mimetype='application/zip', resumable=True)
                file4_metadata = {'name': 'embedding.zip', 'parents': [parent_id]}
                return self.__service.files().create(body=file4_metadata, media_body=media4, fields='id').execute()
        except Exception as e:
            print("[SYSTEM] Failed when upload a zip file")
            print('Error:', e)
            

    def upload_mixed_files(self, parent_id: str, watermarked_image: np.ndarray, key_image: np.ndarray, block_position: np.ndarray):
        try:
            responses = {}

            responses['watermarked_image'] = self.__upload_single_image(parent_id=parent_id, output_name='watermarked_image', image_array=watermarked_image.copy())
            responses['key_image'] = self.__upload_single_image(parent_id=parent_id, output_name='key_image', image_array=watermarked_image.copy())
            responses['block_position'] = self.__upload_single_image(parent_id=parent_id, output_name='block_position', image_array=watermarked_image.copy())

            responses['embedding_result_zip'] = self.__upload_zip(parent_id=parent_id, watermarked_image=watermarked_image.copy(), key_image=key_image.copy(), block_position=block_position.copy())

            print("Uploaded all files successfully")

            return responses
        except Exception as e:
            print("[SYSTEM] Failed to upload mixed files")
            print('Error:', e)

        

