import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = os.environ["GDRIVE_FOLDER_ID"]
creds_dict = json.loads(os.environ["GDRIVE_CREDENTIALS"])
creds = service_account.Credentials.from_service_account_info(
    creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)

# Gauname esamus failus aplanke
results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()
existing_files = {f["name"]: f["id"] for f in results.get("files", [])}

# Keliami tik pagrindiniai repozitorijos failai (ignoruojant paslėptus)
for filename in os.listdir("."):
    if filename.startswith(".") or os.path.isdir(filename) or filename == "sync.py":
        continue

    media = MediaFileUpload(filename, resumable=True)
    if filename in existing_files:
        service.files().update(fileId=existing_files[filename], media_body=media).execute()
        print(f"Atnaujintas: {filename}")
    else:
        file_metadata = {"name": filename, "parents": [FOLDER_ID]}
        service.files().create(body=file_metadata, media_body=media).execute()
        print(f"Įkeltas: {filename}")
