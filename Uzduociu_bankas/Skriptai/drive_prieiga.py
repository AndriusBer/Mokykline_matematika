#!/usr/bin/env python3
"""Patikrina ar parengia vieno banko PDF Drive prieigą, naudodamas rclone OAuth."""
import argparse
import configparser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

BANKAS = Path(__file__).resolve().parents[1]
ID_PATTERN = re.compile(r"U[0-9]{6}")
DRIVE_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
BASE = "https://www.googleapis.com/drive/v3/"
FILE_FIELDS = ("id,name,mimeType,trashed,capabilities(canShare,"
               "canChangeItemDownloadRestriction),downloadRestrictions("
               "itemDownloadRestriction(restrictedForReaders,restrictedForWriters),"
               "effectiveDownloadRestrictionWithContext(restrictedForReaders,restrictedForWriters))")
PERMISSION_FIELDS = "nextPageToken,permissions(id,type,role,allowFileDiscovery,permissionDetails(inherited))"


class PatikrosKlaida(Exception):
    pass


def parinkti_failus(rows, registry, target):
    if not isinstance(rows, list) or not isinstance(registry, dict):
        raise PatikrosKlaida("Netinkamas lsjson arba registro formatas")
    found = {}
    seen_drive_ids = set()
    path_re = re.compile(r"Uzduociu_bankas/Uzdaviniai/(U[0-9]{6})/(U[0-9]{6})\.pdf")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("Path"), str):
            raise PatikrosKlaida("Netinkamas lsjson įrašas")
        match = path_re.fullmatch(row["Path"])
        if not match:
            continue
        task, filename = match.groups()
        if task != filename:
            raise PatikrosKlaida(f"Nesutampa katalogo ir failo ID: {row['Path']}")
        if target != "visi" and task != target:
            continue
        drive_id = row.get("ID")
        if row.get("IsDir") is not False or not isinstance(drive_id, str) or not DRIVE_ID_PATTERN.fullmatch(drive_id):
            raise PatikrosKlaida(f"Netinkamas PDF arba Drive ID: {task}")
        if task in found or drive_id in seen_drive_ids:
            raise PatikrosKlaida(f"Pasikartojantis kelias arba Drive ID: {task}")
        saved = registry.get(task)
        if not isinstance(saved, dict) or saved.get("drive_id") != drive_id:
            raise PatikrosKlaida(f"Registro Drive ID nesutampa arba jo trūksta: {task}")
        if saved.get("url") != f"https://drive.google.com/file/d/{drive_id}/view":
            raise PatikrosKlaida(f"Netinkama registro nuoroda: {task}")
        found[task] = drive_id
        seen_drive_ids.add(drive_id)
    if target != "visi" and target not in found:
        raise PatikrosKlaida(f"Nerastas vienareikšmis Drive PDF: {target}")
    if not found:
        raise PatikrosKlaida("Nerasta uždavinių PDF")
    if target == "visi":
        missing = sorted(set(registry) - set(found))
        if missing:
            raise PatikrosKlaida(f"Drive sąraše trūksta registro uždavinių: {', '.join(missing)}")
    return dict(sorted(found.items()))


class DriveAPI:
    def __init__(self, token):
        self.token = token

    def request(self, method, path, params=None, data=None):
        query = urllib.parse.urlencode(params or {})
        url = BASE + path + ("?" + query if query else "")
        payload = None if data is None else json.dumps(data).encode("utf-8")
        request = urllib.request.Request(url, data=payload, method=method,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise PatikrosKlaida(f"Drive API atsakė HTTP {error.code} ({method}); duomenys nespausdinami") from None
        except (urllib.error.URLError, OSError, ValueError):
            raise PatikrosKlaida("Nepavyko pasiekti Drive API arba perskaityti atsakymo") from None

    def file(self, file_id):
        return self.request("GET", f"files/{file_id}",
                            {"fields": FILE_FIELDS, "supportsAllDrives": "true"})

    def permissions(self, file_id):
        permissions = []
        page = None
        seen_pages = set()
        while True:
            params = {"fields": PERMISSION_FIELDS, "pageSize": 100, "supportsAllDrives": "true"}
            if page:
                params["pageToken"] = page
            result = self.request("GET", f"files/{file_id}/permissions", params)
            page_permissions = result.get("permissions")
            if not isinstance(page_permissions, list) or not all(isinstance(p, dict) for p in page_permissions):
                raise PatikrosKlaida("Gautas nepilnas arba netinkamas Drive teisių sąrašas")
            permissions.extend(page_permissions)
            page = result.get("nextPageToken")
            if not page:
                return permissions
            if page in seen_pages:
                raise PatikrosKlaida("Pasikartojantis Drive teisių puslapio žymeklis")
            seen_pages.add(page)

    def restrict(self, file_id):
        return self.request("PATCH", f"files/{file_id}",
            {"fields": "id", "supportsAllDrives": "true"},
            {"downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": True}}})

    def create_permission(self, file_id):
        return self.request("POST", f"files/{file_id}/permissions",
            {"fields": "id", "supportsAllDrives": "true"},
            {"type": "anyone", "role": "reader", "allowFileDiscovery": False})

    def update_permission(self, file_id, permission_id):
        return self.request("PATCH", f"files/{file_id}/permissions/{permission_id}",
            {"fields": "id", "supportsAllDrives": "true"},
            {"role": "reader", "allowFileDiscovery": False})


def read_state(api, task, file_id):
    file = api.file(file_id)
    if (file.get("id") != file_id or file.get("name") != task + ".pdf"
            or file.get("mimeType") != "application/pdf" or file.get("trashed") is not False):
        raise PatikrosKlaida(f"Drive failo metaduomenys neatitinka registro: {task}")
    permissions = api.permissions(file_id)
    anyone = [p for p in permissions if p.get("type") == "anyone"]
    if len(anyone) > 1:
        raise PatikrosKlaida(f"Rasta daugiau nei viena anyone teisė: {task}")
    permission = anyone[0] if anyone else None
    if permission and not isinstance(permission.get("id"), str):
        raise PatikrosKlaida(f"Nėra anyone teisės ID: {task}")
    restriction = file.get("downloadRestrictions", {}).get("itemDownloadRestriction", {})
    return file, permission, restriction.get("restrictedForReaders") is True


def permission_ok(permission):
    return bool(permission and permission.get("role") == "reader"
                and permission.get("allowFileDiscovery") is False)


def plan(api, task, file_id):
    file, permission, restricted = read_state(api, task, file_id)
    capability = file.get("capabilities", {})
    if not restricted and capability.get("canChangeItemDownloadRestriction") is not True:
        raise PatikrosKlaida(f"Negalima keisti atsisiuntimo apribojimo: {task}")
    if not permission_ok(permission) and capability.get("canShare") is not True:
        raise PatikrosKlaida(f"Negalima keisti bendrinimo: {task}")
    if permission and not permission_ok(permission):
        if any(d.get("inherited") is True for d in permission.get("permissionDetails", [])):
            raise PatikrosKlaida(f"Netinkama anyone teisė paveldėta; keisti automatiškai negalima: {task}")
        if not DRIVE_ID_PATTERN.fullmatch(permission["id"]):
            raise PatikrosKlaida(f"Netinkamas teisės ID: {task}")
    return permission, restricted


def process(api, task, file_id, apply, verify=False):
    if verify:
        _, permission, restricted = read_state(api, task, file_id)
        if not restricted or not permission_ok(permission):
            raise PatikrosKlaida(f"Drive teisės arba apribojimas neatitinka reikalavimų: {task}")
        print(f"{task}: patvirtinta anyone reader teisė ir skaitytojų apribojimas")
        return
    permission, restricted = plan(api, task, file_id)
    if not apply:
        print(f"{task}: apribojimas={'yra' if restricted else 'reikalingas'}, "
              f"anyone reader={'yra' if permission_ok(permission) else 'reikalinga'}")
        return
    if not restricted:
        api.restrict(file_id)
        _, permission, restricted = read_state(api, task, file_id)
        if not restricted:
            raise PatikrosKlaida(f"Nepavyko patvirtinti PDF apribojimo: {task}")
        # Kita sistema galėjo pakeisti teises, kol buvo nustatomas apribojimas.
        permission, restricted = plan(api, task, file_id)
        if not restricted:
            raise PatikrosKlaida(f"Apribojimas pasikeitė prieš bendrinimą: {task}")
    if not permission_ok(permission):
        if permission:
            api.update_permission(file_id, permission["id"])
        else:
            api.create_permission(file_id)
    _, verified_permission, verified_restriction = read_state(api, task, file_id)
    if not verified_restriction or not permission_ok(verified_permission):
        raise PatikrosKlaida(f"Nepavyko patvirtinti galutinės Drive būsenos: {task}")
    print(f"{task}: patvirtinta anyone reader teisė ir skaitytojų apribojimas")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--id", default=None, help="Uždavinio ID; numatytasis U000001")
    group.add_argument("--visi", action="store_true", help="Tik skaitymui patikrinti visus PDF")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Taikyti pakeitimus tik U000001 arba U000002")
    mode.add_argument("--verify", action="store_true", help="Tik patvirtinti jau nustatytas teises")
    args = parser.parse_args()
    target = "visi" if args.visi else (args.id or "U000001")
    if target != "visi" and not ID_PATTERN.fullmatch(target):
        parser.error("ID turi būti U ir šeši skaitmenys")
    if args.apply and target not in {"U000001", "U000002"}:
        parser.error("Taikymas leidžiamas tik U000001 arba U000002")
    try:
        token = os.environ.get("RCLONE_CONFIG_GDRIVE_TOKEN")
        root_id = os.environ.get("RCLONE_CONFIG_GDRIVE_ROOT_FOLDER_ID")
        if not token or not root_id:
            raise PatikrosKlaida("Nėra esamo rclone tokeno arba šakninio aplanko aplinkos kintamojo")
        if os.environ.get("RCLONE_CONFIG_GDRIVE_SCOPE") != "drive":
            raise PatikrosKlaida("Reikalinga esama rclone scope=drive konfigūracija")
        token_data = json.loads(token)
        if not isinstance(token_data, dict) or not isinstance(token_data.get("access_token"), str):
            raise PatikrosKlaida("Netinkamas rclone OAuth tokeno formatas")
        with tempfile.TemporaryDirectory(prefix="drive-prieiga-") as directory:
            config_path = Path(directory) / "rclone.conf"
            cfg = configparser.ConfigParser(interpolation=None)
            cfg["gdrive"] = {"type": "drive", "scope": "drive", "root_folder_id": root_id, "token": token}
            # Jei esamas rclone remote naudoja individualų OAuth klientą, perduodame jo esamas reikšmes.
            for key in ("client_id", "client_secret"):
                value = os.environ.get("RCLONE_CONFIG_GDRIVE_" + key.upper())
                if value:
                    cfg["gdrive"][key] = value
            fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                cfg.write(f)
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("RCLONE_CONFIG_GDRIVE_")}
            env["RCLONE_CONFIG"] = str(config_path)
            pattern = (f"/Uzduociu_bankas/Uzdaviniai/{target}/{target}.pdf"
                       if target != "visi" else "/Uzduociu_bankas/Uzdaviniai/**")
            result = subprocess.run(["rclone", "lsjson", "gdrive:", "--recursive", "--files-only",
                                     "--include", pattern], env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode:
                raise PatikrosKlaida("rclone lsjson nepavyko; patikrinkite autentifikaciją ir prieigą")
            rows = json.loads(result.stdout)
            with (BANKAS / "drive_links.json").open(encoding="utf-8") as f:
                registry = json.load(f)
            tasks = parinkti_failus(rows, registry, target)
            cfg.read(config_path, encoding="utf-8")
            token_data = json.loads(cfg["gdrive"]["token"])
            api = DriveAPI(token_data["access_token"])
            # Failo metaduomenų GET ir teisių GET patikrina gyvą Drive API prieigą.
            for task, file_id in tasks.items():
                process(api, task, file_id, args.apply, args.verify)
    except (PatikrosKlaida, OSError) as error:
        parser.exit(1, f"Klaida: {error}\n")
    except (ValueError, KeyError, configparser.Error):
        parser.exit(1, "Klaida: netinkamas autentifikacijos arba JSON duomenų formatas\n")


if __name__ == "__main__":
    main()
