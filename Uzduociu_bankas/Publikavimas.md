# Uždavinių PDF publikavimas

Publikavimas į Drive pagal nutylėjimą išjungtas. Tiksliai nustačius GitHub
Actions repozitorijos kintamąjį `DRIVE_PDF_PUBLICATION_ENABLED=true`, leidžiami
`main` push ir rankiniai tikri publikavimo vykdymai. Kai kintamasis išjungtas,
leidžiamas rankinis `workflow_dispatch` dry-run ir atskira griežtai apribota
`U000001` ir pirmųjų `U000003` bei `U000004` tikrų bandymų išimtys. Workflow praleidžia Drive operacijas per
pirmą push, kuriuo jis pats pridedamas.

Po `main` push automatiškai atrenkami tik nauji arba turiniu pasikeitę Git
sekami `Uzduociu_bankas/Uzdaviniai/UXXXXXX/UXXXXXX.pdf` failai, palyginti su
paskutine sėkmingo publikavimo žyma `drive_publication_state.json`. Jei tokių
PDF nėra, rclone nepaleidžiamas ir jokių Drive rašymo operacijų nevyksta.
Jei ankstesnis publikavimas nepavyko, vėlesnis push gali pakartotinai apdoroti
jo dar nepatvirtintus PDF, net jeigu tame vėlesniame push pakeistas tik `.tex`.
Vien pakeitus `.tex`, būtina atskirai sugeneruoti ir į Git įtraukti atitinkamą
PDF – pats `.tex` pakeitimas naujo PDF nesukuria.

Prieš `rclone copy` ir po jo patikrinami anksčiau registre išsaugoti
Drive ID; po kopijavimo ir po teisių nustatymo patikrinami failo ID ir turinio
MD5. Teisės nustatomos ir patvirtinamos tik šiems PDF. Po visų patikrų `drive_links.json` papildomas
naujais ID ir siunčiamas į `main`, jeigu šaka per vykdymą nepasikeitė.
`rclone copy` nešalina kitų Drive failų. Esamas atskiras `sync-drive.yml`
lieka su `--dry-run`.

Pradinė žyma rodo į `f5ce3592d6b90ad323991aaf0a42c8fadf0ca491`: tai
pradinis Git palyginimo taškas, o ne įrodymas, kad visi senesni PDF jau
sutampa su Drive. Prieš įjungiant automatizavimą būtina atskirai patikrinti
esamų PDF ID, MD5 ir teises. Senesni už šią žymą pakeitimai automatiškai
neatrenkami. Žymos failo nešalinkite ir nekeiskite rankiniu būdu, kol neįvertinta
Git istorija ir Drive būsena. Trūkstama žyma, nepilna istorija ar ne protėvio
commit sustabdo vykdymą.

Sėkmingai patikrinus visus pasirinktus PDF, registras ir žyma įrašomi vienu Git
commit. Klaidos arba nepavykusio Git push atveju GitHub žyma nepasistūmėja;
kitas sėkmingai pradėtas vykdymas vėl atrinks nepatvirtintus pakeitimus. Jei
`main` pasikeičia vykdymo metu, job baigiamas klaida be force push. Eilė
serializuoja iki 100 laukiančių vykdymų; esant daugiau, dalis gali būti
atšaukta, o paskesnis vykdymas lygins nuo paskutinės išsaugotos žymos.

Saugiam bandymui: pirmiausia rankiniu workflow vykdymu pasirinkite `apply=false`
ir `U000001`. Tikram rankiniam šio PDF bandymui bendro kintamojo įjungti
nereikia: pasirinkite `apply=true`, ID `U000001` ir patvirtinimo lauke tiksliai
įrašykite `PUBLISH U000001`. Išimtis veikia tik `workflow_dispatch` įvykiui
`main` šakoje. Pirmajam `U000003` publikavimui analogiškai pasirinkite
`task_id=U000003`, `apply=true` ir tiksliai `PUBLISH U000003`. Šis režimas
prieš kopijavimą privalo nerasti `U000003` nei registre, nei Drive uždavinių
kataloge. Pirmiausia paleiskite tą patį ID su `apply=false` ir patikrinkite
dry-run rezultatą. Pirmojo `U000004` bandymo išimtis aprašyta toliau. Kitiems PDF tikrai publikuoti reikia bendro kintamojo `true`;
rankinis publikavimas taip pat reikalauja `PUBLISH <ID>` patvirtinimo.
Pirmiausia patikrinkite esamą Drive API autentifikaciją, GitHub Actions rašymo
leidimus ir šakos apsaugas.

Pakeitimai Drive ir registro GitHub commit nėra viena transakcija. Jei dalis
operacijų nepavyksta, ankstesni pakeitimai neatšaukiami. Jei naujas PDF liko
Drive be registro įrašo, pakartotinis vykdymas jį priims tik jeigu kelias
vienareikšmis, o MD5 atitinka Git PDF. MD5 yra turinio klaidų patikra, o ne
apsauga nuo tyčinio klastojimo. Pasikeitus anksčiau įregistruotam ID,
atsiradus dublikatui ar nesutampant turiniui, vykdymas nutraukiamas.
Pirmųjų `U000003` ir `U000004` bandymų išimtys yra griežtesnės: po dalinio įkėlimo ji
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

Pirmojo `U000004` piloto metu pasirinkite `task_id=U000004`, `apply=true` ir
tikslų patvirtinimą `PUBLISH U000004`. Pirmiau galima patikrinti su `apply=false`.
Pilotas sustoja, jei ID jau yra registre arba PDF randamas Drive. Po dalinio
įkėlimo pakartotinai nepaleiskite: pirmiausia išsiaiškinkite Drive ir registro būseną.
