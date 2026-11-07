#!/usr/bin/env python3
"""Generuoja pasirinkto arba visų uždavinių PDF ir bandomąjį rinkinį."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BANKAS = Path(__file__).resolve().parents[1]
ID_FORMATAS = re.compile(r"U[0-9]{6}")


def tikrinti_uzdavini(identifikatorius):
    if not ID_FORMATAS.fullmatch(identifikatorius):
        raise ValueError("ID turi būti U ir šeši skaitmenys.")
    katalogas = BANKAS / "Uzdaviniai" / identifikatorius
    for vardas in (f"{identifikatorius}.tex", "meta.yaml"):
        if not (katalogas / vardas).is_file():
            raise ValueError(f"Nerastas failas: {katalogas / vardas}")
    return katalogas


def parengti_nuorodas(katalogas):
    registro_failas = BANKAS / "drive_links.json"
    try:
        with registro_failas.open(encoding="utf-8") as failas:
            def be_dublikatu(poros):
                rezultatas = {}
                for raktas, reiksme in poros:
                    if raktas in rezultatas:
                        raise ValueError(f"Pasikartojantis registro laukas: {raktas}")
                    rezultatas[raktas] = reiksme
                return rezultatas
            registras = json.load(failas, object_pairs_hook=be_dublikatu)
    except FileNotFoundError:
        raise ValueError(f"Nerastas nuorodų registras: {registro_failas}") from None
    if not isinstance(registras, dict):
        raise ValueError("Nuorodų registras turi būti JSON objektas")
    eilutes = []
    for identifikatorius, irasas in sorted(registras.items()):
        if not ID_FORMATAS.fullmatch(identifikatorius) or not isinstance(irasas, dict):
            raise ValueError(f"Netinkamas registro įrašas: {identifikatorius}")
        drive_id = irasas.get("drive_id")
        url = irasas.get("url")
        if (not isinstance(drive_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", drive_id)
                or url != f"https://drive.google.com/file/d/{drive_id}/view"):
            raise ValueError(f"Netinkama Drive nuoroda uždaviniui {identifikatorius}")
        eilutes.append(r"\expandafter\def\csname bankourl@" + identifikatorius
                       + r"\endcsname{\detokenize{" + url + "}}\n")
    nuorodu_failas = Path(katalogas) / "nuorodos.tex"
    nuorodu_failas.write_text("".join(eilutes), encoding="utf-8")
    return nuorodu_failas


def kompiliuoti(vardas, ivestis, paskirtis, rinkinys=False):
    with tempfile.TemporaryDirectory(prefix=".latex-", dir=BANKAS) as laikinas:
        if rinkinys:
            nuorodos = parengti_nuorodas(laikinas)
            ivestis = rf"\def\bankonuorodufailas{{{nuorodos}}}\input{{{ivestis}}}"
        for _ in range(2):
            procesas = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                 "-no-shell-escape", f"-output-directory={laikinas}",
                 f"-jobname={vardas}", ivestis],
                cwd=BANKAS, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if procesas.returncode:
                raise RuntimeError(procesas.stdout)
        shutil.copy2(Path(laikinas) / f"{vardas}.pdf", paskirtis)
    print(f"Sukurta: {paskirtis.relative_to(BANKAS)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    pasirinkimas = parser.add_mutually_exclusive_group(required=True)
    pasirinkimas.add_argument("id", nargs="?", help="U ir šeši skaitmenys")
    pasirinkimas.add_argument("--visi", action="store_true", help="Visi uždaviniai")
    pasirinkimas.add_argument("--rinkinys", action="store_true", help="Bandomasis rinkinys")
    args = parser.parse_args()
    try:
        if not shutil.which("xelatex"):
            raise ValueError("Nerasta XeLaTeX programa (xelatex).")
        if args.rinkinys:
            saltinis = BANKAS / "Rinkiniai/bandomasis.tex"
            if not saltinis.is_file():
                raise ValueError(f"Nerastas failas: {saltinis}")
            kompiliuoti("bandomasis", "Rinkiniai/bandomasis.tex",
                        saltinis.with_suffix(".pdf"), rinkinys=True)
            return
        if args.visi:
            identifikatoriai = sorted(
                p.name for p in (BANKAS / "Uzdaviniai").iterdir()
                if p.is_dir() and ID_FORMATAS.fullmatch(p.name)
            )
            if not identifikatoriai:
                raise ValueError("Nerasta uždavinių katalogų su tinkamais ID.")
        else:
            identifikatoriai = [args.id]
        katalogai = [(i, tikrinti_uzdavini(i)) for i in identifikatoriai]
        if not (BANKAS / "Sablonai/sprendimas.tex").is_file():
            raise ValueError("Nerastas Sablonai/sprendimas.tex.")
        for identifikatorius, katalogas in katalogai:
            ivestis = (rf"\def\uzdavinioid{{{identifikatorius}}}"
                       r"\input{Sablonai/sprendimas.tex}")
            kompiliuoti(identifikatorius, ivestis,
                        katalogas / f"{identifikatorius}.pdf")
    except (ValueError, OSError, RuntimeError) as klaida:
        parser.exit(1, f"Klaida: {klaida}\n")


if __name__ == "__main__":
    main()
