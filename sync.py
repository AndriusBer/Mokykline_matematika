import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

folder_id = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
creds_raw = os.environ.get("GDRIVE_CREDENTIALS", "").strip()

print(f"--> Pradedama sinchronizacija i aplanka: {folder_id}")

creds_dict = json.loads(creds_raw)
creds = service_account.Credentials.from_service_account_info(
    creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)

# Aplanku talpykla (cache), kad nekurtume dublikatu
folder_cache = {".": folder_id}

def get_or_create_drive_folder(local_folder_path, parent_id, folder_name):
    if local_folder_path in folder_cache:
        return folder_cache[local_folder_path]

    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = res.get("files", [])

    if files:
        target_id = files[0]["id"]
    else:
        meta = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }
        f = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
        target_id = f["id"]
        print(f"[Aplankas sukurtas] {local_folder_path}")

    folder_cache[local_folder_path] = target_id
    return target_id

# Apeiname visus failus ir poaplankius
uploaded_count = 0
for root, dirs, files in os.walk("."):
    # Praleisti pasleptas direktorijas (.git, .github)
    dirs[:] = [d for d in dirs if not d.startswith(".")]

    # Nustatome Google Drive aplanka siai vietai
    if root == ".":
        current_parent_id = folder_id
    else:
        parent_dir = os.path.dirname(root)
        dir_name = os.path.basename(root)
        parent_gdrive_id = folder_cache.get(parent_dir, folder_id)
        current_parent_id = get_or_create_drive_folder(root, parent_gdrive_id, dir_name)

    # Keliame failus
    for filename in files:
        if filename.startswith(".") or filename in ["sync.py", "service_account.json"]:
            continue

        local_path = os.path.join(root, filename)
        print(f"Keliamas failas: {local_path}")

        # Tikriname, ar jau yra toks failas siame aplanke
        q = f"'{current_parent_id}' in parents and name='{filename}' and trashed=false"
        existing = service.files().list(q=q, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get("files", [])

        media = MediaFileUpload(local_path, resumable=True)
        if existing:
            service.files().update(fileId=existing[0]["id"], media_body=media, supportsAllDrives=True).execute()
            print(f" -> Atnaujintas: {local_path}")
        else:
            meta = {"name": filename, "parents": [current_parent_id]}
            service.files().create(body=meta, media_body=media, supportsAllDrives=True).execute()
            print(f" -> Ikeltas: {local_path}")

        uploaded_count += 1

print(f"--> PABAIGA! Is viso sinchronizuota failu: {uploaded_count}")
