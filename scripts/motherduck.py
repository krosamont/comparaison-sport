"""Données de comparaison_sport vers la base foot du serveur (~/data/foot.duckdb, $FOOT_DB), schéma comparaison_sport.
(MotherDuck abandonné le 2026-11-03 : trop cher ; le nom du script est resté.)

    python scripts/motherduck.py export          # Mac : data/video + data/champions -> data/motherduck/*.csv
    python scripts/motherduck.py load [--dry-run] # serveur : data/motherduck/*.csv -> ~/data/foot.duckdb (remplace les tables)

Tables (une ligne par…) :
  competitions    compétition
  champions       compétition × saison (champion, finaliste ; champion vide = titre non attribué)
  participations  compétition × saison × club (nom, région, position et logo de la saison)
  clubs           compétition × club × époque (NBA : déménagements / changements de nom ou de logo)
"""
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "motherduck"
SCHEMA = "comparaison_sport"

COMPETITIONS = {  # clé du fichier data/video -> (titre, sport, fichier data/champions)
    "france": ("Championnat de France", "football", "ligue1.csv"),
    "angleterre": ("Championnat d'Angleterre", "football", "angleterre.csv"),
    "liga": ("Championnat d'Espagne", "football", "liga.csv"),
    "ligue_des_champions": ("Ligue des champions", "football", "ligue_des_champions.csv"),
    "nba": ("NBA", "basket", "nba.csv"),
}
COLONNES = {
    "competitions": {"competition": "VARCHAR", "titre": "VARCHAR", "sport": "VARCHAR",
                     "premiere_saison": "VARCHAR", "derniere_saison": "VARCHAR", "nb_clubs": "INTEGER"},
    "champions": {"competition": "VARCHAR", "saison": "VARCHAR", "annee_debut": "INTEGER", "club_id": "VARCHAR",
                  "champion": "VARCHAR", "finaliste": "VARCHAR", "region": "VARCHAR"},
    "participations": {"competition": "VARCHAR", "saison": "VARCHAR", "annee_debut": "INTEGER", "club_id": "VARCHAR",
                       "nom": "VARCHAR", "region": "VARCHAR", "lat": "DOUBLE", "lon": "DOUBLE",
                       "champion": "BOOLEAN", "logo": "VARCHAR"},
    "clubs": {"competition": "VARCHAR", "club_id": "VARCHAR", "premiere_saison": "INTEGER",
              "derniere_saison": "INTEGER", "nom": "VARCHAR", "region": "VARCHAR", "lat": "DOUBLE",
              "lon": "DOUBLE", "logo": "VARCHAR"},
}


def saison(an):
    return f"{an}/{str(an + 1)[2:]}"


def ere(club, an):
    eres = club.get("eres") or [dict(club, de=-9999, a=9999)]
    for e in eres:
        if e["de"] <= an <= e["a"]:
            return e
    return eres[-1]


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    lignes = {t: [] for t in COLONNES}
    for comp, (titre, sport, fichier_champ) in COMPETITIONS.items():
        chemin = ROOT / "data" / "video" / f"{comp}.json"
        if not chemin.exists():
            print(f"{comp}: pas de données ({chemin.name}), ignorée")
            continue
        d = json.loads(chemin.read_text())
        annees = sorted(int(a) for a in d["saisons"])
        finalistes = {}
        with open(ROOT / "data" / "champions" / fichier_champ, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                finalistes[int(r["annee_fin"]) - 1] = r["finaliste"]
        lignes["competitions"].append(dict(competition=comp, titre=titre, sport=sport,
                                           premiere_saison=saison(annees[0]), derniere_saison=saison(annees[-1]),
                                           nb_clubs=len(d["clubs"])))
        for an in annees:
            champ = d["champions"][str(an)]
            ec = ere(d["clubs"][champ], an) if champ else None
            lignes["champions"].append(dict(competition=comp, saison=saison(an), annee_debut=an, club_id=champ or "",
                                            champion=ec["nom"] if ec else "", finaliste=finalistes.get(an, ""),
                                            region=ec["region"] if ec else ""))
            for cle in d["saisons"][str(an)]:
                e = ere(d["clubs"][cle], an)
                lignes["participations"].append(dict(competition=comp, saison=saison(an), annee_debut=an, club_id=cle,
                                                     nom=e["nom"], region=e["region"], lat=e["lat"], lon=e["lon"],
                                                     champion=cle == champ, logo=e.get("logo") or ""))
        for cle, c in d["clubs"].items():
            for e in c.get("eres") or [dict(c, de=annees[0], a=annees[-1])]:
                lignes["clubs"].append(dict(competition=comp, club_id=cle, premiere_saison=max(e["de"], annees[0]),
                                            derniere_saison=min(e["a"], annees[-1]), nom=e["nom"], region=e["region"],
                                            lat=e["lat"], lon=e["lon"], logo=e.get("logo") or ""))
        print(f"{comp}: {len(annees)} saisons, {len(d['clubs'])} clubs")
    for t, rows in lignes.items():
        with open(OUT / f"{t}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(COLONNES[t]))
            w.writeheader()
            w.writerows(rows)
        print(f"  {t}.csv : {len(rows)} lignes")


def load(dry_run=False):
    import duckdb
    base = os.environ.get("FOOT_DB", os.path.expanduser("~/data/foot.duckdb"))
    con = duckdb.connect(":memory:" if dry_run else base)
    con.execute(f"create schema if not exists {SCHEMA}")
    con.execute("begin")
    try:
        for t, cols in COLONNES.items():
            types = "{" + ", ".join(f"'{c}': '{typ}'" for c, typ in cols.items()) + "}"
            con.execute(f"create or replace table {SCHEMA}.{t} as select *, now()::timestamp as _loaded_at "
                        f"from read_csv('{OUT / (t + '.csv')}', header=true, columns={types})")
            n = con.execute(f"select count(*) from {SCHEMA}.{t}").fetchone()[0]
            print(f"{'(test) ' if dry_run else ''}{SCHEMA}.{t} : {n} lignes")
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise


if __name__ == "__main__":
    {"export": lambda: export(), "load": lambda: load("--dry-run" in sys.argv)}[sys.argv[1]]()
