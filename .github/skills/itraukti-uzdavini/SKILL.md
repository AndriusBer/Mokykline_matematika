---
name: itraukti-uzdavini
description: >-
  Įtraukti vartotojo pateiktą matematikos uždavinį arba LaTeX failo uždavinių rinkinį į
  Mokykline_matematika projekto Uzduociu_bankas nuo sąlygos iki patikrinto
  sprendimo PDF, metaduomenų, Git commit/push ir automatinės Google Drive
  publikavimo nuorodos, prireikus parengiant nuorodas turintį rinkinį. Naudoti, kai vartotojas prašo „įtrauk uždavinį į banką“,
  „pridėk į uždavinių banką“ arba iškviečia /itraukti-uzdavini.
user-invocable: true
disable-model-invocation: false
---

# Įtraukti matematikos uždavinį į uždavinių banką

## Tikslas ir įvestis

Vartotojas gali pateikti tik uždavinio sąlygą LaTeX formatu ir parašyti
„Įtrauk į uždavinių banką“. Dirbk savarankiškai nuo A iki Ž, **tačiau niekada
nepranešk apie atliktą publikavimą, kol jo nepatvirtino GitHub Actions ir
nuorodų registras**. Skill iškvietimas su uždaviniu reiškia leidimą vykdyti
aprašytą įprastą naujo uždavinio kūrimo, vieno izoliuoto commit ir push procesą.
Jeigu naudotojas aiškiai prašo tik parengti ar peržiūrėti, commit/push nedaryk.

Jeigu įvestyje trūksta informacijos, kuri **nebūtina** išspręsti uždavinį ir
sukurti įrašą, jos nespėliok: naudok `null`, tuščią sąrašą arba atitinkamą
nepatvirtintą būseną pagal schemą. Klausk tik tada, kai sąlyga esmingai
dviprasmiška, negali patikimai nustatyti teisingo rezultato, aptiktas
dublikatas, arba operacija nesaugi.

## Projekto dokumentai ir nekintami faktai

- Projektas: `Mokykline_matematika`; banko šaknis `Uzduociu_bankas/`.
- Uždaviniai: `Uzdaviniai/UXXXXXX/UXXXXXX.tex`, `UXXXXXX.pdf`, `meta.yaml`.
- LaTeX aplinkos: `salyga`, `atsakymas`, `sprendimas`; pirmiausia perskaityk
  `Uzduociu_bankas/README.md`, `Sablonai/bendras.tex`,
  `Sablonai/sprendimas.tex` ir gretimus uždavinius.
- Komanda iš projekto šaknies:
  `python3 Uzduociu_bankas/Skriptai/generuoti.py UXXXXXX`.
- Meta v1 dokumentai, jeigu įdiegti:
  `Uzduociu_bankas/Metaduomenys/metaduomenu_standartas_v1.md`,
  `meta.schema.json`, `zodynas_v1.yaml`.
- Metaduomenų vienintelis šaltinis: kiekvieno uždavinio `meta.yaml`.
- Viešų PDF nuorodų vienintelis šaltinis:
  `Uzduociu_bankas/drive_links.json`.
- Publikavimo progreso žyma:
  `Uzduociu_bankas/drive_publication_state.json`.
- Workflow: `.github/workflows/publikuoti-uzdavinius.yml`
  (`Publish task PDFs to Drive`). Automatinė publikacija prasideda **tik po
  naujo / pasikeitusio PDF push į `main`**, kai nustatytas GitHub Actions
  kintamasis `DRIVE_PDF_PUBLICATION_ENABLED=true`.
- Negalima tiesiogiai rašyti į Drive, perrašyti registro, keisti publikavimo
  žymos arba įjungti `sync-drive.yml` (jis privalo išlikti `--dry-run`).
- Vieno uždavinio režimu rinkinį pildyk tik naudotojui paprašius. Kelių
  uždavinių rinkinio importo režimu parenk atskirą rinkinį pagal toliau
  pateiktą procedūrą, jeigu naudotojas neprašo kitaip.

## 1. Išankstinės saugos patikros

1. Įsitikink, kad atidarytas šis projektas ir jo Git šaknis.
2. Užfiksuok `git status --short`, `git branch --show-current` ir `git rev-parse HEAD`.
   **Nepanaikink ir neperrašyk jokių vartotojo vietinių pakeitimų**.
3. Vykdyk `git fetch origin main`, palygink vietinį `HEAD` su `origin/main`.
   Jeigu nesi `main`, šakos nesutampa arba saugiai atlikti fast-forward
   neįmanoma, sustok su konkrečiu paaiškinimu. Nesinaudok force push,
   `git reset --hard`, `git clean`, `git stash` ar rebase be atskiro leidimo.
4. Patikrink, ar nėra svetimų **jau sustaguotų** failų. Jei yra, sustok:
   neleisk šiam skill netyčia jų įtraukti į commit.
5. Nustatyk kitą laisvą ID iš Git stebimų katalogų ir darbo medžio. Rinkis
   **vienu didesnį už didžiausią esamą numerį** (`U` + 6 skaitmenys), nepernaudok
   ankstesnių ID. Patikrink, kad jo nėra ir `drive_links.json`.
6. Palygink vartotojo sąlygą su esamų `.tex` uždavinių sąlygomis. Jei yra
   tikslus arba akivaizdus turinio dublikatas, sustok ir pateik esamą ID;
   nedaryk antros kopijos be aiškaus nurodymo.
7. **Prieš kuriant v1 metaduomenis** patikrink, ar įdiegtas visas `Metaduomenys`
   standartas ir veikiantis `Skriptai/tikrinti_meta.py`. Jei jis jau įdiegtas,
   privaloma jo laikytis. Jei dar neįdiegtas, naudok tik projekto **esamą**
   legacy `meta.yaml` formatą ir galutinėje ataskaitoje aiškiai pažymėk, kad
   metaduomenų v1 migracija nebaigta. Neišgalvok trūkstamų schemos laukų,
   nepakeisk esamos klasifikavimo sistemos tyliai.

## Kelių uždavinių importas iš LaTeX failo

Šis režimas taikomas, kai naudotojas pateikia LaTeX failą su keliais uždaviniais
ir prašo juos įtraukti į banką. Po publikavimo parenk atskirą rinkinį, nebent
naudotojas nurodo kitaip. Šiame skyriuje aprašyti
skirtumai pakeičia vieno uždavinio taisykles tik šiam režimui; visos saugos,
metaduomenų, matematinės patikros ir naudotojo apribojimų taisyklės galioja.
Jeigu prašoma tik parengti, o ne publikuoti, neatlik commit ar push ir nelauk
Drive publikavimo; rinkinį sukurk tik tada, kai visos jo nuorodos jau patvirtintos.

1. Perskaityk visą šaltinį ir jo lokalias priklausomybes (makrokomandas,
   `\input`, paveikslėlius, TikZ bibliotekas). Sudaryk sunumeruotą šaltinio
   uždavinių sąrašą. Išskirk tikrą uždavinio ribą, o ne kiekvieną `enumerate`
   punktą: a), b), c) dalys, jų formulės, duomenys ir brėžiniai lieka kartu.
   Palygink sąrašą su visu šaltiniu; nepraleisk ir nesujunk uždavinių spėliodamas.
   Jei ribos ar priklausomybės dviprasmiškos arba trūksta medžiagos, sustok
   ir paaiškink. Nekopijuok svetimų failų ar neįvesk priklausomybių, kurių
   nėra leidžiama ir patikimai atkurti. Patikrink kiekvieną gautą sąlygą bei
   brėžinį su originalu ir išsaugok pirminę uždavinių eilę.
2. Palygink kiekvieną sąlygą su banko `.tex` sąlygomis ir su jau atrinktais
   įvesties uždaviniais, atsižvelk į formulių ir žymėjimo variantus. Tikslų
   arba aiškų dublikatą susiek su esamu ID, nekeisdamas esamo uždavinio ir
   nekurdamas jo kopijos. Pirminėje eilėje išlaikyk kiekvieną pateiktą poziciją,
   įskaitant pasikartojančią nuorodą į tą patį ID. Jei panašumas abejotinas,
   nevadink jo dublikatu be pagrindo: sustok ir pateik konkretų palyginimą.
3. Naujiems uždaviniams rezervuok skirtingus paeiliui einančius laisvus ID
   pagal 1 skyriaus 5 punktą, tikrindamas visus darbo medžio katalogus ir
   registrą. Kiekvienam sukurk atskirą `.tex`, `.pdf`, `meta.yaml`; sąlygoje
   išsaugok visus dalinius klausimus ir brėžinius. Išspręsk ir patikrink
   kiekvieną atskirai pagal 2–5 skyrius. Asmenines žymas ir šaltinio faktus
   perkelk tik į jiems skirtus v1 laukus. Patikrink visą metaduomenų banką ir
   visus projekto testus. Jei bent vienas naujas uždavinys neišspręstas ar
   patikros nepraeina, nepublikuok dalinio rinkinio be naudotojo nurodymo.
4. Prieš vienintelį uždavinių push patikrink esamą publikavimo workflow,
   `DRIVE_PDF_PUBLICATION_ENABLED`, publikavimo žymą, `main` būseną ir staged
   failus. Nepakeisk kintamojo, žymos, Drive teisių ar workflow. Jeigu automatinis
   publikavimas išjungtas arba iš žymos workflow atrinktų papildomų PDF,
   kurių naudotojas neleido publikuoti, sustok prieš push ir paaiškink kodėl.
   Viename izoliuotame commit įtrauk tik naujų uždavinių `.tex`, `.pdf`,
   `meta.yaml` ir būtinas susijusias žodyno pataisas; naudok `git add --` su
   aiškiais keliais, tada vieną įprastą `git push origin main`.
5. Stebėk būtent šio push SHA workflow, kaip nurodyta 7 skyriuje; patikrink
   visus numatytus naujus ID, sėkmingus ID, MD5 ir teisių patikrinimus bei
   registro commit. Patikrink visų rinkinio ID galiojančius registro įrašus ir
   veikiančias peržiūros nuorodas. Jei bent viena publikacija ar nuoroda
   nepatvirtinta, nepateik jos kaip veikiančios ir nesukurk galutinio rinkinio.
   Nesupainiok lokalaus pasenusio registro su naujausiu nuotoliniu `main`;
   atnaujink jį tik saugiai ir neperrašydamas naudotojo vietinių pakeitimų.
6. Tik po visų sėkmingų patikrų sukurk atskirą naują `.tex` failą kataloge
   `Rinkiniai/`: `\begin{enumerate}` aplinkoje kiekvienai šaltinio pozicijai
   ta pačia tvarka įrašyk `\Uzdavinys{UXXXXXX}`. Pavadinimą parink saugų,
   unikalų ir neperrašyk esamo rinkinio. Generuok
   `python3 Uzduociu_bankas/Skriptai/generuoti.py --rinkinys <vardas>`;
   galima nurodyti ir `<vardas>.tex`. Patikrink PDF vizualiai: numeraciją,
   pozicijų skaičių, formules, dalis ir brėžinius. Patikrink kiekvienos PDF
   „Ats.“ nuorodos paskirtį ir jos atitiktį naujausiam `drive_links.json`.
   Atskiro rinkinio commit ar antro push neatlik be naudotojo nurodymo.
7. Ataskaitoje nurodyk šaltinio pozicijų ir ID atvaizdavimą, esamus dublikatus,
   sukurtus failus, testus, commit ir workflow rezultatus, kiekvieną patvirtintą
   nuorodą ir vietinę rinkinio vietą; gedimų atveju nurodyk sustojimo etapą.

## 2. Matematinis darbas

1. Išsaugok pateiktos sąlygos matematinę prasmę, duomenis ir reikalavimus.
   Taisyk tik aiškias rašybos ar tipografijos klaidas. Jei pakeitimas keičia
   sąlygą, paprašyk patvirtinimo.
2. Savarankiškai išspręsk uždavinį ir dar kartą patikrink loginį pagrįstumą.
   Sudėtingam olimpiadiniam uždaviniui ieškok nepriklausomos patikros,
   kontrpavyzdžių, ribinių atvejų. Nesugalvok įrodymo ar atsakymo.
3. Rašyk natūralia, taisyklinga akademine lietuvių kalba, suprantamai
   mokiniams. Aiškiai apibrėžk papildomas konstrukcijas, tikrink visų teoremų
   prielaidas, kiekvieną esminį teiginį pagrįsk ir įrodyk būtent tai, ko prašoma.
   Geometrijoje brėžinys nėra įrodymas. Vartok projekto jau nusistovėjusius
   terminus ir žymėjimą, įskaitant „priekampis“, „atskliausti“,
   „ekstremumo taškas“ ir „ekstremumas“, kai jie tinka kontekstui.
4. Jei sprendimo matematinio teisingumo negali pakankamai patikimai nustatyti,
   **nestumk jo į `main` ir nepublikuok**. Pateik neišspręstą dalį vartotojui.

## 3. Failų kūrimas

1. Sukurk tik `Uzduociu_bankas/Uzdaviniai/<ID>/` katalogą.
2. `<ID>.tex` pagal esamą sintaksę turi turėti tris aplinkas tokia tvarka:
   `salyga`, `atsakymas`, `sprendimas`.
3. `<ID>.pdf` generuok **esamu projekto skriptu**, ne savadarbiu LaTeX
   apėjimu: `python3 Uzduociu_bankas/Skriptai/generuoti.py <ID>`.
4. Patikrink, kad PDF atsidaro, sąlyga ir atsakymas yra prieš sprendimą,
   sprendimas prasideda naujame puslapyje ir nėra dingusių formulių ar TikZ
   elementų. Trumpam uždaviniui įprastai du puslapiai; ilgesniam gali būti
   daugiau. Vien kompiliavimo kodas 0 neįrodo vizualinės kokybės.

## 4. Metaduomenys ir naudotojo žymos

Jei įdiegtas v1 standartas:

- Paruošk `meta.yaml` tik pagal `meta.schema.json`, `zodynas_v1.yaml`
  ir `metaduomenu_standartas_v1.md`.
- Užpildyk `schemos_versija`, `id`, `pavadinimas`, `klasifikacija`, `didaktika`,
  `sudetingumas`, `sprendimas`, `saltinis`, `kokybe`.
- Temas, sritis, metodus, auditorijas, paskirtis ir būtinas žinias parink
  **tik iš žodyno**. Jei trūksta tikslaus kodo, pasiūlyk ir nuosekliai pridėk
  vieną naują lietuviškai aprašytą kodą į `zodynas_v1.yaml`, išbandyk
  validatorių; tokiu atveju žodyno pakeitimas yra susijęs su nauju uždaviniu.
- Naudotojo pasakytas laisvas / asmenines žymas saugok
  `klasifikacija.zymos` (NE išgalvotame `asmenines_zymos` lauke): normalizuok
  mažosiomis ASCII raidėmis, tarpus keisk `_`, neleisk dublikatų, nekeisk
  semantikos. Pavyzdžiui, „Gražus uždavinys“ → `grazus_uzdavinys`.
- Ilgesnius naudotojo komentarus saugok `mokytojo_pastabos`.
- `sudetingumas.mokyklinis` ir `olimpiadinis`: 1–5 arba `null`, balai
  preliminarūs, skirtingų skalių nelygink. Jei negalima pagrįsti – `null`.
- `kokybe.matematine_perziura: nepatvirtinta`; keisk į
  `mokytojo_patvirtinta` tik vartotojui **aiškiai** patvirtinus.
- `saltinis.tipas: nezinomas`, `teisiu_busena: neivertinta`, kol vartotojas
  nepateikia tikslių faktų. Neišgalvok autoriaus, olimpiados, metų, licencijos.
- `rysiai` su kitais ID – tik jei ryšys pagrįstas; nesukurk neegzistuojančių ID.
- Nerašyk Drive URL / ID į `meta.yaml`.
- Paleisk `tikrinti_meta.py` pagal jo `--help` ar dokumentuotą naudojimą;
  jei jis gali tikrinti visą banką, tą patikrą taip pat atlik.

Jei v1 standartas dar neįdiegtas:

- Palaikyk esamus laukus `id`, `tema`, `sunkumas`, `sprendimo_metodai`,
  `google_drive_url: null` (pastarasis – tik suderinamumui su senu formatu).
- Nerašyk laisvų žymų į neegzistuojantį lauką; jei vartotojas jų prašo,
  **sustok prieš commit** ir paaiškink, kad reikia užbaigti v1 migraciją,
  kad žymos nebūtų prarastos ar įrašytos nesuderinamu formatu.

## 5. Tikrinimas prieš įkėlimą

1. Atidžiai patikrink įvestį ir galutinę sąlygą, atsakymą, sprendimą, PDF,
   `meta.yaml`, ID ir nuorodas. Prieš publikavimą turi būti visi reikalingi
   failai (be trūkstamų išorinių paveikslėlių).
2. Jei v1, paleisk metaduomenų validatorių. Visada paleisk visus dabartinius
   testus: `python3 -B -m unittest discover -s Uzduociu_bankas/Testai -v`.
3. Patikrink `git diff --check` ir būsimų staged failų sąrašą. **Jei testas
   ar validacija nepavyksta, commit/push nedaryk**.
4. Jeigu uždavinys perkeliamas iš knygos / olimpiados, nurodyk šaltinį ir
   nepublikuok, jei teisių būklė aiškiai neleidžia viešos reprodukcijos.

## 6. Tik vieno uždavinio commit ir push

1. Dar kartą `git fetch origin main` ir patikrink, kad `origin/main == HEAD`,
   `main` šaka nepasikeitė ir nėra svetimų staged pakeitimų.
2. `git add --` **tik** `<ID>.tex`, `<ID>.pdf`, `meta.yaml`; jei būtina
   papildyti v1 žodyną, papildomai `Uzduociu_bankas/Metaduomenys/zodynas_v1.yaml`.
3. `git diff --cached --name-only` turi būti tik šių leistinų failų sąrašas;
   `git diff --cached --check` turi praeiti. Nekeičiami kiti uždaviniai,
   jokie kitų katalogų ar vartotojo failai.
4. `git commit -m "Add task <ID>"` ir `git push origin main`.
5. **Niekada** nenaudok `git add .`, `git commit -a`, `git push --force`,
   `git reset --hard`, `git clean` arba visos Drive saugyklos `rclone sync`.
6. Jei push nepavyko dėl šakos pasikeitimo ar autentifikacijos, sustok:
   automatiškai neperrašinėk nuotolinių commit ir nesiimk destruktyvių veiksmų.

## 7. Patikrintas automatinis publikavimas

1. Jeigu įmanoma, naudok `gh run list --workflow publikuoti-uzdavinius.yml`
   ir `gh run view <run-id> --log` arba GitHub Actions API, žiūrėk būtent
   **`push` įvykį ir ką tik išsiųstą commit SHA**. Nesupainiok su rankiniu
   `workflow_dispatch` ar `Sync to Google Drive`.
2. Patikrink, ar workflow baigėsi `success`, ar atrinktas tik naujasis ID,
   ar `Publish PDFs and verify Drive access` ir `Persist verified registry
   to main` žingsniai baigėsi sėkmingai.
3. Iš `main` naujausio `Uzduociu_bankas/drive_links.json` pasiimk tikrą
   naujo ID `drive_id` ir `url`; patikrink šių dviejų laukų formatą ir kad
   URL naudoja tą patį ID. Žyma turi rodyti į publikuotą PDF turėjusį commit.
   Neformuok išgalvoto ID arba nuorodos.
4. Patikrink, ar loguose patvirtintos `anyone/reader` teisės ir skaitytojų
   atsisiuntimo apribojimas. Jei turi API skaitymo prieigą, gali patikrinti
   ir nuotolinius metaduomenis. Nepainiok nuorodos peržiūros su teise platinti.
5. Tik po sėkmingo vykdymo ir registro commit bandyk
   `git pull --ff-only origin main`. Jei vietiniai pakeitimai trukdo,
   **sustok, jų neliesk**, o galutinę nuorodą paimk tiesiai iš `origin/main`.
6. Jei vykdymas nepavyko, užtruko, buvo praleistas arba paskelbtas PDF,
   bet registras neatnaujintas, nerašyk „sėkmingai publikuota“.
   Pateik workflow nuorodą ir tikslų gedimo etapą. Niekada automatiškai
   nekartok pirmojo publikavimo ar nekeisk Drive failų rankomis.

## 8. Galutinė ataskaita

Trumpai pateik:

- ID, pavadinimą ir trumpą matematinį atsakymą;
- pagrindinę temą, sprendimo metodus, naudotojo žymas (jei buvo);
- sukurtų failų kelius ir patikrų rezultatus;
- commit SHA, `push` būseną, workflow rezultatą;
- **nuolatinę Drive „Ats.“ nuorodą tik jei patvirtinta**;
- perspėjimus dėl neaiškaus šaltinio, preliminaraus sudėtingumo ar
  nepatvirtinto matematinio sprendimo.

Vieno uždavinio režimu rinkinio automatiškai negeneruok. Kelių uždavinių
importo režimu taikyk atskiro rinkinio kūrimo tvarką aukščiau.
