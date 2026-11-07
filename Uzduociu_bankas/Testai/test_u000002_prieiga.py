import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BANKAS = Path(__file__).resolve().parents[1]
SCRIPT = BANKAS / "Skriptai/drive_prieiga.py"
WORKFLOW = BANKAS.parent / ".github/workflows/drive-access-apply-u000002.yml"
spec = importlib.util.spec_from_file_location("u2_drive", SCRIPT)
drive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drive)


def registry():
    return {"U000002": {"drive_id": "ID_2", "url": "https://drive.google.com/file/d/ID_2/view"}}


class FakeDrive:
    def __init__(self):
        self.restricted = False
        self.permission = None
        self.writes = []

    def file(self, fid):
        return {"id": fid, "name": "U000002.pdf", "mimeType": "application/pdf", "trashed": False,
                "capabilities": {"canShare": True, "canChangeItemDownloadRestriction": True},
                "downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": self.restricted}}}

    def permissions(self, fid):
        return [self.permission.copy()] if self.permission else []

    def restrict(self, fid):
        self.writes.append(("restrict", fid))
        self.restricted = True

    def create_permission(self, fid):
        self.writes.append(("create", fid))
        self.permission = {"id": "anyone_id", "type": "anyone", "role": "reader", "allowFileDiscovery": False}

    def update_permission(self, fid, pid):
        self.writes.append(("update", fid))
        self.permission.update(role="reader", allowFileDiscovery=False)


class U000002PrieigosTestai(unittest.TestCase):
    def test_apply_leidziamas_tik_dviem_id(self):
        env = {"PATH": os.environ.get("PATH", "")}
        for task in ("U000001", "U000002"):
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--id", task, "--apply"],
                               env=env, capture_output=True, text=True)
            with self.subTest(task=task):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("Nėra esamo rclone tokeno", p.stderr)
        for args in (["--id", "U000003", "--apply"], ["--visi", "--apply"]):
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                               env=env, capture_output=True, text=True)
            with self.subTest(args=args):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("tik U000001 arba U000002", p.stderr)

    def test_patikrinimas_taikymas_ir_pakartojimas_tik_uzregistruotam_id(self):
        fake = FakeDrive()
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            bank = Path(temp)
            reg = bank / "drive_links.json"
            reg.write_text(json.dumps(registry()))
            before = reg.read_bytes()
            def list_remote(args, **kwargs):
                calls.append(args)
                row = {"Path": "Uzduociu_bankas/Uzdaviniai/U000002/U000002.pdf", "ID": "ID_2", "IsDir": False}
                return subprocess.CompletedProcess(args, 0, json.dumps([row]), "")
            env = {"RCLONE_CONFIG_GDRIVE_TOKEN": json.dumps({"access_token": "test-token"}),
                   "RCLONE_CONFIG_GDRIVE_ROOT_FOLDER_ID": "root-id", "RCLONE_CONFIG_GDRIVE_SCOPE": "drive"}
            with patch.object(drive, "BANKAS", bank), patch.dict(os.environ, env, clear=True), \
                 patch.object(drive.subprocess, "run", side_effect=list_remote), \
                 patch.object(drive, "DriveAPI", return_value=fake), contextlib.redirect_stdout(io.StringIO()):
                for option in ("--apply", "--apply", "--verify"):
                    with patch.object(sys, "argv", [str(SCRIPT), "--id", "U000002", option]):
                        drive.main()
            self.assertEqual(fake.writes, [("restrict", "ID_2"), ("create", "ID_2")])
            self.assertTrue(fake.restricted)
            self.assertEqual(fake.permission["type"], "anyone")
            self.assertEqual(fake.permission["role"], "reader")
            self.assertIs(fake.permission["allowFileDiscovery"], False)
            self.assertEqual(reg.read_bytes(), before)
            for args in calls:
                self.assertEqual(args[1], "lsjson")
                self.assertIn("/Uzduociu_bankas/Uzdaviniai/U000002/U000002.pdf", args)
                self.assertNotIn("copy", args)

    def test_neatitinkantis_id_sustabdo_pries_api(self):
        rows = [{"Path": "Uzduociu_bankas/Uzdaviniai/U000002/U000002.pdf", "ID": "OTHER", "IsDir": False}]
        with self.assertRaisesRegex(drive.PatikrosKlaida, "nesutampa"):
            drive.parinkti_failus(rows, registry(), "U000002")

    def test_restriction_ir_permission_api_laukai(self):
        api = drive.DriveAPI("mock")
        with patch.object(api, "request", return_value={}) as request:
            api.restrict("ID_2")
            self.assertEqual(request.call_args.args[1], "files/ID_2")
            self.assertEqual(request.call_args.args[3], {"downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": True}}})
            api.create_permission("ID_2")
            self.assertEqual(request.call_args.args[1], "files/ID_2/permissions")
            self.assertEqual(request.call_args.args[3], {"type": "anyone", "role": "reader", "allowFileDiscovery": False})

    def test_patikrinimas_butent_tikslus(self):
        text = WORKFLOW.read_text()
        part = text.split("      - name: Validate confirmation\n", 1)[1].split("      - name: Checkout", 1)[0]
        script = part.split("        run: |\n", 1)[1]
        script = "\n".join(x[10:] if x.startswith("          ") else x for x in script.splitlines())
        for confirmation, expected in [("APPLY U000002", True), ("apply U000002", False),
                                        ("APPLY U000001", False), ("APPLY U000002 ", False), ("", False)]:
            p = subprocess.run(["bash", "-c", script], env={"CONFIRMATION": confirmation},
                               capture_output=True, text=True)
            with self.subTest(confirmation=confirmation):
                self.assertEqual(p.returncode == 0, expected)

    def test_workflow_vykdo_tik_u2_ir_patikrina_po_klaidos_nesitęsia(self):
        text = WORKFLOW.read_text()
        part = text.split("      - name: Check, apply and verify U000002 Drive access\n", 1)[1]
        script = part.split("        run: |\n", 1)[1]
        script = "\n".join(x[10:] if x.startswith("          ") else x for x in script.splitlines())
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "python3"
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\ncase "$*" in *--apply*) [ "$FAIL_APPLY" != 1 ] || exit 7;; esac\n')
            executable.chmod(0o755)
            log = Path(temp) / "calls"
            for fail in ("0", "1"):
                log.unlink(missing_ok=True)
                env = {"PATH": temp, "CALL_LOG": str(log), "FAIL_APPLY": fail}
                p = subprocess.run(["/bin/bash", "-c", script], env=env, capture_output=True, text=True)
                calls = log.read_text().splitlines()
                with self.subTest(fail=fail):
                    self.assertEqual(p.returncode == 0, fail == "0")
                    self.assertEqual(len(calls), 3 if fail == "0" else 2)
                    self.assertTrue(all("--id U000002" in line for line in calls))
                    self.assertNotIn("--apply", calls[0])
                    self.assertIn("--apply", calls[1])
                    if fail == "0":
                        self.assertIn("--verify", calls[2])


if __name__ == "__main__":
    unittest.main()
