
import io
import os
from dotenv import load_dotenv
from boxsdk import OAuth2, Client
from boxsdk.exception import BoxAPIException 

load_dotenv() 

BOX_CLIENT_ID = os.getenv('BOX_CLIENT_ID')
BOX_CLIENT_SECRET = os.getenv('BOX_CLIENT_SECRET')
BOX_DEVELOPER_TOKEN_DOWNLOAD = os.getenv('BOX_DEVELOPER_TOKEN_DOWNLOAD')
BOX_DEVELOPER_TOKEN_UPLOAD = os.getenv('BOX_DEVELOPER_TOKEN_UPLOAD')

def get_box_client(token):

    if not BOX_CLIENT_ID or not BOX_CLIENT_SECRET or not token:
        print("ERROR: Box Client ID, Client Secret, or Token is missing from .env. Please check your .env file.")
        return None
    try:
        auth = OAuth2(BOX_CLIENT_ID, BOX_CLIENT_SECRET, access_token=token)
        return Client(auth)
    except Exception as e:
        print(f"Error authenticating with Box: {e}")
        return None

def download_box_files(folder_id, target_dir, token, file_prefix_filter=None):
   
    client = get_box_client(token)
    if client is None:
        return []

    try:
        folder = client.folder(folder_id).get()
        print(f"Accessing Box folder '{folder.name}' (ID: {folder_id})...")
    except BoxAPIException as e:
        print(f"ERROR: Box API access failed for folder ID {folder_id}: {e.status} - {e.message}")
        if e.status == 404:
            print("Please ensure the folder ID is correct and the token has access.")
        elif e.status == 401:
            print("Authentication error. Please check your BOX_DEVELOPER_TOKEN_DOWNLOAD in .env.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while accessing Box folder ID {folder_id}: {e}")
        return []

    os.makedirs(target_dir, exist_ok=True)
    downloaded_files = []

    print(f"Checking files in Box folder '{folder.name}'...")
    for file_item in folder.get_items():
        if file_item.type == 'file':
            if file_prefix_filter and not file_item.name.startswith(file_prefix_filter):
                print(f"Skipping: {file_item.name} (does not start with '{file_prefix_filter}')")
                continue 

            print(f"Downloading: {file_item.name}")
            try:
                file_content = io.BytesIO()
                file_item.download_to(file_content)

                file_path = os.path.join(target_dir, file_item.name)
                with open(file_path, 'wb') as f:
                    f.write(file_content.getbuffer())
                downloaded_files.append(file_item.name)
            except Exception as e:
                print(f"ERROR: Failed to download {file_item.name}: {e}")
                continue
    print(f"Downloaded files: {downloaded_files}")
    return downloaded_files

def upload_file_to_box(folder_id, file_path, token):
  
    client = get_box_client(token)
    if client is None:
        return None

    if not os.path.exists(file_path):
        print(f"ERROR: Local file not found for upload: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    try:
        folder = client.folder(folder_id) 
        uploaded_file = folder.upload(file_path, file_name=file_name)
        print(f"Uploaded file '{file_name}' to Box folder '{folder_id}' with file ID: {uploaded_file.id}")
        return uploaded_file
    except BoxAPIException as e:
        print(f"ERROR: Box API upload failed for file '{file_name}' to folder ID {folder_id}: {e.status} - {e.message}")
        if e.status == 404:
            print("Please ensure the upload folder ID is correct and exists.")
        elif e.status == 403:
            print("Permission denied. Please check your BOX_DEVELOPER_TOKEN_UPLOAD for write access.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload of '{file_name}': {e}")
        return None

if __name__ == "__main__":
    print("\n--- Attempting to download cleaned CSV files from Box ---")
    download_box_files(
        folder_id='315133614684', 
        target_dir='data/Source_Data',
        token=BOX_DEVELOPER_TOKEN_DOWNLOAD,
        file_prefix_filter='cleaned_' 
    )

    
    