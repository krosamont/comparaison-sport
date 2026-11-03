# Les championnats sur la carte

Cinquante saisons (1975/76 → 2025/26) de cinq compétitions sur une carte : championnat de France, d'Angleterre et
d'Espagne, Ligue des champions et NBA. Chaque club engagé est placé à son stade, saison après saison ; la couleur
d'une région montre ses titres, son relief le nombre de clubs présents, et la région du champion se soulève.

**Le visuel en ligne : <https://data-workers.com/projet/comparaison/>** (carte interactive avec bouton lecture ;
en anglais : <https://data-workers.com/en/projet/comparaison/>).

Le même moteur produit les vidéos (Reels Instagram, posts 4:5, GIF) : une compétition par vidéo, ou les cinq
côte à côte sur 5, 10, 25 ou 50 ans.

## Exemple reproductible (championnat de France)

L'échantillon versionné suffit pour le championnat de France : champions (`data/champions/ligue1.csv`, tirés de
Wikipédia), clubs de chaque saison (`data/engsoccerdata/france.csv`), régions (`data/geo/FRA_ADM1.geojson`,
geoBoundaries) et l'état préparé `data/video/france.json`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/prepare.py france                 # télécharge les logos des clubs (Wikipédia) -> data/logos/france/
.venv/bin/python scripts/render.py france --apercu 600     # une image de la vidéo -> videos/apercu_france_600.png
.venv/bin/python scripts/render.py france                  # la vidéo complète -> videos/france.mp4 (ffmpeg requis)
```

## Les autres compétitions

| Compétition | Données | Préparation |
|---|---|---|
| Angleterre | engsoccerdata `england.csv` (renommé `angleterre.csv`), geoBoundaries GBR ADM1/ADM2 | `scripts/prepare.py angleterre` |
| Espagne | classements Wikipédia « YYYY–YY La Liga », Wikidata, geoBoundaries ESP ADM1 | `scripts/liga.py` |
| Ligue des champions | phases de groupes / premier tour sur Wikipédia, stades sur Wikidata, geoBoundaries ADM0 (52 pays) | `scripts/c1_participants.py`, `c1_clubs.py`, `prepare_c1.py` |
| NBA | franchises et déménagements (`scripts/nba.py`), logos SportsLogos.net, geoBoundaries USA/CAN ADM1 | `scripts/nba.py` |

Les champions de chaque compétition viennent de `data/wikipedia_brut/` (exports de tableaux Wikipédia) via
`scripts/champions.py`. Les frontières se téléchargent sur l'API geoBoundaries
(`https://www.geoboundaries.org/api/current/gbOpen/<ISO>/<ADM>/`) dans `data/geo/`.

## Scripts

| Script | Rôle |
|---|---|
| `render.py <ligue>` | vidéo d'une compétition (format Reels 1080 × 1920) |
| `render_comparaison.py [--annees 5\|10\|25\|50] [--reel]` | les cinq compétitions côte à côte (GIF + MP4 paysage, ou Reels) |
| `formats.sh` | déclinaisons post Instagram (4:5) et GIF des vidéos |
| `export_web.py`, `page_site.py`, `site/carte.js` | la carte interactive de data-workers.com (FR / EN, thèmes sombre et clair) |
| `motherduck.py` | export des tables vers MotherDuck (`comparaison_sport.*`) |

Données : Wikipédia (CC BY-SA), engsoccerdata (James Curley, GPL-3), Wikidata (CC0), geoBoundaries (CC BY 4.0).
Les logos des clubs ne sont pas versionnés : ils se téléchargent depuis Wikipédia et SportsLogos.net.
Polices : Arvo et Inter (SIL Open Font License).
