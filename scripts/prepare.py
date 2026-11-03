"""Prépare les données d'une vidéo : clubs par saison, champions, régions, logos.

Usage : python scripts/prepare.py france|angleterre
Sortie : data/video/<ligue>.json et data/logos/<ligue>/*.png
"""
import csv
import io
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from PIL import Image
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
from clubs import ALIASES, ANGLETERRE, CHAMPIONS, FRANCE, SAISONS_MANQUANTES  # noqa: E402
from regions import regions  # noqa: E402
from wiki import get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEBUT, FIN = 1975, 2025  # années de début de saison

TELECHARGER = True  # prepare_c1 le désactive sauf avec --logos
LIGUE = sys.argv[1] if __name__ == "__main__" else None  # prepare_c1 importe ce module
REF = {"france": FRANCE, "angleterre": ANGLETERRE}.get(LIGUE)
FICHIER_CHAMPIONS = {"france": "ligue1.csv", "angleterre": "angleterre.csv"}.get(LIGUE)


def participants():
    d = pd.read_csv(ROOT / "data" / "engsoccerdata" / f"{LIGUE}.csv", low_memory=False)
    d = d[(d.tier == 1) & (d.Season >= DEBUT)]
    par_saison = {int(s): sorted(set(g.home) | set(g.visitor)) for s, g in d.groupby("Season")}
    for an, spec in SAISONS_MANQUANTES[LIGUE].items():
        if isinstance(spec, str):  # "2024 -A -B +C" : saison de référence avec montées/descentes
            base, *ops = spec.split(" ")
            clubs = set(par_saison[int(base)])
            for op in " ".join(ops).replace(" -", "\0-").replace(" +", "\0+").split("\0"):
                (clubs.discard if op[0] == "-" else clubs.add)(op[1:])
            spec = sorted(clubs)
        par_saison[an] = spec
    out = {}
    for an in range(DEBUT, FIN + 1):
        clubs = sorted({ALIASES.get(c, c) for c in par_saison[an]})
        inconnus = [c for c in clubs if c not in REF]
        assert not inconnus, (an, inconnus)
        out[an] = clubs
    return out


def champions():
    out = {}
    with open(ROOT / "data" / "champions" / FICHIER_CHAMPIONS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nom = r["champion"]
            out[int(r["annee_fin"]) - 1] = CHAMPIONS.get(nom, nom) if nom else None
    return out


def vignettes(pages):
    """Page Wikipedia -> URL de l'image principale (logo), par lots de 50."""
    out = {}
    for i in range(0, len(pages), 50):
        lot = pages[i:i + 50]
        r = json.loads(get("https://en.wikipedia.org/w/api.php", {
            "action": "query", "prop": "pageimages", "titles": "|".join(lot), "piprop": "thumbnail",
            "pithumbsize": 300, "pilicense": "any", "redirects": 1, "format": "json"}))
        q = r["query"]
        alias = {x["from"]: x["to"] for x in q.get("normalized", []) + q.get("redirects", [])}
        src = {p["title"]: p.get("thumbnail", {}).get("source") for p in q["pages"].values()}
        for page in lot:
            t = page
            while t in alias:
                t = alias[t]
            out[page] = src.get(t)
    return out


def logo(cle, page, thumb):
    dest = ROOT / "data" / "logos" / LIGUE / f"{cle}.png"
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not thumb or not TELECHARGER:
        if thumb:
            print("  logo non téléchargé (relancer avec --logos) :", cle)
        else:
            print("  pas de logo :", cle, page)
        return None
    img = None
    # thumb.wikimedia.org ne répond pas partout : upload.wikimedia.org sert les mêmes fichiers
    for url in dict.fromkeys([thumb.replace("://thumb.wikimedia.org/", "://upload.wikimedia.org/"), thumb]):
        try:
            img = Image.open(io.BytesIO(get(url, binary=True))).convert("RGBA")
            break
        except Exception as err:  # réseau, limite de débit Wikimedia... : on retentera au prochain passage
            print("  logo reporté :", cle, type(err).__name__)
    if img is None:
        return None
    img = img.crop(img.getbbox())
    img.save(dest)
    return dest


def main():
    saisons = participants()
    champ = champions()
    for an, c in champ.items():
        if DEBUT <= an <= FIN and c:
            assert c in saisons[an], (an, c)
    tous = sorted({c for cl in saisons.values() for c in cl})
    geo = regions(LIGUE)
    thumbs = vignettes([REF[c][3] for c in tous])
    geo_m = geo.to_crs(3857)
    clubs = {}
    for cle in tous:
        nom, lat, lon, page = REF[cle]
        pt = Point(lon, lat)
        reg = geo[geo.contains(pt)]
        region = reg.iloc[0]["region"] if len(reg) else geo.iloc[geo_m.distance(gpd.GeoSeries([pt], crs=4326).to_crs(3857).iloc[0]).argmin()]["region"]
        chemin = logo(cle, page, thumbs[page])
        clubs[cle] = dict(nom=nom, lat=lat, lon=lon, region=region,
                          logo=str(chemin.relative_to(ROOT)) if chemin else None)
    out = dict(ligue=LIGUE, saisons={str(a): saisons[a] for a in saisons},
               champions={str(a): champ.get(a) for a in saisons}, clubs=clubs)
    dest = ROOT / "data" / "video" / f"{LIGUE}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{LIGUE}: {len(tous)} clubs, {len(saisons)} saisons -> {dest}")
    for cle, c in clubs.items():
        print(f"  {c['nom']:<15} {c['region']:<28} {'logo' if c['logo'] else '-'}")


if __name__ == "__main__":
    main()
