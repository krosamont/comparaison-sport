#!/usr/bin/env bash
# Déclinaisons Instagram des vidéos Reels (videos/<ligue>.mp4, 1080x1920) :
#   videos/post/<ligue>.mp4  post du fil, 1080x1350 (4:5) : on garde la zone utile (titre -> sources), sans les
#                            marges réservées à l'interface Reels, réduite et centrée sur le fond papier
#   videos/gif/<ligue>.gif   GIF du post (540x675, 12 images/s, palette optimisée)
# Usage : scripts/formats.sh [ligue ...]   (par défaut : toutes les vidéos de videos/)
set -euo pipefail
cd "$(dirname "$0")/.."
PAPIER=0xebe7de
mkdir -p videos/post videos/gif
ligues=("$@")
[ ${#ligues[@]} -gt 0 ] || ligues=($(ls videos/*.mp4 | xargs -n1 basename | sed 's/\.mp4$//'))
for l in "${ligues[@]}"; do
  # zone utile : y 40 -> 1650 (1610 px) ; 4:5 => largeur 1288, on complète les côtés avec le papier
  ffmpeg -v error -y -i "videos/$l.mp4" \
    -vf "crop=1080:1610:0:40,pad=1288:1610:104:0:color=$PAPIER,scale=1080:1350:flags=lanczos" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "videos/post/$l.mp4"
  ffmpeg -v error -y -i "videos/post/$l.mp4" \
    -vf "fps=12,scale=540:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
    "videos/gif/$l.gif"
  echo "$l : post $(du -h "videos/post/$l.mp4" | cut -f1), gif $(du -h "videos/gif/$l.gif" | cut -f1)"
done
