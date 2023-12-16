from drive_service import DriveApiService
import cv2

CLIENT_SECRET_PATH = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
ROOT_FOLDER = '1msOd9fbC2aXIcEQli29L_9C1RRHoL1XB'

driverApiService = DriveApiService(client_secret_path=CLIENT_SECRET_PATH, api_name=API_NAME, api_version=API_VERSION, scopes=SCOPES, root_folder=ROOT_FOLDER)

# driverApiService.create_folders(['1', '2'], parent_id='1oDJ1MSPi845nhl6g9LHZW7QA3GhRIs6S')

# print(driverApiService.check_folder_exists('najibfikri131@gmail.com', parent_id='1msOd9fbC2aXIcEQli29L_9C1RRHoL1XB'))

lenna = cv2.imread('./assets/host-lenna.bmp',0)
man = cv2.imread('./assets/host-man.bmp',0)
block_position = cv2.imread('./assets/host-pepper.bmp',0)


driverApiService.upload_mixed_files(parent_id='1bXXW6rBGilJtxycNcVflSHCTxdw7a4sY', watermarked_image=lenna.copy(), key_image=man.copy(), block_position=block_position.copy())

