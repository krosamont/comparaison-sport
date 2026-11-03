"""Les cinq compétitions côte à côte, saison par saison (GIF et MP4) : France, Angleterre, Espagne, Ligue des champions, NBA.

    python scripts/render_comparaison.py --apercu 50          # une image (saison 2025/26) dans videos/
    python scripts/render_comparaison.py                      # videos/comparaison.mp4 et videos/gif/comparaison.gif
    python scripts/render_comparaison.py --reel [--apercu 50]  # videos/comparaison_reel.mp4 (1080 × 1920, Instagram Reels)
    python scripts/render_comparaison.py --annees 10 [--reel]  # les 10 dernières saisons : titres comptés depuis 2016/17

Chaque case reprend la page « Les championnats sur la carte » : la carte (couleur = titres, relief = clubs présents,
logos de tous les clubs), le champion de la saison, le classement des titres (et les titres par pays / par État pour la
Ligue des champions et la NBA). Les états des saisons viennent du moteur des vidéos (render.Donnees).
"""
import argparse
import math
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import render as R  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080
FPS = 12
F_SAISON = 6           # images par saison (0,5 s) ; plus pour les périodes courtes (voir periode())
ANNEES = 50            # période : les N dernières saisons (50 = depuis 1975/76)


def periode(n):
    """Les N dernières saisons : première saison et rythme (les périodes courtes défilent moins vite)."""
    global ANNEES, F_SAISON
    ANNEES = n
    F_SAISON = {5: 30, 10: 15, 25: 9}.get(n, 6)
    return 2025 - n + 1 if n < 50 else None   # 50 = toute la période (51 saisons depuis 1975/76)
F_FIN = 36             # pause sur 2025/26
TRANSITION = 0.6
LEVEE = 26             # px de relief en plus pour la région du champion (en plus de celui du moteur)
ZOOM = 1.4             # le logo du champion encore agrandi (× celui du moteur)
LIGUES = ['france', 'angleterre', 'liga', 'ligue_des_champions', 'nba']
NOMS = {'france': 'Championnat de France', 'angleterre': "Championnat d'Angleterre", 'liga': "Championnat d'Espagne",
        'ligue_des_champions': 'Ligue des champions', 'nba': 'NBA'}
# cases (x, y, largeur, hauteur) en pixels depuis le bas ; la 6e case porte le titre et la saison
MARGE, GOUTTIERE = 28, 18
CW = (W - 2 * MARGE - 2 * GOUTTIERE) / 3
CH = (H - 2 * MARGE - GOUTTIERE) / 2
# en haut : France, le titre (saison, légende), Espagne ; en bas : Ligue des champions, NBA, Angleterre
POSITIONS = {'france': (0, 0), 'liga': (0, 2), 'ligue_des_champions': (1, 0), 'nba': (1, 1), 'angleterre': (1, 2)}
CASES = {l: (MARGE + c * (CW + GOUTTIERE), MARGE + (1 - r) * (CH + GOUTTIERE), CW, CH) for l, (r, c) in POSITIONS.items()}
CASE_TITRE = (MARGE + (CW + GOUTTIERE), MARGE + CH + GOUTTIERE, CW, CH)
DEBUT = None          # première saison (None = 1975/76)
COL_DROITE = 196       # colonne du champion et des titres, à droite de chaque case
PARAMS = {l: dict(col=COL_DROITE, cote=92, n=5, nom=15, petit=1.0) for l in LIGUES}   # par case : colonne, cadre, lignes


def format_reel():
    """1080 × 1920 pour Instagram Reels : le contenu reste entre y = 380 et y = 1670 (haut et bas recouverts par
    l'interface d'Instagram). Bandeau titre en haut, France | Espagne, Angleterre | Ligue des champions, NBA en large."""
    global W, H, CASES, CASE_TITRE, PARAMS
    W, H = 1080, 1920
    m, g = 22, 14
    bas, haut, bande = 572, 1862, 262      # tout le contenu remonté de 10 % de la hauteur (192 px)
    hc = (haut - bande - g - bas - 2 * g) / 3
    wc = (W - 2 * m - g) / 2
    y3, y2, y1 = bas, bas + hc + g, bas + 2 * (hc + g)
    CASES = {'france': (m, y1, wc, hc), 'liga': (m + wc + g, y1, wc, hc), 'angleterre': (m, y2, wc, hc),
             'ligue_des_champions': (m + wc + g, y2, wc, hc), 'nba': (m, y3, W - 2 * m, hc)}
    CASE_TITRE = (m, haut - bande, W - 2 * m, bande)
    PARAMS = {l: dict(col=196, cote=78, n=3, nom=17, petit=1.18) for l in LIGUES}
    PARAMS['nba'] = dict(col=236, cote=70, n=4, nom=17, petit=1.22)


class Case:
    """Une compétition : ses saisons (moteur des vidéos) ramenées dans la zone de carte de sa case."""

    def __init__(self, ligue):
        self.d = R.Donnees(ligue, debut=DEBUT)
        x, y, w, h = CASES[ligue]
        # cadrage sur les vrais contours (régions + logos de toutes les saisons), pas sur le cadre du format Reels
        pts = [a for r in self.d.regions for a in r['anneaux']]
        pts += [np.array(list(et['pos'].values())) for et in self.d.etats if et['pos']]
        allp = np.vstack(pts)
        cx0, cy0 = allp.min(axis=0) - 12
        cx1, cy1 = allp.max(axis=0) + 26
        zx0, zy0, zx1, zy1 = x + 6, y + 8, x + w - PARAMS[ligue]['col'] - 4, y + h - 40   # zone de la carte dans la case
        k = min((zx1 - zx0) / (cx1 - cx0), (zy1 - zy0) / (cy1 - cy0))
        ox = zx0 + ((zx1 - zx0) - (cx1 - cx0) * k) / 2
        oy = zy0 + ((zy1 - zy0) - (cy1 - cy0) * k) / 2
        self.k = k
        self.tf = lambda p: np.column_stack([ox + (p[:, 0] - cx0) * k, oy + (p[:, 1] - cy0) * k])
        self.pt = lambda q: (ox + (q[0] - cx0) * k, oy + (q[1] - cy0) * k)
        self.regions = [dict(nom=r['nom'], anneaux=[self.tf(a) for a in r['anneaux']]) for r in self.d.regions]


def dessiner(ax, case, ligue, k, e, u):
    d = case.d
    cur = d.etats[k]
    prev = d.etats[k - 1] if k > 0 else cur
    lerp = lambda a, b: a + (b - a) * e  # noqa: E731
    x, y, w, h = CASES[ligue]
    sc = case.k * 1.9   # relief et logos : un peu plus grands que la simple réduction de la carte
    # levée supplémentaire de la région du champion (fondu entre la saison précédente et celle-ci)
    levee = lambda reg: LEVEE * ((e if reg == cur.get('reg_champ') else 0) + ((1 - e) if k and reg == prev.get('reg_champ') else 0))  # noqa: E731

    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=4", facecolor=R.CADRE_FOND,
                                edgecolor=R.ENCRE, lw=1.5, zorder=0.5))
    P = PARAMS[ligue]
    R.texte(ax, x + 12, y + h - 28, NOMS[ligue], P['nom'], R.F_TITRE)

    # carte en relief
    for r in case.regions:
        if not r['anneaux']:
            continue
        hh = lerp(prev['hauteur'][r['nom']], cur['hauteur'][r['nom']]) * sc * 0.55 + levee(r['nom'])
        c = R.couleur_region(lerp(prev['reg_titres'].get(r['nom'], 0), cur['reg_titres'].get(r['nom'], 0)), d.max_reg)
        murs = [a + (0, dy) for dy in np.arange(0, hh, 1.0) for a in r['anneaux']]
        ax.add_collection(PolyCollection(murs, facecolor=c * 0.72, edgecolor='none', zorder=2))
        ax.add_collection(PolyCollection([a + (0, hh) for a in r['anneaux']], facecolor=c, edgecolor=R.CADRE_FOND,
                                         lw=0.5, zorder=2))
        if r['nom'] == cur.get('reg_champ'):
            ax.add_collection(PolyCollection([a + (0, hh) for a in r['anneaux']], facecolor='none', edgecolor=R.ROUGE,
                                             lw=1.6, alpha=e, zorder=2.1))
    # anciens clubs
    for cle, er in cur['anciens'].items():
        px, py = case.pt(er['px'])
        ax.add_patch(Circle((px, py + cur['hauteur'][er['region']] * sc * 0.55 + levee(er['region'])), 1.8, facecolor=R.CADRE_FOND,
                            edgecolor=R.ENCRE, lw=0.7, zorder=3))
    # logos des clubs présents (le champion devant, cerclé)
    dessin = []
    for c in set(cur['presents']) | set(prev['presents']):
        dans_p, dans_c = c in prev['pos'], c in cur['pos']
        if dans_p and dans_c:
            p = prev['pos'][c] * (1 - e) + cur['pos'][c] * e
            s, a, cl = lerp(prev['tailles'][c], cur['tailles'][c]), 1, cur['info'][c]['cle_logo']
        elif dans_c:
            p, s, a, cl = cur['pos'][c], cur['tailles'][c] * e, e, cur['info'][c]['cle_logo']
        else:
            p, s, a, cl = prev['pos'][c], prev['tailles'][c] * (1 - e), 1 - e, prev['info'][c]['cle_logo']
        px, py = case.pt(p)
        reg = (cur['info'].get(c) or prev['info'][c])['region']
        py += levee(reg)
        zoom = 1 + (ZOOM - 1) * (e if c == cur['champ'] else 0) + (ZOOM - 1) * ((1 - e) if k and c == prev['champ'] else 0)
        dessin.append((c == cur['champ'], -py, px, py, s * case.k * 1.25 * zoom, a, cl, c))
    for champ, _, px, py, s, a, cl, c in sorted(dessin):
        if champ:
            ax.add_patch(Circle((px, py), s * 0.62, facecolor='none', edgecolor=R.ROUGE, lw=1.8, alpha=e, zorder=5.9))
        R.logo(ax, d, cl, px, py, s, a, z=6 if champ else 5, ombre=False)

    # colonne de droite : champion puis titres
    cx = x + w - P['col'] / 2 - 8
    cote = P['cote']
    cy = y + h - 48 - cote / 2   # le cadre remonte : il ne touche plus le nom du champion
    y_nom = cy - cote / 2 - 8 - 15 * P['petit']
    ax.add_patch(Rectangle((cx - cote / 2 + 4, cy - cote / 2 - 4), cote, cote, facecolor=R.OMBRE, lw=0, zorder=7))
    ax.add_patch(Rectangle((cx - cote / 2, cy - cote / 2), cote, cote, facecolor=R.CADRE_FOND, edgecolor=R.ROUGE, lw=2.5, zorder=7.5))
    if cur['champ']:
        R.logo(ax, d, cur['champ_logo'], cx, cy, cote * 0.76, 1, z=8, ombre=False)
        R.texte(ax, cx, y_nom, cur['info'][cur['champ']]['nom'], 10.5 * P['petit'], R.F_GRAS, ha='center')
    else:
        R.texte(ax, cx, cy + 4, 'Titre non', 10.5, R.F_TITRE, couleur=R.ROUGE, ha='center')
        R.texte(ax, cx, cy - 12, 'attribué', 10.5, R.F_TITRE, couleur=R.ROUGE, ha='center')
        R.texte(ax, cx, y_nom, 'Affaire VA-OM', 10 * P['petit'], R.F_SEMI, couleur=R.GRIS, ha='center')
    x0, y0 = x + w - P['col'], y_nom - 26 * P['petit']
    R.texte(ax, x0, y0, 'Titres', 11.5 * P['petit'], R.F_TITRE)
    rang = sorted(cur['titres'], key=lambda c: (-cur['titres'][c], cur['info'][c]['nom']))
    n_lignes = P['n']
    barre = P['col'] - 56
    for j, c in enumerate(rang[:n_lignes]):
        yy = y0 - 24 * P['petit'] - j * 25 * P['petit']
        R.logo(ax, d, cur['info'][c]['cle_logo'], x0 + 9, yy + 2, 17 * P['petit'], 1, z=8, ombre=False)
        R.texte(ax, x0 + 24, yy + 3, cur['info'][c]['nom'], 8.5 * P['petit'], R.F_GRAS)
        ax.add_patch(Rectangle((x0 + 22, yy - 6), barre, 4, color=R.PISTE, lw=0, zorder=7))
        ax.add_patch(Rectangle((x0 + 22, yy - 6), barre * cur['titres'][c] / d.max_titres, 4, color=R.ROUGE, lw=0, zorder=7))
        R.texte(ax, x + w - 12, yy - 4, str(cur['titres'][c]), 9.5 * P['petit'], R.F_TITRE, ha='right')


def case_titre(ax, an, i_total):
    x, y, w, h = CASE_TITRE
    R.texte(ax, x + 4, y + h - 52, f'{ANNEES} ans de champions', 34, R.F_TITRE, couleur=R.OMBRE, zorder=4)
    R.texte(ax, x + 2, y + h - 50, f'{ANNEES} ans de champions', 34, R.F_TITRE, zorder=5)
    R.texte(ax, x + 2, y + h - 84, 'Cinq compétitions sur la carte, saison par saison', 14, R.F_SEMI, couleur=R.GRIS)
    s = R.saison_txt(an)
    R.texte(ax, x + 6, y + h - 236, s, 92, R.F_ANNEE, couleur=R.OMBRE, zorder=4)
    R.texte(ax, x + 2, y + h - 232, s, 92, R.F_ANNEE, couleur=R.ROUGE, zorder=5)
    # progression
    ax.add_patch(FancyBboxPatch((x + 4, y + h - 268), w - 8, 7, boxstyle="round,pad=0,rounding_size=3.5", color=R.PISTE, lw=0, zorder=7))
    ax.add_patch(FancyBboxPatch((x + 4, y + h - 268), max(7, (w - 8) * i_total), 7, boxstyle="round,pad=0,rounding_size=3.5",
                                color=R.ROUGE, lw=0, zorder=7))
    R.texte(ax, x + 4, y + h - 290, R.saison_txt(DEBUT or 1975), 10, R.F_TITRE)
    R.texte(ax, x + w - 4, y + h - 290, '2025/26', 10, R.F_TITRE, ha='right')
    # légende
    ly = y + 150
    ax.add_patch(Rectangle((x + 4, ly - 4), 16, 16, color=R.RAMPE[2], lw=0, zorder=7))
    R.texte(ax, x + 28, ly, 'couleur d\'une région = ses titres', 12, R.F_SEMI)
    ax.add_patch(Rectangle((x + 5, ly - 33), 14, 10, color=R.RAMPE[1] * 0.72, lw=0, zorder=7))   # bloc en relief
    ax.add_patch(Rectangle((x + 5, ly - 27), 14, 10, color=R.RAMPE[1], lw=0, zorder=7.1))
    R.texte(ax, x + 28, ly - 28, 'relief = nombre de clubs engagés', 12, R.F_SEMI)
    ax.add_patch(Circle((x + 12, ly - 50), 9, facecolor='none', edgecolor=R.ROUGE, lw=2, zorder=7))
    R.texte(ax, x + 28, ly - 56, 'le champion de la saison', 12, R.F_SEMI)
    ax.add_patch(Circle((x + 12, ly - 78), 3.5, facecolor=R.CADRE_FOND, edgecolor=R.ENCRE, lw=1.2, zorder=7))
    R.texte(ax, x + 28, ly - 84, 'ancien club de la compétition', 12, R.F_SEMI)
    R.texte(ax, x + 4, y + 22, 'Données : Wikipedia · engsoccerdata · Wikidata · SportsLogos.net', 9.5, R.F_SEMI, couleur=R.GRIS)
    R.texte(ax, x + 4, y + 6, 'Frontières : geoBoundaries · data-workers.com', 9.5, R.F_SEMI, couleur=R.GRIS)


def bandeau_reel(ax, an, i_total):
    x, y, w, h = CASE_TITRE
    R.texte(ax, x + 3, y + h - 50, f'{ANNEES} ans de champions', 38, R.F_TITRE, couleur=R.OMBRE, zorder=4)
    R.texte(ax, x + 1, y + h - 48, f'{ANNEES} ans de champions', 38, R.F_TITRE, zorder=5)
    R.texte(ax, x + 1, y + h - 84, 'Cinq compétitions sur la carte, saison par saison', 16, R.F_SEMI, couleur=R.GRIS)
    s = R.saison_txt(an)
    R.texte(ax, x + w + 3, y + h - 186, s, 76, R.F_ANNEE, couleur=R.OMBRE, ha='right', zorder=4)
    R.texte(ax, x + w, y + h - 182, s, 76, R.F_ANNEE, couleur=R.ROUGE, ha='right', zorder=5)
    ly = y + h - 124
    ax.add_patch(Rectangle((x + 1, ly - 2), 15, 15, color=R.RAMPE[2], lw=0, zorder=7))
    R.texte(ax, x + 24, ly, 'couleur = titres', 13, R.F_SEMI)
    ax.add_patch(Rectangle((x + 1, ly - 30), 15, 10, color=R.RAMPE[1] * 0.72, lw=0, zorder=7))
    ax.add_patch(Rectangle((x + 1, ly - 24), 15, 10, color=R.RAMPE[1], lw=0, zorder=7.1))
    R.texte(ax, x + 24, ly - 26, 'relief = clubs engagés', 13, R.F_SEMI)
    ax.add_patch(Circle((x + 9, ly - 46), 7.5, facecolor='none', edgecolor=R.ROUGE, lw=2, zorder=7))
    R.texte(ax, x + 24, ly - 52, 'champion de la saison', 13, R.F_SEMI)
    ax.add_patch(Circle((x + 9, ly - 72), 3.6, facecolor=R.CADRE_FOND, edgecolor=R.ENCRE, lw=1.2, zorder=7))
    R.texte(ax, x + 24, ly - 78, 'ancien club', 13, R.F_SEMI)
    ax.add_patch(FancyBboxPatch((x, y + 22), w, 8, boxstyle="round,pad=0,rounding_size=4", color=R.PISTE, lw=0, zorder=7))
    ax.add_patch(FancyBboxPatch((x, y + 22), max(8, w * i_total), 8, boxstyle="round,pad=0,rounding_size=4", color=R.ROUGE, lw=0, zorder=7))
    R.texte(ax, x, y, R.saison_txt(DEBUT or 1975), 12, R.F_TITRE)
    R.texte(ax, x + w, y, '2025/26', 12, R.F_TITRE, ha='right')


def frame(cases, i, chemin):
    n = len(cases['france'].d.etats)
    k = min(i // F_SAISON, n - 1)
    u = (i - k * F_SAISON) / F_SAISON if i < n * F_SAISON else 1.0
    e = R.ease(u / TRANSITION)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor(R.PAPIER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
    for l in LIGUES:
        dessiner(ax, cases[l], l, k, e, u)
    prog = (k - 1 + e) / (n - 1) if 0 < k and i < n * F_SAISON else (1 if k else 0)
    if W < H:  # Reels
        bandeau_reel(ax, cases['france'].d.etats[k]['an'], prog)
        R.texte(ax, W / 2, 540, 'Données : Wikipedia · engsoccerdata · Wikidata · SportsLogos.net · Frontières : geoBoundaries',
                11, R.F_SEMI, couleur=R.GRIS, ha='center')
    else:
        case_titre(ax, cases['france'].d.etats[k]['an'], prog)
    fig.savefig(chemin, dpi=100)
    plt.close(fig)


_C = None


def _init(reel=False, annees=50):
    global _C, DEBUT
    DEBUT = periode(annees)
    if reel:
        format_reel()
    _C = {l: Case(l) for l in LIGUES}


def _job(a):
    frame(_C, *a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apercu', type=int, nargs='*', help='saisons (0 à 50) à rendre en PNG seulement')
    ap.add_argument('--reel', action='store_true', help='format Instagram Reels (1080 × 1920)')
    ap.add_argument('--annees', type=int, default=50, help='les N dernières saisons (5, 10, 25 ou 50)')
    a = ap.parse_args()
    out = ROOT / 'videos'
    suffixe = '' if a.annees == 50 else f'_{a.annees}ans'
    periode(a.annees)
    if a.apercu is not None:
        _init(a.reel, a.annees)
        for s in a.apercu:
            p = out / f'apercu_comparaison{"_reel" if a.reel else ""}{suffixe}_{s}.png'
            frame(_C, s * F_SAISON + F_SAISON - 1, p)
            print(p)
        return
    frames = out / (('frames_comparaison_reel' if a.reel else 'frames_comparaison') + suffixe)
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    total = min(a.annees, 51) * F_SAISON + F_FIN
    with Pool(7, initializer=_init, initargs=(a.reel, a.annees)) as pool:
        for j, _ in enumerate(pool.imap_unordered(_job, [(i, frames / f'{i:05d}.png') for i in range(total)], chunksize=6)):
            if j % 60 == 0:
                print(f'{j}/{total}', flush=True)
    mp4 = out / (('comparaison_reel' if a.reel else 'comparaison') + suffixe + '.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', str(frames / '%05d.png'), '-c:v', 'libx264',
                    '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4)], check=True)
    if a.reel:  # Reels : pas de GIF
        shutil.rmtree(frames)
        print(mp4)
        return
    (out / 'gif').mkdir(exist_ok=True)
    gif = out / 'gif' / f'comparaison{suffixe}.gif'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-vf',
                    'fps=12,scale=1280:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4',
                    str(gif)], check=True)
    shutil.rmtree(frames)
    print(mp4, gif)


if __name__ == '__main__':
    main()
