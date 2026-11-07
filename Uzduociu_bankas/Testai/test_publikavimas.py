import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BANKAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BANKAS / "Skriptai"))
spec = importlib.util.spec_from_file_location("publikuoti_pdf", BANKAS / "Skriptai/publikuoti_pdf.py")
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def local(task, md5):
    return {"path": f"Uzduociu_bankas/Uzdaviniai/{task}/{task}.pdf", "md5": md5}


def entry(fid):
    return {"drive_id": fid, "url": f"https://drive.google.com/file/d/{fid}/view"}


class FakeBackend:
    """Imituoja rclone ir Drive API būseną; tikro tinklo nėra."""
    def __init__(self, files):
        self.files = copy.deepcopy(files)
        self.actions = []
        self.states = {}
        for task, data in self.files.items():
            self.states[data["id"]] = {"task": task, "restricted": False, "permission": None}
        self.next_ids = {"U000003": "NEW_3", "U000004": "NEW_4"}
        self.new_hashes = {"U000003": "3" * 32, "U000004": "4" * 32}
        self.failed = False
        self.replace_id = False

    def list(self):
        self.actions.append("list")
        return [{"Path": local(task, "")["path"], "ID": data["id"], "IsDir": False,
                 "Hashes": {"md5": data["md5"]}} for task, data in self.files.items()]

    def copy(self, paths, dry_run=False):
        self.actions.append(("copy", tuple(paths)))
        if dry_run:
            self.actions.append("dry-run")
            return
        for path in paths:
            task = pub.PATH_RE.fullmatch(path).group(1)
            if task not in self.files:
                fid = self.next_ids[task]
                self.files[task] = {"id": fid, "md5": self.new_hashes[task]}
                self.states[fid] = {"task": task, "restricted": False, "permission": None}
            elif task in self.new_hashes:
                self.files[task]["md5"] = self.new_hashes[task]
            if self.replace_id:
                self.files[task]["id"] = "CHANGED"

    def request(self, method, path, params=None, data=None):
        parts = path.split("/")
        fid = parts[1]
        state = self.states[fid]
        self.actions.append((method, path, copy.deepcopy(data)))
        if len(parts) == 2 and method == "GET":
            return {"id": fid, "name": state["task"] + ".pdf", "mimeType": "application/pdf", "trashed": False,
                    "capabilities": {"canShare": True, "canChangeItemDownloadRestriction": True},
                    "downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": state["restricted"]}}}
        if len(parts) == 3 and parts[2] == "permissions" and method == "GET":
            return {"permissions": [copy.deepcopy(state["permission"])] if state["permission"] else []}
        if len(parts) == 2 and method == "PATCH":
            self.assert_request(data, {"downloadRestrictions": {"itemDownloadRestriction": {"restrictedForReaders": True}}})
            state["restricted"] = True
            return {"id": fid}
        if len(parts) == 3 and method == "POST":
            self.assert_request(data, {"type": "anyone", "role": "reader", "allowFileDiscovery": False})
            if self.failed:
                raise pub.drive.PatikrosKlaida("imituota API klaida")
            state["permission"] = {"id": "anyone_id", **data}
            return {"id": "anyone_id"}
        raise AssertionError((method, path, data))

    @staticmethod
    def assert_request(actual, expected):
        if actual != expected:
            raise AssertionError((actual, expected))

    def api(self):
        api = pub.drive.DriveAPI("test")
        api.request = self.request
        return api

    def plan(self, task, fid):
        return pub.drive.plan(self.api(), task, fid)

    def apply_and_verify(self, task, fid):
        api = self.api()
        pub.drive.process(api, task, fid, apply=True)
        pub.drive.process(api, task, fid, apply=False, verify=True)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.old = {"U000001": entry("ID_1"), "U000002": entry("ID_2")}
        self.local = {"U000001": local("U000001", "1" * 32), "U000003": local("U000003", "3" * 32)}
        self.backend = FakeBackend({"U000001": {"id": "ID_1", "md5": "1" * 32},
                                    "U000002": {"id": "ID_2", "md5": "2" * 32}})

    def execute(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return pub.publish(self.local, self.old, self.backend)

    def test_naujo_publikavimas_id_teises_ir_pakartojimas(self):
        result = self.execute()
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(result["U000002"], self.old["U000002"])
        self.assertEqual(result["U000003"], entry("NEW_3"))
        self.assertEqual(list(result), ["U000001", "U000002", "U000003"])
        self.assertEqual([x for x in self.backend.actions if isinstance(x, tuple) and x[0] == "POST"].__len__(), 2)
        self.assertIsNone(self.backend.states["ID_2"]["permission"])
        self.old = result
        self.backend.actions.clear()
        self.assertEqual(self.execute(), result)
        self.assertFalse([x for x in self.backend.actions if isinstance(x, tuple) and x[0] in ("POST", "PATCH")])

    def test_senas_id_pasikeite_sustabdo_pries_kopijavima(self):
        self.backend.files["U000001"]["id"] = "OTHER"
        with self.assertRaisesRegex(pub.PublicationError, "pasikeitė Drive ID"):
            self.execute()
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))

    def test_pries_copy_tikrinami_md5_ir_drive_teises(self):
        self.local["U000001"]["md5"] = "a" * 32
        self.backend.new_hashes["U000001"] = "a" * 32
        with contextlib.redirect_stdout(io.StringIO()):
            pub.publish(self.local, self.old, self.backend,
                        previous_md5={"U000001": "1" * 32, "U000003": None})
        copy_index = next(i for i, action in enumerate(self.backend.actions)
                          if isinstance(action, tuple) and action[0] == "copy")
        reads = self.backend.actions[:copy_index]
        self.assertTrue(any(isinstance(x, tuple) and x[:2] == ("GET", "files/ID_1") for x in reads))
        self.assertTrue(any(isinstance(x, tuple) and x[:2] == ("GET", "files/ID_1/permissions") for x in reads))
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH") for x in reads))

    def test_drive_md5_nesutapus_pries_copy_sustabdo(self):
        self.backend.files["U000001"]["md5"] = "b" * 32
        with self.assertRaisesRegex(pub.PublicationError, "MD5 neatitinka"):
            pub.publish(self.local, self.old, self.backend,
                        previous_md5={"U000001": "1" * 32, "U000003": None})
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))

    def test_tarpine_git_versija_leidziama_ankstesniam_drive_id(self):
        self.backend.files["U000001"]["md5"] = "b" * 32
        self.local["U000001"]["md5"] = "a" * 32
        self.backend.new_hashes["U000001"] = "a" * 32
        with contextlib.redirect_stdout(io.StringIO()):
            result = pub.publish(self.local, self.old, self.backend,
                previous_md5={"U000001": ["1" * 32, "b" * 32, "a" * 32], "U000003": None})
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(self.backend.files["U000001"]["md5"], "a" * 32)

    def test_pakeistas_pdf_atnaujinamas_issaugant_drive_id(self):
        self.local["U000001"]["md5"] = "a" * 32
        self.backend.new_hashes["U000001"] = "a" * 32
        result = self.execute()
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(self.backend.files["U000001"], {"id": "ID_1", "md5": "a" * 32})

    def test_po_kopijavimo_pasikeites_id_sustabdo_pries_teises(self):
        self.backend.replace_id = True
        with self.assertRaises(pub.PublicationError):
            self.execute()
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("PATCH", "POST") for x in self.backend.actions))

    def test_nutruke_publikavimas_atsigauna_pagal_ta_pati_turini_ir_id(self):
        self.backend.failed = True
        with self.assertRaises(pub.drive.PatikrosKlaida):
            self.execute()
        self.assertNotIn("U000003", self.old)
        self.assertEqual(self.backend.files["U000003"]["id"], "NEW_3")
        self.backend.failed = False
        result = self.execute()
        self.assertEqual(result["U000003"]["drive_id"], "NEW_3")

    def test_nezinomas_pdf_skirtingo_turinio_nelieciamas(self):
        self.backend.files["U000003"] = {"id": "OTHER", "md5": "b" * 32}
        with self.assertRaisesRegex(pub.PublicationError, "turinys nesutampa"):
            self.execute()
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))

    def test_drive_dublikatai_ir_nesutampantys_pavadinimai_atmetami(self):
        duplicate = self.backend.list()[0]
        with self.assertRaises(pub.PublicationError):
            pub.remote_files([duplicate, duplicate])
        duplicate["Path"] = "Uzduociu_bankas/Uzdaviniai/U000001/U000002.pdf"
        with self.assertRaises(pub.PublicationError):
            pub.remote_files([duplicate])

    def test_md5_mazosios_ir_didziosios_normalizuojamos(self):
        expected = "0123456789abcdef0123456789abcdef"
        row = self.backend.list()[0]
        for hashes in ({"md5": expected}, {"md5": expected.upper()},
                       {"MD5": expected.upper()}, {"md5": expected, "MD5": expected.upper()}):
            with self.subTest(hashes=hashes):
                row["Hashes"] = hashes
                self.assertEqual(pub.remote_files([row])["U000001"]["md5"], expected)

    def test_trukstama_arba_netinkama_md5_atmetama(self):
        row = self.backend.list()[0]
        for hashes in (None, {}, [], {"sha1": "1" * 40}, {"md5": ""},
                       {"md5": None}, {"md5": 123}, {"md5": "1" * 31},
                       {"md5": "g" * 32}, {"md5": "1" * 32 + "\n"},
                       {"md5": "1" * 32, "MD5": "netinkama"}):
            with self.subTest(hashes=hashes):
                row["Hashes"] = hashes
                with self.assertRaisesRegex(pub.PublicationError, "MD5 kontrolin"):
                    pub.remote_files([row])
        del row["Hashes"]
        with self.assertRaisesRegex(pub.PublicationError, "Trūksta.*MD5"):
            pub.remote_files([row])

    def test_nesutampancios_dvi_md5_reiksmes_atmetamos(self):
        row = self.backend.list()[0]
        row["Hashes"] = {"md5": "1" * 32, "MD5": "2" * 32}
        with self.assertRaisesRegex(pub.PublicationError, "Nesutampa.*MD5"):
            pub.remote_files([row])

    @unittest.skipUnless(shutil.which("rclone"), "Nerastas rclone")
    def test_tikras_rclone_lsjson_md5_formatas(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "U000001.pdf").write_bytes(b"bandomasis PDF turinys")
            out = subprocess.run(["rclone", "lsjson", directory, "--hash", "--files-only"],
                                 capture_output=True, text=True, check=True)
            row = json.loads(out.stdout)[0]
            self.assertIn("md5", row["Hashes"])
            row["Path"] = local("U000001", "")["path"]
            row["ID"] = "test_id"
            self.assertEqual(pub.remote_files([row])["U000001"]["md5"], row["Hashes"]["md5"])

    def test_rclone_naudoja_copy_ir_tik_exact_failu_sarasa(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = object.__new__(pub.RcloneBackend)
            backend.dir = Path(directory)
            calls = []
            backend._run = lambda args: calls.append(args)
            paths = [self.local["U000001"]["path"], self.local["U000003"]["path"]]
            backend.copy(paths)
            self.assertEqual(calls[0][:4], ["copy", ".", "gdrive:", "--files-from-raw"])
            self.assertEqual(Path(calls[0][4]).read_text().splitlines(), paths)
            backend.copy(paths, dry_run=True)
            self.assertEqual(calls[1][-1], "--dry-run")

    def test_parenkami_tik_git_sekami_taisyklingi_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            base = root / "Uzduociu_bankas/Uzdaviniai"
            for task in ["U000001", "U000003"]:
                folder = base / task
                folder.mkdir(parents=True)
                (folder / f"{task}.pdf").write_bytes(b"pdf")
            subprocess.run(["git", "-C", str(root), "add", "--",
                            "Uzduociu_bankas/Uzdaviniai/U000001/U000001.pdf"], check=True)
            self.assertEqual(list(pub.local_files(root)), ["U000001"])
            with self.assertRaises(pub.PublicationError):
                pub.local_files(root, "U000003")

    def test_pries_teisiu_keitima_visiems_patikrinamos_galimybes(self):
        original = self.backend.plan
        def plan(task, fid):
            if task == "U000003":
                raise pub.drive.PatikrosKlaida("neleidžiama")
            return original(task, fid)
        self.backend.plan = plan
        with self.assertRaises(pub.drive.PatikrosKlaida):
            self.execute()
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH") for x in self.backend.actions))

    def test_nepavykus_teisiu_nustatymui_registras_neperrasomas(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            old = path.read_bytes()
            self.backend.failed = True
            with patch.object(pub, "REGISTRY", path), self.assertRaises(pub.drive.PatikrosKlaida):
                pub.write_registry(self.execute())
            self.assertEqual(path.read_bytes(), old)

    def test_visa_cli_eiga_su_imituotu_drive_ir_registro_irasymais(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            with patch.object(pub, "REGISTRY", path), \
                 patch.object(pub, "local_files", return_value=self.local), \
                 patch.object(pub, "RcloneBackend", return_value=self.backend), \
                 patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "true"}), \
                 patch.object(sys, "argv", [str(pub.__file__), "--publish"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pub.main()
            self.assertEqual(json.loads(path.read_text())["U000003"], entry("NEW_3"))

    def test_cli_dry_run_veikia_isjungus_ir_nekeicia_registro(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            originalas = path.read_bytes()
            with patch.object(pub, "REGISTRY", path), \
                 patch.object(pub, "local_files", return_value=self.local), \
                 patch.object(pub, "RcloneBackend", return_value=self.backend), \
                 patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "false"}), \
                 patch.object(sys, "argv", [str(pub.__file__), "--dry-run"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pub.main()
            self.assertEqual(path.read_bytes(), originalas)
            self.assertIn("dry-run", self.backend.actions)
            self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH")
                                 for x in self.backend.actions))

    def test_isjungtas_publish_nepasiekia_rclone_ar_drive(self):
        for value in (None, "false", "TRUE", "1"):
            env = dict(os.environ)
            if value is None:
                env.pop("DRIVE_PDF_PUBLICATION_ENABLED", None)
            else:
                env["DRIVE_PDF_PUBLICATION_ENABLED"] = value
            with self.subTest(value=value):
                p = subprocess.run([sys.executable, "-B", str(pub.__file__), "--publish"],
                                   env=env, capture_output=True, text=True)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("DRIVE_PDF_PUBLICATION_ENABLED=true", p.stderr)

    def test_workflow_komandos_blokuoja_publish_kai_kintamasis_isjungtas(self):
        workflow = (BANKAS.parent / ".github/workflows/publikuoti-uzdavinius.yml").read_text()
        step = workflow.split("      - name: Publish PDFs and verify Drive access\n", 1)[1]
        script = step.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "python3"
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n')
            executable.chmod(0o755)
            log = Path(directory) / "calls"
            for event, apply, enabled, task, confirm, success, expected in [
                ("push", "", "", "U000001", "PUBLISH U000001", False, None),
                ("workflow_dispatch", "true", "", "U000001", "", False, None),
                ("workflow_dispatch", "true", "", "U000001", "publish U000001", False, None),
                ("workflow_dispatch", "true", "", "U000002", "PUBLISH U000002", False, None),
                ("workflow_dispatch", "true", "", "U000004", "PUBLISH U000003", False, None),
                ("workflow_dispatch", "true", "", "U000004", "publish U000004", False, None),
                ("workflow_dispatch", "true", "", "U000004", "PUBLISH U000004", True, "--pilot-u000004"),
                ("workflow_dispatch", "false", "", "U000004", "", True, "--first-u000004"),
                ("workflow_dispatch", "true", "", "U000003", "PUBLISH U000002", False, None),
                ("workflow_dispatch", "true", "", "U000003", "publish U000003", False, None),
                ("workflow_dispatch", "true", "", "U000003", "PUBLISH U000003", True, "--pilot-u000003"),
                ("workflow_dispatch", "true", "true", "U000003", "PUBLISH U000003", True, "--pilot-u000003"),
                ("workflow_dispatch", "false", "", "U000003", "", True, "--first-u000003"),
                ("workflow_dispatch", "true", "", "U000001", "PUBLISH U000001", True, "--pilot-u000001"),
                ("workflow_dispatch", "false", "", "U000001", "", True, "--dry-run"),
                ("workflow_dispatch", "true", "true", "U000001", "", False, None),
                ("workflow_dispatch", "true", "true", "U000001", "PUBLISH U000001", True, "--publish"),
                ("push", "", "true", "U000001", "", True, "--publish"),
            ]:
                log.unlink(missing_ok=True)
                env = dict(os.environ, PATH=directory, CALL_LOG=str(log),
                           GITHUB_EVENT_NAME=event, PILOT_APPLY=apply,
                           PILOT_TASK_ID=task, DRIVE_PILOT_CONFIRMATION=confirm,
                           DRIVE_PDF_PUBLICATION_ENABLED=enabled, GITHUB_SHA="f" * 40)
                result = subprocess.run(["/bin/bash", "-c", script], env=env,
                                        capture_output=True, text=True)
                with self.subTest(event=event, apply=apply, enabled=enabled):
                    self.assertEqual(result.returncode == 0, success, result.stderr)
                    if expected is None:
                        self.assertFalse(log.exists())
                    else:
                        self.assertIn(expected, log.read_text())

    def test_piloto_isimtis_leidziama_tik_rankiniu_budu_su_tiksliu_patvirtinimu(self):
        valid = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
                 "GITHUB_REF": "refs/heads/main", "DRIVE_PILOT_CONFIRMATION": "PUBLISH U000001",
                 "DRIVE_PDF_PUBLICATION_ENABLED": ""}
        for change in [{"GITHUB_ACTIONS": "false"}, {"GITHUB_EVENT_NAME": "push"},
                       {"GITHUB_REF": "refs/heads/kita"}, {"DRIVE_PILOT_CONFIRMATION": ""},
                       {"DRIVE_PILOT_CONFIRMATION": "publish U000001"}]:
            env = dict(valid, **change)
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), "--publish", "--only",
                                "U000001", "--pilot-u000001"], env=env, capture_output=True, text=True)
            with self.subTest(change=change):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("Pilotas leidžiamas tik", p.stderr)
        for args in (["--publish", "--only", "U000002", "--pilot-u000001"],
                     ["--publish", "--pilot-u000001"],
                     ["--dry-run", "--only", "U000001", "--pilot-u000001"]):
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), *args], env=valid,
                               capture_output=True, text=True)
            with self.subTest(args=args):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("Pilotas leidžiamas tik", p.stderr)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            with patch.object(pub, "REGISTRY", path), \
                 patch.object(pub, "local_files", return_value={"U000001": self.local["U000001"]}), \
                 patch.object(pub, "RcloneBackend", return_value=self.backend), \
                 patch.dict(os.environ, valid, clear=True), \
                 patch.object(sys, "argv", [str(pub.__file__), "--publish", "--only", "U000001", "--pilot-u000001"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pub.main()
            copies = [x for x in self.backend.actions if isinstance(x, tuple) and x[0] == "copy"]
            self.assertEqual(copies[0][1], (self.local["U000001"]["path"],))
            self.assertIsNone(self.backend.states["ID_2"]["permission"])

    def test_u000003_pirmas_publikavimas_ir_senu_id_apsauga(self):
        selected = {"U000003": self.local["U000003"]}
        with contextlib.redirect_stdout(io.StringIO()):
            result = pub.publish(selected, self.old, self.backend, first_u000003=True)
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(result["U000002"], self.old["U000002"])
        self.assertEqual(result["U000003"], entry("NEW_3"))
        self.assertEqual(self.backend.files["U000003"]["md5"], selected["U000003"]["md5"])
        changes = [x for x in self.backend.actions if isinstance(x, tuple) and x[0] in ("PATCH", "POST")]
        self.assertTrue(changes)
        self.assertTrue(all("files/NEW_3" in action[1] for action in changes))
        self.assertTrue(self.backend.states["NEW_3"]["restricted"])
        self.assertTrue(pub.drive.permission_ok(self.backend.states["NEW_3"]["permission"]))
        copy_actions = [x for x in self.backend.actions if isinstance(x, tuple) and x[0] == "copy"]
        self.assertEqual(copy_actions[0][1], (selected["U000003"]["path"],))

    def test_u000003_jau_registre_ar_drive_sustabdo_pries_copy(self):
        selected = {"U000003": self.local["U000003"]}
        with self.assertRaisesRegex(pub.PublicationError, "jau yra registre"):
            pub.publish(selected, {**self.old, "U000003": entry("NEW_3")}, self.backend, first_u000003=True)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))
        self.backend.files["U000003"] = {"id": "NEW_3", "md5": "3" * 32}
        for operation in (pub.publish, pub.preview):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(pub.PublicationError, "jau yra Drive"):
                operation(selected, self.old, self.backend, first_u000003=True)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))

    def test_u000003_nesutapus_md5_teises_ir_registras_nekeičiami(self):
        selected = {"U000003": self.local["U000003"]}
        self.backend.new_hashes["U000003"] = "9" * 32
        with self.assertRaisesRegex(pub.PublicationError, "nepatvirtintas įkelto PDF turinys"):
            pub.publish(selected, self.old, self.backend, first_u000003=True)
        self.assertNotIn("U000003", self.old)
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH") for x in self.backend.actions))

    def test_pirmas_rezimas_neapima_kitu_pdf(self):
        with self.assertRaisesRegex(pub.PublicationError, "tik U000003"):
            pub.publish(self.local, self.old, self.backend, first_u000003=True)
        self.assertEqual(self.backend.actions, [])

    def test_u000003_pilotas_reikalauja_visu_saugikliu(self):
        valid = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
                 "GITHUB_REF": "refs/heads/main", "DRIVE_PILOT_CONFIRMATION": "PUBLISH U000003",
                 "DRIVE_PDF_PUBLICATION_ENABLED": ""}
        for change in [{"GITHUB_ACTIONS": "false"}, {"GITHUB_EVENT_NAME": "push"},
                       {"GITHUB_REF": "refs/heads/kita"}, {"DRIVE_PILOT_CONFIRMATION": ""},
                       {"DRIVE_PILOT_CONFIRMATION": "publish U000003"},
                       {"DRIVE_PILOT_CONFIRMATION": "PUBLISH U000001"}]:
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), "--publish", "--only",
                                "U000003", "--pilot-u000003"], env=dict(valid, **change),
                               capture_output=True, text=True)
            with self.subTest(change=change):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("Pilotas leidžiamas tik", p.stderr)
        for args in (["--publish", "--only", "U000001", "--pilot-u000003"],
                     ["--publish", "--pilot-u000003"],
                     ["--dry-run", "--only", "U000003", "--pilot-u000003"],
                     ["--publish", "--only", "U000003", "--first-u000003"],
                     ["--dry-run", "--only", "U000001", "--first-u000003"]):
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), *args], env=valid,
                               capture_output=True, text=True)
            with self.subTest(args=args):
                self.assertNotEqual(p.returncode, 0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            with patch.object(pub, "REGISTRY", path), \
                 patch.object(pub, "local_files", return_value={"U000003": self.local["U000003"]}), \
                 patch.object(pub, "RcloneBackend", return_value=self.backend), \
                 patch.dict(os.environ, valid, clear=True), \
                 patch.object(sys, "argv", [str(pub.__file__), "--publish", "--only", "U000003", "--pilot-u000003"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pub.main()
            saved = json.loads(path.read_text())
            self.assertEqual(saved["U000003"], entry("NEW_3"))
            self.assertEqual(saved["U000001"], self.old["U000001"])
            self.assertEqual(saved["U000002"], self.old["U000002"])

    def test_u000004_pirmas_publikavimas_ir_senu_id_apsauga(self):
        self.local["U000004"] = local("U000004", "4" * 32)
        selected = {"U000004": self.local["U000004"]}
        with contextlib.redirect_stdout(io.StringIO()):
            result = pub.publish(selected, self.old, self.backend, first_u000004=True)
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(result["U000002"], self.old["U000002"])
        self.assertEqual(result["U000004"], entry("NEW_4"))
        self.assertEqual(self.backend.files["U000004"]["md5"], selected["U000004"]["md5"])
        changes = [x for x in self.backend.actions if isinstance(x, tuple) and x[0] in ("PATCH", "POST")]
        self.assertTrue(changes)
        self.assertTrue(all("files/NEW_4" in action[1] for action in changes))
        self.assertTrue(self.backend.states["NEW_4"]["restricted"])
        self.assertTrue(pub.drive.permission_ok(self.backend.states["NEW_4"]["permission"]))
        copy_actions = [x for x in self.backend.actions if isinstance(x, tuple) and x[0] == "copy"]
        self.assertEqual(copy_actions[0][1], (selected["U000004"]["path"],))

    def test_u000004_jau_registre_ar_drive_sustabdo_pries_copy(self):
        self.local["U000004"] = local("U000004", "4" * 32)
        selected = {"U000004": self.local["U000004"]}
        with self.assertRaisesRegex(pub.PublicationError, "jau yra registre"):
            pub.publish(selected, {**self.old, "U000004": entry("NEW_4")}, self.backend, first_u000004=True)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))
        self.backend.files["U000004"] = {"id": "NEW_4", "md5": "4" * 32}
        for operation in (pub.publish, pub.preview):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(pub.PublicationError, "jau yra Drive"):
                operation(selected, self.old, self.backend, first_u000004=True)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "copy" for x in self.backend.actions))

    def test_u000004_nesutapus_md5_teises_ir_registras_nekeičiami(self):
        self.local["U000004"] = local("U000004", "4" * 32)
        selected = {"U000004": self.local["U000004"]}
        self.backend.new_hashes["U000004"] = "9" * 32
        with self.assertRaisesRegex(pub.PublicationError, "nepatvirtintas įkelto PDF turinys"):
            pub.publish(selected, self.old, self.backend, first_u000004=True)
        self.assertNotIn("U000004", self.old)
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH") for x in self.backend.actions))

    def test_u000004_pirmas_rezimas_neapima_kitu_pdf(self):
        self.local["U000004"] = local("U000004", "4" * 32)
        with self.assertRaisesRegex(pub.PublicationError, "tik U000004"):
            pub.publish(self.local, self.old, self.backend, first_u000004=True)
        self.assertEqual(self.backend.actions, [])

    def test_u000004_pilotas_reikalauja_visu_saugikliu(self):
        self.local["U000004"] = local("U000004", "4" * 32)
        valid = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
                 "GITHUB_REF": "refs/heads/main", "DRIVE_PILOT_CONFIRMATION": "PUBLISH U000004",
                 "DRIVE_PDF_PUBLICATION_ENABLED": ""}
        for change in [{"GITHUB_ACTIONS": "false"}, {"GITHUB_EVENT_NAME": "push"},
                       {"GITHUB_REF": "refs/heads/kita"}, {"DRIVE_PILOT_CONFIRMATION": ""},
                       {"DRIVE_PILOT_CONFIRMATION": "publish U000004"},
                       {"DRIVE_PILOT_CONFIRMATION": "PUBLISH U000001"}]:
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), "--publish", "--only",
                                "U000004", "--pilot-u000004"], env=dict(valid, **change),
                               capture_output=True, text=True)
            with self.subTest(change=change):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("Pilotas leidžiamas tik", p.stderr)
        for args in (["--publish", "--only", "U000001", "--pilot-u000004"],
                     ["--publish", "--pilot-u000004"],
                     ["--dry-run", "--only", "U000004", "--pilot-u000004"],
                     ["--publish", "--only", "U000004", "--first-u000004"],
                     ["--dry-run", "--only", "U000001", "--first-u000004"]):
            p = subprocess.run([sys.executable, "-B", str(pub.__file__), *args], env=valid,
                               capture_output=True, text=True)
            with self.subTest(args=args):
                self.assertNotEqual(p.returncode, 0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drive_links.json"
            path.write_text(json.dumps(self.old))
            with patch.object(pub, "REGISTRY", path), \
                 patch.object(pub, "local_files", return_value={"U000004": self.local["U000004"]}), \
                 patch.object(pub, "RcloneBackend", return_value=self.backend), \
                 patch.dict(os.environ, valid, clear=True), \
                 patch.object(sys, "argv", [str(pub.__file__), "--publish", "--only", "U000004", "--pilot-u000004"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                pub.main()
            saved = json.loads(path.read_text())
            self.assertEqual(saved["U000004"], entry("NEW_4"))
            self.assertEqual(saved["U000001"], self.old["U000001"])
            self.assertEqual(saved["U000002"], self.old["U000002"])

    def test_po_teisiu_keitimo_dar_karta_tikrinami_id_ir_md5(self):
        original = self.backend.apply_and_verify
        def pakeisti(task, fid):
            original(task, fid)
            self.backend.files[task]["md5"] = "c" * 32
        self.backend.apply_and_verify = pakeisti
        with self.assertRaisesRegex(pub.PublicationError, "pasikeitė PDF ID arba turinys"):
            self.execute()

    def test_po_teisiu_keitimo_pasikeites_drive_id_atmetamas(self):
        original = self.backend.apply_and_verify
        def pakeisti(task, fid):
            original(task, fid)
            if task == "U000001":
                self.backend.files[task]["id"] = "KITAS_ID"
        self.backend.apply_and_verify = pakeisti
        with self.assertRaisesRegex(pub.PublicationError, "pasikeitė Drive ID"):
            self.execute()

    def test_pirmas_workflow_push_praleidzia_publikavima(self):
        workflow = (BANKAS.parent / ".github/workflows/publikuoti-uzdavinius.yml").read_text()
        step = workflow.split("      - name: Guard first publication of this workflow\n", 1)[1]
        script = step.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "git"
            executable.write_text('#!/bin/sh\nexit "$FAKE_GIT_EXIT"\n')
            executable.chmod(0o755)
            output = Path(directory) / "output"
            for event, git_exit, expected in [("push", "1", "skip=true"),
                                               ("push", "0", "skip=false"),
                                               ("workflow_dispatch", "1", "skip=false")]:
                output.unlink(missing_ok=True)
                env = dict(os.environ, PATH=directory, GITHUB_OUTPUT=str(output),
                           GITHUB_EVENT_NAME=event, GITHUB_SHA="commit-id",
                           FAKE_GIT_EXIT=git_exit)
                result = subprocess.run(["/bin/bash", "-c", script], env=env,
                                        capture_output=True, text=True)
                with self.subTest(event=event, git_exit=git_exit):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected, output.read_text())

    def test_workflow_registro_git_irasymai_ir_klaidos(self):
        workflow = (BANKAS.parent / ".github/workflows/publikuoti-uzdavinius.yml").read_text()
        step = workflow.split("      - name: Persist verified registry to main\n", 1)[1]
        script = step.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "git"
            executable.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$CALL_LOG"
case "$1" in
  rev-parse) printf '%s\\n' "$FAKE_MAIN" ;;
  diff) exit "$FAKE_DIFF" ;;
  push) exit "$FAKE_PUSH" ;;
esac
''')
            executable.chmod(0o755)
            log = Path(directory) / "calls"
            cases = [
                ("same", "1", "0", True, True),
                ("same", "0", "0", True, False),
                ("same", "1", "1", False, True),
                ("changed", "1", "0", False, False),
            ]
            for main, diff, push, success, push_called in cases:
                log.unlink(missing_ok=True)
                env = dict(os.environ, PATH=directory, CALL_LOG=str(log), GITHUB_SHA="same",
                           FAKE_MAIN=main, FAKE_DIFF=diff, FAKE_PUSH=push)
                result = subprocess.run(["/bin/bash", "-c", script], env=env,
                                        capture_output=True, text=True)
                calls = log.read_text()
                with self.subTest(main=main, diff=diff, push=push):
                    self.assertEqual(result.returncode == 0, success, result.stderr)
                    self.assertEqual("push origin HEAD:main" in calls, push_called)
                    self.assertNotIn("--force", calls)
                    if push_called:
                        self.assertIn("add -- Uzduociu_bankas/drive_links.json", calls)
                        self.assertIn("Uzduociu_bankas/drive_publication_state.json", calls)

    def test_workflow_pakeitimu_atranka_tusciam_ir_netusciam_sarasui(self):
        workflow = (BANKAS.parent / ".github/workflows/publikuoti-uzdavinius.yml").read_text()
        step = workflow.split("      - name: Find changed task PDFs\n", 1)[1]
        script = step.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "python3"
            executable.write_text('''#!/bin/sh
case "$1" in
  -c) exec "$REAL_PYTHON" "$@" ;;
  *) printf '%s\\n' "$FAKE_TASKS" ;;
esac
''')
            executable.chmod(0o755)
            output = Path(directory) / "output"
            for tasks, expected in [([], "has_pdfs=false"), (["U000001", "U000003"], "has_pdfs=true")]:
                output.unlink(missing_ok=True)
                env = dict(os.environ, PATH=directory, RUNNER_TEMP=directory,
                           GITHUB_OUTPUT=str(output), GITHUB_SHA="f" * 40,
                           FAKE_TASKS=json.dumps({"tasks": tasks}), REAL_PYTHON=sys.executable)
                p = subprocess.run(["/bin/bash", "-c", script], env=env, capture_output=True, text=True)
                with self.subTest(tasks=tasks):
                    self.assertEqual(p.returncode, 0, p.stderr)
                    self.assertEqual(output.read_text().strip(), expected)

    def test_pavojingas_cli_be_publish_neveikia(self):
        p = subprocess.run([sys.executable, "-B", str(pub.__file__)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--publish", p.stderr)

    def test_dry_run_nesiuncia_mutaciju(self):
        with contextlib.redirect_stdout(io.StringIO()):
            pub.preview(self.local, self.old, self.backend)
        self.assertIn("dry-run", self.backend.actions)
        self.assertNotIn("U000003", self.backend.files)
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ("POST", "PATCH") for x in self.backend.actions))


class GitPakeitimuTestai(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.bank = self.root / "Uzduociu_bankas"
        self.bank.mkdir()
        self.write_pdf("U000001", b"pirmas senas")
        self.write_pdf("U000002", b"antras nepakites")
        self.commit("pradinis")
        self.base = self.head()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def head(self):
        return self.git("rev-parse", "HEAD").decode().strip()

    def write_pdf(self, task, contents):
        folder = self.bank / "Uzdaviniai" / task
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{task}.pdf").write_bytes(contents)

    def commit(self, message):
        self.git("add", "--all")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", message)

    def test_naujas_pdf_atrenkamas(self):
        self.write_pdf("U000003", b"naujas pdf")
        self.commit("naujas")
        changed = pub.changed_files(self.root, self.base, self.head())
        self.assertEqual(list(changed), ["U000003"])
        self.assertIsNone(changed["U000003"]["previous_md5"])
        self.assertEqual(changed["U000003"]["md5"], hashlib.md5(b"naujas pdf").hexdigest())

    def test_pakeistas_ir_nepakites_pdf(self):
        self.write_pdf("U000001", b"pirmas naujas")
        self.commit("pakeistas")
        changed = pub.changed_files(self.root, self.base, self.head())
        self.assertEqual(list(changed), ["U000001"])
        self.assertEqual(changed["U000001"]["previous_md5"], hashlib.md5(b"pirmas senas").hexdigest())
        self.assertNotIn("U000002", changed)

    def test_keli_pdf_ir_keli_commit(self):
        self.write_pdf("U000001", b"pirmas naujas")
        self.commit("pirmas push")
        self.write_pdf("U000002", b"antras naujas")
        self.write_pdf("U000003", b"trecias naujas")
        self.commit("antras push")
        changed = pub.changed_files(self.root, self.base, self.head())
        self.assertEqual(list(changed), ["U000001", "U000002", "U000003"])

    def test_tarpiniu_commit_maisos_teisetam_atkartojimui(self):
        self.write_pdf("U000001", b"tarpine versija")
        self.commit("ankstesnis push")
        self.write_pdf("U000001", b"velesne versija")
        self.commit("velesnis push")
        changed = pub.changed_files(self.root, self.base, self.head())["U000001"]
        self.assertIn(hashlib.md5(b"pirmas senas").hexdigest(), changed["known_md5"])
        self.assertIn(hashlib.md5(b"tarpine versija").hexdigest(), changed["known_md5"])
        self.assertIn(hashlib.md5(b"velesne versija").hexdigest(), changed["known_md5"])

    def test_tex_pakeitimas_neatrenka_pdf(self):
        (self.bank / "Uzdaviniai/U000001/U000001.tex").write_text("pakeista sąlyga")
        self.commit("tik tex")
        self.assertEqual(pub.changed_files(self.root, self.base, self.head()), {})

    def test_grazintas_pradinis_pdf_neatrenkamas(self):
        self.write_pdf("U000001", b"laikinas pakeitimas")
        self.commit("pakeistas")
        self.write_pdf("U000001", b"pirmas senas")
        self.commit("atstatytas")
        self.assertEqual(pub.changed_files(self.root, self.base, self.head()), {})

    def test_neteisinga_arba_ne_istorijos_zyma_sustabdo(self):
        with self.assertRaises(pub.PublicationError):
            pub.changed_files(self.root, "blogas", self.head())
        with self.assertRaises(pub.PublicationError):
            pub.changed_files(self.root, "0" * 40, self.head())

    def test_nepakeitus_pdf_nera_jokiu_drive_operaciju(self):
        checkpoint = self.bank / "drive_publication_state.json"
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        (self.bank / "README.md").write_text("tik dokumentacija")
        self.commit("tik dokumentacija")
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        before = checkpoint.read_bytes()
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "CHECKPOINT", checkpoint), \
             patch.object(pub, "RcloneBackend") as backend, \
             patch.object(pub, "write_registry") as write_registry, \
             patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "true"}), \
             patch.object(sys, "argv", [str(pub.__file__), "--publish", "--target-commit", self.head()]), \
             contextlib.redirect_stdout(io.StringIO()):
            pub.main()
        backend.assert_not_called()
        write_registry.assert_not_called()
        self.assertEqual(checkpoint.read_bytes(), before)

    def test_pakeitimu_sarasas_nereikalauja_drive_prisijungimo(self):
        self.write_pdf("U000003", b"naujas")
        self.commit("pdf")
        checkpoint = self.bank / "drive_publication_state.json"
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        output = io.StringIO()
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "CHECKPOINT", checkpoint), \
             patch.object(pub, "RcloneBackend") as backend, patch.dict(os.environ, {}, clear=True), \
             patch.object(sys, "argv", [str(pub.__file__), "--list-changed", "--target-commit", self.head()]), \
             contextlib.redirect_stdout(output):
            pub.main()
        backend.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {"tasks": ["U000003"]})

    def test_is_paskutinio_sekmingo_commit_apdorojamas_ir_ankstesnis_nepavykes_push(self):
        self.write_pdf("U000001", b"dar nepublikuotas")
        self.commit("ankstesnis push")
        (self.bank / "README.md").write_text("vėlesnis push")
        self.commit("velesnis push be pdf")
        changed = pub.changed_files(self.root, self.base, self.head())
        self.assertEqual(list(changed), ["U000001"])

    def test_localus_neirasytas_pdf_nesupainiojamas_su_commit(self):
        self.write_pdf("U000001", b"commite naujas")
        self.commit("pdf")
        target = self.head()
        checkpoint = self.bank / "drive_publication_state.json"
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        self.write_pdf("U000001", b"vietinis kitoks")
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "CHECKPOINT", checkpoint), \
             patch.object(pub, "RcloneBackend") as backend, \
             patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "true"}), \
             patch.object(sys, "argv", [str(pub.__file__), "--publish", "--target-commit", target]), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                pub.main()
        self.assertNotEqual(error.exception.code, 0)
        backend.assert_not_called()

    def test_uzbaigus_keiciasi_tik_sekmingo_commit_zyma(self):
        self.write_pdf("U000001", b"atnaujintas")
        self.write_pdf("U000003", b"naujas")
        self.commit("du pdf")
        target = self.head()
        checkpoint = self.bank / "drive_publication_state.json"
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        registry_path = self.bank / "drive_links.json"
        old = {"U000001": entry("ID_1"), "U000002": entry("ID_2")}
        registry_path.write_text(json.dumps(old))
        fake = FakeBackend({"U000001": {"id": "ID_1", "md5": hashlib.md5(b"pirmas senas").hexdigest()},
                            "U000002": {"id": "ID_2", "md5": hashlib.md5(b"antras nepakites").hexdigest()}})
        fake.new_hashes["U000001"] = hashlib.md5(b"atnaujintas").hexdigest()
        fake.new_hashes["U000003"] = hashlib.md5(b"naujas").hexdigest()
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "CHECKPOINT", checkpoint), \
             patch.object(pub, "REGISTRY", registry_path), patch.object(pub, "RcloneBackend", return_value=fake), \
             patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "true"}), \
             patch.object(sys, "argv", [str(pub.__file__), "--publish", "--target-commit", target]), \
             contextlib.redirect_stdout(io.StringIO()):
            pub.main()
        self.assertEqual(json.loads(checkpoint.read_text())["last_published_commit"], target)
        registry = json.loads(registry_path.read_text())
        self.assertEqual(registry["U000001"], old["U000001"])
        self.assertEqual(registry["U000002"], old["U000002"])
        self.assertEqual(registry["U000003"], entry("NEW_3"))
        copies = [x for x in fake.actions if isinstance(x, tuple) and x[0] == "copy"]
        self.assertEqual(set(copies[0][1]), {
            "Uzduociu_bankas/Uzdaviniai/U000001/U000001.pdf",
            "Uzduociu_bankas/Uzdaviniai/U000003/U000003.pdf"})
        changes = [x for x in fake.actions if isinstance(x, tuple) and x[0] in ("PATCH", "POST")]
        self.assertTrue(all("files/ID_2" not in action[1] for action in changes))

    def test_api_klaida_nepakeicia_registro_ir_publikavimo_žymos(self):
        self.write_pdf("U000003", b"naujas")
        self.commit("naujas")
        target = self.head()
        checkpoint = self.bank / "drive_publication_state.json"
        checkpoint.write_text(json.dumps({"last_published_commit": self.base}))
        registry_path = self.bank / "drive_links.json"
        old = {"U000001": entry("ID_1"), "U000002": entry("ID_2")}
        registry_path.write_text(json.dumps(old))
        checkpoint_before = checkpoint.read_bytes()
        registry_before = registry_path.read_bytes()
        fake = FakeBackend({"U000001": {"id": "ID_1", "md5": hashlib.md5(b"pirmas senas").hexdigest()},
                            "U000002": {"id": "ID_2", "md5": hashlib.md5(b"antras nepakites").hexdigest()}})
        fake.new_hashes["U000003"] = hashlib.md5(b"naujas").hexdigest()
        fake.failed = True
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "CHECKPOINT", checkpoint), \
             patch.object(pub, "REGISTRY", registry_path), patch.object(pub, "RcloneBackend", return_value=fake), \
             patch.dict(os.environ, {"DRIVE_PDF_PUBLICATION_ENABLED": "true"}), \
             patch.object(sys, "argv", [str(pub.__file__), "--publish", "--target-commit", target]), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                pub.main()
        self.assertNotEqual(error.exception.code, 0)
        self.assertEqual(checkpoint.read_bytes(), checkpoint_before)
        self.assertEqual(registry_path.read_bytes(), registry_before)


if __name__ == "__main__":
    unittest.main()
