import os
import base64
import requests
import logging
from app_files.chatbot.file_manager import FileStorageManager
import config 

storage = config.storage_type

# --- Config ---
CLIENT_ID = os.getenv("AZURE_BOT_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_BOT_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_BOT_TENANT_ID")

# Validate environment variables
if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID]):
    logging.error("Missing one or more required environment variables: CLIENT_ID, CLIENT_SECRET, TENANT_ID")
    raise EnvironmentError("Missing required environment variables")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_API_ENDPOINT = config.graph_api_endpoint
SCOPES = config.azure_bot_scopes


def get_access_token_from_refresh_token(refresh_token: str) -> str | None:
    try:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(SCOPES)
        }

        response = requests.post(TOKEN_ENDPOINT, data=data)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            logging.error("No access token returned in response.")
            return "No access token returned in response."

        logging.info("Access token refreshed successfully.")
        return access_token

    except requests.RequestException as e:
        logging.error(f"Token refresh failed: {e}")
        if e.response:
            logging.error(f"Response body: {e.response.text}")
        return f"Response body: {e.response.text}"


def encode_sharing_url(url: str) -> str:
    base64_value = base64.b64encode(url.encode()).decode()
    return "u!" + base64_value.rstrip("=").replace("/", "_").replace("+", "-")


def download_and_save_video(access_token: str, sharing_url: str, user_id: str, unique_id: str, filename: str) -> str | None:
    try:
        encoded_url = encode_sharing_url(sharing_url)
        api_url = f"{GRAPH_API_ENDPOINT}/shares/{encoded_url}/driveItem"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get metadata and download URL
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        file_metadata = response.json()
        download_url = file_metadata.get("@microsoft.graph.downloadUrl")

        if not download_url:
            logging.error("Download URL not found in metadata.")
            return "Download URL not found in metadata."

        # Download content
        download_response = requests.get(download_url)
        download_response.raise_for_status()
        video_content = download_response.content

        # Save via FileStorageManager
        try:
            manager = FileStorageManager(storage)  # Change to 'gcs' if needed
            saved_path = manager.save_file(user_id=user_id, unique_id=unique_id, filename=filename, content=video_content)
            logging.info(f"File saved successfully: {saved_path}")
            return saved_path
        except Exception as fe:
            logging.error(f"Error saving file: {fe}")
            return f"Error saving file: {fe}"

    except requests.RequestException as e:
        logging.error(f"Video download failed: {e}")
        if e.response:
            logging.error(f"Response body: {e.response.text}")
        return f"Response body: {e.response.text}"
    except Exception as ex:
        logging.error(f"Unexpected error during download/save: {ex}")
        return f"Unexpected error during download/save: {ex}"


def download_meeting_video(user_id: str, unique_id: str, refresh_token: str, sharing_url: str, meet_name: str) -> str | None:
    if not refresh_token or not sharing_url or not user_id or not unique_id:
        logging.error("Missing required inputs: user_id, unique_id, refresh_token, or sharing_url.")
        return "Missing required inputs: user_id, unique_id, refresh_token, or sharing_url."

    access_token = get_access_token_from_refresh_token(refresh_token)
    if not access_token:
        logging.error("Could not get access token.")
        return "Could not get access token."

    return download_and_save_video(access_token, sharing_url, user_id, unique_id, meet_name)
