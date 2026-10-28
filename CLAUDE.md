# Handleidingen · context voor Claude Code

Website met handleidingen voor leerlingen van Melanchthon Mavo Schiebroek. Eigenaar: Joey Bonte (j.bonte@cvo.nl).
Niet specifiek voor het vak PORT: op de site heet het gewoon "Handleidingen" (geen PORT in titels, logo of teksten).
"Bijschrift PORT" in de omzetter is de naam van een Word-stijl en blijft zo.
Communiceer in het Nederlands, kort en praktisch. Afspraken over inhoud, taal en opmaak van de handleidingen:
`../PORT_Handleidingen_v26_02/00_LEESMIJ_Doelen_en_werkwijze.md`.

## Opbouw
- Vervangt de Lovable-site (melanchthon.xyz). Inhoud, opmaak (src/styles.css) en de omzetter komen uit die export.
- **Word is de enige bron.** `word/*.docx` → `scripts/word-naar-json.py` (python-docx + Pillow) → `public/data/<slug>.json`
  + `public/i/*.webp`. Die uitvoer staat niet in git; GitHub Actions maakt hem bij elke push (.github/workflows/deploy.yml).
  Klopt de site niet? Word aanpassen of de omzetter verbeteren, nooit de uitvoer.
- `src/catalogus.json`: groepen, kaarten, iconen, Beta-label en extra's per handleiding. `bron` = bestandsnaam zonder `_vX_Y`;
  de omzetter kiest de hoogste versie en zoekt in de hele repo (ook als een upload in een verkeerde map belandt).
  Python én React lezen dit bestand.
- React 18 + Vite 5, geen router: hash-adressen `#/slug/hoofdstuk` (zelfde als de oude site). `public/handleidingen/index.html`
  stuurt oude links door.
- Extra's (3D-viewer, animaties, MakeCode-oefenpagina, Lovable-oefeningen) in `public/extra/`, als iframe op de pagina; de animaties laden three.js van jsDelivr.

## Word-sjabloon v27 (vanaf 24 oktober 2026)
Sjablonen: `../PORT_Handleidingen_v26_02/07_Werkwijze/Handleiding_SJABLOON_v27_01.docx` en `Informatie_SJABLOON_v27_01.docx`.
De omzetter herkent onderdelen aan de **Word-stijl**, niet aan tekst. Oude documenten (v26) werken via de oude regels nog steeds.

| Word | HTML |
|---|---|
| Kop 1 / Kop 2 | sectie / `h3` |
| Stap + tekenstijl `Stapletter` | `ol.steps` met `.badge` |
| tekenstijl `Knopnummer`, `KnopnummerGroen`, `KnopnummerOranje`, `KnopnummerRood` | `span.k.k-b / k-g / k-o / k-r` |
| Afbeelding: maat uit `wp:extent` (≥ 10 cm breed, staand = telefoon, anders klein) | `figure.shot` / `.shot.tel` / `.shot.small` |
| 2-koloms tabel: tekst links, afbeelding of "Screenshot volgt" rechts | `.mt` (`.mt-t` + `.mt-m`) |
| meerdere afbeeldingen in één alinea | `.mt-row` |
| 1-cel tabel, titel in stijl `Blok Tip / Blok Let op / Blok Veilig / Blok Info` (anders: celkleur, dan titeltekst) | `aside.blk.tip / warn / danger / info` |
| stijl `Code` | `.code pre` |
| 1-cel tabel "Screenshot volgt: …" | `aside.blk.ph` |
| Kop 1 "Bouwstenen…" | wordt overgeslagen, met alles erna |

Controle na een wijziging aan de omzetter: draai hem op alle `word/*.docx` en vergelijk met de vorige uitvoer: de tekst moet gelijk blijven.

## Online zetten
- Op deze pc staan geen git/node/python. Gebruiker uploadt via github.com (repo FoeFelaar010/Handleidingen, branch main);
  controleren met de Actions-run "Online zetten" (stap "Word naar site" toont per document hoofdstukken/afbeeldingen/ontbrekende alinea's).
- Live: https://foefelaar010.github.io/Handleidingen/
- Webupload: maximaal ± 15 MB per keer slepen. Bestanden met een punt (.github, .gitignore) slaat slepen over: Add file → Create new file.
- Codeblokken (stijl Code) krijgen op de site een kopieerknop (src/pages/Handleiding.jsx); oude Arduino-code via src/arduino.js.

## Beheer (#/beheer)
- src/pages/Beheer.jsx (apart geladen) + src/supabase.js. Supabase-project = dat van het MOL-portaal (icwpaomwjwlcxzuircgh),
  zelfde wachtwoordaccounts, eigen opslagsleutel. Rechten: tabel `hl_beheerders` (e-mail), logboek `hl_logboek`.
- Edge Function `handleidingen-beheer` (bron in supabase/functions/) zet Word-bestanden en catalogus.json via de GitHub-API
  in de repo (secret `HL_GITHUB_TOKEN`: fine-grained token, alleen repo Handleidingen, Contents read/write + Actions read).
  Upload = hoogste versie + 1 in dezelfde map, oudere versies van die bron worden in dezelfde commit verwijderd.
- Beheerder toevoegen: `insert into hl_beheerders (email) values ('…');` (account met wachtwoord moet bestaan, zie MOL).

## Later
- Domein melanchthon.xyz overzetten van Lovable naar GitHub Pages (CNAME in public/, DNS, Pages → Custom domain).
- Portaal voor projecten/lessen met Supabase op dezelfde site; handleidingen blijven openbaar.
