"""Construit un fichier propre par compétition : une ligne par saison -> champion.

Les CSV bruts (scrapés depuis Wikipedia) ont des colonnes décalées d'une ligne à
l'autre à cause des cellules fusionnées. On s'appuie donc sur l'ordre des liens
(href) dans chaque ligne plutôt que sur la position des colonnes.
"""
import csv
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
BRUT = ROOT / "data" / "wikipedia_brut"
OUT = ROOT / "data" / "champions"
OUT.mkdir(exist_ok=True)

DEBUT = 1976  # saison 1975/76 -> année de fin 1976


def lignes(nom):
    with open(BRUT / nom, encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        yield from r


def page(url):
    return unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def liens_wiki(row):
    return [c for c in row if c.startswith("https://") and "wikipedia.org/wiki/" in c]


def saison(fin):
    return f"{fin - 1}/{str(fin)[2:]}"


NOMS = {
    "Association sportive de Saint-Étienne": "AS Saint-Étienne",
    "Olympique Gymnaste Club de Nice": "OGC Nice",
    "Football Club de Nantes": "FC Nantes",
    "Racing Club de Lens": "RC Lens",
    "Association sportive de Monaco Football Club": "AS Monaco",
    "Racing Club de Strasbourg Alsace": "RC Strasbourg",
    "Football Club Sochaux-Montbéliard": "FC Sochaux",
    "Football Club des Girondins de Bordeaux": "Girondins de Bordeaux",
    "Paris Saint-Germain Football Club": "Paris Saint-Germain",
    "Association de la jeunesse auxerroise": "AJ Auxerre",
    "Football Club de Metz": "FC Metz",
    "Olympique lyonnais": "Olympique lyonnais",
    "Montpellier Hérault Sport Club": "Montpellier HSC",
    "Real Madrid Club de Fútbol": "Real Madrid",
    "FC Barcelone (football)": "FC Barcelone",
    "Associazione Calcio Milan": "AC Milan",
    "FC Internazionale Milano": "Inter Milan",
    "Associazione Sportiva Roma": "AS Rome",
    "Unione Calcio Sampdoria": "Sampdoria",
    "Fotbal Club FCSB": "Steaua Bucarest",
    "Étoile rouge de Belgrade (football)": "Étoile rouge de Belgrade",
    "Valencia Club de Fútbol": "Valence CF",
    "Club Atlético de Madrid": "Atlético de Madrid",
    "Club Bruges KV": "Club Bruges",
    "Hambourg SV": "Hambourg SV",
}


def nom_court(page_):
    if page_ in NOMS:
        return NOMS[page_]
    return page_.replace(" Football Club", "")


def ecrire(nom, rows):
    rows = [dict(r, champion=nom_court(r["champion"]), finaliste=nom_court(r["finaliste"])) for r in rows]
    rows = sorted((r for r in rows if r["annee_fin"] >= DEBUT), key=lambda r: r["annee_fin"])
    with open(OUT / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["saison", "annee_fin", "champion", "finaliste", "page_champion"])
        w.writeheader()
        w.writerows(rows)
    print(f"{nom}: {len(rows)} saisons ({rows[0]['saison']} -> {rows[-1]['saison']})")


# --- Championnats (Ligue 1, Angleterre) : lien 1 = saison, 2 = champion, 3 = vice
def championnat(fichiers):
    out = {}
    for nom in fichiers:
        for row in lignes(nom):
            l = liens_wiki(row)
            if len(l) < 3:
                continue
            m = re.search(r"(\d{4})-(\d{4})$", page(l[0]))
            if not m:
                continue
            fin = int(m.group(2))
            if row[0] == "non attribué":  # 1992/93 : titre retiré à l'OM, non réattribué
                out[fin] = dict(saison=saison(fin), annee_fin=fin, champion="",
                                finaliste=page(l[1]), page_champion="")
                continue
            out[fin] = dict(saison=saison(fin), annee_fin=fin, champion=page(l[1]),
                            finaliste=page(l[2]), page_champion=page(l[1]))
    return out.values()


# --- Liga (en.wikipedia) : lien 1 = saison « YYYY–YY La Liga », lien 2 = champion, lien 3 = vice
def liga():
    out = []
    for row in lignes("liga_champions_1929-2026.csv"):
        l = liens_wiki(row)
        m = re.match(r"(\d{4})(?:–(\d{2,4}))? La Liga", page(l[0])) if l else None
        if not m or not m.group(2):
            continue
        fin = int(m.group(1)) + 1
        champ, vice = CORRECTIONS_LIGA.get(fin, (page(l[1]), page(l[2])))
        out.append(dict(saison=saison(fin), annee_fin=fin, champion=champ, finaliste=vice, page_champion=champ))
    return out


# Lignes décalées par le scraper (cellule du champion perdue) : corrigées d'après les classements Wikipedia
CORRECTIONS_LIGA = {2000: ("Deportivo de La Coruña", "FC Barcelona"), 2021: ("Atlético Madrid", "Real Madrid CF")}


# --- NBA : le score est donné du point de vue de la conférence Ouest, mais l'ordre
# des équipes dans la ligne est mélangé par le scraper -> on repère l'équipe de l'Ouest
# par sa conférence (finalistes depuis 1976).
OUEST = {"Los Angeles Lakers", "Seattle SuperSonics", "Portland Trail Blazers", "Phoenix Suns",
         "Houston Rockets", "Utah Jazz", "San Antonio Spurs", "Dallas Mavericks",
         "Oklahoma City Thunder", "Golden State Warriors", "Denver Nuggets"}


def nba():
    out = []
    for row in lignes("nba_finales_1947-2026.csv"):
        if not re.fullmatch(r"\d{4}", row[0]):
            continue
        fin = int(row[0])
        equipes = [re.sub(r"^\d{4}–\d{2,4} | season$", "", page(c)) for c in liens_wiki(row) if c.endswith("_season")]
        score = next((c for c in row if re.fullmatch(r"\d–\d", c)), None)
        if len(equipes) < 2 or not score:
            print("NBA ignoré", fin, equipes, score)
            continue
        if fin >= DEBUT:
            ouest = [e for e in equipes[:2] if e in OUEST]
            assert len(ouest) == 1, (fin, equipes)
            ouest, est = ouest[0], next(e for e in equipes[:2] if e != ouest[0])
        else:
            ouest, est = equipes[:2]
        gagne_ouest = int(score[0]) > int(score[2])
        champ, fin_ = (ouest, est) if gagne_ouest else (est, ouest)
        out.append(dict(saison=saison(fin), annee_fin=fin, champion=champ, finaliste=fin_, page_champion=champ))
    return out


# --- Ligue des champions : liens de clubs dans l'ordre vainqueur, finaliste
EXCLUS = ("Coupe_des_clubs", "Ligue_des_champions", "Finale_", "commons.wikimedia")


def c1():
    out = []
    for row in lignes("ligue_des_champions_finales_1956-2026.csv"):
        an = next((c for c in row[:3] if re.fullmatch(r"\d{4}", c)), None)
        if not an:
            continue
        clubs = [page(c) for c in liens_wiki(row) if not any(e in c for e in EXCLUS)]
        if len(clubs) < 2:
            print("C1 ignoré", an, clubs)
            continue
        fin = int(an)
        if fin > 2026:  # finale future (lieu déjà désigné)
            continue
        out.append(dict(saison=saison(fin), annee_fin=fin, champion=clubs[0], finaliste=clubs[1], page_champion=clubs[0]))
    return out


if __name__ == "__main__":
    ecrire("ligue1.csv", championnat(["ligue1_champions_1945-2002.csv", "ligue1_champions_2002-2026.csv"]))
    ecrire("angleterre.csv", championnat(["angleterre_champions_1892-1992.csv", "premier_league_champions_1992-2026.csv"]))
    ecrire("nba.csv", nba())
    ecrire("liga.csv", liga())
    ecrire("ligue_des_champions.csv", c1())
