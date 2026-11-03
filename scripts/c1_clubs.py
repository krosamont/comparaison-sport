"""Référentiel des clubs de C1 : position (Wikidata : stade > coordonnées du club > siège > ville) et logo.

Sortie : data/c1/clubs.json  {page: {"qid", "lat", "lon", "source"}}
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wiki import get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://en.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"


def par_lots(xs, n=50):
    xs = list(xs)
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def qids(pages):
    out = {}
    for lot in par_lots(pages):
        r = json.loads(get(API, {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                                 "titles": "|".join(lot), "redirects": 1, "format": "json"}))
        for p in r["query"]["pages"].values():
            if "pageprops" in p:
                out[p["title"]] = p["pageprops"]["wikibase_item"]
    return out


def entites(ids):
    out = {}
    for lot in par_lots(sorted(set(ids))):
        r = json.loads(get(WD, {"action": "wbgetentities", "ids": "|".join(lot), "props": "claims|labels",
                                "languages": "fr|en", "format": "json"}))
        out.update(r["entities"])
    return out


def valeurs(ent, prop):
    out = []
    for c in ent.get("claims", {}).get(prop, []):
        v = c["mainsnak"].get("datavalue", {}).get("value")
        if v is not None:
            out.append(v)
    return out


def coord(ent):
    v = valeurs(ent, "P625")
    return (v[0]["latitude"], v[0]["longitude"]) if v else None


def main():
    part = json.loads((ROOT / "data" / "c1" / "participants.json").read_text())
    pages = sorted({c["page"] for cl in part.values() for c in cl})
    q = qids(pages)
    manquants = [p for p in pages if p not in q]
    assert not manquants, manquants
    clubs = entites(q.values())
    liens = {}  # P115 stade, P159 siège, P131 localisation
    for qid, e in clubs.items():
        for prop in ("P115", "P159", "P131"):
            liens[(qid, prop)] = [v["id"] for v in valeurs(e, prop)]
    lieux = entites({i for v in liens.values() for i in v})
    out = {}
    for page in pages:
        qid = q[page]
        e = clubs[qid]
        res, source = None, None
        for prop in ("P115",):
            for i in liens[(qid, prop)]:
                res = res or coord(lieux.get(i, {}))
            source = source or (prop if res else None)
        if not res and coord(e):
            res, source = coord(e), "P625"
        for prop in ("P159", "P131"):
            if res:
                break
            for i in liens[(qid, prop)]:
                res = res or coord(lieux.get(i, {}))
            source = prop if res else None
        label = e.get("labels", {}).get("fr", e.get("labels", {}).get("en", {})).get("value", page)
        out[page] = dict(qid=qid, label_fr=label, lat=res[0] if res else None, lon=res[1] if res else None,
                         source=source)
    dest = ROOT / "data" / "c1" / "clubs.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    sans = [p for p, c in out.items() if c["lat"] is None]
    print(len(out), "clubs ;", "sans position :", sans)
    from collections import Counter
    print(Counter(c["source"] for c in out.values()))


if __name__ == "__main__":
    main()
