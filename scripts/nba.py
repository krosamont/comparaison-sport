"""Données de la vidéo NBA -> data/video/nba.json.

Chaque franchise a des époques (nom, ville, page sportslogos.net). Le logo affiché pour une saison est
le logo principal (Primary Logo) en usage cette saison-là, d'après sportslogos.net.
Les champions viennent de data/champions/nba.csv.
"""
import csv
import io
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
from bs4 import BeautifulSoup
from PIL import Image
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
from regions import regions  # noqa: E402
from wiki import get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEBUT, FIN = 1975, 2025
SL = "https://www.sportslogos.net"
LOGOS = ROOT / "data" / "logos" / "nba"

# franchise : [(première saison, dernière saison, nom, id sportslogos, lat, lon)], saisons = année de début
FRANCHISES = {
    "Hawks": [(1975, 2025, "Atlanta Hawks", 220, 33.757, -84.396)],
    "Celtics": [(1975, 2025, "Boston Celtics", 213, 42.366, -71.062)],
    "Nets": [(1976, 1976, "New York Nets", 1428, 40.723, -73.590),
             (1977, 2011, "New Jersey Nets", 215, 40.813, -74.074),
             (2012, 2025, "Brooklyn Nets", 3786, 40.683, -73.975)],
    "Hornets": [(1988, 2001, "Charlotte Hornets", 256, 35.225, -80.839),
                (2004, 2013, "Charlotte Bobcats", 258, 35.225, -80.839),
                (2014, 2025, "Charlotte Hornets", 5120, 35.225, -80.839)],
    "Bulls": [(1975, 2025, "Chicago Bulls", 221, 41.881, -87.674)],
    "Cavaliers": [(1975, 2025, "Cleveland Cavaliers", 222, 41.497, -81.688)],
    "Mavericks": [(1980, 2025, "Dallas Mavericks", 228, 32.790, -96.810)],
    "Nuggets": [(1976, 2025, "Denver Nuggets", 229, 39.749, -105.008)],
    "Pistons": [(1975, 2025, "Detroit Pistons", 223, 42.341, -83.055)],
    "Warriors": [(1975, 2018, "Golden State Warriors", 235, 37.750, -122.203),
                 (2019, 2025, "Golden State Warriors", 235, 37.768, -122.388)],
    "Rockets": [(1975, 2025, "Houston Rockets", 230, 29.751, -95.362)],
    "Pacers": [(1976, 2025, "Indiana Pacers", 224, 39.764, -86.155)],
    "Clippers": [(1975, 1977, "Buffalo Braves", 253, 42.875, -78.876),
                 (1978, 1983, "San Diego Clippers", 254, 32.755, -117.212),
                 (1984, 2023, "Los Angeles Clippers", 236, 34.043, -118.267),
                 (2024, 2025, "Los Angeles Clippers", 236, 33.945, -118.343)],
    "Lakers": [(1975, 1998, "Los Angeles Lakers", 237, 33.958, -118.342),
               (1999, 2025, "Los Angeles Lakers", 237, 34.043, -118.267)],
    "Grizzlies": [(1995, 2000, "Vancouver Grizzlies", 257, 49.278, -123.109),
                  (2001, 2025, "Memphis Grizzlies", 231, 35.138, -90.051)],
    "Heat": [(1988, 2025, "Miami Heat", 214, 25.781, -80.188)],
    "Bucks": [(1975, 2025, "Milwaukee Bucks", 225, 43.045, -87.917)],
    "Timberwolves": [(1989, 2025, "Minnesota Timberwolves", 232, 44.980, -93.276)],
    "Pelicans": [(2002, 2012, "New Orleans Hornets", 226, 29.949, -90.082),
                 (2013, 2025, "New Orleans Pelicans", 4962, 29.949, -90.082)],
    "Knicks": [(1975, 2025, "New York Knicks", 216, 40.751, -73.993)],
    "Thunder": [(1975, 2007, "Seattle SuperSonics", 241, 47.622, -122.354),
                (2008, 2025, "Oklahoma City Thunder", 2687, 35.463, -97.515)],
    "Magic": [(1989, 2025, "Orlando Magic", 217, 28.539, -81.384)],
    "76ers": [(1975, 2025, "Philadelphia 76ers", 218, 39.901, -75.172)],
    "Suns": [(1975, 2025, "Phoenix Suns", 238, 33.446, -112.071)],
    "Trail Blazers": [(1975, 2025, "Portland Trail Blazers", 239, 45.532, -122.667)],
    "Kings": [(1975, 1984, "Kansas City Kings", 248, 39.097, -94.580),
              (1985, 2025, "Sacramento Kings", 240, 38.580, -121.500)],
    "Spurs": [(1976, 2025, "San Antonio Spurs", 233, 29.427, -98.438)],
    "Raptors": [(1995, 2025, "Toronto Raptors", 227, 43.643, -79.379)],
    "Jazz": [(1975, 1978, "New Orleans Jazz", 255, 29.951, -90.081),
             (1979, 2025, "Utah Jazz", 234, 40.768, -111.901)],
    "Wizards": [(1975, 1996, "Washington Bullets", 587, 38.904, -76.858),
                (1997, 2025, "Washington Wizards", 219, 38.898, -77.021)],
}
# nombre d'équipes attendu (contrôle) : ABA en 1976, expansions 1980, 1988, 1989, 1995, 2004 ; Charlotte vide 2002-03
ATTENDU = {1975: 18, 1976: 22, 1980: 23, 1988: 25, 1989: 27, 1995: 29, 2004: 30}

ABREV = {"Golden State Warriors": "GS Warriors", "Portland Trail Blazers": "Portland", "Oklahoma City Thunder": "OKC Thunder",
         "Los Angeles Lakers": "LA Lakers", "Los Angeles Clippers": "LA Clippers", "Minnesota Timberwolves": "Minnesota",
         "Philadelphia 76ers": "Philadelphia", "Seattle SuperSonics": "Seattle Sonics"}


def logos_principaux(team_id):
    """[(première saison, dernière saison, url)] des logos principaux d'une page d'équipe sportslogos."""
    html = get(f"{SL}/logos/list_by_team/{team_id}/")
    s = BeautifulSoup(html, "lxml")
    grands = {}
    for a in s.find_all("a", href=re.compile(r"/logos/view/[^/]+/.+/Primary-Logo$")):
        img = a.find("img")
        if img and "/full/" in img.get("src", ""):
            grands[a["href"].split("/")[3]] = img["src"]
    out = []
    for a in s.find_all("a", href=re.compile(r"/logos/view/[^/]+/.+/Primary-Logo$")):
        m = re.search(r"(\d{4})/\d{2}\s*-\s*(?:(\d{4})/\d{2}|Pres)|(\d{4})/\d{2}$", a.get_text(" ", strip=True))
        img = a.find("img")
        if not m or not img:
            continue
        de = int(m.group(1) or m.group(3))
        fin = int(m.group(2)) if m.group(2) else (9999 if m.group(1) else de)
        lid = a["href"].split("/")[3]
        out.append((de, fin, grands.get(lid, img["src"])))
    return sorted(set(out))


def telecharger(url):
    dest = LOGOS / (re.sub(r"\W+", "_", url.rsplit("/", 1)[-1].rsplit(".", 1)[0]) + ".png")
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(io.BytesIO(get(url, binary=True))).convert("RGBA")
        # les .gif de sportslogos ont un fond blanc opaque : remplissage transparent depuis les bords
        # (seul le blanc relié au bord disparaît, le blanc à l'intérieur du logo est conservé)
        from PIL import ImageDraw
        w, h = img.size
        for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
            r, g, b, a = img.getpixel((x, y))
            if a and min(r, g, b) > 225:
                ImageDraw.floodfill(img, (x, y), (255, 255, 255, 0), thresh=40)
        img.crop(img.getbbox()).save(dest)
    return str(dest.relative_to(ROOT))


def main():
    saisons = {an: [] for an in range(DEBUT, FIN + 1)}
    for f, eres in FRANCHISES.items():
        for de, a, *_ in eres:
            for an in range(de, a + 1):
                saisons[an].append(f)
    attendu = None
    for an in range(DEBUT, FIN + 1):
        attendu = ATTENDU.get(an, attendu)
        assert len(saisons[an]) == attendu, (an, len(saisons[an]), attendu)

    geo = regions("nba")
    geo_m = geo.to_crs(5070)
    clubs = {}
    for f, eres in FRANCHISES.items():
        sorties = []
        for de, a, nom, tid, lat, lon in eres:
            pt = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(5070).iloc[0]
            reg = geo.iloc[[geo_m.distance(pt).argmin()]]  # région contenant le point, ou la plus proche (rives)
            logos = [(d, fi, u) for d, fi, u in logos_principaux(tid) if fi >= de and d <= a]
            assert logos, (nom, tid)
            for an in range(de, a + 1):
                cand = [u for d, fi, u in logos if d <= an <= fi]
                url = cand[-1] if cand else min(logos, key=lambda x: abs(x[0] - an))[2]
                sorties.append(dict(de=an, a=an, nom=ABREV.get(nom, nom), lat=lat, lon=lon,
                                    region=reg.iloc[0]["region"], logo=telecharger(url)))
        # regroupe les saisons consécutives identiques
        eres_out = []
        for e in sorties:
            p = eres_out[-1] if eres_out else None
            if p and p["a"] == e["de"] - 1 and all(p[k] == e[k] for k in ("nom", "lat", "lon", "logo")):
                p["a"] = e["a"]
            else:
                eres_out.append(e)
        dernier = eres_out[-1]
        clubs[f] = dict(nom=dernier["nom"], lat=dernier["lat"], lon=dernier["lon"], region=dernier["region"],
                        logo=dernier["logo"], eres=eres_out)
        print(f"{f:<14}", " | ".join(f"{e['de']}-{e['a']} {e['nom']}" for e in eres_out))

    nom2f = {nom: f for f, eres in FRANCHISES.items() for _, _, nom, *_ in eres}
    champions = {}
    with open(ROOT / "data" / "champions" / "nba.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            an = int(r["annee_fin"]) - 1
            f = nom2f[r["champion"]]
            assert f in saisons[an], (an, f)
            champions[an] = f
    out = dict(ligue="nba", saisons={str(a): sorted(v) for a, v in saisons.items()},
               champions={str(a): champions.get(a) for a in saisons}, clubs=clubs)
    dest = ROOT / "data" / "video" / "nba.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(clubs), "franchises ->", dest)


if __name__ == "__main__":
    main()
