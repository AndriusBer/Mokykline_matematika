# Publikavimo žymos suderinimo patikra

Rankinis `Audit task PDF publication (read-only)` workflow tikrina tiksliai
paleidimo `main` commit Git turinį, o ne darbo katalogo pakeitimus. Jis skaito
visus Git sekamus uždavinių PDF ir registrą, reikalauja bent U000001–U000004,
reikalauja vienodų Git, registro ir Drive PDF sąrašų bei išsaugotų senų ID.
Kiekvienam PDF lygina Git turinio MD5, Drive ID ir nuorodą bei patvirtina
`anyone/reader`, `allowFileDiscovery=false` ir `restrictedForReaders=true`.
Nuo dabartinės žymos ištrinti PDF stabdo patikrą. Drive API ir rclone naudojami
skaitymui; atsakymų apie prieigos teises nepakanka, jei API grąžina klaidą.

Patikrą galima paleisti tik paskelbus workflow ir skriptą GitHub `main` šakoje.
Prieš tai visų PDF, įskaitant U000004, tikri Drive ID turi būti registre tame
pačiame commit. Workflow žymos nekeičia. Sėkmingo vykdymo žurnale nurodomas
pilnas patikrinto commit SHA. Prieš suderinant žymą reikia dar kartą įsitikinti,
kad GitHub `main` teberodo į tą patį SHA, kad po patikros nesikeitė Drive PDF,
jų ID ar teisės, ir kad automatinis publikavimas vis dar išjungtas.

Atskirame švariame `main` darbiniame kataloge pakeiskite tik
`Uzduociu_bankas/drive_publication_state.json` lauką `last_published_commit` į
patikrintą pilną SHA ir parenkite tik šio failo commit. Žyma turi rodyti į
patikrintą commit, o ne į patį žymos commit. Prieš push dar kartą patikrinkite,
kad nuotolinio `main` HEAD yra patikrintas SHA; naudokite įprastą push be force.
Jei main pasistūmėjo, Drive būsena pasikeitė, patikra nepavyko arba kyla
abejonių, žymos nekeiskite ir pakartokite patikrą su nauju `main` commit.

Ši patikra nėra transakcija su Drive: kitas naudotojas gali pakeisti failus po
patikros. Sulyginimą atlikite iškart po jos, be lygiagrečių Drive pakeitimų.
Tik po atskiro sprendimo ir žymos commit publikavimo kintamąjį galima įjungti.
