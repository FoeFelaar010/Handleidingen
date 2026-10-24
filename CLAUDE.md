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
  de omzetter kiest de hoogste versie. Python én React lezen dit bestand.
- React 18 + Vite 5, geen router: hash-adressen `#/slug/hoofdstuk` (zelfde als de oude site). `public/handleidingen/index.html`
  stuurt oude links door.
- Extra's (3D-viewer, animaties, MakeCode-oefenpagina) in `public/extra/`, als iframe op de pagina; de animaties laden three.js van jsDelivr.

## Online zetten
- Op deze pc staan geen git/node/python. Gebruiker uploadt via github.com (repo FoeFelaar010/handleidingen, branch main);
  controleren met de Actions-run "Online zetten" (waarschuwingen van de omzetter staan in de log).

## Later
- Domein melanchthon.xyz overzetten van Lovable naar GitHub Pages (CNAME in public/, DNS, Pages → Custom domain).
- Portaal voor projecten/lessen met Supabase op dezelfde site; handleidingen blijven openbaar.
