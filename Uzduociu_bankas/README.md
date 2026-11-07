# Uždavinių bankas

Komandos iš projekto šakninio katalogo:

```sh
python3 Uzduociu_bankas/Skriptai/generuoti.py U000001
python3 Uzduociu_bankas/Skriptai/generuoti.py --visi
python3 Uzduociu_bankas/Skriptai/generuoti.py --rinkinys
```

Pirmoji komanda generuoja tik pasirinkto uždavinio sprendimo PDF, antroji –
visų uždavinių sprendimų PDF, trečioji – bandomąjį sąlygų rinkinį.
Galima vykdyti ir iš kito darbinio katalogo, pateikus skripto kelią.
Būtinas vienas iš šių trijų pasirinkimų.

ID formatas: `U` ir tiksliai šeši ASCII skaitmenys. Kiekvienam uždaviniui
būtini `Uzdaviniai/<ID>/<ID>.tex` ir `meta.yaml`. Visų uždavinių režimu
surandami tinkamo ID formato katalogai ir surikiuojami pagal ID; kitokie
katalogų pavadinimai praleidžiami. Visi pasirinkti šaltiniai patikrinami prieš
kompiliavimą. YAML turinys šiuo metu nevaliduojamas.

Kiekvienas uždavinio `.tex` yra fragmentas su `salyga`, `atsakymas` ir
`sprendimas` aplinkomis. Šiame faile saugomas visas uždavinio turinys, taip pat
TikZ brėžiniai ir vidiniai numeruoti sąrašai. `meta.yaml` saugo metaduomenis;
`google_drive_url: null` palikta būsimai nuorodai.

`Sablonai/sprendimas.tex` neturi numatytojo ID: jį pateikia generatorius.
`Sablonai/bendras.tex` apibrėžia abu režimus ir bendrus paketus.
Sprendimo dokumente sąlyga ir atsakymas eina prieš sprendimą, kuris
prasideda naujame puslapyje. Ilgas turinys gali užimti daugiau puslapių.
Rinkinio režimas įtraukia tik sąlygą kaip išorinio `enumerate` sąrašo punktą;
atsakymas ir sprendimas nevykdomi.

`Rinkiniai/bandomasis.tex` sąrašas valdomas rankiniu būdu: šiuo metu įtraukti
abu bandomieji uždaviniai. Naujam uždaviniui rinkinyje reikia pridėti `\input`.
`--visi` šio sąrašo nekeičia ir rinkinio automatiškai negeneruoja.

Reikalingas XeLaTeX, Latin Modern šriftai ir šablone naudojami paketai
(įskaitant Polyglossia, AMS, environ, enumitem ir TikZ).
Kiekvienas dokumentas kompiliuojamas du kartus su išjungtu shell escape.
Pagalbiniai failai laikomi laikiname kataloge banko viduje ir pašalinami tiek
sėkmės, tiek klaidos atveju. Klaidos išvestis pateikiama terminale.
PDF kopijuojamas į paskirties vietą tik sėkmingai baigus abu kompiliavimus;
esamas atitinkamo uždavinio PDF tada perrašomas. Visų uždavinių generavimas
nėra viena transakcija: vėlesnė klaida neatšaukia jau sugeneruotų PDF.

LaTeX šaltiniai laikomi patikimais projekto failais: tai nėra nepatikimo kodo
izoliavimo sistema. Aplinkos, renkančios turinį per `environ`, neskirtos
`verbatim` tipo turiniui. Šablonų keliai skaičiuojami nuo banko katalogo;
rankiniu būdu kompiliuojant reikia naudoti šį darbinį katalogą.

Pastebėta, kad VS Code automatinis kompiliavimas bandė naudoti pdfLaTeX
(ir paliko pagalbinius failus prie rinkinio). Šiam bankui naudokite aukščiau
pateiktą XeLaTeX skriptą; IDE kompiliavimo konfigūracija nekeičiama.
