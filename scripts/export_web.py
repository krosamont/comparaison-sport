"""Données de la carte interactive (page /projet/comparaison/) : une saison = un état précalculé.

    python scripts/export_web.py [ligue ...]     # écrit site/data/<ligue>.json et site/data/logos/<ligue>/*.png

Reprend le moteur des vidéos (render.Donnees) : régions en relief, positions des logos sans chevauchement, titres,
hauteurs, champion. Les coordonnées sont celles de la carte des vidéos (pixels, y vers le haut), retournées pour le SVG.
Les noms (clubs, régions) existent en français et en anglais ; les logos sont réduits à 128 px.
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'site' / 'data'
H = render.H
LIGUES = ['france', 'angleterre', 'liga', 'ligue_des_champions', 'nba']

# noms anglais (ceux qui diffèrent) : clubs champions, pays, États
EN = {
    'FC Barcelone': 'FC Barcelona', 'Valence CF': 'Valencia CF', 'Deportivo La Corogne': 'Deportivo La Coruña',
    'Atlético de Madrid': 'Atlético Madrid', 'Hambourg SV': 'Hamburger SV', 'Steaua Bucarest': 'Steaua Bucharest',
    'Étoile rouge de Belgrade': 'Red Star Belgrade', 'Ajax Amsterdam': 'Ajax', 'AS Rome': 'AS Roma',
    'Benfica Lisbonne': 'Benfica', 'Club Bruges': 'Club Brugge',
    # pays (Ligue des champions)
    'Albanie': 'Albania', 'Andorre': 'Andorra', 'Arménie': 'Armenia', 'Autriche': 'Austria', 'Azerbaïdjan': 'Azerbaijan',
    'Biélorussie': 'Belarus', 'Belgique': 'Belgium', 'Bosnie': 'Bosnia', 'Bulgarie': 'Bulgaria', 'Croatie': 'Croatia',
    'Chypre': 'Cyprus', 'Tchéquie': 'Czechia', 'Danemark': 'Denmark', 'Estonie': 'Estonia', 'Féroé': 'Faroe Islands',
    'Finlande': 'Finland', 'Géorgie': 'Georgia', 'Allemagne': 'Germany', 'Grèce': 'Greece', 'Hongrie': 'Hungary',
    'Islande': 'Iceland', 'Irlande': 'Ireland', 'Israël': 'Israel', 'Italie': 'Italy', 'Lettonie': 'Latvia',
    'Lituanie': 'Lithuania', 'Moldavie': 'Moldova', 'Monténégro': 'Montenegro', 'Pays-Bas': 'Netherlands',
    'Macédoine du Nord': 'North Macedonia', 'Norvège': 'Norway', 'Pologne': 'Poland', 'Roumanie': 'Romania',
    'Russie': 'Russia', 'Saint-Marin': 'San Marino', 'Serbie': 'Serbia', 'Slovaquie': 'Slovakia', 'Slovénie': 'Slovenia',
    'Espagne': 'Spain', 'Suède': 'Sweden', 'Suisse': 'Switzerland', 'Turquie': 'Turkey', 'Angleterre': 'England',
    'Écosse': 'Scotland', 'Pays de Galles': 'Wales', 'Irlande du Nord': 'Northern Ireland',
    # États / provinces (NBA)
    'Californie': 'California', 'Pennsylvanie': 'Pennsylvania', 'Floride': 'Florida', 'Louisiane': 'Louisiana',
    'Caroline du Nord': 'North Carolina', 'Caroline du Sud': 'South Carolina', 'État de Washington': 'Washington',
    'État de New York': 'New York', 'Washington D.C.': 'Washington, D.C.', 'Colombie-Britannique': 'British Columbia',
    'Québec': 'Quebec', 'Nouveau-Mexique': 'New Mexico', 'Virginie': 'Virginia', 'Virginie-Occidentale': 'West Virginia',
    'Dakota du Nord': 'North Dakota', 'Dakota du Sud': 'South Dakota',
    # régions (France, Angleterre, Espagne) : affichées seulement au survol
    'Bretagne': 'Brittany', 'Normandie': 'Normandy', 'Corse': 'Corsica', 'Nord-Ouest': 'North West', 'Nord-Est': 'North East',
    "Midlands de l'Est": 'East Midlands', "Midlands de l'Ouest": 'West Midlands', 'Est': 'East of England',
    'Londres': 'London', 'Sud-Est': 'South East', 'Sud-Ouest': 'South West', 'Andalousie': 'Andalusia',
    'Canaries': 'Canary Islands', 'Cantabrie': 'Cantabria', 'Castille-et-León': 'Castile and León',
    'Castille-La Manche': 'Castilla-La Mancha', 'Catalogne': 'Catalonia', 'Valence': 'Valencia', 'Estrémadure': 'Extremadura',
    'Galice': 'Galicia', 'Baléares': 'Balearic Islands', 'Pays basque': 'Basque Country', 'Asturies': 'Asturias', 'Murcie': 'Murcia',
}


def r1(v):
    return round(float(v), 1)


def chemin(anneaux):
    """Contours simplifiés (0,7 px, invisible à l'écran) en chemin SVG, y retourné."""
    out = []
    for a in anneaux:
        p = Polygon(a).simplify(0.7, preserve_topology=True)
        if p.is_empty or p.area < 4:
            continue
        xy = list(p.exterior.coords)
        out.append('M' + 'L'.join(f'{x:.0f},{H - y:.0f}' for x, y in xy) + 'Z')
    return ''.join(out)


def exporter(ligue):
    d = render.Donnees(ligue)
    dest_logos = OUT / 'logos' / ligue
    dest_logos.mkdir(parents=True, exist_ok=True)
    logos = {}
    for cle_logo, arr in d.logos.items():
        nom = hashlib.md5(cle_logo.encode()).hexdigest()[:10] + '.png'
        im = Image.fromarray(arr)
        im.thumbnail((128, 128), Image.LANCZOS)
        im.save(dest_logos / nom, optimize=True)
        logos[cle_logo] = nom
    cx0, cy0, cx1, cy1 = d.cfg['carte']
    marge = 70
    vb = [cx0 - 10, r1(H - cy1 - marge), cx1 - cx0 + 20, r1(cy1 - cy0 + marge + 30)]
    regions = [dict(n=r['nom'], e=EN.get(r['nom'], r['nom']), d=chemin(r['anneaux'])) for r in d.regions if r['anneaux']]
    saisons = []
    for et in d.etats:
        info = et['info']
        titres = et['titres']
        saisons.append(dict(
            an=et['an'], c=et['champ'], cl=logos.get(et['champ_logo']) if et['champ'] else None, rc=et.get('reg_champ'),
            p=[[c, r1(et['pos'][c][0]), r1(H - et['pos'][c][1]), r1(et['tailles'][c]), logos[info[c]['cle_logo']]] for c in et['presents']],
            a=[[r1(e['px'][0]), r1(H - e['px'][1] - et['hauteur'][e['region']])] for e in et['anciens'].values()],
            t=titres,
            nt={c: [info[c]['nom'], EN.get(info[c]['nom'], info[c]['nom']), logos[info[c]['cle_logo']]] for c in titres},
            r=et['reg_titres'],
            h={k: r1(v) for k, v in et['hauteur'].items() if v > 5.01},
        ))
    out = dict(ligue=ligue, viewBox=vb, regions=regions, logos=f'/projet/comparaison/data/logos/{ligue}/',
               maxTitres=d.max_titres, maxReg=d.max_reg, panneauRegions=d.cfg['panneau_regions'], saisons=saisons)
    (OUT / f'{ligue}.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    taille = (OUT / f'{ligue}.json').stat().st_size / 1e3
    print(f'{ligue}: {len(saisons)} saisons, {len(regions)} régions, {len(logos)} logos, {taille:.0f} Ko')


if __name__ == '__main__':
    for l in sys.argv[1:] or LIGUES:
        exporter(l)
