# Matematinės mokomosios medžiagos (LaTeX) generavimo instrukcijos

Šis dokumentas apibrėžia struktūros, formos ir stiliaus reikalavimus, kuriais remiantis generuojama mokyklinės matematikos medžiaga (handout'ai) LaTeX formatu.

## 1. Bendra informacija ir stilius
- **Kalba:** Taisyklinga, aiški lietuvių kalba, pritaikyta mokykliniam lygiui.
- **Stilius:** Akademinis, tikslus, struktūruotas, be bereikalingų įžangų.
- **Išvestis:** Tik sukompiliuojamas LaTeX kodas.

## 2. Šablonas ir preambulė
Kiekvienas dokumentas privalo naudoti šią tikslią preambulę ir pradžią. Klasės ir paketų keisti negalima.

```latex
\documentclass[11pt,a4paper]{scrartcl}

\usepackage{../manostilius_lt}

\title{[Temos pavadinimas]}
\author{[Autoriaus vardas, pavardė]}

\begin{document}

\maketitle
```

## 3. Teorijos dalies formatavimas
Teorinė medžiaga skaidoma į logines dalis, naudojant šias aplinkas:

- **Skyriai:** `\section{...}`.
- **Apibrėžimai:** `definition` aplinka. Pagrindinė sąvoka išryškinama komanda `\vocab{...}` ir atskiriama brūkšniu `--`.
  ```latex
  \begin{definition}
  \vocab{Sąvoka} -- tai apibrėžimas.
  \end{definition}
  ```
- **Savybės ir taisyklės:** `property` aplinka. Pavadinimas nurodomas laužtiniuose skliaustuose.
  ```latex
  \begin{property}[Savybės pavadinimas]
  Savybės aprašymas arba formulė.
  \end{property}
  ```
- **Pastabos ir įrodymai:** `\begin{remark} ... \end{remark}` arba `\begin{proof} ... \end{proof}`.

## 4. Matematinių formulių formatavimas
- Blokinių formulių apibrėžimui griežtai draudžiama naudoti `$$ ... $$`. Privaloma naudoti `\[` ir `\]`.
- Kelių eilučių lygtims lygiavimo tikslais privaloma naudoti `aligned` aplinką `\[ ... \]` bloko viduje.
  ```latex
  \[
  \begin{aligned}
  (a+b)^2 &= (a+b)(a+b) \\
  &= a^2+2ab+b^2.
  \end{aligned}
  \]
  ```

## 5. Pavyzdžių formatavimas
Visi pavyzdžiai rašomi `example` aplinkoje. Žodžiai „Sprendimas“ ir „Atsakymas:“ yra privalomi.

```latex
\begin{example}
Užduoties sąlyga:
\[ matematika \]
\textbf{Sprendimas}\\
Sprendimo eiga...
\textbf{Atsakymas:} atsakymas.
\end{example}
```

## 6. Uždavinių skyrius
- Pradedamas nauju skyriumi: `\section{Uždaviniai}`.
- Kiekvienas uždavinių blokas talpinamas į `problem` aplinką.
- Sąlygoms išvardinti privaloma naudoti `tasks` aplinką su parametrais `[label={(\arabic*)}, label-offset=0.9em](n)`, kur `n` yra stulpelių skaičius (paprastai 2 arba 4).
  ```latex
  \begin{problem}
  Išspręskite lygtis:
  \begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
      \task $x+2=0$
      \task $x-3=0$
  \end{tasks}
  \end{problem}
  ```

## 7. Atsakymų skyrius
- Pradedamas komandomis:
  ```latex
  \newpage
  \answerssection
  ```
- Naudojamos tos pačios `problem` ir `tasks` aplinkos.
- **Kritinė sintaksė:** Prieš pradedant `tasks` atsakymuose, iškart po `\begin{problem}` privaloma įrašyti `\phantom{text}`.
- **Skyryba:** Atsakymų elementai baigiasi kabliataškiu `;`, o paskutinis bloko elementas – tašku `.`.
  ```latex
  \begin{problem} \phantom{text}
  \begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
      \task $-2$;
      \task $3$.
  \end{tasks}
  \end{problem}
  ```

## 8. Pabaiga
Dokumentas visada užbaigiamas komanda:
```latex
\end{document}
```

## 9. Pavyzdiniai failai

Žemiau pateikiami idealiai suformatuoti dokumentų pavyzdžiai, į kuriuos AI turi lygiuotis.

### Pavyzdys 1: Pilnojo kvadrato išskyrimas[cite: 1]

```latex
\documentclass[11pt,a4paper]{scrartcl}

\usepackage{../manostilius_lt}

\title{Pilnojo kvadrato išskyrimas}
\author{Andrius Berniukevičius}

\begin{document}

\maketitle

\section{Kas yra pilnojo kvadrato išskyrimas?}
\begin{definition}
\vocab{Pilnasis kvadratas} -- tai reiškinys, kurį galima užrašyti dvinario kvadratu, t. y. forma $(a+b)^2$ arba $(a-b)^2$.
\end{definition}

Pilnojo kvadrato išskyrimas -- tai daugianario pertvarkymas taip, kad jame atsirastų dvinario kvadratas. Šis būdas remiasi greitosios daugybos formulėmis:
\[(a+b)^2=a^2+2ab+b^2,\]
\[(a-b)^2=a^2-2ab+b^2.\]



\begin{definition}
\vocab{Pilnojo kvadrato išskyrimas} -- tai trinario pertvarkymas į dvinario kvadratą arba į dvinario kvadrato ir skaičiaus sumą ar skirtumą.
\end{definition}

Kad trinarį galėtume užrašyti dvinario kvadratu, pirmasis ir paskutinis jo nariai turi būti kvadratai, o vidurinis narys turi būti lygus dvigubai jų kvadratinių šaknų sandaugai.

\section{Pilnojo kvadrato atpažinimas}

\begin{property}[Pilnojo kvadrato trinaris]
Jei trinaris yra formos
\[a^2+2ab+b^2,\]
tai jis lygus $(a+b)^2$. Jei trinaris yra formos
\[a^2-2ab+b^2,\]
tai jis lygus $(a-b)^2$.
\end{property}

\setcounter{theorem}{0}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2+6x+9.\]
\textbf{Sprendimas}\\
Pirmasis narys yra $x^2$, todėl $a=x$. Paskutinis narys yra $9=3^2$, todėl $b=3$. Patikriname vidurinį narį:
\[2ab=2\cdot x\cdot3=6x.\]
Vidurinis narys sutampa, todėl taikome sumos kvadrato formulę:
\[x^2+6x+9=x^2+2\cdot x\cdot3+3^2=(x+3)^2.\]
\textbf{Atsakymas:} $(x+3)^2$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[4x^2-12x+9.\]
\textbf{Sprendimas}\\
Pirmasis narys yra $4x^2=(2x)^2$, o paskutinis narys yra $9=3^2$. Todėl tikriname, ar vidurinis narys yra $-2\cdot2x\cdot3$:
\[-2\cdot2x\cdot3=-12x.\]
Vidurinis narys sutampa, todėl gauname skirtumo kvadratą:
\[4x^2-12x+9=(2x)^2-2\cdot2x\cdot3+3^2=(2x-3)^2.\]
\textbf{Atsakymas:} $(2x-3)^2$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[9a^2+24ab+16b^2.\]
\textbf{Sprendimas}\\
Pirmasis ir paskutinis nariai yra kvadratai:
\[9a^2=(3a)^2, \qquad 16b^2=(4b)^2.\]
Patikriname vidurinį narį:
\[2\cdot3a\cdot4b=24ab.\]
Taigi tai yra sumos kvadratas:
\[9a^2+24ab+16b^2=(3a+4b)^2.\]
\textbf{Atsakymas:} $(3a+4b)^2$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[4a^2+12ab+9b^2.\]
\textbf{Sprendimas}\\
Pirmasis ir paskutinis nariai yra kvadratai:
\[4a^2=(2a)^2, \qquad 9b^2=(3b)^2.\]
Patikriname vidurinį narį:
\[2\cdot2a\cdot3b=12ab.\]
Taigi tai yra sumos kvadratas:
\[4a^2+12ab+9b^2=(2a+3b)^2.\]
\textbf{Atsakymas:} $(2a+3b)^2$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[9m^2n^2-6mny+y^2.\]
\textbf{Sprendimas}\\
Pirmasis ir paskutinis nariai yra kvadratai:
\[9m^2n^2=(3mn)^2, \qquad y^2=y^2.\]
Patikriname vidurinį narį:
\[-2\cdot3mn\cdot y=-6mny.\]
Taigi tai yra skirtumo kvadratas:
\[9m^2n^2-6mny+y^2=(3mn-y)^2.\]
\textbf{Atsakymas:} $(3mn-y)^2$.
\end{example}

\begin{remark}
Ne kiekvienas trinaris yra pilnojo kvadrato trinaris. Pavyzdžiui, reiškinyje $x^2+5x+9$ pirmasis ir paskutinis nariai yra kvadratai, tačiau $2\cdot x\cdot3=6x$, o ne $5x$. Todėl šio trinaro negalime užrašyti $(x+3)^2$ forma.
\end{remark}

\section{Pilnojo kvadrato sudarymas}

Kartais trūksta tik paskutinio nario, kad trinaris taptų pilnojo kvadrato trinariu. Tuomet reikiamą narį pridedame ir iš karto atimame. Reiškinio reikšmė dėl to nesikeičia.

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2+8x.\]
\textbf{Sprendimas}\\
Pirmasis narys yra $x^2$, o vidurinis narys $8x$ turi būti lygus $2\cdot x\cdot b$. Randame $b$:
\[2\cdot x\cdot b=8x, \qquad b=4.\]
Taigi reikia pridėti $4^2=16$. Kad reiškinio reikšmė nepasikeistų, tą patį skaičių ir atimame:
\[\begin{aligned} x^2+8x &=x^2+8x+16-16\\ &=(x+4)^2-16. \end{aligned}\]
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2-10x+7.\]
\textbf{Sprendimas}\\
Viduriniam nariui $-10x$ gauti reikia $b=5$, nes $-2\cdot x\cdot5=-10x$. Pridedame ir atimame $5^2=25$:
\[\begin{aligned} x^2-10x+7 &=x^2-10x+25-25+7\\ &=(x-5)^2-18. \end{aligned}\]
\textbf{Atsakymas:} $(x-5)^2-18$.
\end{example}

\begin{example}
\small
Išskirkite pilnąjį kvadratą:
\[4x^2+12x+1.\]
\textbf{Sprendimas}\\
Pirmasis narys yra $(2x)^2$. Vidurinį narį gauname pagal formulę $2\cdot2x\cdot b=12x$, todėl $b=3$. Pridedame ir atimame $3^2=9$:
\[\begin{aligned} 4x^2+12x+1 &=4x^2+12x+9-9+1\\ &=(2x+3)^2-8. \end{aligned}\]
\textbf{Atsakymas:} $(2x+3)^2-8$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2-\frac{3}{5}x.\]
\textbf{Sprendimas}\\
\[\begin{aligned} x^2-\frac{3}{5}x &=x^2-2\cdot\frac{1}{2}\cdot\frac{3}{5}\cdot x \\ &=x^2-2\cdot x\cdot\frac{3}{10} \\ & =\underbrace{x^2-2\cdot x\cdot\frac{3}{10}+\left(\frac{3}{10}\right)^2}_{\left(x-\frac{3}{10}\right)^2}-\left(\frac{3}{10}\right)^2 \\ & =\left(x-\frac{3}{10}\right)^2-\frac{9}{100}. \end{aligned}\]
\textbf{Atsakymas:} $\left(x-\frac{3}{10}\right)^2-\frac{9}{100}$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2+7x+4.\]
\textbf{Sprendimas}\\
\[\begin{aligned} x^2+7x+4 &=x^2+2\cdot\frac{1}{2}\cdot7x+4 \\ &=x^2+2\cdot x\cdot\frac{7}{2}+4 \\ &=\underbrace{x^2+2\cdot x\cdot\frac{7}{2}+\left(\frac{7}{2}\right)^2}_{\left(x+\frac{7}{2}\right)^2}-\left(\frac{7}{2}\right)^2+4 \\ &=\left(x+\frac{7}{2}\right)^2-\frac{49}{4}+4 \\ &=\left(x+\frac{7}{2}\right)^2-\frac{33}{4}. \end{aligned}\]
\textbf{Atsakymas:} $\left(x+\frac{7}{2}\right)^2-\frac{33}{4}$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[x^2+3x+1.\]
\textbf{Sprendimas}\\
\[\begin{aligned} x^2+3x+1 &=x^2+2\cdot\frac{1}{2}\cdot3x+1\\ &=x^2+2\cdot x\cdot\frac{3}{2}+1\\ &=\underbrace{x^2+2\cdot x\cdot\frac{3}{2}+\left(\frac{3}{2}\right)^2}_{\left(x+\frac{3}{2}\right)^2}-\left(\frac{3}{2}\right)^2+1\\ &=\left(x+\frac{3}{2}\right)^2-\frac{9}{4}+1\\ &=\left(x+\frac{3}{2}\right)^2-\frac{5}{4}. \end{aligned}\]
\textbf{Atsakymas:} $\left(x+\frac{3}{2}\right)^2-\frac{5}{4}$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[2x^2+\frac{1}{5}x+3.\]
\textbf{Sprendimas}\\
Iškeliame $2$ prieš pirmus du narius:
\[\begin{aligned} 2x^2+\frac{1}{5}x+3 &=2\left(x^2+\frac{1}{10}x\right)+3\\ &=2\left(x^2+2\cdot\frac{1}{2}\cdot\frac{1}{10}x\right)+3\\ &=2\left(x^2+2\cdot x\cdot\frac{1}{20}\right)+3\\ &=2\left(\underbrace{x^2+2\cdot x\cdot\frac{1}{20}+\left(\frac{1}{20}\right)^2}_{\left(x+\frac{1}{20}\right)^2}-\left(\frac{1}{20}\right)^2\right)+3\\ &=2\cdot\left(\left(x+\frac{1}{20}\right)^2-\frac{1}{400}\right)+3\\ &=2\left(x+\frac{1}{20}\right)^2-\frac{1}{200}+3\\ &=2\left(x+\frac{1}{20}\right)^2+\frac{599}{200}. \end{aligned}\]
\textbf{Atsakymas:} $2\left(x+\frac{1}{20}\right)^2+\frac{599}{200}$.
\end{example}

\begin{example}
Išskirkite pilnąjį kvadratą:
\[25a^2b^2+10abc+a.\]
\textbf{Sprendimas}\\
Pridedame ir atimame $c^2$, kad pirmi trys nariai sudarytų pilnojo kvadrato trinarį:
\[\begin{aligned} 25a^2b^2+10abc+a &=25a^2b^2+10abc+c^2-c^2+a\\ &=(5ab+c)^2-c^2+a. \end{aligned}\]
\textbf{Atsakymas:} $(5ab+c)^2-c^2+a$.
\end{example}

\section{Uždaviniai}

\begin{problem}
Išskirkite pilnąjį kvadratą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $x^2+10x+25$
	\task $x^2-14x+49$
	\task $4a^2+20a+25$
	\task $9y^2-24y+16$
	\task $25m^2+30mn+9n^2$
	\task $16p^2-40pq+25q^2$
	\task $a^2-6ab+9b^2$
	\task $x^2+12xy+36y^2$
\end{tasks}
\end{problem}

\begin{problem}
Išskirkite pilnąjį kvadratą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $9a^2b^2-6abx+x^2$
	\task $4m^2n^2-12mny+9y^2$
	\task $25p^2q^2-20pqr+4r^2$
	\task $x^2-14xy+49y^2$
\end{tasks}
\end{problem}

\begin{problem}
Išskirkite pilnąjį kvadratą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $x^2+4x$
	\task $x^2-6x$
	\task $x^2+12x+5$
	\task $x^2-8x+3$
	\task $4x^2+20x$
	\task $9x^2-30x+4$
	\task $a^2+14a-2$
	\task $4y^2-4y+6$
\end{tasks}
\end{problem}

\begin{problem}
Išskirkite pilnąjį kvadratą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $x^2+x+2$
	\task $x^2+5x-1$
	\task $x^2-3x+4$
	\task $x^2-7x+2$
	\task $x^2+\frac{1}{2}x+1$
	\task $x^2-\frac{3}{2}x+5$
	\task $x^2+\frac{7}{3}x-2$
	\task $x^2-\frac{5}{3}x+3$
\end{tasks}
\end{problem}

\begin{problem}
Išskirkite pilnąjį kvadratą, prieš tai iškeldami pirmojo nario koeficientą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $2x^2+2x+3$
	\task $5x^2-4x+1$
	\task $-3x^2+9x-2$
	\task $4x^2-x+4$
	\task $-x^2+ \frac{1}{4} x+1$
	\task $2x^2-0,1x-1$
	\task $3x^2+ \frac{2}{3} x-1$
	\task $-4x^2-x+2$
\end{tasks}
\end{problem}
\newpage
\begin{problem}
Išskirkite pilnąjį kvadratą:
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $9a^2b^2+12abc+d$
	\task $16x^2y^2-24xyz-9$
	\task $25m^2+20mn-p$
	\task $4r^2s^2+4rst-uv$
\end{tasks}
\end{problem}

\begin{problem}
Išskirkite pilnąjį kvadratą.
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](4)
	\task $x^2+6x+2$
	\task $2x^2+4x+1$
	\task $x^2-8x+5$
	\task $-3x^2+5x+2$
	\task $x^2+\frac{1}{3}x-2$
	\task $4x^2-5x+3$
	\task $x^2-\frac{5}{2}x+1$
	\task $-2x^2-x+3$
	\task $3x^2+2x-1$
	\task $5x^2-5x+2$
	\task $x^2+9x+3$
	\task $10x^2-x$
	\task $x^2-\frac{4}{5}x+4$
	\task $-4x^2+8x-1$
	\task $x^2+\frac{9}{2}x-2$
	\task $2x^2-12x+5$
	\task $x^2+\frac{1}{4}x+2$
	\task $-3x^2-12x+1$
	\task $4x^2+x-2$
	\task $5x^2+15x-1$
\end{tasks}
\end{problem}

\newpage
\answerssection

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(x+5)^2$;
	\task $(x-7)^2$;
	\task $(2a+5)^2$;
	\task $(3y-4)^2$;
	\task $(5m+3n)^2$;
	\task $(4p-5q)^2$;
	\task $(a-3b)^2$;
	\task $(x+6y)^2$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(3ab-x)^2$;
	\task $(2mn-3y)^2$;
	\task $(5pq-2r)^2$;
	\task $(x-7y)^2$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(x+2)^2-4$;
	\task $(x-3)^2-9$;
	\task $(x+6)^2-31$;
	\task $(x-4)^2-13$;
	\task $(2x+5)^2-25$;
	\task $(3x-5)^2-21$;
	\task $(a+7)^2-51$;
	\task $(2y-1)^2+5$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $\left(x+\frac{1}{2}\right)^2+\frac{7}{4}$;
	\task $\left(x+\frac{5}{2}\right)^2-\frac{29}{4}$;
	\task $\left(x-\frac{3}{2}\right)^2+\frac{7}{4}$;
	\task $\left(x-\frac{7}{2}\right)^2-\frac{41}{4}$;
	\task $\left(x+\frac{1}{4}\right)^2+\frac{15}{16}$;
	\task $\left(x-\frac{3}{4}\right)^2+\frac{71}{16}$;
	\task $\left(x+\frac{7}{6}\right)^2-\frac{121}{36}$;
	\task $\left(x-\frac{5}{6}\right)^2+\frac{83}{36}$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}

\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $2\left(x+\frac{1}{2}\right)^2+\frac{5}{2}$;
	\task $5\left(x-\frac{2}{5}\right)^2+\frac{1}{5}$;
	\task $-3\left(x-\frac{3}{2}\right)^2+\frac{19}{4}$;
	\task $4\left(x-\frac{1}{8}\right)^2+\frac{63}{16}$;
	\task $-\left(x-\frac{1}{8}\right)^2+\frac{65}{64}$;
	\task $2\left(x-\frac{1}{40}\right)^2-\frac{801}{800}$;
	\task $3\left(x+\frac{1}{9}\right)^2-\frac{28}{27}$;
	\task $-4\left(x+\frac{1}{8}\right)^2+\frac{33}{16}$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(3ab+2c)^2-4c^2+d$;
	\task $(4xy-3z)^2-9z^2-9$;
	\task $(5m+2n)^2-4n^2-p$;
	\task $(2rs+t)^2-t^2-uv$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](4)
	\task $(x+3)^2-7$;
	\task $2(x+1)^2-1$;
	\task $(x-4)^2-11$;
	\task $-3\left(x-\frac{5}{6}\right)^2+\frac{49}{12}$;
	\task $\left(x+\frac{1}{6}\right)^2-\frac{73}{36}$;
	\task $4\left(x-\frac{5}{8}\right)^2+\frac{23}{16}$;
	\task $\left(x-\frac{5}{4}\right)^2-\frac{9}{16}$;
	\task $-2\left(x+\frac{1}{4}\right)^2+\frac{25}{8}$;
	\task $3\left(x+\frac{1}{3}\right)^2-\frac{4}{3}$;
	\task $5\left(x-\frac{1}{2}\right)^2+\frac{3}{4}$;
	\task $\left(x+\frac{9}{2}\right)^2-\frac{69}{4}$;
	\task $10\left(x-\frac{1}{20}\right)^2-\frac{1}{40}$;
	\task $\left(x-\frac{2}{5}\right)^2+\frac{96}{25}$;
	\task $-4(x-1)^2+3$;
	\task $\left(x+\frac{9}{4}\right)^2-\frac{113}{16}$;
	\task $2(x-3)^2-13$;
	\task $\left(x+\frac{1}{8}\right)^2+\frac{127}{64}$;
	\task $-3(x+2)^2+13$;
	\task $4\left(x+\frac{1}{8}\right)^2-\frac{33}{16}$;
	\task $5\left(x+\frac{3}{2}\right)^2-\frac{49}{4}$.
\end{tasks}
\end{problem}

\end{document}
```

### Pavyzdys 2: Greitosios daugybos formulės[cite: 2]

```latex
\documentclass[11pt,a4paper]{scrartcl}

\usepackage{../manostilius_lt}

\title{Greitosios daugybos formulės}
\author{Andrius Berniukevičius}

\begin{document}

\maketitle

\section{Sumos ir skirtumo kvadratas}

Greitosios daugybos formulės leidžia greitai išskleisti skliaustus arba išskaidyti reiškinį dauginamaisiais. Pirmiausia išnagrinėkime sumos kvadratą.

\begin{property}[Sumos kvadratas]
\[(a+b)^2=a^2+2ab+b^2.\]
\end{property}

\begin{proof}
Laipsnis $2$ reiškia, kad reiškinį dauginame iš savęs. Pritaikę dviejų dvinarių daugybos taisyklę, gauname:
\[\begin{aligned} (a+b)^2&=(a+b)(a+b)\\ &=a\cdot a+a\cdot b+b\cdot a+b\cdot b\\ &=a^2+ab+ab+b^2\\ &=a^2+2ab+b^2. \end{aligned}\]
\end{proof}

\begin{property}[Skirtumo kvadratas]
\[(a-b)^2=a^2-2ab+b^2.\]
\end{property}

\begin{proof}
 Atskliaudžiame ir sutraukiame panašiuosius vienanarius:
\[\begin{aligned} (a-b)^2&=(a-b)(a-b)\\ &=a^2-ab-ba+b^2\\ &=a^2-2ab+b^2. \end{aligned}\]
\end{proof}

\begin{example}
Supaprastinkite reiškinį:
\[(3x+5)^2.\]
\textbf{Sprendimas}\\
Taikome sumos kvadrato formulę, kai $a=3x$, o $b=5$:
\[(3x+5)^2=(3x)^2+2\cdot3x\cdot5+5^2=9x^2+30x+25.\]
\textbf{Atsakymas:} $9x^2+30x+25$.
\end{example}

\begin{example}
Supaprastinkite reiškinį:
\[(2x-3y)^2.\]
\textbf{Sprendimas}\\
Taikome skirtumo kvadrato formulę, kai $a=2x$, o $b=3y$:
\[(2x-3y)^2=(2x)^2-2\cdot2x\cdot3y+(3y)^2=4x^2-12xy+9y^2.\]
\textbf{Atsakymas:} $4x^2-12xy+9y^2$.
\end{example}

\section{Kvadratų skirtumas}

\begin{property}[Kvadratų skirtumas]
\[a^2-b^2=(a-b)(a+b).\]
\end{property}

\begin{proof}
 Atskliaudžiame ir sutraukiame panašiuosius vienanarius:
\[\begin{aligned} (a-b)(a+b)&=a^2+ab-ab-b^2\\ &=a^2+ab-ab-b^2\\ &=a^2-b^2. \end{aligned}\]
\end{proof}

\begin{example}
Išskaidykite dauginamaisiais:
\[25x^2-16.\]
\textbf{Sprendimas}\\
Atpažįstame kvadratų skirtumą: $25x^2=(5x)^2$, o $16=4^2$. Todėl:
\[25x^2-16=(5x-4)(5x+4).\]
\textbf{Atsakymas:} $(5x-4)(5x+4).
\end{example}

\section{Sumos ir skirtumo kubas}

\begin{property}[Sumos kubas]
\[(a+b)^3=a^3+b^3+3ab(a+b).\]
\end{property}

\begin{proof}
Sumos kubą užrašome kaip sumos kvadrato ir dar vienos tokios pačios sumos sandaugą:
\[\begin{aligned} (a+b)^3&=(a+b)^2(a+b)\\ &=(a^2+2ab+b^2)(a+b)\\ &=a^3+a^2b+2a^2b+2ab^2+ab^2+b^3\\ &=a^3+3a^2b+3ab^2+b^3\\ &=a^3+b^3+3ab(a+b). \end{aligned}\]
\end{proof}

\begin{property}[Skirtumo kubas]
\[(a-b)^3=a^3-b^3-3ab(a-b).\]
\end{property}

\begin{proof}
 Atskliaudžiame ir sutraukiame panašiuosius vienanarius:
\[\begin{aligned} (a-b)^3&=(a-b)(a-b)^2\\ &=(a-b)(a^2-2ab+b^2)\\ &=a^3-2a^2b+ab^2-a^2b+2ab^2-b^3\\ &=a^3-3a^2b+3ab^2-b^3\\ &=a^3-b^3-3ab(a-b). \end{aligned}\]
\end{proof}

\begin{remark}
Palyginkime sumos kvadratą ir sumos kubą:
\[(a+b)^2=a^2+b^2+2ab,\]
\[(a+b)^3=a^3+b^3+3ab(a+b).\]
Abiejose formulėse pirmieji nariai yra atskirai pakelti laipsniu, o vidurinis narys turi skaičių, lygų keliamo laipsnio rodikliui: kvadrato formulėje $2$, kubo formulėje $3$. Kubo formulėje dar atsiranda daugiklis $(a+b)$.\\ \\
Skirtumo kubo formulę lengva įsiminti iš sumos kubo formulės: visus pliuso ženklus pakeičiame minuso ženklais:
\[(a+b)^3=a^3+b^3+3ab(a+b),\]
\[(a-b)^3=a^3-b^3-3ab(a-b).\]
\end{remark}

\begin{example}
Supaprastinkite reiškinį:
\[(x+2)^3.\]
\textbf{Sprendimas}\\
Taikome sumos kubo formulę, kai $a=x$, o $b=2$:
\[(x+2)^3=x^3+2^3+3\cdot x\cdot2(x+2)=x^3+6x^2+12x+8.\]
\textbf{Atsakymas:} $x^3+6x^2+12x+8$.
\end{example}

\begin{example}
Supaprastinkite reiškinį:
\[(4x-y)^3.\]
\textbf{Sprendimas}\\
Taikome skirtumo kubo formulę, kai $a=4x$, o $b=y$:
\[\begin{aligned} (4x-y)^3&=(4x)^3-y^3-3\cdot4x\cdot y(4x-y)\\ &=64x^3-y^3-48x^2y+12xy^2\\ &=64x^3-48x^2y+12xy^2-y^3. \end{aligned}\]
\textbf{Atsakymas:} $64x^3-48x^2y+12xy^2-y^3$.
\end{example}

\section{Kubų suma ir skirtumas}

\begin{property}[Kubų suma]
\[a^3+b^3=(a+b)(a^2-ab+b^2).\]
\end{property}

\begin{proof}
Pritaikome daugianarių daugybą:
\[\begin{aligned} (a+b)(a^2-ab+b^2) &=a^3-a^2b+ab^2+a^2b-ab^2+b^3\\ &=a^3+b^3. \end{aligned}\]
\end{proof}

\begin{property}[Kubų skirtumas]
\[a^3-b^3=(a-b)(a^2+ab+b^2).\]
\end{property}

\begin{proof}
Atskliaudžiame ir sutraukiame panašiuosius vienanarius:
\[\begin{aligned} (a-b)(a^2+ab+b^2) &=a^3+a^2b+ab^2-a^2b-ab^2-b^3\\ &=a^3-b^3. \end{aligned}\]
\end{proof}

\begin{example}
Išskaidykite dauginamaisiais:
\[x^3+27.\]
\textbf{Sprendimas}\\
Kadangi $27=3^3$, taikome kubų sumos formulę:
\[x^3+27=x^3+3^3=(x+3)(x^2-3x+9).\]
\textbf{Atsakymas:} $(x+3)(x^2-3x+9)$.
\end{example}

\begin{example}
Išskaidykite dauginamaisiais:
\[8a^3-b^3.\]
\textbf{Sprendimas}\\
Kadangi $8a^3=(2a)^3$, taikome kubų skirtumo formulę:
\[8a^3-b^3=(2a-b)(4a^2+2ab+b^2).\]
\textbf{Atsakymas:} $(2a-b)(4a^2+2ab+b^2)$.
\end{example}

\section{Uždaviniai}

\begin{problem}
 Atskliauskite taikydami greitosios daugybos formules.
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(x+5)^2$
	\task $(2a-3)^2$
	\task $(3m+n)^2$
	\task $(y-4)^2$
	\task $(x+2)^3$
	\task $(a-3)^3$
	\task $(2p+q)^3$
	\task $(3x-2y)^3$
\end{tasks}
\end{problem}

\begin{problem}
Išskaidykite reiškinius dauginamaisiais taikydami greitosios daugybos formules.
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $x^2-49$
	\task $9a^2-16b^2$
	\task $m^3+8$
	\task $27x^3-y^3$
	\task $a^2+10a+25$
	\task $4p^2-12p+9$
	\task $x^3-125$
	\task $8a^3+27b^3$
\end{tasks}
\end{problem}

\newpage
\answerssection

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $x^2+10x+25$;
	\task $4a^2-12a+9$;
	\task $9m^2+6mn+n^2$;
	\task $y^2-8y+16$;
	\task $x^3+6x^2+12x+8$;
	\task $a^3-9a^2+27a-27$;
	\task $8p^3+12p^2q+6pq^2+q^3$;
	\task $27x^3-54x^2y+36xy^2-8y^3$.
\end{tasks}
\end{problem}

\begin{problem} \phantom{text}
\begin{tasks}[label={(\arabic*)}, label-offset=0.9em](2)
	\task $(x-7)(x+7)$;
	\task $(3a-4b)(3a+4b)$;
	\task $(m+2)(m^2-2m+4)$;
	\task $(3x-y)(9x^2+3xy+y^2)$;
	\task $(a+5)^2$;
	\task $(2p-3)^2$;
	\task $(x-5)(x^2+5x+25)$;
	\task $(2a+3b)(4a^2-6ab+9b^2)$.
\end{tasks}
\end{problem}

\end{document}
```