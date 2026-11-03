"""Clubs de la Ligue des champions par saison, depuis Wikipedia (en).

- jusqu'en 1993/94 : tous les clubs du premier tour (pas de phase de groupes en début de compétition)
- 1994/95 -> 2023/24 : tous les clubs de la phase de groupes
- depuis 2024/25 : tous les clubs de la phase de ligue

Sortie : data/c1/participants.json  {annee_debut: [{"page": titre_article, "nom": texte}]}
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from wiki import get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://en.wikipedia.org/w/api.php"


def html(titre):
    r = json.loads(get(API, {"action": "parse", "page": titre, "prop": "text", "format": "json", "redirects": 1}))
    return BeautifulSoup(r["parse"]["text"]["*"], "lxml") if "parse" in r else None


def section(soup, noms):
    """Éléments situés entre le titre h2 dont le texte commence par un des noms et le h2 suivant."""
    out, dedans = [], False
    for el in soup.find_all(True, recursive=True):
        if el.name == "div" and "mw-heading2" in (el.get("class") or []):
            dedans = any(el.get_text(strip=True).startswith(n) for n in noms)
            continue
        if dedans and el.name == "table":
            out.append(el)
    return out


def equipe(cell):
    for a in cell.find_all("a", href=True):
        if a.find_parent(class_="flagicon") or not a["href"].startswith("/wiki/") or ":" in a["href"]:
            continue
        return dict(page=unquote(a["href"][6:].split("#")[0]).replace("_", " "), nom=a.get_text(strip=True))
    return None


def premier_tour(soup):
    clubs = []
    for tb in section(soup, ["First round"]):
        if "Team 1" not in tb.select("tr")[0].get_text():
            continue
        for tr in tb.select("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 3:
                for c in (cells[0], cells[2]):
                    e = equipe(c)
                    if e:
                        clubs.append(e)
    return clubs


def groupes(soup, noms=None):
    tables = section(soup, noms) if noms else soup.select("table.wikitable")
    clubs = []
    for tb in tables:
        tete = tb.select("tr")[0].get_text(" ")
        if "Pld" not in tete or "Pts" not in tete:
            continue
        for tr in tb.select("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) > 3:
                e = equipe(cells[1]) or equipe(cells[0])
                if e:
                    clubs.append(e)
    return clubs


def saison(an):
    s = f"{an}–{an + 1 if an == 1999 else str(an + 1)[2:]}"  # Wikipedia écrit 1999–2000
    if an <= 1990:
        return premier_tour(html(f"{s} European Cup"))
    if an <= 1993:
        return premier_tour(html(f"{s} European Cup") or html(f"{s} UEFA Champions League"))
    if an >= 2024:
        return groupes(html(f"{s} UEFA Champions League league phase"), ["League phase table"])
    if an in (1999, 2000, 2001, 2002):  # deux phases de groupes : on prend la première
        page = html(f"{s} UEFA Champions League first group stage")
        if page is not None:
            return groupes(page, ["Groups", "Group"])
    page = html(f"{s} UEFA Champions League group stage")
    if page is not None:
        return groupes(page, ["Groups", "Group"])
    return groupes(html(f"{s} UEFA Champions League"), ["Group stage"])


def canoniques(pages):
    """Résout les redirections (titres d'articles différents pour un même club)."""
    out = {}
    pages = sorted(set(pages))
    for i in range(0, len(pages), 50):
        lot = pages[i:i + 50]
        r = json.loads(get(API, {"action": "query", "titles": "|".join(lot), "redirects": 1, "format": "json"}))
        q = r["query"]
        alias = {x["from"]: x["to"] for x in q.get("normalized", []) + q.get("redirects", [])}
        for p in lot:
            t = p
            while t in alias:
                t = alias[t]
            out[p] = t
    return out


def main():
    attendu = lambda an: 32 if an <= 1993 else 16 if an <= 1996 else 24 if an <= 1998 else 32 if an <= 2023 else 36  # noqa: E731
    brut = {}
    for an in range(1975, 2026):
        clubs = saison(an)
        uniques = {c["page"]: c for c in clubs}
        brut[an] = list(uniques.values())
        flag = "" if len(uniques) == attendu(an) else f"  <-- attendu {attendu(an)}"
        print(an, len(uniques), flag)
    canon = canoniques([c["page"] for cl in brut.values() for c in cl])
    out = {an: [dict(c, page=canon[c["page"]]) for c in cl] for an, cl in brut.items()}
    dest = ROOT / "data" / "c1" / "participants.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    tous = {c["page"] for cl in out.values() for c in cl}
    print(len(tous), "clubs ->", dest)


if __name__ == "__main__":
    main()
