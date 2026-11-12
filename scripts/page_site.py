"""Page du projet sur data-workers.com : la carte interactive, avec le choix de la ligue et un bouton lecture.

    python scripts/export_web.py       # données de la carte : site/data/<ligue>.json + logos
    python scripts/page_site.py        # écrit site/projet/comparaison/ et site/en/projet/comparaison/ (+ clair/)
    scripts/deploy_site.sh             # publie pages, carte.js et données sur data-workers.com

Quatre pages : français et anglais, chacune en version sombre et claire (les thèmes de data-workers.com). La carte
(site/carte.js) prend ses couleurs dans les variables CSS du thème et ses textes dans la langue de la page.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_REPO = ROOT.parents[2] / 'site_data_workers' / 'data-workers-links'   # pour reprendre les boutons clair / sombre
sys.path.insert(0, str(ROOT.parents[2] / 'outils' / 'html'))
try:  # aperçu des liens partagés (le logo Data Workers) : outil du site, absent d'un clone du dépôt seul
    from partage import avec_logo  # noqa: E402
except ImportError:
    def avec_logo(page):
        return page

MEDIA = '/projet/comparaison/media/'
LIGUES = ['france', 'angleterre', 'liga', 'ligue_des_champions', 'nba']
NOMS = {
    'fr': {'france': 'Championnat de France', 'angleterre': "Championnat d'Angleterre", 'liga': "Championnat d'Espagne",
           'ligue_des_champions': 'Ligue des champions', 'nba': 'NBA'},
    'en': {'france': 'French league', 'angleterre': 'English league', 'liga': 'Spanish league',
           'ligue_des_champions': 'Champions League', 'nba': 'NBA'},
}
COURTS = {'fr': {'france': 'France', 'angleterre': 'Angleterre', 'liga': 'Espagne', 'ligue_des_champions': 'Ligue des champions', 'nba': 'NBA'},
          'en': {'france': 'France', 'angleterre': 'England', 'liga': 'Spain', 'ligue_des_champions': 'Champions League', 'nba': 'NBA'}}
SOURCES = {'france': 'Wikipedia × engsoccerdata', 'angleterre': 'Wikipedia × engsoccerdata', 'liga': 'Wikipedia × Wikidata',
           'ligue_des_champions': 'Wikipedia × Wikidata', 'nba': 'Wikipedia × SportsLogos.net'}
NOMS_EN = {'FC Barcelone': 'FC Barcelona', 'Valence CF': 'Valencia CF', 'Deportivo La Corogne': 'Deportivo La Coruña'}

T = {
    'fr': dict(
        titre='Les championnats sur la carte', kicker='Data visualisation · Sport',
        lead="Cinquante saisons, de 1975/76 à 2025/26 : chaque club engagé est placé sur la carte, saison après saison. "
             "La couleur d'une région montre ses titres, sa hauteur le nombre de clubs présents, et la région du champion se soulève à chaque titre.",
        choisir='Choisir une compétition', clubs='{n} clubs engagés', franchises='{n} franchises', saisons='51 saisons · 1975/76 → 2025/26',
        titres_h='Titres', plus='Le plus titré', titres='{n} titres', ex='ex aequo avec', lire='Comment lire la vidéo',
        legende=["<b>La couleur</b> d'une région : ses titres cumulés", "<b>La hauteur</b> : le nombre de clubs présents cette saison",
                 "<b>Le champion</b> grossit et sa région se soulève, avec un contour rouge", "<b>Les points</b> : les clubs déjà passés par la compétition",
                 "<b>En haut</b> : la frise des champions et le classement des titres"],
        sources='Données', telecharger='Télécharger la vidéo', autre='Version claire', autre_sombre='Version sombre',
        nav_projets='Projets', video_alt='Vidéo : {nom}, 1975/76 → 2025/26', description="Cinquante saisons de football et de NBA sur la carte : tous les clubs, les titres par région et les champions, de 1975/76 à 2025/26."),
    'en': dict(
        titre='The leagues on the map', kicker='Data visualisation · Sport',
        lead='Fifty seasons, from 1975/76 to 2025/26: every club taking part is placed on the map, season after season. '
             "A region's colour shows its titles, its height the number of clubs present, and the champion's region rises with every title.",
        choisir='Choose a competition', clubs='{n} clubs', franchises='{n} franchises', saisons='51 seasons · 1975/76 → 2025/26',
        titres_h='Titles', plus='Most titles', titres='{n} titles', ex='level with', lire='How to read the video',
        legende=["<b>Colour</b> of a region: its total titles", "<b>Height</b>: the number of clubs present that season",
                 "<b>The champion</b> grows and its region rises, outlined in red", "<b>Dots</b>: clubs that have already taken part",
                 "<b>At the top</b>: the timeline of champions and the titles ranking"],
        sources='Data', telecharger='Download the video', autre='Light version', autre_sombre='Dark version',
        nav_projets='Projects', video_alt='Video: {nom}, 1975/76 → 2025/26', description='Fifty seasons of football and NBA on the map: every club, titles by region and the champions, from 1975/76 to 2025/26.'),
}


def chiffres(ligue, langue):
    d = json.loads((ROOT / 'data' / 'video' / f'{ligue}.json').read_text())
    titres = {}
    for c in d['champions'].values():
        if c:
            titres[c] = titres.get(c, 0) + 1
    top = max(titres.values())
    noms = sorted(d['clubs'][c]['nom'] for c, n in titres.items() if n == top)
    if langue == 'en':
        noms = [NOMS_EN.get(n, n) for n in noms]
    return len(d['clubs']), noms, top


def style_switch(fichier):
    if not (SITE_REPO / fichier).exists():  # clone du dépôt seul : pas de bouton clair / sombre du site
        return ''
    m = re.search(r'<style id="theme-switch">.*?</style>', (SITE_REPO / fichier).read_text(encoding='utf-8'), re.S)
    return m.group(0) if m else ''


SWITCH_LANGUE = {
    False: "a.lang-switch { position: fixed; top: 56px; right: 14px; z-index: 1000; display: inline-flex; align-items: center; justify-content: center; min-width: 42px; padding: 8px 12px; font: 600 13px/1 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: .04em; text-decoration: none; border: 1px solid rgba(255,255,255,.24); border-radius: 999px; background: rgba(7,11,21,.8); color: #e2e8f0; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); }\na.lang-switch:hover { border-color: #2dc4c2; color: #fff; }",
    True: "a.lang-switch { position: fixed; top: 56px; right: 14px; z-index: 1000; display: inline-flex; align-items: center; justify-content: center; min-width: 42px; padding: 8px 12px; font: 13px/1 'Arvo', Rockwell, Georgia, serif; text-decoration: none; border: 1.5px solid #1d1b19; border-radius: 2px; background: #ebe7de; color: #1d1b19; }\na.lang-switch:hover { background: #1d1b19; color: #ebe7de; }",
}

THEMES = {
    # rampe des titres des régions (0 -> moyen -> max), murs (part de noir), points, halo des logos, accent
    False: """:root { --bg: #070b15; --panel: rgba(255,255,255,.04); --line: rgba(255,255,255,.09); --ink: #f8fafc; --ink2: #cbd5e1; --muted: #94a3b8;
  --accent: #2dc4c2; --accent-ink: #04121a; --radius: 16px; --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --rampe0: #1c2536; --rampe1: #1d7f80; --rampe2: #2dc4c2; --mur: .45; --bord: #070b15; --point: #070b15; --point-ink: #94a3b8;
  --halo: rgba(248,250,252,.94); --piste: rgba(255,255,255,.1); --champ: #2dc4c2; }
body { background: var(--bg) radial-gradient(ellipse 80% 40% at 50% -5%, rgba(45,196,194,.12), transparent 70%) no-repeat; }
h1 { font-weight: 800; letter-spacing: -.02em; } h1 span { color: var(--accent); }
.pills button { border: 1px solid var(--line); border-radius: 999px; background: var(--panel); color: var(--ink2); font-weight: 600; }
.pills button:hover { border-color: rgba(45,196,194,.5); color: var(--ink); }
.pills button.on { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.boite { border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); }
#play { border-radius: 999px; background: var(--accent); color: var(--accent-ink); }
.champion .cadre { border: 2px solid var(--accent); border-radius: 14px; background: #0b1020; }
.saison { font-weight: 800; letter-spacing: -.02em; color: var(--accent); }""",
    True: """:root { --bg: #ebe7de; --panel: #f6f3ec; --line: #1d1b19; --ink: #1d1b19; --ink2: #3b3833; --muted: #6f6a62;
  --accent: #c2393f; --accent-ink: #ebe7de; --radius: 2px; --font: 'Arvo', Rockwell, Georgia, serif;
  --rampe0: #ddd6c8; --rampe1: #cf6266; --rampe2: #8e2a2f; --mur: .28; --bord: #f6f3ec; --point: #f6f3ec; --point-ink: #1d1b19;
  --halo: transparent; --piste: #d9d3c7; --champ: #c2393f; }
body { background: var(--bg); }
h1 { font-weight: 700; text-shadow: 3px 3px 0 #cfc9bd; } h1 span { color: #fe4d1a; }
.pills button { border: 1.5px solid var(--ink); border-radius: 2px; background: var(--panel); color: var(--ink); }
.pills button:hover { box-shadow: 3px 3px 0 #fe4d1a; transform: translate(-1px, -1px); }
.pills button.on { background: var(--ink); color: var(--bg); }
.boite { border: 1.5px solid var(--ink); border-radius: 2px; background: var(--panel); box-shadow: 4px 4px 0 rgba(0,0,0,.12); }
#play { border-radius: 2px; background: var(--ink); color: var(--bg); }
.champion .cadre { border: 3px solid var(--accent); border-radius: 2px; background: var(--panel); box-shadow: 5px 5px 0 #cfc9bd; }
.saison { font-weight: 700; color: var(--accent); text-shadow: 3px 3px 0 #cfc9bd; }""",
}
STYLE = """* { box-sizing: border-box; }
body { margin: 0; color: var(--ink); font-family: var(--font); }
.wrap { max-width: 1180px; margin: 0 auto; padding: 22px 20px 56px; }
.sitenav { display: flex; align-items: center; gap: 12px; font-size: 14px; margin-bottom: 30px; }
.sitenav img { width: 30px; height: 30px; } .sitenav a { color: var(--muted); text-decoration: none; } .sitenav a:hover { color: var(--ink); }
.sitenav span { color: var(--muted); opacity: .6; }
.kicker { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; color: var(--accent); margin: 0 0 12px; }
h1 { margin: 0; font-size: clamp(32px, 6vw, 54px); line-height: 1.05; }
.lead { margin: 16px 0 0; max-width: 76ch; color: var(--muted); font-size: 16px; line-height: 1.65; }
.choisir { margin: 26px 0 10px; font-size: 13px; color: var(--muted); }
.pills { display: flex; flex-wrap: wrap; gap: 8px; }
.pills button { font: inherit; font-size: 14px; padding: 9px 16px; cursor: pointer; transition: all .15s; }
/* la carte interactive */
.app { margin-top: 22px; display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 20px; }
.app.charge .scene-carte { opacity: .35; }
.scene-carte { position: relative; padding: 10px; transition: opacity .2s; align-self: start; }
#carte-svg { width: 100%; height: auto; display: block; max-height: 74vh; }
#carte-msg { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--muted); pointer-events: none; }
.reg path { stroke: var(--bord); stroke-width: 1; transition: transform .45s ease, fill .45s ease; }
.reg path.mur { stroke: none; }
.reg path.top.champ { stroke: var(--champ); stroke-width: 2.4; }
.anciens circle { fill: var(--point); stroke: var(--point-ink); stroke-width: 1.3; }
.logos .logo { transition: transform .45s ease, opacity .45s ease; }
.logos .logo.entre, .logos .logo.sort { opacity: 0; }
.logos .halo { fill: var(--halo); }
.logos .anneau { fill: none; stroke: var(--champ); stroke-width: 6; opacity: 0; transition: opacity .3s; }
.logos .logo.champ .anneau { opacity: 1; }
.panneaux { display: flex; flex-direction: column; gap: 16px; }
.lecture { padding: 16px; }
.saison { font-size: 46px; line-height: 1; margin: 0 0 12px; font-variant-numeric: tabular-nums; }
.ctrl { display: flex; align-items: center; gap: 12px; }
#play { width: 44px; height: 44px; flex: none; border: 0; cursor: pointer; display: grid; place-items: center; font-size: 0; }
#play::before { content: ''; margin-left: 4px; border-left: 15px solid currentColor; border-top: 9px solid transparent; border-bottom: 9px solid transparent; }
#play.pause::before { margin: 0; width: 14px; height: 16px; border: 0; border-left: 5px solid currentColor; border-right: 5px solid currentColor; }
#curseur { flex: 1; accent-color: var(--accent); }
.champion { padding: 16px; display: grid; justify-items: center; text-align: center; gap: 4px; }
.champion .cadre { width: 132px; height: 132px; display: grid; place-items: center; margin-bottom: 8px; }
.champion .cadre img { width: 96px; height: 96px; object-fit: contain; }
.champion .cadre.vide b { color: var(--accent); font-size: 15px; padding: 10px; }
.champion > b { font-size: 17px; } .champion > span { color: var(--muted); font-size: 14px; }
.liste { padding: 16px; } .liste h3 { margin: 0 0 12px; font-size: 15px; }
#titres { position: relative; list-style: none; margin: 0; padding: 0; height: 240px; }
#titres li { position: absolute; left: 0; right: 0; top: 0; height: 36px; display: grid; grid-template-columns: 30px 1fr auto; column-gap: 8px; align-items: center;
  transition: transform .45s ease, opacity .4s; opacity: 0; }
#titres img { width: 26px; height: 26px; object-fit: contain; grid-row: span 2; }
#titres .nom { font-size: 13px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#titres .n { font-size: 13px; font-weight: 700; grid-row: span 2; }
#titres i { height: 6px; background: var(--piste); border-radius: 3px; overflow: hidden; } #titres i b { display: block; height: 100%; background: var(--accent); transition: width .45s; }
#regions { list-style: none; margin: 0; padding: 0; font-size: 13px; }
#regions li { display: grid; grid-template-columns: 16px 1fr auto; gap: 8px; align-items: center; padding: 3px 0; }
#regions li i { width: 14px; height: 14px; border-radius: 2px; }
.frise { grid-column: 1 / -1; padding: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(34px, 1fr)); gap: 6px; }
.frise button { border: 0; background: none; padding: 2px; cursor: pointer; opacity: .2; transition: opacity .2s, transform .2s; border-radius: 6px; }
.frise button.passe { opacity: 1; } .frise button.on { outline: 2px solid var(--accent); transform: scale(1.12); }
.frise img { width: 100%; aspect-ratio: 1; object-fit: contain; display: block; } .frise i { color: var(--muted); font-style: normal; }
.lire { margin-top: 22px; padding: 18px 20px; }
.lire h3 { margin: 0 0 8px; font-size: 14px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.lire ul { margin: 0 0 10px; padding-left: 18px; color: var(--ink2); font-size: 14px; line-height: 1.7; columns: 2 300px; }
.lire .src { font-size: 13px; color: var(--muted); margin: 0; }
.sitefoot { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); } .sitefoot a { color: var(--ink2); }
@media (max-width: 900px) { .app { grid-template-columns: 1fr; } .panneaux { display: grid; grid-template-columns: 1fr 1fr; } .lecture { grid-column: 1 / -1; } }
@media (max-width: 560px) { .panneaux { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .reg path, .logos .logo, #titres li, #titres i b { transition: none; } }"""

T['fr'].update(legende=["<b>La couleur</b> d'une région : ses titres cumulés", "<b>La hauteur</b> : le nombre de clubs présents cette saison",
                        "<b>Le champion</b> grossit et sa région se soulève, cerclée", "<b>Les points</b> : les clubs déjà passés par la compétition",
                        "<b>La frise</b> : un clic sur un champion ramène à sa saison", "<b>Lecture</b> : la barre d'espace, les flèches ← → pour avancer"],
               lire='Comment lire la carte')
T['en'].update(legende=["<b>Colour</b> of a region: its total titles", "<b>Height</b>: the number of clubs present that season",
                        "<b>The champion</b> grows and its region rises, outlined", "<b>Dots</b>: clubs that have already taken part",
                        "<b>The timeline</b>: click a champion to jump to its season", "<b>Playback</b>: space bar, arrow keys ← → to step"],
               lire='How to read the map')


def page(langue, clair):
    t = T[langue]
    racine = '/en' if langue == 'en' else ''
    sous = 'clair/' if clair else ''
    fr_url, en_url = f'/projet/comparaison/{sous}', f'/en/projet/comparaison/{sous}'
    boutons = ''.join(f'<button type="button" data-l="{l}" aria-pressed="false">{html.escape(COURTS[langue][l])}</button>' for l in LIGUES)
    cible, code, titre_l = (en_url, 'en', 'English version') if langue == 'fr' else (fr_url, 'fr', 'Version française')
    # bouton clair / sombre dans le fil d'Ariane, comme les autres pages projet (projet/penaltys/) ; « Projets » mène à /projet/
    switch_theme = f'<a class="switch theme-switch" href="{"../" if clair else "clair/"}">{t["autre_sombre"] if clair else t["autre"]}</a>'
    accueil = f'{racine}/clair/' if clair else f'{racine}/'
    fonts = ('family=Arvo:ital,wght@0,400;0,700;1,400' if clair else 'family=Inter:wght@400;500;600;700;800')
    sources = ' · '.join(f'{COURTS[langue][l]} : {SOURCES[l]}' for l in LIGUES)
    titre_h1 = html.escape(t['titre']).replace(' sur la carte', ' <span>sur la carte</span>').replace(' on the map', ' <span>on the map</span>')
    page = f"""<!doctype html>
<html lang="{langue}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t['titre'])} · Data Workers</title>
<meta name="description" content="{html.escape(t['description'])}">
<meta property="og:title" content="{html.escape(t['titre'])}">
<meta property="og:description" content="{html.escape(t['description'])}">
<meta property="og:url" content="https://data-workers.com{en_url if langue == 'en' else fr_url}">
<link rel="icon" href="/assets/images/logo.ico">
<link rel="alternate" hreflang="fr" href="https://data-workers.com{fr_url}">
<link rel="alternate" hreflang="en" href="https://data-workers.com{en_url}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?{fonts}&display=swap" rel="stylesheet">
<style>{THEMES[clair]}
{STYLE}</style>
{style_switch('clair/index.html' if clair else 'index.html')}
<style id="lang-switch">
{SWITCH_LANGUE[clair]}
@media (max-width: 600px) {{ a.lang-switch {{ right: 10px; width: 38px; height: 38px; min-width: 0; padding: 0; font-size: 12px; }} }}
</style>
</head>
<body>
<a class="lang-switch" href="{cible}" hreflang="{code}" lang="{code}" title="{titre_l}">{code.upper()}</a>
<div class="wrap">
  <nav class="sitenav"><img src="/assets/images/{'logo_orange' if clair else 'logo'}.png" alt=""><a href="{accueil}">Data Workers</a><span>/</span><a href="{racine}/projet/{sous}">{t['nav_projets']}</a>{switch_theme}</nav>
  <p class="kicker">{t['kicker']}</p>
  <h1>{titre_h1}</h1>
  <p class="lead">{html.escape(t['lead'])}</p>
  <p class="choisir">{t['choisir']}</p>
  <nav class="pills" id="pills" aria-label="{t['choisir']}">{boutons}</nav>
  <section class="app" id="carte-app">
    <div class="scene-carte boite">
      <svg id="carte-svg" role="img" aria-label="{html.escape(t['titre'])}"><g class="regs"></g><g class="anciens"></g><g class="logos"></g></svg>
      <div id="carte-msg"></div>
    </div>
    <aside class="panneaux">
      <div class="lecture boite"><p class="saison" id="saison">1975/76</p>
        <div class="ctrl"><button id="play" type="button" aria-label="Lecture"></button><input id="curseur" type="range" min="0" max="50" value="50" aria-label="{'Season' if langue == 'en' else 'Saison'}"></div></div>
      <div class="champion boite" id="champion"></div>
      <div class="liste boite"><h3>{t['titres_h']}</h3><ol id="titres"></ol></div>
      <div class="liste boite" id="bloc-regions" hidden><h3 id="titre-regions"></h3><ol id="regions"></ol></div>
    </aside>
    <div class="frise boite" id="frise"></div>
  </section>
  <section class="lire boite">
    <h3>{t['lire']}</h3>
    <ul>{''.join(f'<li>{x}</li>' for x in t['legende'])}</ul>
    <p class="src">{t['sources']}{':' if langue == 'en' else ' :'} {html.escape(sources)} · geoBoundaries</p>
  </section>
  <footer class="sitefoot"><a href="{accueil}">data-workers.com</a> · Kevin Rosamont Prombo · <a href="https://github.com/krosamont/comparaison-sport">{'The code on GitHub' if langue == 'en' else 'Le code sur GitHub'}</a></footer>
</div>
<script src="/projet/comparaison/carte.js?v=1"></script>
<script>
  const pills = document.getElementById('pills');
  function choisirLigue(l) {{
    if (!{json.dumps(LIGUES)}.includes(l)) l = 'france';
    pills.querySelectorAll('button').forEach((b) => {{ const on = b.dataset.l === l; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); }});
    history.replaceState(null, '', '?ligue=' + l);
    window.carteChoisir(l);
  }}
  pills.addEventListener('click', (e) => {{ const b = e.target.closest('button'); if (b) choisirLigue(b.dataset.l); }});
  choisirLigue(new URLSearchParams(location.search).get('ligue') || 'france');
  // les boutons de langue et de thème gardent la compétition choisie
  document.querySelectorAll('a.lang-switch, a.theme-switch').forEach((a) => a.addEventListener('click', () => {{ a.href = a.getAttribute('href').split('?')[0] + location.search; }}));
</script>
</body>
</html>
"""
    return avec_logo(page)


if __name__ == '__main__':
    for langue in ('fr', 'en'):
        for clair in (False, True):
            dest = ROOT / 'site' / ('en/' if langue == 'en' else '') / 'projet' / 'comparaison' / ('clair' if clair else '') / 'index.html'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(page(langue, clair), encoding='utf-8')
            print(dest.relative_to(ROOT))
