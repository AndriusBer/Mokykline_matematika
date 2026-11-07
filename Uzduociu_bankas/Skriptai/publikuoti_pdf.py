#!/usr/bin/env python3
"""Kontroliuojamas uždavinių PDF publikavimas per rclone copy ir Drive API."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import drive_prieiga as drive

BANKAS = Path(__file__).resolve().parents[1]
ROOT = BANKAS.parent
REGISTRY = BANKAS / "drive_links.json"
CHECKPOINT = BANKAS / "drive_publication_state.json"
PATH_RE = re.compile(r"Uzduociu_bankas/Uzdaviniai/(U[0-9]{6})/(U[0-9]{6})\.pdf")
SHA_RE = re.compile(r"[0-9a-f]{40}")


class PublicationError(Exception):
    pass


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"Pasikartojantis JSON laukas: {key}")
        result[key] = value
    return result


def read_registry(path):
    with path.open(encoding="utf-8") as file:
        data = json.load(file, object_pairs_hook=unique_json)
    if not isinstance(data, dict):
        raise PublicationError("Registras turi būti JSON objektas")
    ids = set()
    for task, entry in data.items():
        if not drive.ID_PATTERN.fullmatch(task) or not isinstance(entry, dict):
            raise PublicationError(f"Netinkamas registro uždavinys: {task}")
        file_id = entry.get("drive_id")
        if not isinstance(file_id, str) or not drive.DRIVE_ID_PATTERN.fullmatch(file_id):
            raise PublicationError(f"Netinkamas Drive ID: {task}")
        if file_id in ids or entry.get("url") != f"https://drive.google.com/file/d/{file_id}/view":
            raise PublicationError(f"Pasikartojantis ID arba netinkamas URL: {task}")
        ids.add(file_id)
    return data


def local_files(root, only=None, selected=None):
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--",
                             "Uzduociu_bankas/Uzdaviniai"], check=True, stdout=subprocess.PIPE)
    found = {}
    for path in result.stdout.decode("utf-8").split("\0"):
        match = PATH_RE.fullmatch(path)
        if not match:
            continue
        task, filename = match.groups()
        if task != filename:
            raise PublicationError(f"Nesutampa katalogo ir PDF ID: {path}")
        if only and task != only:
            continue
        if selected is not None and task not in selected:
            continue
        file = root / path
        if file.is_symlink() or not file.is_file():
            raise PublicationError(f"Nerastas įprastas PDF failas: {path}")
        with file.open("rb") as stream:
            digest = hashlib.md5()  # noqa: S324 – Drive failų turinio atitikimui, ne saugai
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        found[task] = {"path": path, "md5": digest.hexdigest()}
    if not found:
        raise PublicationError("Nerasta pasirinktų Git sekamų uždavinių PDF")
    return dict(sorted(found.items()))


def read_checkpoint(path):
    with path.open(encoding="utf-8") as file:
        data = json.load(file, object_pairs_hook=unique_json)
    if not isinstance(data, dict) or set(data) != {"last_published_commit"}:
        raise PublicationError("Netinkamas publikavimo žymos formatas")
    sha = data["last_published_commit"]
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise PublicationError("Netinkamas publikavimo žymos commit SHA")
    return sha


def changed_files(root, checkpoint, target):
    """Grąžina nuo paskutinio patvirtinto commit naujus ir pakeistus PDF."""
    if not SHA_RE.fullmatch(checkpoint) or not SHA_RE.fullmatch(target):
        raise PublicationError("Netinkamas Git commit SHA")
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != target:
        raise PublicationError("Darbinis Git commit neatitinka tikslinio commit")
    ancestry = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", checkpoint, target],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ancestry.returncode != 0:
        raise PublicationError("Publikavimo žyma nėra tikslinio commit protėvis arba trūksta Git istorijos")
    raw = subprocess.check_output(["git", "-C", str(root), "diff", "--name-status", "-z",
                                   "--no-renames", "--diff-filter=AM", checkpoint, target,
                                   "--", "Uzduociu_bankas/Uzdaviniai"])
    fields = raw.decode("utf-8").split("\0")
    if fields[-1] != "" or len(fields[:-1]) % 2:
        raise PublicationError("Netinkamas Git pakeitimų sąrašas")
    changed = {}
    for status, path in zip(fields[0:-1:2], fields[1:-1:2]):
        match = PATH_RE.fullmatch(path)
        if not match:
            continue
        task, filename = match.groups()
        if task != filename:
            raise PublicationError(f"Nesutampa katalogo ir PDF ID: {path}")
        content = subprocess.check_output(["git", "-C", str(root), "show", f"{target}:{path}"])
        current = hashlib.md5(content).hexdigest()
        previous = None
        if status == "M":
            before = subprocess.check_output(["git", "-C", str(root), "show", f"{checkpoint}:{path}"])
            previous = hashlib.md5(before).hexdigest()
            if previous == current:
                continue
        elif status != "A":
            raise PublicationError(f"Netikėtas Git pakeitimo tipas: {status}")
        known = {current}
        if previous is not None:
            known.add(previous)
        commits = subprocess.check_output(["git", "-C", str(root), "log", "--format=%H",
                                           "--diff-filter=AM", f"{checkpoint}..{target}", "--", path], text=True)
        for commit in commits.splitlines():
            if not SHA_RE.fullmatch(commit):
                raise PublicationError("Netinkamas istorinio Git commit SHA")
            version = subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{path}"])
            known.add(hashlib.md5(version).hexdigest())
        changed[task] = {"path": path, "md5": current, "previous_md5": previous,
                         "known_md5": sorted(known)}
    return dict(sorted(changed.items()))


def remote_files(rows):
    if not isinstance(rows, list):
        raise PublicationError("Netinkamas rclone lsjson formatas")
    found, ids = {}, set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("Path"), str):
            raise PublicationError("Netinkamas rclone įrašas")
        match = PATH_RE.fullmatch(row["Path"])
        if not match:
            continue
        task, filename = match.groups()
        if task != filename:
            raise PublicationError(f"Nesutampa Drive katalogo ir failo ID: {row['Path']}")
        fid = row.get("ID")
        if row.get("IsDir") is not False or not isinstance(fid, str) or not drive.DRIVE_ID_PATTERN.fullmatch(fid):
            raise PublicationError(f"Netinkamas Drive failas arba ID: {task}")
        if task in found or fid in ids:
            raise PublicationError(f"Drive yra dubliuotų kelių arba ID: {task}")
        hashes = row.get("Hashes")
        if not isinstance(hashes, dict) or not ({"md5", "MD5"} & hashes.keys()):
            raise PublicationError(f"Trūksta Drive PDF MD5 kontrolinės sumos: {task}")
        values = [hashes[key] for key in ("md5", "MD5") if key in hashes]
        if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", value)
               for value in values):
            raise PublicationError(f"Netinkama Drive PDF MD5 kontrolinė suma: {task}")
        values = [value.lower() for value in values]
        if len(set(values)) != 1:
            raise PublicationError(f"Nesutampa Drive PDF MD5 kontrolinės sumos: {task}")
        md5 = values[0]
        found[task] = {"id": fid, "md5": md5}
        ids.add(fid)
    return found


def validate_existing(registry, remote):
    for task, entry in registry.items():
        if task not in remote or remote[task]["id"] != entry["drive_id"]:
            raise PublicationError(f"Trūksta įregistruoto PDF arba pasikeitė Drive ID: {task}")


def preflight(local, registry, backend, first_u000003=False, previous_md5=None):
    if first_u000003:
        if set(local) != {"U000003"}:
            raise PublicationError("Pirmojo bandymo režimas leidžiamas tik U000003")
        if "U000003" in registry:
            raise PublicationError("U000003 jau yra registre; pirmasis bandymas nutrauktas")
    before = remote_files(backend.list())
    validate_existing(registry, before)
    if first_u000003 and "U000003" in before:
        raise PublicationError("U000003 jau yra Drive; pirmasis bandymas nutrauktas")
    # Po nutrūkusio vykdymo neįregistruotą failą galima priimti tik esant tam pačiam turiniui.
    for task, local_file in local.items():
        if task in before and task not in registry and before[task]["md5"] != local_file["md5"]:
            raise PublicationError(f"Neįregistruoto Drive PDF turinys nesutampa: {task}")
        if task in before and task in registry and previous_md5 is not None:
            old_hash = previous_md5.get(task)
            allowed = set(old_hash) if isinstance(old_hash, (list, tuple, set)) else {old_hash}
            allowed.add(local_file["md5"])
            if old_hash is not None and before[task]["md5"] not in allowed:
                raise PublicationError(f"Drive PDF MD5 neatitinka ankstesnio ar naujo Git turinio: {task}")
        if task in before:
            backend.plan(task, before[task]["id"])
    return before


def preview(local, registry, backend, first_u000003=False):
    before = preflight(local, registry, backend, first_u000003)
    backend.copy([entry["path"] for entry in local.values()], dry_run=True)
    for task in local:
        if task in before:
            permission, restricted = backend.plan(task, before[task]["id"])
            content = "turinys sutampa" if before[task]["md5"] == local[task]["md5"] else "turinys skirtųsi"
            print(f"{task}: {content}; apribojimas={'yra' if restricted else 'reikalingas'}; "
                  f"anyone reader={'yra' if drive.permission_ok(permission) else 'reikalinga'}")
        else:
            print(f"{task}: būtų kuriamas PDF; teises bus galima patikrinti tik jį sukūrus")


def publish(local, registry, backend, first_u000003=False, previous_md5=None):
    """Patikrina ID prieš ir po kopijavimo; grąžina registrą tik patvirtinus teises."""
    before = preflight(local, registry, backend, first_u000003, previous_md5)
    backend.copy([entry["path"] for entry in local.values()])
    after = remote_files(backend.list())
    validate_existing(registry, after)
    for task, local_file in local.items():
        if task not in after or after[task]["md5"] != local_file["md5"]:
            raise PublicationError(f"Nerastas arba nepatvirtintas įkelto PDF turinys: {task}")
        if task in before and before[task]["id"] != after[task]["id"]:
            raise PublicationError(f"Kopijuojant pasikeitė Drive ID: {task}")
    result = dict(registry)
    all_ids = {entry["drive_id"] for entry in registry.values()}
    for task in local:
        fid = after[task]["id"]
        if task not in result:
            if fid in all_ids:
                raise PublicationError(f"Drive ID jau priskirtas kitam uždaviniui: {task}")
            result[task] = {"drive_id": fid, "url": f"https://drive.google.com/file/d/{fid}/view"}
            all_ids.add(fid)
    # Parengiame visus planus prieš pirmą teisių keitimą.
    for task in local:
        backend.plan(task, after[task]["id"])
    for task in local:
        backend.apply_and_verify(task, after[task]["id"])
    # Patvirtiname kelią, ID ir turinį dar kartą jau po teisių nustatymo.
    final = remote_files(backend.list())
    validate_existing(registry, final)
    for task, local_file in local.items():
        if (task not in final or final[task]["id"] != after[task]["id"]
                or final[task]["md5"] != local_file["md5"]):
            raise PublicationError(f"Po teisių nustatymo pasikeitė PDF ID arba turinys: {task}")
    return dict(sorted(result.items()))


class RcloneBackend:
    def __init__(self, directory):
        self.dir = Path(directory)
        token = os.environ.get("RCLONE_CONFIG_GDRIVE_TOKEN")
        root_id = os.environ.get("RCLONE_CONFIG_GDRIVE_ROOT_FOLDER_ID")
        if not token or not root_id or os.environ.get("RCLONE_CONFIG_GDRIVE_SCOPE") != "drive":
            raise PublicationError("Nėra esamos rclone OAuth konfigūracijos arba scope=drive")
        obj = json.loads(token)
        if not isinstance(obj, dict) or not isinstance(obj.get("access_token"), str):
            raise PublicationError("Netinkamas rclone tokeno formatas")
        self.cfgfile = self.dir / "rclone.conf"
        cfg = configparser.ConfigParser(interpolation=None)
        cfg["gdrive"] = {"type": "drive", "scope": "drive", "root_folder_id": root_id, "token": token}
        for key in ("client_id", "client_secret"):
            value = os.environ.get("RCLONE_CONFIG_GDRIVE_" + key.upper())
            if value:
                cfg["gdrive"][key] = value
        fd = os.open(self.cfgfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            cfg.write(file)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("RCLONE_CONFIG_GDRIVE_")}
        self.env["RCLONE_CONFIG"] = str(self.cfgfile)

    def _run(self, args):
        result = subprocess.run(["rclone", *args], cwd=ROOT, env=self.env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise PublicationError(f"rclone {args[0]} nepavyko; autentifikacijos duomenys nespausdinami")
        return result.stdout

    def list(self):
        return json.loads(self._run(["lsjson", "gdrive:", "--recursive", "--files-only", "--hash",
                                     "--include", "/Uzduociu_bankas/Uzdaviniai/**"]))

    def copy(self, paths, dry_run=False):
        path = self.dir / "failai.txt"
        path.write_text("".join(item + "\n" for item in paths), encoding="utf-8")
        args = ["copy", ".", "gdrive:", "--files-from-raw", str(path)]
        if dry_run:
            args.append("--dry-run")
        self._run(args)

    def api(self):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(self.cfgfile, encoding="utf-8")
        return drive.DriveAPI(json.loads(cfg["gdrive"]["token"])["access_token"])

    def plan(self, task, file_id):
        return drive.plan(self.api(), task, file_id)

    def apply_and_verify(self, task, file_id):
        api = self.api()
        drive.process(api, task, file_id, apply=True)
        drive.process(api, task, file_id, apply=False, verify=True)


def write_json_atomic(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".drive-links-", delete=False) as file:
            temporary = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_registry(registry):
    write_json_atomic(REGISTRY, registry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true",
                      help="Vykdo tikrus rclone copy ir Drive API pakeitimus")
    mode.add_argument("--dry-run", action="store_true",
                      help="Tik skaito Drive ir imituoja kopijavimą")
    mode.add_argument("--list-changed", action="store_true",
                      help="Tik išvardija PDF, pasikeitusius po publikavimo žymos")
    parser.add_argument("--target-commit", help="Tikslus tikslinio Git commit SHA")
    parser.add_argument("--only", help="Bandomajam vykdymui apdoroti tik vieną uždavinio ID")
    pilots = parser.add_mutually_exclusive_group()
    pilots.add_argument("--pilot-u000001", action="store_true",
                        help="Patvirtinta rankinė GitHub Actions išimtis vien U000001")
    pilots.add_argument("--pilot-u000003", action="store_true",
                        help="Patvirtintas pirmas rankinis U000003 publikavimas")
    parser.add_argument("--first-u000003", action="store_true",
                        help="Dry-run metu patikrinti pirmojo U000003 publikavimo sąlygas")
    args = parser.parse_args()
    if args.only and not drive.ID_PATTERN.fullmatch(args.only):
        parser.error("ID turi būti U ir šeši skaitmenys")
    pilot_task = "U000001" if args.pilot_u000001 else "U000003" if args.pilot_u000003 else None
    if pilot_task and not (args.publish and args.only == pilot_task
                      and os.environ.get("GITHUB_ACTIONS") == "true"
                      and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
                      and os.environ.get("GITHUB_REF") == "refs/heads/main"
                      and os.environ.get("DRIVE_PILOT_CONFIRMATION") == f"PUBLISH {pilot_task}"):
        parser.error("Pilotas leidžiamas tik rankiniam, patvirtintam U000001 arba U000003 vykdymui main šakoje")
    if args.first_u000003 and (not args.dry_run or args.only != "U000003"):
        parser.error("--first-u000003 leidžiamas tik su --dry-run --only U000003")
    if args.list_changed and not args.target_commit:
        parser.error("--list-changed reikalauja --target-commit")
    if args.target_commit and (args.only or pilot_task or args.first_u000003):
        parser.error("--target-commit negalima derinti su vieno uždavinio arba piloto režimu")
    if args.publish and os.environ.get("DRIVE_PDF_PUBLICATION_ENABLED") != "true" and not pilot_task:
        parser.error("Tikram publikavimui reikia DRIVE_PDF_PUBLICATION_ENABLED=true")
    try:
        changed = None
        if args.target_commit:
            changed = changed_files(ROOT, read_checkpoint(CHECKPOINT), args.target_commit)
            if args.list_changed:
                print(json.dumps({"tasks": list(changed)}, ensure_ascii=False))
                return
            if not changed:
                print("Naujų arba pakeistų PDF nėra; Drive operacijos nevykdomos")
                return
            local = local_files(ROOT, selected=set(changed))
            if set(local) != set(changed) or any(local[t]["md5"] != changed[t]["md5"] for t in changed):
                raise PublicationError("Vietiniai PDF neatitinka tikslinio Git commit")
        else:
            local = local_files(ROOT, args.only)
        registry = read_registry(REGISTRY)
        with tempfile.TemporaryDirectory(prefix="publikuoti-pdf-") as tmp:
            backend = RcloneBackend(tmp)
            if args.dry_run:
                preview(local, registry, backend, first_u000003=args.first_u000003)
            else:
                previous = {task: item["known_md5"] for task, item in changed.items()} if changed else None
                result = publish(local, registry, backend, first_u000003=args.pilot_u000003,
                                 previous_md5=previous)
        if args.dry_run:
            print(f"Dry-run patikrinta uždavinių: {len(local)}")
        else:
            write_registry(result)
            if changed:
                write_json_atomic(CHECKPOINT, {"last_published_commit": args.target_commit})
            print(f"Patikrinta ir publikuota uždavinių: {len(local)}")
    except (PublicationError, drive.PatikrosKlaida, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Klaida: {error}\n")
    except (ValueError, KeyError, configparser.Error):
        parser.exit(1, "Klaida: netinkamas autentifikacijos arba JSON duomenų formatas\n")


if __name__ == "__main__":
    main()
