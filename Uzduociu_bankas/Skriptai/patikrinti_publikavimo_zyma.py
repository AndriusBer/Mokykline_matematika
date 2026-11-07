#!/usr/bin/env python3
"""Tik skaitymo Drive ir konkretaus Git commit suderinimo patikra."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import drive_prieiga as drive
import publikuoti_pdf as pub

REQUIRED = {f"U{i:06d}" for i in range(1, 5)}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def snapshot(root, target):
    if not pub.SHA_RE.fullmatch(target):
        raise pub.PublicationError("Būtinas pilnas Git commit SHA")
    if git(root, "rev-parse", "HEAD").decode().strip() != target:
        raise pub.PublicationError("HEAD neatitinka tikrinamo commit")
    with tempfile.TemporaryDirectory(prefix="drive-patikra-git-") as tmp:
        registry_path = Path(tmp) / "registry.json"
        registry_path.write_bytes(git(root, "show", f"{target}:Uzduociu_bankas/drive_links.json"))
        registry = pub.read_registry(registry_path)
        checkpoint_path = Path(tmp) / "state.json"
        checkpoint_path.write_bytes(git(root, "show", f"{target}:Uzduociu_bankas/drive_publication_state.json"))
        checkpoint = pub.read_checkpoint(checkpoint_path)
    # Ancestry and changed PDF history are checked by the publication code.
    changes = pub.changed_files(root, checkpoint, target)
    with tempfile.TemporaryDirectory(prefix="drive-patikra-pradine-") as tmp:
        baseline_path = Path(tmp) / "registry.json"
        baseline_path.write_bytes(git(root, "show", f"{checkpoint}:Uzduociu_bankas/drive_links.json"))
        baseline = pub.read_registry(baseline_path)
    for task, entry in baseline.items():
        if registry.get(task) != entry:
            raise pub.PublicationError(f"Pasikeitė arba pašalintas ankstesnis registro ID: {task}")
    deleted = git(root, "diff", "--name-only", "-z", "--no-renames", "--diff-filter=D",
                  checkpoint, target, "--", "Uzduociu_bankas/Uzdaviniai").decode().split("\0")
    if any(pub.PATH_RE.fullmatch(path) for path in deleted):
        raise pub.PublicationError("Nuo žymos ištrintas PDF; būtina atskira peržiūra")
    raw = git(root, "ls-tree", "-r", "-z", "--full-tree", target, "--", "Uzduociu_bankas/Uzdaviniai")
    local = {}
    for row in raw.split(b"\0"):
        if not row:
            continue
        meta, path_bytes = row.split(b"\t", 1)
        path = path_bytes.decode("utf-8")
        match = pub.PATH_RE.fullmatch(path)
        if not match:
            continue
        task, filename = match.groups()
        mode, kind, _ = meta.split()
        if task != filename or mode != b"100644" or kind != b"blob":
            raise pub.PublicationError(f"Netinkamas Git PDF: {path}")
        local[task] = {"path": path, "md5": hashlib.md5(git(root, "show", f"{target}:{path}")).hexdigest()}
    if not REQUIRED <= local.keys() or set(local) != set(registry):
        raise pub.PublicationError("Git PDF ir registro uždavinių sąrašai nesutampa arba trūksta U000001–U000004")
    if not set(changes) <= local.keys():
        raise pub.PublicationError("Ne visi pasikeitę PDF bus patikrinti")
    return local, registry, checkpoint


def verify(local, registry, backend):
    remote = pub.remote_files(backend.list())
    pub.validate_existing(registry, remote)
    if set(remote) != set(local):
        raise pub.PublicationError("Drive PDF sąrašas nesutampa su Git ir registru")
    api = backend.api()
    for task, item in sorted(local.items()):
        if remote[task]["md5"] != item["md5"]:
            raise pub.PublicationError(f"Drive ir Git PDF MD5 nesutampa: {task}")
        drive.process(api, task, remote[task]["id"], apply=False, verify=True)
        print(f"{task}: Drive ID ir MD5 sutampa")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-commit", required=True, help="Tikslus pilnas Git commit SHA")
    args = parser.parse_args()
    try:
        local, registry, checkpoint = snapshot(pub.ROOT, args.target_commit)
        with tempfile.TemporaryDirectory(prefix="drive-patikra-") as tmp:
            verify(local, registry, pub.RcloneBackend(tmp))
        print(f"Patikrintas Git commit: {args.target_commit}")
        print(f"Ankstesnė žyma: {checkpoint}")
        print("Žyma automatiškai nekeičiama; suderinkite ją tik patikrinę main būseną.")
    except (pub.PublicationError, drive.PatikrosKlaida, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Klaida: {error}\n")
    except (ValueError, KeyError):
        parser.exit(1, "Klaida: netinkamas JSON arba autentifikacijos formatas\n")


if __name__ == "__main__":
    main()
