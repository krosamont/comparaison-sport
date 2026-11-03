"""Vidéo animée : tous les clubs d'une compétition sur la carte, saison par saison.

Usage : python scripts/render.py france|angleterre|ligue_des_champions|nba [--apercu N ...]
Entrée : data/video/<ligue>.json (prepare.py, prepare_c1.py, nba.py)
Sortie : videos/<ligue>.mp4 (frames temporaires dans videos/frames_<ligue>/)

Un club peut avoir des « époques » (champ `eres`) : nom, ville et logo qui changent selon la saison
(déménagements et changements de logo en NBA). Les titres restent comptés pour la région où ils ont été gagnés.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from shapely.geometry import MultiPolygon, Point, Polygon  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from regions import decor, regions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
FPS = 30
F_SAISON = 14          # frames par saison
F_FIN = 90             # pause finale
TRANSITION = 0.45      # part de la saison consacrée à la transition
MONTEE_CHAMPION = 26   # pixels de relief en plus pour la région du champion
ZOOM_CHAMPION = 1.6    # le logo du champion est agrandi sur la carte pendant sa saison

# Thème repris de parcours_tirs (templates/interactive.html) : papier, encre, rouge du cadre, Arvo
FONTS = ROOT / "fonts"
F_ANNEE = FontProperties(fname=FONTS / "Arvo-Bold.ttf")
F_TITRE = F_GRAS = F_ANNEE
F_SEMI = FontProperties(fname=FONTS / "Arvo-Regular.ttf")

PAPIER = "#ebe7de"
CADRE_FOND = "#f6f3ec"
ENCRE = "#1d1b19"
ROUGE = "#c2393f"
GRIS = "#6f6a62"
PALE = "#9a948a"
PISTE = "#d9d3c7"
OMBRE = "#cfc9bd"
RAMPE = [np.array(to_rgb(c)) for c in ("#ddd6c8", "#cf6266", "#8e2a2f")]

# Format Instagram Reels (9:16). Coordonnées en pixels depuis le bas. On garde le contenu entre ~y=350 et
# ~y=1790 : le haut et le bas de l'écran sont recouverts par l'interface d'Instagram.
COMMUN = dict(sous_titre="Tous les clubs sur la carte · depuis 1975/76", label_regions="Titres par région",
              label_ancien="ancien club de l'élite", logo=(56, 9.0, 100), carte=(20, 340, 1060, 1000), panneau_regions=True,
              non_attribue="Affaire VA-OM", sources="Données : Wikipedia × engsoccerdata · Frontières : geoBoundaries")
CONFIG = {
    "france": dict(COMMUN, titre="Championnat de France", taille_titre=44, crs=2154, panneau_regions=False),
    "angleterre": dict(COMMUN, titre="Championnat d'Angleterre", taille_titre=38, crs=27700, panneau_regions=False),
    "liga": dict(COMMUN, titre="Championnat d'Espagne", taille_titre=40, crs=25830, panneau_regions=False,
                 sources="Données : Wikipedia × Wikidata · Frontières : geoBoundaries"),
    "ligue_des_champions": dict(
        COMMUN, titre="Ligue des champions", taille_titre=36, crs=3035, carte=(10, 330, 1070, 1005), point=3.4,
        sous_titre="Tous les clubs engagés sur la carte · depuis 1975/76", label_regions="Titres par pays",
        label_ancien="ancien participant", logo=(40, 7.0, 76),
        sources="Données : Wikipedia × Wikidata · Frontières : geoBoundaries"),
    "nba": dict(
        COMMUN, titre="NBA", taille_titre=46, crs=5070, carte=(55, 360, 1045, 1000),
        sous_titre="Toutes les franchises sur la carte · depuis 1975/76", label_regions="Titres par État",
        label_ancien="ancienne ville d'une franchise", logo=(58, 7.5, 96),
        sources="Données : Wikipedia · Logos : SportsLogos.net · Frontières : geoBoundaries"),
}


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def saison_txt(an):
    return f"{an}/{str(an + 1)[2:]}"


def pastille(nom):
    """Logo de secours : initiales du club dans un rond (quand aucune image n'existe)."""
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((4, 4, 156, 156), fill=PISTE, outline=GRIS, width=6)
    mots = [m for m in nom.replace("-", " ").split() if m[0].isalpha() and m.upper() not in ("FC", "CF", "SK", "FK", "AC")]
    initiales = "".join(m[0] for m in mots[:3]).upper() or nom[:2]
    f = ImageFont.truetype(str(FONTS / "Arvo-Bold.ttf"), 60 if len(initiales) < 3 else 48)
    dr.text((80, 82), initiales, font=f, fill=ENCRE, anchor="mm")
    return im


# ----------------------------------------------------------------------------- données
class Donnees:
    def __init__(self, ligue, debut=None):   # debut : première saison prise en compte (titres, clubs vus, tailles)
        self.ligue = ligue
        cfg = self.cfg = CONFIG[ligue]
        self.titre = cfg["titre"]
        d = json.loads((ROOT / "data" / "video" / f"{ligue}.json").read_text())
        self.annees = sorted(int(a) for a in d["saisons"] if debut is None or int(a) >= debut)
        self.clubs = d["clubs"]
        for c in self.clubs.values():  # un club sans époques = une seule époque
            c.setdefault("eres", [dict(de=-9999, a=9999, nom=c["nom"], lat=c["lat"], lon=c["lon"],
                                       region=c["region"], logo=c["logo"])])
        geo = regions(ligue).to_crs(cfg["crs"])
        dec = decor(ligue)

        # projection -> pixels (échelle commune, carte centrée dans son cadre)
        x0, y0, x1, y1 = geo.total_bounds
        cx0, cy0, cx1, cy1 = cfg["carte"]
        k = min((cx1 - cx0) / (x1 - x0), (cy1 - cy0) / (y1 - y0))
        ox = cx0 + ((cx1 - cx0) - (x1 - x0) * k) / 2
        oy = cy0 + ((cy1 - cy0) - (y1 - y0) * k) / 2
        self.px = lambda x, y: (ox + (np.asarray(x) - x0) * k, oy + (np.asarray(y) - y0) * k)

        self.regions = []
        for _, r in geo.iterrows():
            polys = [g for g in getattr(r.geometry, "geoms", [r.geometry]) if isinstance(g, Polygon)]
            polys += [q for g in getattr(r.geometry, "geoms", []) if isinstance(g, MultiPolygon) for q in g.geoms]
            anneaux = [np.column_stack(self.px(*p.exterior.xy)) for p in polys if p.area * k * k > 3]
            # les micro-États (Monaco...) restent dans les calculs même s'ils sont trop petits pour être dessinés
            self.regions.append(dict(nom=r.region, anneaux=anneaux, cy=self.px(0, r.geometry.centroid.y)[1]))
        self.regions.sort(key=lambda r: -r["cy"])  # du nord au sud : ordre de dessin
        self.decor_anneaux = []
        if dec is not None:
            for g in dec.to_crs(cfg["crs"]).geometry.clip_by_rect(x0 - 1e6, y0, x1 + 1e6, y1 + 6 / k):
                for p in (g.geoms if isinstance(g, MultiPolygon) else [g]):
                    if p.area * k * k > 3:
                        self.decor_anneaux.append(np.column_stack(self.px(*p.exterior.xy)))

        # position (pixels) et logo de chaque époque
        eres = [e for c in self.clubs.values() for e in c["eres"]]
        pts = gpd.GeoSeries([Point(e["lon"], e["lat"]) for e in eres], crs=4326).to_crs(cfg["crs"])
        self.logos = {}
        for e, p in zip(eres, pts):
            e["px"] = np.array(self.px(p.x, p.y), dtype=float)
            e["lieu"] = (round(e["lat"], 3), round(e["lon"], 3))
            cle_logo = e["logo"] or f"pastille:{e['nom']}"
            e["cle_logo"] = cle_logo
            if cle_logo not in self.logos:
                fichier = ROOT / e["logo"] if e["logo"] else None   # logo pas (encore) téléchargé : pastille à initiales
                im = Image.open(fichier).convert("RGBA") if fichier and fichier.exists() else pastille(e["nom"])
                im.thumbnail((160, 160), Image.LANCZOS)
                self.logos[cle_logo] = np.asarray(im)

        self._etats(d)

    def ere(self, cle, an):
        eres = self.clubs[cle]["eres"]
        for e in eres:
            if e["de"] <= an <= e["a"]:
                return e
        avant = [e for e in eres if e["de"] <= an]
        return avant[-1] if avant else eres[0]

    def _etats(self, d):
        titres, reg_titres, vus, lieux_vus = {}, {}, set(), {}
        self.etats = []
        pos_prec = {}
        for an in self.annees:
            presents = d["saisons"][str(an)]
            champ = d["champions"][str(an)]
            vus |= set(presents)
            info = {c: self.ere(c, an) for c in vus}
            for c in presents:
                lieux_vus[(c, info[c]["lieu"])] = info[c]
            if champ:
                titres[champ] = titres.get(champ, 0) + 1
                reg = info[champ]["region"]  # le titre reste à la région où il a été gagné
                reg_titres[reg] = reg_titres.get(reg, 0) + 1
            reg_clubs = {}
            for c in presents:
                reg_clubs[info[c]["region"]] = reg_clubs.get(info[c]["region"], 0) + 1
            hauteur = {r["nom"]: 5 + 2.4 * reg_clubs.get(r["nom"], 0) for r in self.regions}
            reg_champ = info[champ]["region"] if champ else None
            if reg_champ:  # la région du champion se soulève pendant sa saison de titre
                hauteur[reg_champ] += MONTEE_CHAMPION
            tailles = {c: self.taille(titres.get(c, 0), c == champ, self.cfg["logo"]) for c in presents}
            pos = self.disposer(presents, tailles, hauteur, pos_prec, info)
            pos_prec = pos
            occupes = {(c, info[c]["lieu"]) for c in presents}
            anciens = {k: e for k, e in lieux_vus.items() if k not in occupes}
            self.etats.append(dict(an=an, presents=presents, champ=champ, titres=dict(titres),
                                   vus=set(vus), reg_titres=dict(reg_titres), hauteur=hauteur,
                                   tailles=tailles, pos=pos, info=info, anciens=anciens, reg_champ=reg_champ,
                                   champ_logo=info[champ]["cle_logo"] if champ else None))
        self.max_titres = max(titres.values())
        self.max_reg = max(reg_titres.values())

    @staticmethod
    def taille(n, champion, regle):
        base, coef, maxi = regle
        taille = min(base + coef * math.sqrt(n), maxi)
        return taille * ZOOM_CHAMPION if champion else taille

    def disposer(self, presents, tailles, hauteur, prec, info):
        """Anti-chevauchement des logos : répulsion + rappel vers le stade (départ = saison précédente)."""
        cles = list(presents)
        ancres = np.array([info[c]["px"] + (0, hauteur[info[c]["region"]]) for c in cles])
        # un club qui a déménagé repart de sa nouvelle ville (pas de sa position précédente)
        p = np.array([prec[c] if c in prec and np.linalg.norm(prec[c] - a) < 60 else a
                      for c, a in zip(cles, ancres)], dtype=float)
        r = np.array([tailles[c] / 2 + 1.5 for c in cles])
        jitter = np.random.default_rng(0)
        for _ in range(900):
            delta = p[:, None, :] - p[None, :, :]
            dist = np.linalg.norm(delta, axis=2) + np.eye(len(cles))
            mini = r[:, None] + r[None, :]
            chevauche = np.clip(mini - dist, 0, None) * (1 - np.eye(len(cles)))
            same = dist < 1e-3
            delta[same] = jitter.normal(size=(same.sum(), 2))
            dist = np.linalg.norm(delta, axis=2) + np.eye(len(cles))
            pousse = (delta / dist[..., None] * chevauche[..., None] * 0.6).sum(axis=1)
            p += pousse + (ancres - p) * 0.015
        return {c: p[i] for i, c in enumerate(cles)}


# ----------------------------------------------------------------------------- dessin
def couleur_region(n, max_reg):
    t = (n / max_reg) ** 0.55 if n else 0
    if t < 0.5:
        return RAMPE[0] + (RAMPE[1] - RAMPE[0]) * t * 2
    return RAMPE[1] + (RAMPE[2] - RAMPE[1]) * (t - 0.5) * 2


def logo(ax, d, cle_logo, x, y, s, alpha=1.0, z=10, ombre=True):
    if s < 1 or alpha <= 0.01:
        return
    im = d.logos[cle_logo]
    h, w = im.shape[:2]
    sw, sh = (s, s * h / w) if w >= h else (s * w / h, s)
    if ombre:
        ax.add_patch(Circle((x + 1.5, y - 2.5), s * 0.5, color="black", alpha=0.10 * alpha, lw=0, zorder=z - 0.1))
    ax.imshow(im, extent=(x - sw / 2, x + sw / 2, y - sh / 2, y + sh / 2), zorder=z, alpha=alpha,
              interpolation="antialiased")


def texte(ax, x, y, s, taille, font, couleur=ENCRE, ha="left", va="baseline", **kw):
    kw.setdefault("zorder", 8)
    return ax.text(x, y, s, fontproperties=font, fontsize=taille, color=couleur, ha=ha, va=va, **kw)


def frame(d, i, chemin):
    n = len(d.etats)
    k = min(i // F_SAISON, n - 1)
    u = (i - k * F_SAISON) / F_SAISON if i < n * F_SAISON else 1.0
    e = ease(u / TRANSITION)
    cur = d.etats[k]
    prev = d.etats[k - 1] if k > 0 else dict(presents=[], titres={}, reg_titres={}, vus=set(), champ=None,
                                              hauteur={r["nom"]: 5 for r in d.regions}, tailles={}, pos={},
                                              info={}, anciens={})
    lerp = lambda a, b: a + (b - a) * e  # noqa: E731

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor(PAPIER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # --- carte en relief : couleur = titres, hauteur = clubs présents
    if d.decor_anneaux:
        ax.add_collection(PolyCollection(d.decor_anneaux, facecolor=PISTE, edgecolor=PAPIER, lw=0.8, zorder=1))
    tous = [a for r in d.regions for a in r["anneaux"]]
    ax.add_collection(PolyCollection([a + (3, -7) for a in tous], facecolor="black", alpha=0.07, lw=0, zorder=1.5))
    haut = {}
    for r in d.regions:
        h = lerp(prev["hauteur"][r["nom"]], cur["hauteur"][r["nom"]])
        haut[r["nom"]] = h
        c = couleur_region(lerp(prev["reg_titres"].get(r["nom"], 0), cur["reg_titres"].get(r["nom"], 0)), d.max_reg)
        if not r["anneaux"]:
            continue
        murs = [a + (0, dy) for dy in np.arange(0, h, 1.2) for a in r["anneaux"]]
        ax.add_collection(PolyCollection(murs, facecolor=c * 0.72, edgecolor="none", zorder=2))
        ax.add_collection(PolyCollection([a + (0, h) for a in r["anneaux"]], facecolor=c,
                                         edgecolor=CADRE_FOND, lw=0.9, zorder=2))
        if r["nom"] == cur.get("reg_champ"):  # contour rouge sur la région du champion
            ax.add_collection(PolyCollection([a + (0, h) for a in r["anneaux"]], facecolor="none",
                                             edgecolor=ROUGE, lw=2.2, alpha=e, zorder=2.1))

    # anciens clubs / anciennes villes : point (fondu à l'apparition et à la disparition)
    for cle_l in set(cur["anciens"]) | set(prev["anciens"]):
        a = (1.0 if cle_l in prev["anciens"] else 0.0) * (1 - e) + (1.0 if cle_l in cur["anciens"] else 0.0) * e
        if a <= 0.01:
            continue
        er = (cur["anciens"].get(cle_l) or prev["anciens"][cle_l])
        x, y = er["px"] + (0, haut[er["region"]])
        rp = d.cfg.get("point", 4.2)
        ax.add_patch(Circle((x, y), rp, facecolor=CADRE_FOND, edgecolor=ENCRE, lw=rp / 3, alpha=a, zorder=3))

    # clubs présents : logos (entrées / sorties en fondu, déménagements en glissé, changement de logo en fondu)
    dessin = []
    for cle in set(cur["presents"]) | set(prev["presents"]):
        dans_p, dans_c = cle in prev["pos"], cle in cur["pos"]
        if dans_p and dans_c:
            p = prev["pos"][cle] * (1 - e) + cur["pos"][cle] * e
            s = lerp(prev["tailles"][cle], cur["tailles"][cle])
            lp, lc = prev["info"][cle]["cle_logo"], cur["info"][cle]["cle_logo"]
            couches = [(lc, 1.0)] if lp == lc else [(lp, 1 - e), (lc, e)]
        elif dans_c:
            p, s = cur["pos"][cle], cur["tailles"][cle] * e
            couches = [(cur["info"][cle]["cle_logo"], e)]
        else:
            p, s = prev["pos"][cle], prev["tailles"][cle] * (1 - e)
            couches = [(prev["info"][cle]["cle_logo"], 1 - e)]
        dessin.append((p[1], cle, p, s, couches))
    for _, cle, p, s, couches in sorted(dessin, key=lambda t: -t[0]):
        z = 6 if cle == cur["champ"] else 5
        if cle == cur["champ"]:
            ax.add_patch(Circle(p, s * 0.62, facecolor="none", edgecolor=ROUGE, lw=2.2, alpha=e, zorder=z - 0.05))
        for j, (cl, a) in enumerate(couches):
            logo(ax, d, cl, p[0], p[1], s, a, z=z + j * 0.01, ombre=j == 0)

    # --- en-tête
    tt = d.cfg["taille_titre"]
    texte(ax, 62, 1768, d.titre, tt, F_TITRE, couleur=OMBRE, zorder=4)
    texte(ax, 60, 1770, d.titre, tt, F_TITRE, zorder=5)
    texte(ax, 60, 1728, d.cfg["sous_titre"], 17, F_SEMI, couleur=GRIS)
    an = saison_txt(cur["an"])
    if d.cfg["panneau_regions"]:  # saison dans l'en-tête (la droite du champion est prise par les régions)
        texte(ax, 1024, 1726, an, 66, F_ANNEE, couleur=OMBRE, ha="right", zorder=4)
        texte(ax, 1020, 1730, an, 66, F_ANNEE, couleur=ROUGE, ha="right", zorder=5)
    else:  # saison en grand dans l'espace libre à droite du champion
        texte(ax, 868, 1176, an, 68, F_ANNEE, couleur=OMBRE, ha="center", zorder=4)
        texte(ax, 864, 1180, an, 68, F_ANNEE, couleur=ROUGE, ha="center", zorder=5)

    nom_de = lambda et, c: et["info"][c]["nom"] if c in et["info"] else d.clubs[c]["nom"]  # noqa: E731
    logo_de = lambda et, c: et["info"][c]["cle_logo"] if c in et["info"] else None  # noqa: E731

    # --- frise des champions : 2 lignes de grandes icônes, puis la barre de progression
    gx0, gx1, taille_ic = 82, 998, 64
    par_ligne = math.ceil(n / 4)
    pas = (gx1 - gx0) / (par_ligne - 1)
    for j in range(k + 1):
        ligne, col = divmod(j, par_ligne)
        x, y = gx0 + col * pas, 1652 - ligne * 68
        cl = d.etats[j]["champ_logo"]
        a = e if j == k else 1
        if cl:
            logo(ax, d, cl, x, y, taille_ic * (1 + 0.25 * (1 - e)) if j == k else taille_ic, a, z=8, ombre=False)
        else:
            texte(ax, x, y - 12, "–", 28, F_TITRE, couleur=GRIS, ha="center", alpha=a)
    BARRE = 1400
    ax.add_patch(FancyBboxPatch((gx0 - 15, BARRE), gx1 - gx0 + 30, 8, boxstyle="round,pad=0,rounding_size=4",
                                color=PISTE, lw=0, zorder=7))
    prog = (k - 1 + e) / (n - 1) if k > 0 else 0
    if i >= n * F_SAISON:
        prog = 1
    ax.add_patch(FancyBboxPatch((gx0 - 15, BARRE), max(8, (gx1 - gx0 + 30) * prog), 8,
                                boxstyle="round,pad=0,rounding_size=4", color=ROUGE, lw=0, zorder=7))
    texte(ax, gx0 - 15, BARRE - 24, saison_txt(d.annees[0]), 12, F_TITRE)
    texte(ax, gx1 + 15, BARRE - 24, saison_txt(d.annees[-1]), 12, F_TITRE, ha="right")

    # --- champion de la saison, en grand au centre, dans un cadre rouge (comme la photo de parcours_tirs)
    cx, cy, cote = W / 2, 1208, 220
    pop = 1 + 0.15 * math.sin(math.pi * min(u / TRANSITION, 1)) if u < TRANSITION else 1
    ax.add_patch(Rectangle((cx - cote / 2 + 8, cy - cote / 2 - 8), cote, cote, facecolor=OMBRE, lw=0, zorder=7))
    ax.add_patch(Rectangle((cx - cote / 2, cy - cote / 2), cote, cote, facecolor=CADRE_FOND, edgecolor=ROUGE,
                           lw=4, zorder=7.5))
    if cur["champ"]:
        logo(ax, d, cur["champ_logo"], cx, cy, 165 * pop, 1, z=8, ombre=False)
        texte(ax, cx, cy - cote / 2 - 34, "Champion", 19, F_TITRE, ha="center")
        texte(ax, cx, cy - cote / 2 - 58, nom_de(cur, cur["champ"]), 15, F_SEMI, couleur=GRIS, ha="center")
    else:
        texte(ax, cx, cy + 8, "Titre non", 22, F_TITRE, couleur=ROUGE, ha="center")
        texte(ax, cx, cy - 24, "attribué", 22, F_TITRE, couleur=ROUGE, ha="center")
        texte(ax, cx, cy - cote / 2 - 34, d.cfg["non_attribue"], 15, F_SEMI, couleur=GRIS, ha="center")

    # --- classement des titres (à gauche du champion, rangs animés)
    x0, y0 = 40, 1322
    texte(ax, x0, y0, "Titres", 19, F_TITRE)
    rang = lambda et: sorted(et["titres"], key=lambda c: (-et["titres"][c], nom_de(et, c)))[:6]  # noqa: E731
    rc, rp = rang(cur), rang(prev)
    for cle in set(rc) | set(rp):
        yc = rc.index(cle) if cle in rc else 6.5
        yp = rp.index(cle) if cle in rp else 6.5
        r = lerp(yp, yc)
        a = 1 - max(0, min(1, r - 5))
        if a <= 0:
            continue
        y = y0 - 50 - r * 50
        nt = lerp(prev["titres"].get(cle, 0), cur["titres"].get(cle, 0))
        logo(ax, d, logo_de(cur, cle) or logo_de(prev, cle), x0 + 23, y - 3, 46, a, z=8, ombre=False)
        texte(ax, x0 + 56, y + 4, nom_de(cur, cle), 14, F_GRAS, alpha=a)
        ax.add_patch(Rectangle((x0 + 56, y - 14), 248, 8, color=PISTE, lw=0, alpha=a, zorder=7))
        ax.add_patch(Rectangle((x0 + 56, y - 14), 248 * nt / d.max_titres, 8, color=ROUGE, lw=0, alpha=a, zorder=7))
        texte(ax, x0 + 345, y - 15, str(cur["titres"].get(cle, 0)), 13, F_TITRE, alpha=a, ha="right")

    # --- titres par région (à droite du champion)
    x1, y1 = 680, 1322
    if not d.cfg["panneau_regions"]:  # France / Angleterre : seulement la légende, centrée à droite
        y1 += 100
    else:
        texte(ax, x1, y1, d.cfg["label_regions"], 19, F_TITRE)
    regs = sorted(cur["reg_titres"], key=lambda r: -cur["reg_titres"][r])[:5] if d.cfg["panneau_regions"] else []
    for j, reg in enumerate(regs):
        y = y1 - 40 - j * 33
        nreg = lerp(prev["reg_titres"].get(reg, 0), cur["reg_titres"][reg])
        ax.add_patch(Rectangle((x1, y - 5), 19, 19, color=couleur_region(nreg, d.max_reg), lw=0, zorder=7))
        texte(ax, x1 + 28, y, reg, 12.5, F_SEMI)
        texte(ax, 1040, y, str(cur["reg_titres"][reg]), 13, F_TITRE, ha="right")
    # légende des points, en bas juste au-dessus des sources
    largeur = len(d.cfg["label_ancien"]) * 7.2
    ax.add_patch(Circle((W / 2 - largeur / 2 - 12, 349), 5.5, facecolor=CADRE_FOND, edgecolor=ENCRE, lw=1.6, zorder=7))
    texte(ax, W / 2 - largeur / 2, 343, d.cfg["label_ancien"], 13, F_SEMI)

    texte(ax, W / 2, 305, d.cfg["sources"], 12, F_SEMI, couleur=GRIS, ha="center")

    fig.savefig(chemin, dpi=100)
    plt.close(fig)


# ----------------------------------------------------------------------------- orchestration
_D = None


def _init(ligue):
    global _D
    _D = Donnees(ligue)


def _job(args):
    i, chemin = args
    frame(_D, i, chemin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ligue", choices=list(CONFIG))
    ap.add_argument("--apercu", type=int, nargs="*", help="numéros de frames à rendre en PNG seulement")
    a = ap.parse_args()
    out = ROOT / "videos"
    out.mkdir(exist_ok=True)
    if a.apercu is not None:
        _init(a.ligue)
        for i in a.apercu:
            frame(_D, i, out / f"apercu_{a.ligue}_{i}.png")
            print(out / f"apercu_{a.ligue}_{i}.png")
        return
    frames = out / f"frames_{a.ligue}"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    d = Donnees(a.ligue)
    total = len(d.etats) * F_SAISON + F_FIN
    jobs = [(i, frames / f"{i:05d}.png") for i in range(total)]
    with Pool(7, initializer=_init, initargs=(a.ligue,)) as pool:
        for j, _ in enumerate(pool.imap_unordered(_job, jobs, chunksize=8)):
            if j % 100 == 0:
                print(f"{j}/{total}", flush=True)
    mp4 = out / f"{a.ligue}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
                   check=True)
    shutil.rmtree(frames)
    print(mp4)


if __name__ == "__main__":
    main()
