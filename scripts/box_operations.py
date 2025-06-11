import io
import os
from dotenv import load_dotenv
from boxsdk import OAuth2, Client
from boxsdk.exception import BoxAPIException

# Load environment variables from .env file
load_dotenv()

# Box OAuth2 Authentication Details
BOX_CLIENT_ID = os.getenv('BOX_CLIENT_ID')
BOX_CLIENT_SECRET = os.getenv('BOX_CLIENT_SECRET')
BOX_REFRESH_TOKEN = os.getenv('BOX_REFRESH_TOKEN')

# Box Folder IDs
BOX_DOWNLOAD_FOLDER_ID = os.getenv('BOX_DOWNLOAD_FOLDER_ID')
BOX_UPLOAD_FOLDER_ID = os.getenv('BOX_UPLOAD_FOLDER_ID')

# Source data directory
SOURCE_DATA_DIR = os.getenv('SOURCE_DATA_DIR')

# Function to store tokens (required by Box SDK's OAuth2 for automatic refresh)
# This function is called by the Box SDK when tokens are refreshed.
# For simplicity in this script, we'll just acknowledge the refresh.
# In a robust production setup, you might want to write the new refresh_token
# back to a persistent, secure storage (like your .env file or a database)
# if you find the refresh token itself eventually expires or changes,
# though Box refresh tokens are typically long-lived.
def store_tokens(access_token, refresh_token):
    pass # The SDK internally uses the refreshed tokens. We don't need to save it back to .env every time.


def get_box_client():
    """
    Authenticates with Box using OAuth2 with Refresh Tokens and returns a Box client.
    The access token will be automatically refreshed by the SDK using the refresh token.
    """
    if not all([BOX_CLIENT_ID, BOX_CLIENT_SECRET, BOX_REFRESH_TOKEN]):
        print("ERROR: One or more required Box OAuth2 environment variables (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) are missing from .env.")
        print("Ensure BOX_CLIENT_ID, BOX_CLIENT_SECRET are set from your Box App config, and BOX_REFRESH_TOKEN is obtained via get_box_tokens.py.")
        return None

    try:
        oauth = OAuth2(
            client_id=BOX_CLIENT_ID,
            client_secret=BOX_CLIENT_SECRET,
            access_token=None,  # Will be obtained using refresh token
            refresh_token=BOX_REFRESH_TOKEN, # Use the stored refresh token from .env
            store_tokens=store_tokens, # Pass the callback function for token refresh
        )
        # The SDK will automatically use the refresh token to get a new access token here
        return Client(oauth)
    except Exception as e:
        print(f"Error authenticating with Box using OAuth2 Refresh Token: {e}")
        print("Possible causes: Invalid BOX_CLIENT_ID, BOX_CLIENT_SECRET, or expired/invalid BOX_REFRESH_TOKEN.")
        print("If BOX_REFRESH_TOKEN is invalid, re-run get_box_tokens.py to get a new one.")
        return None

def download_box_files(folder_id, target_dir, file_prefix_filter=None):
    """
    Downloads files from a specified Box folder to a local directory.

    Args:
        folder_id (str): The ID of the Box folder to download from.
        target_dir (str): The local directory to save the files to.
        file_prefix_filter (str, optional): If provided, only files whose names
                                            start with this prefix will be downloaded.
    Returns:
        list: A list of names of the successfully downloaded files.
    """
    client = get_box_client()
    if client is None:
        return []

    try:
        folder = client.folder(folder_id).get()
        print(f"Accessing Box folder '{folder.name}' (ID: {folder_id})...")
    except BoxAPIException as e:
        print(f"ERROR: Box API access failed for folder ID {folder_id}: {e.status} - {e.message}")
        if e.status == 404:
            print("Please ensure the folder ID is correct and the Box application has access.")
        elif e.status == 401:
            print("Authentication error. Please check your Box OAuth2 credentials and application authorization.")
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

def upload_file_to_box(folder_id, file_path):
    """
    Uploads a local file to a specified Box folder.

    Args:
        folder_id (str): The ID of the Box folder to upload to.
        file_path (str): The local path of the file to upload.

    Returns:
        boxsdk.object.file.File or None: The uploaded Box File object, or None if failed.
    """
    client = get_box_client()
    if client is None:
        return None

    if not os.path.exists(file_path):
        print(f"ERROR: Local file not found for upload: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    try:
        folder = client.folder(folder_id).get() # Get the folder object to use .upload()
        uploaded_file = folder.upload(file_path, file_name=file_name)
        print(f"Uploaded file '{file_name}' to Box folder '{folder.name}' (ID: {folder_id}) with file ID: {uploaded_file.id}")
        return uploaded_file
    except BoxAPIException as e:
        print(f"ERROR: Box API upload failed for file '{file_name}' to folder ID {folder_id}: {e.status} - {e.message}")
        if e.status == 404:
            print("Please ensure the upload folder ID is correct and exists.")
        elif e.status == 403:
            print("Permission denied. Please check your Box application's permissions for write access.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during upload of '{file_name}': {e}")
        return None

if __name__ == "__main__":
    # Ensure SOURCE_DATA_DIR is created if it doesn't exist
    os.makedirs(SOURCE_DATA_DIR, exist_ok=True)

    print("\n--- Attempting to download cleaned CSV files from Box using OAuth2 Refresh Token ---")
    download_box_files(
        folder_id=BOX_DOWNLOAD_FOLDER_ID,
        target_dir=SOURCE_DATA_DIR,
        file_prefix_filter='cleaned_'
    )

    # Example of uploading a file (you might generate a cleaned CSV or analysis result)
    # Be sure to have a file at 'data/Cleaned_Data/some_result.csv' for this to work
    # if os.path.exists('data/Cleaned_Data/some_result.csv'):
    #     print("\n--- Attempting to upload a sample result file to Box using OAuth2 ---")
    #     upload_file_to_box(
    #         folder_id=BOX_UPLOAD_FOLDER_ID,
    #         file_path='data/Cleaned_Data/some_result.csv'
    #     )
    # else:
    #     print("\nSkipping sample upload: 'data/Cleaned_Data/some_result.csv' not found.")
