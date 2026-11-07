import contextlib
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
        self.next_ids = {"U000003": "NEW_3"}
        self.new_hashes = {"U000003": "hash3"}
        self.failed = False
        self.replace_id = False

    def list(self):
        self.actions.append("list")
        return [{"Path": local(task, "")["path"], "ID": data["id"], "IsDir": False,
                 "Hashes": {"MD5": data["md5"]}} for task, data in self.files.items()]

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
        self.local = {"U000001": local("U000001", "hash1"), "U000003": local("U000003", "hash3")}
        self.backend = FakeBackend({"U000001": {"id": "ID_1", "md5": "hash1"},
                                    "U000002": {"id": "ID_2", "md5": "hash2"}})

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

    def test_pakeistas_pdf_atnaujinamas_issaugant_drive_id(self):
        self.local["U000001"]["md5"] = "hash_atnaujintas"
        self.backend.new_hashes["U000001"] = "hash_atnaujintas"
        result = self.execute()
        self.assertEqual(result["U000001"], self.old["U000001"])
        self.assertEqual(self.backend.files["U000001"], {"id": "ID_1", "md5": "hash_atnaujintas"})

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
        self.backend.files["U000003"] = {"id": "OTHER", "md5": "bad"}
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
                           DRIVE_PDF_PUBLICATION_ENABLED=enabled)
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

    def test_po_teisiu_keitimo_dar_karta_tikrinami_id_ir_md5(self):
        original = self.backend.apply_and_verify
        def pakeisti(task, fid):
            original(task, fid)
            self.backend.files[task]["md5"] = "pasikeites"
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


if __name__ == "__main__":
    unittest.main()
