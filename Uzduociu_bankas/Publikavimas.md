# Uždavinių PDF publikavimas

Publikavimas į Drive pagal nutylėjimą išjungtas. Tiksliai nustačius GitHub
Actions repozitorijos kintamąjį `DRIVE_PDF_PUBLICATION_ENABLED=true`, leidžiami
`main` push ir rankiniai tikri publikavimo vykdymai. Kai kintamasis išjungtas,
leidžiamas rankinis `workflow_dispatch` dry-run ir atskira griežtai apribota
`U000001` ir pirmojo `U000003` tikro bandymo išimtys. Workflow praleidžia Drive operacijas per
pirmą push, kuriuo jis pats pridedamas.

Publikuojami tik Git sekami `Uzduociu_bankas/Uzdaviniai/UXXXXXX/UXXXXXX.pdf`
failai. Prieš `rclone copy` ir po jo patikrinami anksčiau registre išsaugoti
Drive ID; po kopijavimo ir po teisių nustatymo patikrinami failo ID ir turinio
MD5. Teisės nustatomos ir patvirtinamos tik šiems PDF. Po visų patikrų `drive_links.json` papildomas
naujais ID ir siunčiamas į `main`, jeigu šaka per vykdymą nepasikeitė.
`rclone copy` nešalina kitų Drive failų. Esamas atskiras `sync-drive.yml`
lieka su `--dry-run`.

Saugiam bandymui: pirmiausia rankiniu workflow vykdymu pasirinkite `apply=false`
ir `U000001`. Tikram rankiniam šio PDF bandymui bendro kintamojo įjungti
nereikia: pasirinkite `apply=true`, ID `U000001` ir patvirtinimo lauke tiksliai
įrašykite `PUBLISH U000001`. Išimtis veikia tik `workflow_dispatch` įvykiui
`main` šakoje. Pirmajam `U000003` publikavimui analogiškai pasirinkite
`task_id=U000003`, `apply=true` ir tiksliai `PUBLISH U000003`. Šis režimas
prieš kopijavimą privalo nerasti `U000003` nei registre, nei Drive uždavinių
kataloge. Pirmiausia paleiskite tą patį ID su `apply=false` ir patikrinkite
dry-run rezultatą. Kitiems PDF tikrai publikuoti reikia bendro kintamojo `true`;
rankinis publikavimas taip pat reikalauja `PUBLISH <ID>` patvirtinimo.
Pirmiausia patikrinkite esamą Drive API autentifikaciją, GitHub Actions rašymo
leidimus ir šakos apsaugas.

Pakeitimai Drive ir registro GitHub commit nėra viena transakcija. Jei dalis
operacijų nepavyksta, ankstesni pakeitimai neatšaukiami. Jei naujas PDF liko
Drive be registro įrašo, pakartotinis vykdymas jį priims tik jeigu kelias
vienareikšmis, o MD5 atitinka Git PDF. MD5 yra turinio klaidų patikra, o ne
apsauga nuo tyčinio klastojimo. Pasikeitus anksčiau įregistruotam ID,
atsiradus dublikatui ar nesutampant turiniui, vykdymas nutraukiamas.
Pirmojo `U000003` bandymo išimtis yra griežtesnė: po dalinio įkėlimo ji
neleis kartoti bandymo, kol esama Drive ir registro būsena nebus atskirai
peržiūrėta ir sutvarkyta; tai neleidžia tyliai perimti esamo failo.

`anyone` leidžia prieigą visiems, turintiems nuorodą. Drive apribojimai
neužkerta kelio ekrano kopijoms. Lygiagretūs nepriklausomi Drive teisių
keitėjai gali konkuruoti su šiuo workflow. Automatiniai testai imituoja API:
OAuth atnaujinimą, Drive politiką, GitHub šakos apsaugas ir tikrą skaitytojo
sąsają reikia patikrinti atskirai. Testų komanda:

```sh
python3 -B -m unittest discover -s Uzduociu_bankas/Testai -p test_publikavimas.py -v
```
