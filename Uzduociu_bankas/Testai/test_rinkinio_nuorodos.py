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

    def paleisti(self):
        return subprocess.run([sys.executable, str(self.bankas / "Skriptai/generuoti.py"),
                               "--rinkinys"], capture_output=True, text=True)

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
