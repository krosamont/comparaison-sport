"""Données de la vidéo Liga -> data/video/liga.json (même format que prepare.py).

Clubs de chaque saison : classement de la page Wikipedia « YYYY–YY La Liga » (le 1er est le champion).
Position des clubs : Wikidata (stade). Logos : Wikipedia. Régions : communautés autonomes (geoBoundaries),
avec les Canaries rapprochées en encart (voir regions.DECALAGE_CANARIES).
"""
import csv
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
import prepare  # noqa: E402  (vignettes / logo)
from c1_clubs import coord, entites, qids, valeurs  # noqa: E402
from c1_participants import canoniques, equipe, html  # noqa: E402
from regions import DECALAGE_CANARIES, regions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIGUE = "liga"
prepare.LIGUE = LIGUE
prepare.TELECHARGER = True
DEBUT, FIN = 1975, 2025

# nombre de clubs attendu par saison (contrôle)
def attendu(an):
    return 18 if an <= 1986 else 20 if an <= 1994 else 22 if an <= 1996 else 20


# noms affichés pour les champions (classement des titres, cadre du champion)
NOMS = {"Real Madrid CF": "Real Madrid", "FC Barcelona": "FC Barcelone", "Atlético Madrid": "Atlético de Madrid",
        "Athletic Bilbao": "Athletic Bilbao", "Real Sociedad": "Real Sociedad", "Valencia CF": "Valence CF",
        "Deportivo de La Coruña": "Deportivo La Corogne",
        "Deportivo de A Coruña": "Deportivo La Corogne"}
# clubs sans coordonnées sur Wikidata (stade, siège, ville)
POSITIONS_MANUELLES = {"Real Burgos CF": (42.338, -3.688)}  # stade El Plantío, Burgos


def classement(an):
    s = f"{an}–{an + 1 if an == 1999 else str(an + 1)[2:]}"
    soup = html(f"{s} La Liga")
    for tb in soup.select("table.wikitable"):
        tete = tb.select("tr")[0].get_text(" ")
        if "Pos" not in tete or "Pts" not in tete:
            continue
        clubs = []
        for tr in tb.select("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) > 3:
                e = equipe(cells[1]) or equipe(cells[0])
                if e:
                    clubs.append(e["page"])
        return clubs
    raise ValueError(f"pas de classement pour {s}")


def main():
    brut = {an: classement(an) for an in range(DEBUT, FIN + 1)}
    canon = canoniques([p for cl in brut.values() for p in cl])
    saisons = {an: [canon[p] for p in cl] for an, cl in brut.items()}
    # champions : data/champions/liga.csv (ton CSV), contrôlés contre le 1er de chaque classement
    with open(ROOT / "data" / "champions" / "liga.csv", encoding="utf-8") as f:
        csv_champ = {int(r["annee_fin"]) - 1: r["champion"] for r in csv.DictReader(f)}
    canon_csv = canoniques(list(csv_champ.values()))
    champions = {an: canon_csv[csv_champ[an]] for an in saisons}
    for an, cl in saisons.items():
        assert champions[an] == cl[0], (an, champions[an], cl[0])
    for an, cl in saisons.items():
        assert len(set(cl)) == attendu(an), (an, len(set(cl)), attendu(an))
    compte = {}
    for c in champions.values():
        compte[c] = compte.get(c, 0) + 1
    print("titres :", compte)

    tous = sorted({p for cl in saisons.values() for p in cl})
    q = qids(tous)
    ents = entites(q.values())
    stades = entites({v["id"] for e in ents.values() for p in ("P115", "P159", "P131") for v in valeurs(e, p)})
    geo = regions(LIGUE)
    geo_m = geo.to_crs(25830)
    thumbs = prepare.vignettes(tous)
    clubs = {}
    for page in tous:
        e = ents[q[page]]
        pos = None
        for prop in ("P115",):
            for v in valeurs(e, prop):
                pos = pos or coord(stades.get(v["id"], {}))
        pos = pos or coord(e)
        for prop in ("P159", "P131"):
            for v in valeurs(e, prop):
                pos = pos or coord(stades.get(v["id"], {}))
        pos = pos or POSITIONS_MANUELLES.get(page)
        assert pos, page
        lat, lon = pos
        if lat < 30:  # Canaries : même décalage que la région pour l'encart
            lon, lat = lon + DECALAGE_CANARIES[0], lat + DECALAGE_CANARIES[1]
        pt = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(25830).iloc[0]
        region = geo.iloc[geo_m.distance(pt).argmin()]["region"]
        cle = re.sub(r"[^\w.-]+", "_", page)
        chemin = prepare.logo(cle, page, thumbs[page])
        label = e.get("labels", {}).get("fr", e.get("labels", {}).get("en", {})).get("value", page)
        clubs[page] = dict(nom=NOMS.get(page, label), lat=lat, lon=lon, region=region,
                           logo=str(chemin.relative_to(ROOT)) if chemin else None)
        print(f"  {page:<32} {region:<22} {lat:.2f} {lon:.2f} {'logo' if chemin else '-'}")
    out = dict(ligue=LIGUE, saisons={str(a): sorted(set(v)) for a, v in saisons.items()},
               champions={str(a): c for a, c in champions.items()}, clubs=clubs)
    dest = ROOT / "data" / "video" / f"{LIGUE}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(tous), "clubs ->", dest, "; sans logo :", [p for p, c in clubs.items() if not c["logo"]])


if __name__ == "__main__":
    main()
