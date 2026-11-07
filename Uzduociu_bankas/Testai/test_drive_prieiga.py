import contextlib
import configparser
import copy
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

SCRIPT = Path(__file__).resolve().parents[1] / "Skriptai/drive_prieiga.py"
spec = importlib.util.spec_from_file_location("drive_prieiga", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(task, drive_id="ID_1"):
    return {"Path": f"Uzduociu_bankas/Uzdaviniai/{task}/{task}.pdf", "ID": drive_id, "IsDir": False}


def registry(task="U000001", drive_id="ID_1"):
    return {task: {"drive_id": drive_id, "url": f"https://drive.google.com/file/d/{drive_id}/view"}}


class FakeDrive:
    def __init__(self, restricted=False, permission=None, can_share=True, can_restrict=True):
        self.file_data = {"id": "ID_1", "name": "U000001.pdf", "mimeType": "application/pdf",
                          "trashed": False, "capabilities": {"canShare": can_share,
                          "canChangeItemDownloadRestriction": can_restrict},
                          "downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": restricted}}}
        self.permission = copy.deepcopy(permission)
        self.calls = []
    def file(self, file_id):
        self.calls.append("get_file")
        return copy.deepcopy(self.file_data)
    def permissions(self, file_id):
        self.calls.append("get_permissions")
        return [copy.deepcopy(self.permission)] if self.permission else []
    def restrict(self, file_id):
        self.calls.append("restrict")
        self.file_data["downloadRestrictions"]["itemDownloadRestriction"]["restrictedForReaders"] = True
    def create_permission(self, file_id):
        self.calls.append("create")
        self.permission = {"id": "anyone_id", "type": "anyone", "role": "reader", "allowFileDiscovery": False}
    def update_permission(self, file_id, permission_id):
        self.calls.append("update")
        self.permission.update(role="reader", allowFileDiscovery=False)


class DrivePrieigosTestai(unittest.TestCase):
    def process(self, drive, apply=False, verify=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return mod.process(drive, "U000001", "ID_1", apply, verify)

    def test_parenkamas_tik_tikslus_pdf_ir_tik_sutampantis_registro_id(self):
        rows = [row("U000001"), {"Path": "Uzduociu_bankas/Rinkiniai/kitas.pdf"}]
        self.assertEqual(mod.parinkti_failus(rows, registry(), "U000001"), {"U000001": "ID_1"})
        for bad in ([row("U000001", "kitoks")], [row("U000001"), row("U000001")], [],
                    [{"Path": "Uzduociu_bankas/Uzdaviniai/U000001/U000002.pdf"}]):
            with self.subTest(bad=bad), self.assertRaises(mod.PatikrosKlaida):
                mod.parinkti_failus(bad, registry(), "U000001")

    def test_numatytasis_rezimas_tik_skaito(self):
        drive = FakeDrive()
        self.process(drive)
        self.assertEqual(drive.calls, ["get_file", "get_permissions"])

    def test_taikymas_pirmiausia_apriboja_ir_patikrina_tada_bendrina(self):
        drive = FakeDrive()
        self.process(drive, apply=True)
        self.assertEqual(drive.calls, ["get_file", "get_permissions", "restrict", "get_file",
                                       "get_permissions", "get_file", "get_permissions",
                                       "create", "get_file", "get_permissions"])
        self.assertTrue(mod.permission_ok(drive.permission))
        self.assertTrue(drive.file_data["downloadRestrictions"]["itemDownloadRestriction"]["restrictedForReaders"])
        drive.calls.clear()
        self.process(drive, apply=True)
        self.assertNotIn("create", drive.calls)
        self.assertNotIn("update", drive.calls)
        self.assertNotIn("restrict", drive.calls)

    def test_esama_tiesiogine_teisė_atnaujinama_be_dublikato(self):
        drive = FakeDrive(restricted=True, permission={"id": "anyone_id", "type": "anyone",
                          "role": "reader", "allowFileDiscovery": True})
        self.process(drive, apply=True)
        self.assertIn("update", drive.calls)
        self.assertNotIn("create", drive.calls)

    def test_paveldeta_teise_ir_trukstamos_galimybes_stabdo(self):
        cases = [FakeDrive(can_restrict=False), FakeDrive(restricted=True, can_share=False),
                 FakeDrive(restricted=True, permission={"id": "anyone_id", "type": "anyone", "role": "writer",
                                                       "permissionDetails": [{"inherited": True}]})]
        for drive in cases:
            with self.subTest(drive=drive), self.assertRaises(mod.PatikrosKlaida):
                self.process(drive, apply=True)
            self.assertNotIn("create", drive.calls)
            self.assertNotIn("update", drive.calls)
            self.assertNotIn("restrict", drive.calls)

    def test_verifikacija_yra_tik_skaitymo_ir_neatitiktis_yra_klaida(self):
        drive = FakeDrive()
        with self.assertRaises(mod.PatikrosKlaida):
            self.process(drive, verify=True)
        drive = FakeDrive(restricted=True, permission={"id": "a", "type": "anyone", "role": "reader", "allowFileDiscovery": False})
        self.process(drive, verify=True)
        self.assertEqual(drive.calls, ["get_file", "get_permissions"])

    def test_api_siuncia_tikslius_laukus_ir_ismetines_nenaudoja(self):
        api = mod.DriveAPI("test-token")
        with patch.object(api, "request", return_value={}) as request:
            api.restrict("ID_1")
            self.assertEqual(request.call_args.args[3], {"downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": True}}})
            api.create_permission("ID_1")
            self.assertEqual(request.call_args.args[3], {"type": "anyone", "role": "reader", "allowFileDiscovery": False})
            api.update_permission("ID_1", "anyone_id")
            self.assertEqual(request.call_args.args[3], {"role": "reader", "allowFileDiscovery": False})

    def test_cli_neleidzia_pirmo_taikymo_kitiems_ir_neatskleidzia_tokeno(self):
        for args in (["--visi", "--apply"], ["--id", "U000003", "--apply"]):
            result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tik U000001", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT)], env={"RCLONE_CONFIG_GDRIVE_TOKEN": "slaptas-testas"}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("slaptas-testas", result.stderr + result.stdout)

    def test_nepatvirtinus_apribojimo_viesinimas_nevykdomas(self):
        drive = FakeDrive()
        drive.restrict = lambda file_id: drive.calls.append("restrict")
        with self.assertRaises(mod.PatikrosKlaida):
            self.process(drive, apply=True)
        self.assertNotIn("create", drive.calls)

    def test_esamo_rclone_tokeno_atnaujinimas_atskirame_laikiname_faile(self):
        captured = {}
        with tempfile.TemporaryDirectory() as directory:
            bank = Path(directory)
            (bank / "drive_links.json").write_text(json.dumps(registry()))

            def fake_rclone(command, *, env, **kwargs):
                config_path = Path(env["RCLONE_CONFIG"])
                captured["path"] = config_path
                self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
                self.assertNotIn("RCLONE_CONFIG_GDRIVE_TOKEN", env)
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.read(config_path)
                self.assertEqual(json.loads(cfg["gdrive"]["token"])["access_token"], "senas-slaptas")
                cfg["gdrive"]["token"] = json.dumps({"access_token": "naujas-slaptas"})
                with config_path.open("w") as file:
                    cfg.write(file)
                return subprocess.CompletedProcess(command, 0, json.dumps([row("U000001")]), "")

            def fake_api(token):
                captured["token"] = token
                return FakeDrive()

            env = {"RCLONE_CONFIG_GDRIVE_TOKEN": json.dumps({"access_token": "senas-slaptas"}),
                   "RCLONE_CONFIG_GDRIVE_ROOT_FOLDER_ID": "root-id",
                   "RCLONE_CONFIG_GDRIVE_SCOPE": "drive"}
            output = io.StringIO()
            with patch.object(mod, "BANKAS", bank), patch.dict(os.environ, env, clear=True), \
                 patch.object(mod.subprocess, "run", side_effect=fake_rclone), \
                 patch.object(mod, "DriveAPI", side_effect=fake_api), \
                 patch.object(sys, "argv", [str(SCRIPT)]), contextlib.redirect_stdout(output):
                mod.main()
            self.assertEqual(captured["token"], "naujas-slaptas")
            self.assertFalse(captured["path"].exists())
            self.assertNotIn("slaptas", output.getvalue())


if __name__ == "__main__":
    unittest.main()
