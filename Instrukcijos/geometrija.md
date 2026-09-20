# BENDROS INSTRUKCIJOS

- **Kiekvieną geometrinės figūros viršūnę žymėk aiškiai matomu tašku.**

- **Skirtingus kampus žymėk skirtingomis spalvomis.**

- **Lygius kampus visada žymėk ta pačia spalva.**  
  Jei du ar daugiau kampų pagal sprendimą yra lygūs, jų lankeliai ir kampų žymėjimai turi būti tos pačios spalvos.

- **Kampo simbolį rašyk prie atitinkamo kampo lankelio.**  
  Jei kampas pažymėtas, pavyzdžiui, $\alpha$, simbolį $\alpha$ visada rašyk virš kampo lankelio arba tiesiai šalia jo taip, kad būtų visiškai aišku, kuriam kampui jis priklauso.

- **Lygaus ilgio atkarpas žymėk vienodais brūkšneliais.**  
  Brūkšneliai turi kirsti atkarpą statmenai. Jei yra kelios skirtingos lygių atkarpų grupės, naudok skirtingą brūkšnelių skaičių:
  - viena lygių atkarpų grupė — vienas brūkšnelis;
  - kita lygių atkarpų grupė — du brūkšneliai;
  - trečia lygių atkarpų grupė — trys brūkšneliai.

- **Kampų spalvos turi būti permatomos.**  
  Kampams žymėti naudok tik pusiau permatomą (`transparent`) spalvinį užpildą.  
  Spalvinis užpildas yra tik pagalbinis žymėjimas ir niekada negali vizualiai uždengti ar susilpninti kraštinių, taškų, kampo lankelių, žymėjimų ar teksto.  
  Visi pagrindiniai geometrinio brėžinio elementai turi būti piešiami aiškiai ir likti vizualiai virš kampų spalvinio užpildo.

- **Nenaudok tos pačios spalvos skirtingiems, nelygiems kampams**, jei tai gali sudaryti klaidingą įspūdį, kad kampai yra lygūs.

- **Nežymėk lygybių brėžinyje iš anksto.**  
  Kampų spalvos, vienodų atkarpų brūkšneliai ir kiti lygybę rodantys žymėjimai turi atsirasti tik tada, kai atitinkama lygybė yra duota sąlygoje arba atsiranda kaip išvada einamajame sprendimo žingsnyje.

---

# UŽDAVINIO SPRENDIMO STRUKTŪRA

## Spręsdamas geometrinį uždavinį visada skaidyk sprendimą į aiškius ir nuoseklius žingsnius:

- **1 žingsnis. Pradinis brėžinys.**  
  Pirmiausia tiksliai ir kokybiškai nubraižyk tik tai, kas tiesiogiai duota uždavinio sąlygoje. Nepridėk jokių papildomų konstrukcijų, pagalbinių tiesių, taškų ar žymėjimų, kurie dar nebuvo įvesti sprendime.

- **Tolesni žingsniai (2, 3 ir t.t.).**  
  Kiekviename naujame žingsnyje atlik vieną ar kelis susijusius aiškius loginius/geometrinius veiksmus. Aprašyk sprendimo logiką trumpu, rišliu tekstu, įterpdamas matematines formules. Matematinius išvedimus pateik centruotai (naudodamas `$$ ... $$` arba `\[ ... \]`), kad tekstas būtų lengvai skaitomas.

- **Po kiekvienu žingsniu turi būti atskiras brėžinys.**

- Brėžiniai turi būti **kaupiamieji**: kiekvienas naujas brėžinys turi išlaikyti visą ankstesnio žingsnio informaciją ir pridėti tik naują informaciją.

- Negalima brėžinyje iš anksto parodyti konstrukcijų, taškų, tiesių ar kitų elementų, kurie sprendime bus įvesti tik vėlesniuose žingsniuose.

- Nepraleisk tarpinių brėžinio būsenų, net jeigu žingsnis atrodo akivaizdus.

---

## Sprendimo pateikimo forma

Sprendimas turi būti pateiktas kaip vientisas, natūralus tekstas. Nenaudok jokių išskleidžiamųjų sąrašų (bullet points) struktūrizuojant pačius žingsnius (t.y. nedaryk sąrašų „Ką darome“, „Kodėl“, „Kas naujo“). 

Naudok tiksliai tokią kodo struktūrą:

```latex
\textbf{Sprendimas:}\\
(Čia gali būti trumpas įvadinis sakinys, apibūdinantis pagrindinę strategiją ar savybę, kuri bus naudojama).

\textbf{1 žingsnis.} (Tekstas, apibūdinantis pradinius veiksmus ir brėžinį, pvz., "Iš pradžių nusibraižome brėžinį:")
\begin{center}
% TikZ brėžinys
\end{center}

\textbf{2 žingsnis.} (Rišlus aiškinamasis tekstas, nurodantis loginius argumentus. Jei reikia, centruotos formulės).
$$\text{formulė}$$
\begin{center}
% Atnaujintas kaupiamasis TikZ brėžinys
\end{center}

\textbf{3 žingsnis.} (Rišlus aiškinamasis tekstas ir loginių veiksmų tąsa).
$$\text{formulė}$$
\begin{center}
% Atnaujintas kaupiamasis TikZ brėžinys
\end{center}

(Tęskite tiek žingsnių, kiek reikia. Sprendimo pabaigoje visada pateikite baigiamąjį žodį, pvz., "Įrodyta. \hfill $\square$").