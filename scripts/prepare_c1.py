"""Données de la vidéo Ligue des champions -> data/video/ligue_des_champions.json (même format que prepare.py).

Entrées : data/c1/participants.json (c1_participants.py), data/c1/clubs.json (c1_clubs.py),
data/champions/ligue_des_champions.csv (champions.py).
"""
import csv
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
import prepare  # noqa: E402  (réutilise vignettes / logo)
from regions import regions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIGUE = "ligue_des_champions"
prepare.LIGUE = LIGUE
prepare.TELECHARGER = "--logos" in sys.argv  # les logos manquants ne sont retentés que sur demande

# Nom du champion (data/champions) -> motif reconnaissant sa page Wikipedia parmi les participants
MOTIFS = {
    "Bayern Munich": r"Bayern Munich", "Liverpool": r"^Liverpool F\.C\.", "Nottingham Forest": r"Nottingham Forest",
    "Aston Villa": r"Aston Villa", "Hambourg SV": r"Hamburger SV", "Juventus": r"^Juventus",
    "Steaua Bucarest": r"Steaua|FCSB", "FC Porto": r"^FC Porto", "PSV Eindhoven": r"PSV Eindhoven",
    "AC Milan": r"^A\.?C\.? Milan", "Étoile rouge de Belgrade": r"Red Star Belgrade",
    "FC Barcelone": r"^FC Barcelona", "Olympique de Marseille": r"Olympique de Marseille",
    "Ajax Amsterdam": r"^AFC Ajax", "Borussia Dortmund": r"Borussia Dortmund", "Real Madrid": r"^Real Madrid",
    "Manchester United": r"^Manchester United", "Inter Milan": r"Inter Milan|Internazionale",
    "Chelsea": r"^Chelsea F\.C\.", "Manchester City": r"^Manchester City", "Paris Saint-Germain": r"Paris Saint-Germain",
}
# Hors cadre (lon > 53) : posés au bord est de la carte, dans le Kazakhstan visible
HORS_CADRE = {"FC Astana": (49.5, 50.3), "FC Kairat": (47.8, 50.3)}


def main():
    part = {int(a): [c["page"] for c in cl] for a, cl in
            json.loads((ROOT / "data" / "c1" / "participants.json").read_text()).items()}
    infos = json.loads((ROOT / "data" / "c1" / "clubs.json").read_text())
    champions, noms = {}, {}
    with open(ROOT / "data" / "champions" / "ligue_des_champions.csv", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    for r in lignes:
        an = int(r["annee_fin"]) - 1
        motif = MOTIFS[r["champion"]]
        cand = sorted({p for cl in part.values() for p in cl if re.search(motif, p)})
        assert len(cand) == 1, (r["champion"], cand)
        champions[an] = cand[0]
        noms[cand[0]] = r["champion"]
    # tenant du titre exempté du premier tour (absent des tableaux du premier tour)
    # 1993/94 exclu : l'OM, tenant, a été exclu de la compétition (affaire VA-OM)
    for an in sorted(part):
        if an <= 1992 and an - 1 in champions and champions[an - 1] not in part[an]:
            part[an].append(champions[an - 1])
            print(f"{an}: tenant du titre ajouté ({noms[champions[an - 1]]}) -> {len(part[an])} clubs")
    for an, c in champions.items():
        assert c in part[an], (an, c)

    tous = sorted({p for cl in part.values() for p in cl})
    geo = regions(LIGUE)
    geo_m = geo.to_crs(3035)
    thumbs = prepare.vignettes(tous)
    clubs = {}
    for page in tous:
        lat, lon = HORS_CADRE.get(page, (infos[page]["lat"], infos[page]["lon"]))
        pt = Point(lon, lat)
        reg = geo[geo.contains(pt)]
        if len(reg):
            region = reg.iloc[0]["region"]
        else:
            region = geo.iloc[geo_m.distance(gpd.GeoSeries([pt], crs=4326).to_crs(3035).iloc[0]).argmin()]["region"]
        cle = re.sub(r"[^\w.-]+", "_", page)
        chemin = prepare.logo(cle, page, thumbs[page])
        clubs[page] = dict(nom=noms.get(page, infos[page]["label_fr"]), lat=lat, lon=lon, region=region,
                           logo=str(chemin.relative_to(ROOT)) if chemin else None)
    sans_logo = [p for p, c in clubs.items() if not c["logo"]]
    out = dict(ligue=LIGUE, saisons={str(a): sorted(part[a]) for a in sorted(part)},
               champions={str(a): champions.get(a) for a in sorted(part)}, clubs=clubs)
    dest = ROOT / "data" / "video" / f"{LIGUE}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(tous)} clubs -> {dest} ; sans logo : {sans_logo}")


if __name__ == "__main__":
    main()
