#!/usr/bin/env bash
# Publie la page du projet sur data-workers.com par le dépôt du site (GitHub Actions) :
#   /projet/comparaison/ (+ clair/) et /en/projet/comparaison/ (+ clair/), la carte interactive (carte.js), ses données
#   (data/<ligue>.json + logos) et la vignette de la carte du projet (/projet/assets/comparaison.jpg).
# À lancer après scripts/export_web.py et scripts/page_site.py. Hors de l'arborescence dataScience : SITE_DEPOT=<dépôt>.
set -euo pipefail
cd "$(dirname "$0")/.."
OUTIL="${OUTIL_SITE:-$HOME/Documents/dataScience/outils/github/site_depot.sh}"
"$OUTIL" "content: Comparaison (interactive map of the leagues) updated" \
  site/projet/comparaison/index.html projet/comparaison/index.html \
  site/projet/comparaison/clair/index.html projet/comparaison/clair/index.html \
  site/en/projet/comparaison/index.html en/projet/comparaison/index.html \
  site/en/projet/comparaison/clair/index.html en/projet/comparaison/clair/index.html \
  site/carte.js projet/comparaison/carte.js \
  site/data projet/comparaison/data \
  site/media/vignette.jpg projet/assets/comparaison.jpg
