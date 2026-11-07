# Uždavinių PDF publikavimas

Publikavimas į Drive pagal nutylėjimą išjungtas. Tiksliai nustačius GitHub
Actions repozitorijos kintamąjį `DRIVE_PDF_PUBLICATION_ENABLED=true`, leidžiami
`main` push ir rankiniai tikri publikavimo vykdymai. Be šio kintamojo leidžiamas
tik rankinis `workflow_dispatch` bandymas su `apply=false`. Workflow taip pat
praleidžia Drive operacijas per pirmą push, kuriuo jis pats pridedamas.

Publikuojami tik Git sekami `Uzduociu_bankas/Uzdaviniai/UXXXXXX/UXXXXXX.pdf`
failai. Prieš `rclone copy` ir po jo patikrinami anksčiau registre išsaugoti
Drive ID; po kopijavimo patikrinamas ir turinio MD5. Teisės nustatomos ir
patvirtinamos tik šiems PDF. Po visų patikrų `drive_links.json` papildomas
naujais ID ir siunčiamas į `main`, jeigu šaka per vykdymą nepasikeitė.
`rclone copy` nešalina kitų Drive failų. Esamas atskiras `sync-drive.yml`
lieka su `--dry-run`.

Saugiam bandymui: pirmiausia rankiniu workflow vykdymu pasirinkite `apply=false`
ir `U000001`. Vėlesniam tikram bandymui būtina aiškiai nustatyti kintamąjį
`true` ir pasirinkti `apply=true`. Kintamasis taip pat leidžia automatinį
publikavimą po `main` push, todėl bandymo metu venkite kitų push. Pirmiausia
patikrinkite esamą Drive API autentifikaciją, GitHub Actions rašymo leidimus ir
šakos apsaugas. Naujų PDF ID registrui patikrinti naudokite atskirą patvirtintą
bandomąjį uždavinį.

Pakeitimai Drive ir registro GitHub commit nėra viena transakcija. Jei dalis
operacijų nepavyksta, ankstesni pakeitimai neatšaukiami. Jei naujas PDF liko
Drive be registro įrašo, pakartotinis vykdymas jį priims tik jeigu kelias
vienareikšmis, o MD5 atitinka Git PDF. MD5 yra turinio klaidų patikra, o ne
apsauga nuo tyčinio klastojimo. Pasikeitus anksčiau įregistruotam ID,
atsiradus dublikatui ar nesutampant turiniui, vykdymas nutraukiamas.

`anyone` leidžia prieigą visiems, turintiems nuorodą. Drive apribojimai
neužkerta kelio ekrano kopijoms. Lygiagretūs nepriklausomi Drive teisių
keitėjai gali konkuruoti su šiuo workflow. Automatiniai testai imituoja API:
OAuth atnaujinimą, Drive politiką, GitHub šakos apsaugas ir tikrą skaitytojo
sąsają reikia patikrinti atskirai. Testų komanda:

```sh
python3 -B -m unittest discover -s Uzduociu_bankas/Testai -p test_publikavimas.py -v
```
