#!/usr/bin/env bash
# Publie la page du projet sur data-workers.com (serveur o2switch, par SSH) :
#   /projet/comparaison/ (+ clair/) et /en/projet/comparaison/ (+ clair/), la carte interactive (carte.js),
#   ses données (data/<ligue>.json + logos) et la vignette de la carte du projet (/projet/assets/comparaison.jpg).
# À lancer après scripts/export_web.py et scripts/page_site.py.
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=mjzg4129@109.234.164.61; SSH="ssh -q -i $HOME/.ssh/id_rsa"; SCP="scp -q -i $HOME/.ssh/id_rsa"
D=data-workers.com
$SSH "$HOST" "mkdir -p $D/projet/comparaison/clair $D/projet/comparaison/data $D/en/projet/comparaison/clair $D/projet/assets"
rsync -a --delete -e "$SSH" site/data/ "$HOST:$D/projet/comparaison/data/"
$SCP site/carte.js "$HOST:$D/projet/comparaison/carte.js"
$SCP site/media/vignette.jpg "$HOST:$D/projet/assets/comparaison.jpg"
$SCP site/projet/comparaison/index.html "$HOST:$D/projet/comparaison/index.html"
$SCP site/projet/comparaison/clair/index.html "$HOST:$D/projet/comparaison/clair/index.html"
$SCP site/en/projet/comparaison/index.html "$HOST:$D/en/projet/comparaison/index.html"
$SCP site/en/projet/comparaison/clair/index.html "$HOST:$D/en/projet/comparaison/clair/index.html"
echo "en ligne : https://data-workers.com/projet/comparaison/ et https://data-workers.com/en/projet/comparaison/ (+ clair/)"
