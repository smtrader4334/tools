/*
 * 더함 회사 소개 — 122 s @ 30 fps (music at 120 BPM: every cue on a 0.5 s beat, bars every 2 s)
 *
 *   0–12    C1 사고는 예고 없이: 화재 · 누수 · 배상책임 · 자연재해
 *  12–26    C2 손해사정이란 (정의와 세 단계)
 *  26–38    C3 손해사정사는 고객도 선임할 수 있습니다
 *  38–62    C4 업무 분야 네 가지
 *  62–80    C5 더함의 기준: 현장 · 자료 · 설명
 *  80–96    C6 구성원과 상담 창구
 *  96–106   C7 부산 · 울산 · 경남
 * 106–122   C8 브랜드 라인 → 로고 → 엔드카드
 */
(() => {
  const { E, P, env, show, chars, grow, draw, setStyle, lerp, blurCss } = M;
  const $ = (id) => document.getElementById(id);
  const TAU = Math.PI * 2;
  const film = new M.Film({ duration: 122, fps: 30 });
  const W = 1920, H = 1080;
  M.fitStage($('stage'), W, H);

  const back = $('fxBack'), bctx = back.getContext('2d');
  const dust = new FX.Dust({ count: 90, seed: 31, color: '142,175,247', size: [0.8, 2.4], speed: 9, alpha: 0.45 });

  // soft light sweeping across the navy scenes
  function glow(ctx, t, k) {
    if (k <= 0.002) return;
    const x = W * (0.25 + 0.5 * (0.5 + 0.5 * Math.sin(t * 0.12))), y = H * 0.3;
    const g = ctx.createRadialGradient(x, y, 0, x, y, 900);
    g.addColorStop(0, `rgba(40,90,245,${(0.10 * k).toFixed(4)})`);
    g.addColorStop(1, 'rgba(40,90,245,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  film.layer((t) => {
    bctx.clearRect(0, 0, W, H);
    // C1, C3, C5, C7, C8 are navy scenes with the dust bed behind them
    const k = Math.max(env(t, 0, 12.4, 1.2, 0.6), env(t, 26.0, 38.4, 0.6, 0.6), env(t, 62.0, 80.4, 0.6, 0.6), env(t, 96.0, 106.4, 0.6, 0.6), env(t, 106.0, 122, 0.6, 0));
    glow(bctx, t, k);
    dust.draw(bctx, t, k);
    const fade = Math.max(1 - P(t, 0, 0.8, E.outQuad), P(t, 120.8, 1.2, E.inOutSine));
    setStyle($('fade'), { opacity: fade });
  });

  // icon paths inside an element draw in turn
  const drawIcons = (el, t, t0, dur = 1.1) => el.querySelectorAll('svg path').forEach((p, i) => draw(p, t, t0 + i * 0.25, dur));

  /* ------------------------------------------------- C1: accidents */
  film.scene('c1', 0, 12.4, (lt, t) => {
    $('c1').style.opacity = env(t, 0, 12.4, 0, 0.6).toFixed(4);
    chars($('c1t'), t, 1.0, 999, { stagger: 0.05, y: 20, blur: 10 });
    ['a1', 'a2', 'a3', 'a4'].forEach((id, i) => {
      const t0 = 3.0 + i * 0.5;
      show($(id), t, t0, 999, { y: 24, blur: 8, fin: 1.0 });
      drawIcons($(id), t, t0, 1.2);
    });
    show($('c1q'), t, 7.5, 999, { y: 16, blur: 8 });
  });

  /* ------------------------------------------ C2: what adjusting is */
  film.scene('c2', 11.8, 26.4, (lt, t) => {
    const w = P(t, 11.8, 0.9, E.inOutQuart);
    $('c2').style.clipPath = w < 1 ? `inset(0 0 0 ${((1 - w) * 100).toFixed(3)}%)` : 'none';
    $('c2').style.opacity = env(t, 11.8, 26.4, 0, 0.6).toFixed(4);
    show($('c2eb'), t, 12.5, 999, { y: 10 });
    chars($('c2w'), t, 12.8, 999, { stagger: 0.07, y: 26, blur: 12 });
    grow($('c2rule'), t, 13.6, 1.1);
    show($('c2d'), t, 14.4, 999, { y: 14, blur: 8 });
    ['s21', 's22', 's23'].forEach((id, i) => show($(id), t, 16.0 + i * 1.0, 999, { y: 30, blur: 8, fin: 1.0 }));
    show($('c2c'), t, 21.0, 999, { y: 14, blur: 8 });
  });

  /* ---------------------------------------------- C3: who adjusts */
  film.scene('c3', 25.8, 38.4, (lt, t) => {
    $('c3').style.opacity = env(t, 25.8, 38.4, 0.6, 0.6).toFixed(4);
    chars($('c3h'), t, 26.5, 999, { stagger: 0.04, y: 22, blur: 10 });
    const dim = P(t, 31.5, 0.8);
    show($('p3a'), t, 28.5, 999, { x: -30, y: 0, blur: 8, alpha: 1 - 0.45 * dim });
    show($('p3b'), t, 30.0, 999, { x: 30, y: 0, blur: 8, scale: 0.96 });
    show($('c3f'), t, 34.0, 999, { y: 14, blur: 8 });
  });

  /* ------------------------------------------- C4: four practice areas */
  const CARDS = ['v1', 'v2', 'v3', 'v4'], CARD_T = [42.0, 45.0, 48.0, 51.0];
  film.scene('c4', 37.8, 62.4, (lt, t) => {
    const w = P(t, 37.8, 0.9, E.inOutQuart);
    $('c4').style.clipPath = w < 1 ? `inset(${((1 - w) * 100).toFixed(3)}% 0 0 0)` : 'none';
    $('c4').style.opacity = env(t, 37.8, 62.4, 0, 0.6).toFixed(4);
    show($('c4eb'), t, 38.5, 999, { y: 10 });
    chars($('c4h'), t, 38.8, 999, { stagger: 0.04, y: 20, blur: 10 });
    CARDS.forEach((id, i) => {
      const t0 = CARD_T[i], el = $(id);
      // lifts while it is being introduced, settles once the next card arrives
      const next = CARD_T[i + 1] ?? 54.0;
      const lift = P(t, t0, 0.6, E.outCubic) * (1 - P(t, next, 0.6, E.inOutSine));
      show(el, t, t0, 999, { y: 40, blur: 8, fin: 1.0 });
      if (t >= t0) el.style.transform = `translate3d(0,${(-14 * lift + (1 - P(t, t0, 1.0, E.outQuart)) * 40).toFixed(2)}px,0)`;
      el.style.boxShadow = `0 ${(16 + 14 * lift).toFixed(1)}px ${(40 + 30 * lift).toFixed(1)}px rgba(16,30,48,${(0.07 + 0.08 * lift).toFixed(3)})`;
      const hl = el.querySelector('.hl');
      hl.style.transform = `scaleX(${P(t, t0 + 0.2, 0.8, E.inOutCubic).toFixed(4)})`;
      drawIcons(el, t, t0 + 0.2, 1.1);
    });
    show($('c4n'), t, 54.0, 999, { y: 8 });
  });

  /* ------------------------------------------------ C5: the standard */
  film.scene('c5', 61.8, 80.4, (lt, t) => {
    $('c5').style.opacity = env(t, 61.8, 80.4, 0.6, 0.6).toFixed(4);
    show($('c5eb'), t, 62.5, 999, { y: 10 });
    chars($('c5h'), t, 62.8, 999, { stagger: 0.045, y: 22, blur: 10 });
    draw($('c5line').querySelector('path'), t, 66.0, 5.0, E.inOutSine);
    ['d1', 'd2', 'd3'].forEach((id, i) => {
      const t0 = 66.0 + i * 2.0;
      show($(id), t, t0, 999, { y: 30, blur: 8, fin: 1.0 });
      drawIcons($(id), t, t0 + 0.2, 1.1);
    });
  });

  /* ---------------------------------------------------- C6: people */
  film.scene('c6', 79.8, 96.4, (lt, t) => {
    const w = P(t, 79.8, 0.9, E.inOutQuart);
    $('c6').style.clipPath = w < 1 ? `inset(0 ${((1 - w) * 100).toFixed(3)}% 0 0)` : 'none';
    $('c6').style.opacity = env(t, 79.8, 96.4, 0, 0.6).toFixed(4);
    show($('c6eb'), t, 80.5, 999, { y: 10 });
    chars($('c6h'), t, 80.8, 999, { stagger: 0.045, y: 20, blur: 10 });
    show($('m1'), t, 83.0, 999, { x: -40, y: 0, blur: 8, fin: 1.1 });
    show($('m2'), t, 85.0, 999, { x: 40, y: 0, blur: 8, fin: 1.1 });
  });

  /* ---------------------------------------------------- C7: region */
  const ns = 'http://www.w3.org/2000/svg';
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
  // positions projected from longitude/latitude (lon 128.55–129.45 → x 40–780, lat 35.62–35.05 → y 60–740)
  const proj = (lon, lat) => [40 + ((lon - 128.55) / 0.9) * 740, 60 + ((35.62 - lat) / 0.57) * 680];
  const HQ = proj(129.075, 35.18);
  const CITIES = [
    ['양산', proj(129.037, 35.335), [18, -14]],
    ['김해', proj(128.889, 35.228), [-18, -22, 'end']],
    ['울산', proj(129.311, 35.539), [22, 10]],
    ['창원', proj(128.681, 35.228), [-18, -22, 'end']],
  ];
  const map = {};
  function buildMap() {
    const svg = $('map');
    const grid = mk('g', {}, svg);
    for (let x = 40; x <= 780; x += 74) mk('line', { x1: x, y1: 40, x2: x, y2: 760, class: 'grid' }, grid);
    for (let y = 40; y <= 760; y += 72) mk('line', { x1: 20, y1: y, x2: 800, y2: y, class: 'grid' }, grid);
    map.grid = grid;
    map.links = []; map.cities = [];
    CITIES.forEach(([name, [x, y], [dx, dy, anchor]]) => {
      const mx = (HQ[0] + x) / 2 + (y - HQ[1]) * 0.12, my = (HQ[1] + y) / 2 - (x - HQ[0]) * 0.12;
      map.links.push(mk('path', { d: `M${HQ[0]} ${HQ[1]}Q${mx.toFixed(1)} ${my.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)}`, class: 'link', pathLength: 1 }, svg));
      const g = mk('g', { opacity: 0 }, svg);
      mk('circle', { cx: x, cy: y, r: 9, class: 'city' }, g);
      const tx = mk('text', { x: x + dx, y: y + dy, 'text-anchor': anchor || 'start' }, g);
      tx.textContent = name;
      map.cities.push(g);
    });
    map.rings = [0, 1, 2].map(() => mk('circle', { cx: HQ[0], cy: HQ[1], r: 0, class: 'ring', opacity: 0 }, svg));
    const hq = mk('g', { opacity: 0 }, svg);
    mk('circle', { cx: HQ[0], cy: HQ[1], r: 15, class: 'hq' }, hq);
    mk('circle', { cx: HQ[0], cy: HQ[1], r: 6, fill: '#fff' }, hq);
    const t1 = mk('text', { x: HQ[0] + 30, y: HQ[1] + 14, class: 'hqt' }, hq); t1.textContent = '부산';
    const t2 = mk('text', { x: HQ[0] + 32, y: HQ[1] + 50, class: 'sub' }, hq); t2.textContent = '연제구 · 더함';
    map.hq = hq;
    const all = mk('text', { x: 40, y: 770, class: 'sub', opacity: 0 }, svg); all.textContent = '경남 전역 상담 안내';
    map.all = all;
  }
  film.scene('c7', 95.8, 106.4, (lt, t) => {
    $('c7').style.opacity = env(t, 95.8, 106.4, 0.6, 0.6).toFixed(4);
    show($('c7eb'), t, 96.5, 999, { y: 10 });
    chars($('c7h'), t, 96.8, 999, { stagger: 0.05, y: 22, blur: 10 });
    show($('c7s'), t, 98.5, 999, { y: 12, blur: 6 });
    map.grid.style.opacity = P(t, 96.5, 1.2).toFixed(3);
    map.hq.setAttribute('opacity', P(t, 98.0, 0.5).toFixed(3));
    map.rings.forEach((r, i) => {
      const u = ((t - 98.0 - i * 0.7) % 2.1 + 2.1) % 2.1, on = t >= 98.0 + i * 0.7;
      r.setAttribute('r', on ? (18 + u * 70).toFixed(1) : 0);
      r.setAttribute('opacity', on ? (0.7 * (1 - u / 2.1)).toFixed(3) : 0);
    });
    CITIES.forEach((_, i) => {
      const t0 = 99.0 + i * 0.5;
      draw(map.links[i], t, t0, 0.8, E.outCubic);
      map.cities[i].setAttribute('opacity', P(t, t0 + 0.5, 0.5).toFixed(3));
    });
    map.all.setAttribute('opacity', P(t, 101.5, 0.8).toFixed(3));
  });

  /* ------------------------------------------- C8: brand + end card */
  const logo = {};
  function loadLogo() {
    return fetch('../common/logo-outline.svg').then((r) => r.text()).then((svgText) => {
      const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
      const g = doc.querySelector('g');
      g.querySelectorAll('path').forEach((p) => p.setAttribute('pathLength', '1'));
      $('logoLines').appendChild(document.importNode(g, true));
      logo.paths = [...$('logoLines').querySelectorAll('path')];
      logo.paths.forEach((p) => (p.style.strokeWidth = '80'));
    });
  }
  film.scene('c8', 105.8, 122.0, (lt, t) => {
    $('c8').style.opacity = env(t, 105.8, 999, 0.6, 0).toFixed(4);
    show($('c8a'), t, 106.5, 109.6, { y: 16, blur: 10 });
    chars($('c8b'), t, 107.2, 109.6, { stagger: 0.05, y: 22, blur: 10 });
    const on = t >= 110.0;
    $('logoWrap').style.opacity = on ? 1 : 0;
    if (on) {
      logo.paths.forEach((p, i) => draw(p, t, 110.0 + i * 0.07, 1.3, E.inOutCubic));
      $('logoLines').style.opacity = (1 - P(t, 111.4, 0.8)).toFixed(3);
      const fill = P(t, 110.7, 1.0, E.inOutSine);
      setStyle($('logoImg'), { opacity: fill, filter: blurCss((1 - fill) * 6) });
    }
    show($('c8n'), t, 111.0, 999, { y: 14, blur: 8 });
    show($('c8m'), t, 111.6, 999, { y: 10 });
    ['ct1', 'ct2', 'ctq'].forEach((id, i) => show($(id), t, 112.5 + i * 0.4, 999, { y: 24, blur: 6, fin: 0.9 }));
    show($('c8i'), t, 114.0, 999, { y: 8 });
    show($('legal'), t, 114.5, 999, { y: 8, fin: 1.2 });
  });

  M.boot(film, async () => {
    buildMap();
    await loadLogo();
  });
})();
