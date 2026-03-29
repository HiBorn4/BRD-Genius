import os
from typing import Optional
from uuid import uuid4
import json
import config
import logging
import sys
import shutil

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s',  handlers=[logging.StreamHandler(sys.stdout)])

# Uncomment if you want GCS
from google.cloud import storage as gcs_storage
 
gcs_bucket = config.gcs_bucket_name

class FileStorageManager:
 
    def __init__(self, storage='local', base_path='app_files/middleware/', gcs_bucket_name=gcs_bucket):
        """
        Initializes FileStorageManager.
 
        Args:
            storage (str): either 'local' or 'gcs'
            base_path (str): directory path for local storage
            gcs_bucket_name (str): GCS bucket name if GCS is used
        """
        self.storage = storage
        self.base_path = base_path
        self.gcs_bucket_name = gcs_bucket_name
        
 
        if self.storage == 'gcs' and gcs_bucket_name:
            # Uncomment if GCS
            self.client = gcs_storage.Client()
            self.bucket = self.client.bucket(gcs_bucket_name)
            pass
 
    def _generate_file_path(self, user_id: str, unique_id: str,filename: str) -> str:
        """Generates a standardized path for saving files."""
        return f"{user_id}/{unique_id}/{filename}"
    
    def _generate_directory_path(self, user_id: str, unique_id: str) -> str:
        """Generates a standardized directory path for saving files."""
        return f"{user_id}/{unique_id}"
 
    def save_file(self, user_id: str, unique_id: str,filename: str, content) -> str:
        """Save a file to local or GCS and return its path or GCS uri."""
        file_path = self._generate_file_path(user_id, unique_id,filename)
 
        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Handle str vs bytes gracefully
            if isinstance(content, str):
                mode = 'w'
                with open(full_path, mode, encoding='utf-8') as f:
                    f.write(content)
            elif isinstance(content, bytes):
                mode = 'wb'
                with open(full_path, mode) as f:
                    f.write(content)
            else:
                raise TypeError("Content must be a str or bytes")
 
            return full_path
        elif self.storage == 'gcs':
            # Uncomment if GCS
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(content)
            return f"{file_path}"
            return f"gs://{self.gcs_bucket_name}/{file_path}"
            pass
    def save_json_file(self, user_id: str, unique_id: str,filename: str, content: Optional[dict]) -> str:
        """Save a JSON file to local or GCS and return its path or GCS uri."""
        if content is None:
            content = {}  # fallback to an empty object

        file_path = self._generate_file_path(user_id, unique_id,filename)

        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
            return full_path
        elif self.storage == 'gcs':
            # Uncomment if GCS
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(json.dumps(content), content_type='application/json')
            return f"{file_path}"
            return f"gs://{self.gcs_bucket_name}/{file_path}"
        
 
    def read_file(self, user_id: str, unique_id: str,filename: str) -> Optional[bytes]:
        """Read a file from local or GCS."""
        file_path = self._generate_file_path(user_id, unique_id,filename)
 
        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    return f.read()
            return None
        elif self.storage == 'gcs':
            # Uncomment if GCS
            blob = self.bucket.blob(file_path)
            return blob.download_as_bytes()
            pass
    def read_json_file(self, user_id: str, unique_id: str,filename: str) -> Optional[dict]:
        """Read a JSON file from local or GCS safely."""
        file_path = self._generate_file_path(user_id, unique_id,filename)

        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    return {}  # fallback to empty
            return {}
        elif self.storage == 'gcs':
            # Uncomment if GCS
            blob = self.bucket.blob(file_path)
            if blob.exists():
                try:
                    return json.loads(blob.download_as_text()) or {}
                except json.JSONDecodeError:
                    return {}
            return {}
        return {}
 
 
    def list_files(self, user_id: str, unique_id: str) -> list:
        """List files under a directory/user/uniqueId."""
        directory = os.path.join(self.base_path, user_id, unique_id)
        if os.path.exists(directory) and os.path.isdir(directory):
            return os.listdir(directory)
        return []
    
    def delete_file(self, user_id: str, unique_id: str, filename: str) -> bool:
        """Delete a file from local or GCS."""
        file_path = self._generate_file_path(user_id, unique_id, filename)

        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        elif self.storage == 'gcs':
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.delete()
                return True
            return False
        return False
    
    def read_file_from_path(self, path:str, os_path) -> Optional[bytes]:
        """Read a file from local or GCS."""
        file_path = path
        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    return f.read()
            return None
        elif self.storage == 'gcs':
            # Uncomment if GCS
            blob = self.bucket.blob(file_path)
            if blob.exists():
                logging.info("Sucessfully took file from GCS: %s", file_path)
            else:
                logging.info("File does not exist in GCS: %s", file_path)
            return blob.download_to_filename(os_path)
            pass

    def delete_file_from_path(self, path) -> bool:
        """Delete a file from local or GCS."""
        file_path = path
        if self.storage == 'local':
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        elif self.storage == 'gcs':
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.delete()
                return True
            return False
        return False
    
    def delete_session(self, user_id: str, unique_id: str) -> bool:
        """
        Delete a session directory from local storage or all GCS blobs under a prefix.
        Returns True if deleted, False if not found.
        """
        try:
            file_path = self._generate_directory_path(user_id, unique_id)

            if self.storage == 'local':
                full_path = os.path.join(self.base_path, file_path)
                if os.path.exists(full_path):
                    shutil.rmtree(full_path)
                    return True
                return False

            elif self.storage == 'gcs':
                blobs = list(self.bucket.list_blobs(prefix=file_path))
                if not blobs:
                    return False
                for blob in blobs:
                    blob.delete()
                return True

            return False
        except Exception as e:
            logging.error(f"Failed to delete session for {user_id} - {unique_id}: {e}")
            raise

# ------------------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Local example
    manager = FileStorageManager(storage='local')
    user_id = "25021807"
    unique_id = str(uuid4())    
 
    # Save a text file
    text_file = "example.txt"
    text_content = b"Hello, world!"
    manager.save_file(user_id, unique_id, text_file, text_content)
 
    # List files
    files = manager.list_files(user_id, unique_id)
    print("Files for this directory:")
    print(files)
 
    # Retrieve a file
    retrieved = manager.read_file(user_id, unique_id, text_file)
    print("Retrieved content:")
    print(retrieved.decode("utf-8"))