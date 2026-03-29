import config
import firebase_admin
from firebase_admin import firestore, credentials
import uuid
import json
from datetime import datetime, timezone, timedelta

storage = config.storage_type
firestore_db = config.firestore_db

if (storage == 'gcs'):
    from google.cloud import secretmanager

    def access_secret_version(project_id, secret_id, version_id='1'):
        """
        Access a secret version from Google Cloud Secret Manager.
        """
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        # name="projects/568063304711/secrets/epod-icr-dev-399519_appspot/versions/1"
    
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    
    # ✅ Example usage with your real values:
    project_id = config.project_id  # Your Google Cloud project ID
    secret_id =  config.secret_id # This must match exactly what's in Secret Manager

    json_key = access_secret_version(project_id, secret_id)
    json_key_data = json.loads(json_key)

    if not firebase_admin._apps:
        cred = credentials.Certificate(json_key_data)
        firebase_admin.initialize_app(cred)

    db = firestore.client(database_id = config.database_id)

elif (storage == 'local'):
    cred = credentials.Certificate("brd001-firebase-adminsdk-fbsvc-20e67bbc71.json")
    firebase_admin.initialize_app(cred)

    db = firestore.client()


def create_entry(user_id: str, file_name: str) -> bool:
    """
    Create or update a BRD entry with a new file under files array.
    If the document doesn't exist, it will create it first.
    """
    try:
        brd_ref = db.collection(firestore_db).document("BRD")

        brd = brd_ref.get()

        if brd.exists:
            brd_data = brd.to_dict()
        else:
            brd_data = {}

        if user_id not in brd_data:
            brd_data[user_id] = {"files": []}

        new_file = {"ID": str(uuid.uuid4()), "file": file_name}
        brd_data[user_id]["files"].append(new_file)

        brd_ref.set(brd_data)
        return new_file["ID"]
    except Exception as e:
        print(f"Error while adding entry for {user_id}: {e}")
        return False


def get_entry(user_id: str) -> dict:
    """
    Retrieve the entry for a particular userId.
    """
    try:
        brd_ref = db.collection(firestore_db).document("BRD")
        brd = brd_ref.get()

        if brd.exists:
            brd_data = brd.to_dict()
            return brd_data.get(user_id, {})
        return {}
    except Exception as e:
        print(f"Error while retrieving entry for {user_id}: {e}")
        return {}
   
def delete_entry(user_id: str, file_id: str) -> bool:
    """
    Delete a specific file entry by its unique ID for a given user.
    Returns True if deleted, False if not found or failed.
    """
    try:
        brd_ref = db.collection(firestore_db).document("BRD")
        brd = brd_ref.get()

        if not brd.exists:
            print(f"BRD document not found.")
            return False

        brd_data = brd.to_dict()

        if user_id not in brd_data:
            print(f"User {user_id} not found in BRD data.")
            return False

        files = brd_data[user_id].get("files", [])
        updated_files = [f for f in files if f["ID"] != file_id]

        if len(files) == len(updated_files):
            print(f"No file with ID {file_id} found for user {user_id}.")
            return False

        brd_data[user_id]["files"] = updated_files
        brd_ref.set(brd_data)
        print(f"Deleted file with ID {file_id} for user {user_id}")
        return True

    except Exception as e:
        print(f"Error deleting entry for {user_id}: {e}")
        return False
    
def store_user_token(user_id: str, access_token: str) -> None:
    """
    Stores or updates the access token and its creation date for a given user in Firestore.
    Token is stored under BRD_db/UserTokens as { user_id: { token, created_at } }
    """
    try:
        token_ref = db.collection(firestore_db).document("UserTokens")
        current_time = datetime.now(timezone.utc).isoformat()
        token_ref.set({
            user_id: {
                "access_token": access_token,
                "created_at": current_time
            }
        }, merge=True)
        print(f"Access token stored for {user_id}")
    except Exception as e:
        print(f"Error saving token for {user_id}: {e}")


def get_user_token(user_id: str) -> str | None:
    """
    Retrieves the access token for a given user from Firestore.
    Returns the token if it is not older than 60 days, else returns None.
    """
    try:
        token_ref = db.collection(firestore_db).document("UserTokens")
        token_doc = token_ref.get()

        if token_doc.exists:
            tokens = token_doc.to_dict()
            user_data = tokens.get(user_id)

            if not user_data:
                print(f"No token data found for user: {user_id}")
                return None

            access_token = user_data.get("access_token")
            created_at_str = user_data.get("created_at")

            if not created_at_str:
                print(f"Token creation date missing for user: {user_id}")
                return None

            created_at = datetime.fromisoformat(created_at_str)
            now = datetime.now(timezone.utc)
            if now - created_at > timedelta(days=60):
                print(f"Token expired for user: {user_id}")
                return None

            return access_token
        else:
            print(f"Token document not found for user: {user_id}")
            return None
    except Exception as e:
        print(f"Error retrieving token for {user_id}: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    user_id = "25000000"
    file_name = "example_file2.txt"

    # Create an entry
    entry_id = create_entry(user_id, file_name)
    print(f"Created entry with ID: {entry_id}")

    # Retrieve the entry
    entry = get_entry(user_id)
    print(f"Retrieved entry for {user_id}: {entry}")