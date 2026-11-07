# Uždavinių bankas

Kiekvienas uždavinys laikomas kataloge `Uzdaviniai/UXXXXXX/`. Jo `.tex` faile
vienoje vietoje saugomos `salyga`, `atsakymas` ir `sprendimas` aplinkos;
`meta.yaml` aprašo uždavinį, o to paties ID PDF pateikia jo sprendimą.
Sprendimo PDF sąlyga ir atsakymas rodomi prieš sprendimą, kuris prasideda
naujame puslapyje. Ilgesnė sąlyga ar atsakymas gali užimti daugiau nei vieną
puslapį.

Pakeitus uždavinio `.tex`, PDF automatiškai nepergeneruojamas: paleiskite
atitinkamo ID generavimo komandą ir įtraukite naują PDF į Git commit. Vien
`.tex` pakeitimas nesukelia to PDF publikavimo į Drive.

Komandos iš projekto šakninio katalogo:

```sh
python3 Uzduociu_bankas/Skriptai/generuoti.py U000001
python3 Uzduociu_bankas/Skriptai/generuoti.py --visi
python3 Uzduociu_bankas/Skriptai/generuoti.py --rinkinys
```

Pirmoji komanda generuoja pasirinkto uždavinio sprendimo PDF, antroji – visų
uždavinių sprendimų PDF, trečioji – bandomąjį sąlygų rinkinį. ID turi būti
`U` ir šeši ASCII skaitmenys. Kiekvienam uždaviniui reikalingi
`Uzdaviniai/<ID>/<ID>.tex` ir `meta.yaml`. Generuojant visus uždavinius
netinkamo formato katalogų pavadinimai praleidžiami; YAML turinys netikrinamas.

Reikalingas XeLaTeX, Latin Modern šriftai ir bendro šablono paketai, įskaitant
Polyglossia, AMS, `environ`, `enumitem`, TikZ ir `hyperref`. Skriptas kiekvieną
PDF kompiliuoja du kartus; LaTeX pagalbiniai failai laikomi laikiname kataloge
ir pašalinami. Esamas PDF perrašomas tik sėkmingai sukompiliavus dokumentą.

## Uždavinių rinkiniai ir „Ats.“ nuorodos

Rinkinio `.tex` faile, `enumerate` aplinkoje, kiekvieną uždavinį įtraukite jo
pastoviu ID:

```latex
\begin{enumerate}[label=\arabic*.]
  \Uzdavinys{U000001}
  \Uzdavinys{U000002}
\end{enumerate}
```

Komanda įterpia sąlygą iš atitinkamo uždavinio `.tex`, automatiškai ją
sunumeruoja ir po sąlyga pateikia paspaudžiamą nuorodą „Ats.“ į to uždavinio
sprendimo PDF. Atsakymo ir sprendimo tekstai į rinkinį neįtraukiami. Keičiant
uždavinių eilę nuorodų paskirtis išlieka susieta su uždavinio ID.
Atidaryti nuorodą gali tik skaitytojai, kuriems suteikta atitinkamo Drive
failo peržiūros prieiga.

Generuojant `--rinkinys`, Python skaito `drive_links.json`, patikrina kiekvieno
įrašo Drive ID ir URL, sukuria laikiną LaTeX nuorodų failą ir perduoda jį
šablonui. Jei registro nėra, nuoroda netinkama arba reikalingo ID registre
trūksta, generavimas sustoja ir esamas rinkinio PDF neperrašomas. URL turi
atitikti `https://drive.google.com/file/d/<drive_id>/view` formą.

`Rinkiniai/bandomasis.tex` sąrašas valdomas rankiniu būdu. Šiuo metu jame yra
`U000001` ir `U000002`; kitam uždaviniui reikia pridėti jo `\Uzdavinys{...}`
komandą. `--visi` rinkinio nekeičia. Rinkinius kompiliuokite per
`generuoti.py --rinkinys`, kad būtų parengtos nuorodos. `environ` pagrindu
apibrėžtos aplinkos neskirtos `verbatim` tipo turiniui.

Testai:

```sh
python3 -B -m unittest discover -s Uzduociu_bankas/Testai -v
```

Apie Drive PDF publikavimo eigą, pirmąjį bandymą ir apribojimus skaitykite
[Publikavimas.md](Publikavimas.md).
