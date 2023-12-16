from drive_service import DriveApiService
import cv2

CLIENT_SECRET_PATH = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
ROOT_FOLDER = '1msOd9fbC2aXIcEQli29L_9C1RRHoL1XB'

driveApiService = DriveApiService(client_secret_path=CLIENT_SECRET_PATH, api_name=API_NAME, api_version=API_VERSION, scopes=SCOPES, root_folder=ROOT_FOLDER)

# driveApiService.createFolders(['1', '2'], parent_id='1oDJ1MSPi845nhl6g9LHZW7QA3GhRIs6S')

# print(driveApiService.checkFolderExists('najibfikri131@gmail.com', parent_id='1msOd9fbC2aXIcEQli29L_9C1RRHoL1XB'))

lenna = cv2.imread('./assets/host-lenna.bmp',0)
man = cv2.imread('./assets/host-man.bmp',0)
block_position = cv2.imread('./assets/host-pepper.bmp',0)


# driveApiService.uploadMixedFiles(parent_id='1HIeIAyfXvo9EJGJ9XnM-cQefeMdTtkXK', watermarked_image=lenna.copy(), key_image=man.copy(), block_position=block_position.copy(), email='najibfikri13@gmail.com')

files_in_folder = driveApiService.getFilesInFolder(folder_id='1HIeIAyfXvo9EJGJ9XnM-cQefeMdTtkXK')

for file in files_in_folder:
    web_view_link, download_link = driveApiService.getFileLinks(file_id=file['id'])

    print(f"File Name: {file['name']}, ID: {file['id']}")
    print(f"Web View Link: {web_view_link}")
    print(f"Download Link: {download_link}")
    print('-'*100)

