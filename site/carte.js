/* Carte interactive « Les championnats sur la carte » (data-workers.com/projet/comparaison/).
   Une saison = un état précalculé par scripts/export_web.py (data/<ligue>.json) : positions des logos, titres, relief.
   Les couleurs viennent des variables CSS de la page (thème sombre ou clair), les textes de <html lang>. */
(() => {
  const EN = document.documentElement.lang === 'en';
  const S = EN ? {
    titres: 'Titles', regions: { ligue_des_champions: 'Titles by country', nba: 'Titles by state' }, champion: 'Champion',
    nonAttribue: 'Title not awarded', vaom: 'VA-OM match-fixing affair', play: 'Play', pause: 'Pause', saison: 'Season',
    chargement: 'Loading the map…', erreur: 'The map could not be loaded.', clubs: (n) => `${n} clubs so far`, franchises: (n) => `${n} franchises so far`,
  } : {
    titres: 'Titres', regions: { ligue_des_champions: 'Titres par pays', nba: 'Titres par État' }, champion: 'Champion',
    nonAttribue: 'Titre non attribué', vaom: 'Affaire VA-OM', play: 'Lecture', pause: 'Pause', saison: 'Saison',
    chargement: 'Chargement de la carte…', erreur: "La carte n'a pas pu être chargée.", clubs: (n) => `${n} clubs au total`, franchises: (n) => `${n} franchises au total`,
  };
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);
  const app = $('carte-app');
  if (!app) return;
  const svg = $('carte-svg'), gRegs = svg.querySelector('.regs'), gPts = svg.querySelector('.anciens'), gLogos = svg.querySelector('.logos');
  const reduit = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cache = {};
  let D = null, ligue = null, i = 0, lecture = null, logosEls = {}, regEls = [];

  const el = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const saisonTxt = (an) => `${an}/${String(an + 1).slice(2)}`;

  // couleurs du thème : rampe des titres (0 -> moyen -> max), murs plus sombres
  const css = (v) => getComputedStyle(app).getPropertyValue(v).trim();
  const rgb = (h) => { h = h.replace('#', ''); return [0, 2, 4].map((k) => parseInt(h.slice(k, k + 2), 16)); };
  const hex = (c) => '#' + c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('');
  const mix = (a, b, t) => a.map((v, k) => v + (b[k] - v) * t);
  function couleur(n) {
    const r = [css('--rampe0'), css('--rampe1'), css('--rampe2')].map(rgb);
    const t = n ? Math.pow(n / D.maxReg, 0.55) : 0;
    return t < 0.5 ? mix(r[0], r[1], t * 2) : mix(r[1], r[2], (t - 0.5) * 2);
  }
  const mur = (c) => hex(mix(c, [0, 0, 0], parseFloat(css('--mur')) || 0.3));

  async function charger(l) {
    if (!cache[l]) cache[l] = fetch(`/projet/comparaison/data/${l}.json`).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
    return cache[l];
  }

  function construire() {
    svg.setAttribute('viewBox', D.viewBox.join(' '));
    gRegs.innerHTML = ''; gPts.innerHTML = ''; gLogos.innerHTML = ''; logosEls = {};
    regEls = D.regions.map((r) => {
      const g = el('g', { class: 'reg' }, gRegs);
      const t = el('title', {}, g); t.textContent = EN ? r.e : r.n;
      return { r, m1: el('path', { d: r.d, class: 'mur' }, g), m2: el('path', { d: r.d, class: 'mur' }, g), top: el('path', { d: r.d, class: 'top' }, g) };
    });
    $('curseur').max = D.saisons.length - 1;
    $('bloc-regions').hidden = !D.panneauRegions;
    if (D.panneauRegions) $('titre-regions').textContent = S.regions[ligue] || '';
    $('frise').innerHTML = D.saisons.map((s, j) => `<button type="button" data-j="${j}" title="${saisonTxt(s.an)}${s.c ? ' · ' + (EN ? s.nt[s.c][1] : s.nt[s.c][0]) : ''}">` +
      (s.cl ? `<img src="${D.logos}${s.cl}" alt="">` : '<i>–</i>') + '</button>').join('');
  }

  function afficher(j) {
    i = Math.max(0, Math.min(D.saisons.length - 1, j));
    const s = D.saisons[i];
    $('saison').textContent = saisonTxt(s.an);
    $('curseur').value = i;
    $('curseur').setAttribute('aria-valuetext', saisonTxt(s.an));
    // relief et couleurs des régions ; la région du champion est soulevée (h) et cerclée
    for (const e of regEls) {
      const h = s.h[e.r.n] || 5, c = couleur(s.r[e.r.n] || 0);
      e.top.style.transform = `translateY(${-h}px)`; e.m2.style.transform = `translateY(${-h / 2}px)`;
      e.top.style.fill = hex(c); e.m1.style.fill = e.m2.style.fill = mur(c);
      e.top.classList.toggle('champ', e.r.n === s.rc);
    }
    // anciens clubs : points
    gPts.innerHTML = s.a.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4"/>`).join('');
    // clubs présents : logos (entrées et sorties en fondu, déplacements animés)
    const vus = new Set();
    for (const [c, x, y, t, logo] of s.p) {
      vus.add(c);
      let g = logosEls[c];
      if (!g) {
        g = el('g', { class: 'logo entre' }, gLogos);
        el('circle', { class: 'halo', r: 47 }, g);
        el('circle', { class: 'anneau', r: 60 }, g);
        el('image', { x: -45, y: -45, width: 90, height: 90 }, g);
        g.style.transform = `translate(${x}px,${y}px) scale(${t / 100})`;
        logosEls[c] = g;
        requestAnimationFrame(() => g.classList.remove('entre'));
      }
      g.classList.remove('sort');
      const img = g.querySelector('image');
      if (img.getAttribute('href') !== D.logos + logo) img.setAttribute('href', D.logos + logo);
      g.style.transform = `translate(${x}px,${y}px) scale(${t / 100})`;
      g.classList.toggle('champ', c === s.c);
      const n = s.nt[c];
      g.querySelector('title')?.remove();
      const ti = el('title', {}, g); ti.textContent = n ? (EN ? n[1] : n[0]) : '';
    }
    for (const c in logosEls) if (!vus.has(c)) {
      const g = logosEls[c]; g.classList.add('sort'); delete logosEls[c];
      setTimeout(() => g.remove(), reduit ? 0 : 500);
    }
    // le champion passe devant
    const gc = logosEls[s.c]; if (gc) gLogos.appendChild(gc);
    // champion
    const champ = $('champion');
    if (s.c) {
      const n = s.nt[s.c];
      champ.innerHTML = `<div class="cadre"><img src="${D.logos}${s.cl}" alt=""></div><b>${S.champion}</b><span>${EN ? n[1] : n[0]}</span>`;
    } else champ.innerHTML = `<div class="cadre vide"><b>${S.nonAttribue}</b></div><b>${S.champion}</b><span>${S.vaom}</span>`;
    // classement des titres (6 premiers, rangs animés)
    const rang = Object.keys(s.t).sort((a, b) => s.t[b] - s.t[a] || s.nt[a][0].localeCompare(s.nt[b][0])).slice(0, 6);
    const ol = $('titres');
    const lis = {};
    ol.querySelectorAll('li').forEach((li) => { lis[li.dataset.c] = li; });
    rang.forEach((c, k) => {
      let li = lis[c];
      if (!li) { li = document.createElement('li'); li.dataset.c = c; li.innerHTML = '<img alt=""><span class="nom"></span><span class="n"></span><i><b></b></i>'; li.style.transform = 'translateY(240px)'; ol.appendChild(li); }
      delete lis[c];
      const n = s.nt[c];
      li.querySelector('img').src = D.logos + n[2];
      li.querySelector('.nom').textContent = EN ? n[1] : n[0];
      li.querySelector('.n').textContent = s.t[c];
      li.querySelector('b').style.width = (100 * s.t[c] / D.maxTitres) + '%';
      requestAnimationFrame(() => { li.style.transform = `translateY(${k * 40}px)`; li.style.opacity = 1; });
    });
    Object.values(lis).forEach((li) => { li.style.opacity = 0; setTimeout(() => li.remove(), 400); });
    // titres par région (Ligue des champions, NBA)
    if (D.panneauRegions) {
      const regs = Object.keys(s.r).sort((a, b) => s.r[b] - s.r[a]).slice(0, 5);
      const nomsEn = Object.fromEntries(D.regions.map((r) => [r.n, r.e]));
      $('regions').innerHTML = regs.map((r) => `<li><i style="background:${hex(couleur(s.r[r]))}"></i><span>${EN ? (nomsEn[r] || r) : r}</span><b>${s.r[r]}</b></li>`).join('');
    }
    // frise : saisons passées pleines, saison en cours marquée
    $('frise').querySelectorAll('button').forEach((b, k) => { b.classList.toggle('passe', k <= i); b.classList.toggle('on', k === i); });
  }

  function jouer(on) {
    clearInterval(lecture); lecture = null;
    const b = $('play');
    if (on) {
      if (i >= D.saisons.length - 1) afficher(0);
      lecture = setInterval(() => { if (i >= D.saisons.length - 1) jouer(false); else afficher(i + 1); }, reduit ? 1200 : 750);
    }
    b.classList.toggle('pause', !!lecture);
    b.setAttribute('aria-label', lecture ? S.pause : S.play);
    b.title = lecture ? S.pause : S.play;
  }

  async function choisir(l, depart) {
    jouer(false);
    ligue = l;
    app.classList.add('charge');
    $('carte-msg').textContent = S.chargement;
    try {
      D = await charger(l);
    } catch (e) { $('carte-msg').textContent = S.erreur; return; }
    if (ligue !== l) return;
    construire();
    afficher(depart ?? D.saisons.length - 1);
    app.classList.remove('charge');
    $('carte-msg').textContent = '';
  }

  $('play').addEventListener('click', () => jouer(!lecture));
  $('curseur').addEventListener('input', (e) => { jouer(false); afficher(+e.target.value); });
  $('frise').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { jouer(false); afficher(+b.dataset.j); } });
  addEventListener('keydown', (e) => {
    if (e.target.closest('input, button, a')) return;
    if (e.key === ' ') { e.preventDefault(); jouer(!lecture); }
    if (e.key === 'ArrowRight') { jouer(false); afficher(i + 1); }
    if (e.key === 'ArrowLeft') { jouer(false); afficher(i - 1); }
  });
  window.carteChoisir = choisir;   // appelé par les boutons de ligue de la page
})();
