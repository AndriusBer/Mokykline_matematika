import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BANKAS = Path(__file__).resolve().parents[1]


class RinkinioNuoroduTestai(unittest.TestCase):
    def setUp(self):
        self.laikinas = tempfile.TemporaryDirectory()
        self.addCleanup(self.laikinas.cleanup)
        self.bankas = Path(self.laikinas.name) / "bankas"
        for vardas in ("Sablonai", "Skriptai", "Rinkiniai", "Uzdaviniai"):
            shutil.copytree(BANKAS / vardas, self.bankas / vardas)
        shutil.copyfile(BANKAS / "drive_links.json", self.bankas / "drive_links.json")
        self.registras = self.bankas / "drive_links.json"
        self.pdf = self.bankas / "Rinkiniai/bandomasis.pdf"
        self.pradinis_pdf = self.pdf.read_bytes()

    def paleisti(self, *argumentai):
        return subprocess.run([sys.executable, str(self.bankas / "Skriptai/generuoti.py"),
                               "--rinkinys", *argumentai], capture_output=True, text=True)

    def test_numatytasis_rinkinys_ir_vieno_uzdavinio_rezimas(self):
        rezultatas = self.paleisti()
        self.assertEqual(rezultatas.returncode, 0, rezultatas.stderr)
        self.assertTrue(self.pdf.read_bytes().startswith(b"%PDF-"))
        rezultatas = subprocess.run([sys.executable, str(self.bankas / "Skriptai/generuoti.py"), "U000001"],
                                   capture_output=True, text=True)
        self.assertEqual(rezultatas.returncode, 0, rezultatas.stderr)
        self.assertTrue((self.bankas / "Uzdaviniai/U000001/U000001.pdf").read_bytes().startswith(b"%PDF-"))

    def test_pasirinktas_rinkinys_generuojamas_is_atskiro_failo(self):
        saltinis = self.bankas / "Rinkiniai/Kitas rinkinys ąžuolas.tex"
        shutil.copyfile(self.bankas / "Rinkiniai/bandomasis.tex", saltinis)
        for vardas in ("Kitas rinkinys ąžuolas", "Kitas rinkinys ąžuolas.tex"):
            with self.subTest(vardas=vardas):
                rezultatas = self.paleisti(vardas)
                self.assertEqual(rezultatas.returncode, 0, rezultatas.stderr)
                self.assertTrue((self.bankas / "Rinkiniai/Kitas rinkinys ąžuolas.pdf").read_bytes().startswith(b"%PDF-"))
                self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)
                self.assertFalse(list(self.bankas.glob(".latex-*")))

    def test_neleistinas_arba_nerastas_rinkinys(self):
        for vardas in ("../bandomasis", "/tmp/test.tex", "a/b", "x.tex.tex", "nera"):
            with self.subTest(vardas=vardas):
                rezultatas = self.paleisti(vardas)
                self.assertNotEqual(rezultatas.returncode, 0)
                self.assertIn("Klaida:", rezultatas.stderr)
                self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)

    def test_pasirinkto_rinkinio_nuorodos_privalomos(self):
        saltinis = self.bankas / "Rinkiniai/kitas.tex"
        shutil.copyfile(self.bankas / "Rinkiniai/bandomasis.tex", saltinis)
        irasai = json.loads(self.registras.read_text())
        del irasai["U000001"]
        self.registras.write_text(json.dumps(irasai))
        rezultatas = self.paleisti("kitas")
        self.assertNotEqual(rezultatas.returncode, 0)
        self.assertIn("Nerasta nuoroda uzdaviniui U000001", rezultatas.stderr)
        self.assertFalse((self.bankas / "Rinkiniai/kitas.pdf").exists())

    def test_saltinio_ir_pdf_simbolines_nuorodos_uzdraustos(self):
        saltinis = self.bankas / "Rinkiniai/kitas.tex"
        saltinis.symlink_to(self.bankas / "Rinkiniai/bandomasis.tex")
        self.assertNotEqual(self.paleisti("kitas").returncode, 0)
        saltinis.unlink()
        shutil.copyfile(self.bankas / "Rinkiniai/bandomasis.tex", saltinis)
        (self.bankas / "Rinkiniai/kitas.pdf").symlink_to(self.pdf)
        self.assertNotEqual(self.paleisti("kitas").returncode, 0)
        self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)

    def test_trukstama_nuoroda_nutraukia_generavima(self):
        irasai = json.loads(self.registras.read_text())
        del irasai["U000002"]
        self.registras.write_text(json.dumps(irasai))
        rezultatas = self.paleisti()
        self.assertNotEqual(rezultatas.returncode, 0)
        self.assertIn("Nerasta nuoroda uzdaviniui U000002", rezultatas.stderr)
        self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)
        self.assertFalse(list(self.bankas.glob(".latex-*")))

    def test_netinkama_nuoroda_nutraukia_generavima(self):
        irasai = json.loads(self.registras.read_text())
        irasai["U000001"]["url"] = "https://example.com/"
        self.registras.write_text(json.dumps(irasai))
        rezultatas = self.paleisti()
        self.assertNotEqual(rezultatas.returncode, 0)
        self.assertIn("Netinkama Drive nuoroda uždaviniui U000001", rezultatas.stderr)
        self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)
        self.assertFalse(list(self.bankas.glob(".latex-*")))

    def test_trukstamas_registras_nutraukia_generavima(self):
        self.registras.unlink()
        rezultatas = self.paleisti()
        self.assertNotEqual(rezultatas.returncode, 0)
        self.assertIn("Nerastas nuorodų registras", rezultatas.stderr)
        self.assertEqual(self.pdf.read_bytes(), self.pradinis_pdf)


if __name__ == "__main__":
    unittest.main()
