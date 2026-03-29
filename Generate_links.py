import os
import json
from google.cloud import storage

# Folder where your PDF files are saved
folder_path = r"C:\Users\HP\Desktop\a\a"

# Base URL
base_url = "https://work.mahindra.com/ui-assist/v1/meconnect/download"

# Dictionary to store filename: URL mapping
file_url_map = {}

# Loop through PDF files and generate full URLs
for file_name in os.listdir(folder_path):
    if file_name.lower().endswith(".pdf"):
        # Replace double underscores with space in the URL
        modified_file_name = file_name.replace("__", " ")
        
        # Replace all spaces in the filename (key) with underscore
        key_name = file_name.replace(" ", "_")

        # Construct full URL
        full_url = f"{base_url}/{modified_file_name}"

        # Add to dictionary
        file_url_map[key_name] = full_url

        # Print output for confirmation
        print(f'"{key_name}": "{full_url}"')

# Save the mapping as a JSON file
local_filename = "policy_mapping.json"
with open(local_filename, "w", encoding="utf-8") as f:
    json.dump(file_url_map, f, indent=4)
print("✅ JSON saved locally as policy_mapping.json.")

# Upload to GCS
def upload_to_gcs(bucket_name, source_file, destination_blob_name):
    client = storage.Client()  # Requires GOOGLE_APPLICATION_CREDENTIALS to be set
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file)
    print(f"✅ Uploaded to GCS: gs://{bucket_name}/{destination_blob_name}")

# Trigger upload
upload_to_gcs("gcs--data--", local_filename, "policy_mapping.json")
