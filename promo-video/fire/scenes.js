/*
 * 더함화재특종손해사정 브랜드 필름 (화재) — 144 s @ 30 fps
 *
 *   0–16   S1 cold open: the fire, text burns into embers
 *  16–28   S2 the insurer's notice → "그대로 받으시겠습니까?"
 *  28–44   S3 what 손해사정 is (dictionary entry + 3 steps)
 *  44–60   S4 who adjusts? balance scale → independent adjuster
 *  60–80   S6 why fire is different: building section + 8 loss items
 *  80–96   S7 the expert: 유승민, credentials
 *  96–112  S8 process 01–04
 * 112–120  S9 timing: the earlier the better
 * 120–144  S10 brand line → logo reveal → end card
 */
(() => {
  const { E, P, env, show, chars, grow, draw, setStyle, lerp, clamp, spring, blurCss } = M;
  const $ = (id) => document.getElementById(id);
  const film = new M.Film({ duration: 144, fps: 30 });
  M.fitStage($('stage'));

  /* ------------------------------------------------ global canvas layers */
  const back = $('fxBack'), bctx = back.getContext('2d');
  const front = $('fxFront'), fctx = front.getContext('2d');
  const embers = new FX.Embers({ count: 280, seed: 7 });
  const smoke = new FX.Smoke({ count: 16, seed: 3, alpha: 0.075 });
  const serif76 = '300 76px "Noto Serif CJK KR"';
  const burn1 = new FX.BurnText({ lines: [{ text: '평생을 일궈 온 공간이', x: 960, y: 500, font: serif76 }], burnStart: 10.0, sweep: 1.9, seed: 11 });
  const burn2 = new FX.BurnText({ lines: [{ text: '한순간, 재가 되었습니다.', x: 960, y: 628, font: serif76 }], burnStart: 10.5, sweep: 2.0, seed: 12 });

  function fireGlow(ctx, t, k) {
    if (k <= 0.002) return;
    const f = 0.78 + 0.22 * FX.noise1(t * 1.7, 5) + 0.06 * Math.sin(t * 9.1) * FX.noise1(t * 3.3, 6);
    const g = ctx.createRadialGradient(960, 1260, 60, 960, 1260, 1150);
    g.addColorStop(0, `rgba(255,122,40,${(0.55 * k * f).toFixed(4)})`);
    g.addColorStop(0.35, `rgba(196,68,18,${(0.22 * k * f).toFixed(4)})`);
    g.addColorStop(0.7, `rgba(90,26,10,${(0.08 * k * f).toFixed(4)})`);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 1920, 1080);
  }

  film.layer((t) => {
    bctx.setTransform(1, 0, 0, 1, 0, 0);
    bctx.clearRect(0, 0, 1920, 1080);
    const k1 = env(t, 0.0, 16.0, 3.5, 2.6, E.inOutSine, E.inOutSine);
    const k6 = env(t, 60.0, 80.0, 2.0, 1.2) * 0.3;
    const k9 = env(t, 112.0, 120.2, 1.6, 1.0) * 0.5;
    const push = t < 16.5 ? 1 + 0.05 * E.inOutSine(clamp(t / 16)) : 1;
    const tr = push !== 1 ? `scale(${push.toFixed(5)})` : '';
    if (back.style.transform !== tr) back.style.transform = tr;
    fireGlow(bctx, t, k1 + k9 * 0.6 + k6 * 0.5);
    smoke.draw(bctx, t, k1 + k9 * 0.7);
    embers.draw(bctx, t, k1 + k6 + k9);

    fctx.clearRect(0, 0, 1920, 1080);
    if (t < 16) {
      const a1 = P(t, 1.8, 2.4, E.outCubic), a2 = P(t, 5.0, 2.4, E.outCubic);
      burn1.draw(fctx, t, a1, (1 - a1) * 16);
      burn2.draw(fctx, t, a2, (1 - a2) * 16);
    }
    const fade = Math.max(1 - P(t, 0, 0.8, E.outQuad), P(t, 142.6, 1.4, E.inOutSine));
    setStyle($('fade'), { opacity: fade });
  });

  /* ------------------------------------------------------ S2 the offer */
  const doc = $('doc'), bars = [...doc.querySelectorAll('.bar')];
  film.scene('s2', 15.6, 28.3, (lt, t) => {
    const T = t - 16;
    $('s2').style.opacity = env(t, 15.6, 28.3, 0.7, 0.7).toFixed(4);
    const din = P(T, 0.2, 1.7, E.outQuart), ddim = P(T, 5.2, 1.2, E.inOutCubic);
    setStyle(doc, {
      opacity: din * (1 - 0.74 * ddim),
      transform: `translate3d(0,${((1 - din) * 90).toFixed(2)}px,0) rotate(${lerp(-5, -2.5, din).toFixed(3)}deg) scale(${(1 - 0.05 * ddim).toFixed(4)})`,
      filter: blurCss((1 - din) * 8 + ddim * 5),
    });
    bars.forEach((b, i) => { b.style.width = (b.dataset.w * P(T, 1.2 + i * 0.28, 0.7, E.outCubic)).toFixed(1) + 'px'; });
    const sp = P(T, 2.72, 0.28, E.inQuad);
    setStyle($('stamp'), { opacity: sp * 0.95, transform: `rotate(-14deg) scale(${lerp(1.7, 1, sp).toFixed(4)})` });
    show($('s2a'), T, 0.9, 5.2, { y: 16 });
    show($('s2b'), T, 1.4, 5.2, { y: 22, blur: 12 });
    show($('s2c'), T, 5.4, 11.8, { y: 20, blur: 10 });
    chars($('s2d'), T, 6.0, 11.8, { stagger: 0.05, y: 26, blur: 12, fin: 1.0 });
  });

  /* ------------------------------------------------- S3 definition */
  film.scene('s3', 28.0, 44.5, (lt, t) => {
    const T = t - 28;
    const w = P(T, 0, 1.0, E.inOutQuart);
    $('s3').style.clipPath = w < 1 ? `inset(${((1 - w) * 100).toFixed(3)}% 0 0 0)` : 'none';
    show($('s3-eb'), T, 0.9, 9.3, { y: 12, blur: 4 });
    chars($('s3w'), T, 1.1, 9.3, { stagger: 0.09, y: 30, blur: 14, fin: 1.1 });
    show($('s3h'), T, 1.8, 9.3, { y: 16 });
    grow($('s3r'), T, 2.2, 1.0, 9.3);
    show($('s3d'), T, 2.6, 9.3, { y: 18, blur: 8 });
    ['st1', 'st2', 'st3'].forEach((id, i) => show($(id), T, 4.5 + i * 1.0, 9.3, { x: 40, y: 0, blur: 6 }));
    chars($('s3i'), T, 10.0, 15.9, { stagger: 0.035, y: 22, blur: 10 });
    grow($('s3u'), T, 11.0, 0.9, 15.9);
  });

  /* ----------------------------------------------------- S4 the scale */
  const PIV = { x: 550, y: 96 }, HALF = 380, LAND1 = 4.5, LAND2 = 11.5, TILT = -0.16;
  const scalePaths = ['scBase', 'scFoot', 'scPost', 'scTop', 'scBeam'].map($);
  const panPaths = [...$('panL').querySelectorAll('path'), ...$('panR').querySelectorAll('path')];
  const beamAngle = (T) => {
    if (T < LAND1) return 0;
    if (T < LAND2) return spring(T, LAND1, 0, TILT, 1.1, 3.2);
    return spring(T, LAND2, spring(LAND2, LAND1, 0, TILT, 1.1, 3.2), 0, 1.0, 3.0);
  };
  function weight(el, T, land) {
    const p = P(T, land - 0.55, 0.55, E.inQuad);
    el.setAttribute('transform', `translate(0 ${(-440 * (1 - p)).toFixed(1)})`);
    el.style.opacity = T < land - 0.55 ? 0 : Math.min(1, p * 2.5).toFixed(3);
  }
  film.scene('s4', 43.8, 60.4, (lt, t) => {
    const T = t - 44;
    $('s4').style.opacity = env(t, 43.8, 60.4, 0.7, 0.6).toFixed(4);
    show($('s4q1'), T, 0.3, 3.4, { y: 20, blur: 10 });
    show($('s4a1'), T, 3.6, 7.4, { y: 20, blur: 10 });
    show($('s4q2'), T, 7.6, 10.9, { y: 20, blur: 10 });
    show($('s4a2'), T, 11.4, 15.7, { y: 20, blur: 10 });
    show($('s4s'), T, 12.2, 15.7, { y: 12, blur: 6 });
    scalePaths.forEach((p, i) => draw(p, T, 0.7 + i * 0.22, 1.2));
    panPaths.forEach((p, i) => draw(p, T, 1.5 + (i % 2) * 0.3, 1.1));
    const lbl = P(T, 2.2, 0.8);
    document.querySelectorAll('#scale .lbl').forEach((l) => (l.style.opacity = lbl.toFixed(3)));
    const th = beamAngle(T);
    $('beam').setAttribute('transform', `rotate(${((th * 180) / Math.PI).toFixed(3)} ${PIV.x} ${PIV.y})`);
    $('panL').setAttribute('transform', `translate(${(PIV.x - HALF * Math.cos(th)).toFixed(2)} ${(PIV.y - HALF * Math.sin(th)).toFixed(2)})`);
    $('panR').setAttribute('transform', `translate(${(PIV.x + HALF * Math.cos(th)).toFixed(2)} ${(PIV.y + HALF * Math.sin(th)).toFixed(2)})`);
    weight($('wL'), T, LAND1);
    weight($('wR'), T, LAND2);
  });

  /* ------------------------------------------ S6 building + loss items */
  const R = (x, y, w, h) => `M${x} ${y}h${w}v${h}h${-w}z`;
  const circ = (x, y, r) => `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
  function stairs(x, y, n, rise, run) { let d = `M${x} ${y}`; for (let i = 0; i < n; i++) d += `v${-rise}h${run}`; return d; }
  function boxes() {
    const r = FX.rng(21), out = [];
    for (const [y, hmax] of [[640, 46], [590, 40], [540, 40], [490, 30]]) {
      let x = 478;
      while (x < 700) {
        const w = 26 + Math.floor(r() * 34), h = 18 + Math.floor(r() * (hmax - 18));
        if (x + w > 714) break;
        out.push(R(x, y - h, w, h));
        x += w + 4 + Math.floor(r() * 8);
      }
    }
    return out;
  }
  function sootLines() { const o = []; for (let x = 150; x < 720; x += 18) o.push(`M${x} 88l-26 44`); return o; }
  const GROUPS = {
    site: ['M0 640H1000'],
    struct: [R(100, 80, 16, 560), R(744, 80, 16, 560), R(423, 92, 14, 548), R(100, 434, 660, 12), R(100, 246, 660, 12), R(92, 68, 676, 14), R(92, 44, 12, 24), R(756, 44, 12, 24), 'M86 640V672H774V640', stairs(130, 640, 10, 19.4, 20), 'M330 434' + 'v-17.6h-20'.repeat(10)],
    finish: ['M116 470H744', 'M116 282H744', 'M116 104H744', 'M94 84V640', 'M766 84V640', 'M116 634H744', 'M116 428H744', 'M116 240H744'],
    mep: [R(134, 500, 44, 70), 'M142 516H170M142 532H170M142 548H170', 'M156 500V484H720', R(300, 288, 360, 22), 'M360 310v12M480 310v12M600 310v12', R(540, 20, 150, 48), circ(582, 44, 14), circ(648, 44, 14), 'M140 118H720M240 118v8M420 118v8M600 118v8'],
    furn: [R(452, 330, 50, 104), 'M452 364H502M452 398H502', 'M528 372H680M536 372V434M672 372V434', R(574, 326, 62, 40), 'M605 366V372', 'M694 398H730M728 398V352M700 398V434M724 398V434', R(470, 214, 170, 32), R(470, 186, 24, 28), R(150, 150, 60, 96), 'M150 182H210M150 214H210'],
    stock: ['M470 640V488M720 640V488', 'M470 590H720M470 540H720M470 490H720', ...boxes()],
    soot: [...sootLines(), 'M300 446v34M322 446v20M548 446v28', 'M262 638q40 -9 84 0M520 638q30 -7 60 0'],
    debris: ['M772 640L784 622L798 628L806 610L822 618L836 604L850 620L862 614L874 640', 'M790 640L796 630L806 636M828 640L838 626L846 640'],
    neigh: ['M880 640V262H1000', 'M880 250H1000', R(910, 300, 40, 52), R(910, 420, 40, 52), R(910, 540, 40, 52)],
  };
  const DIMS = [
    'M48 640V82', 'M40 648L56 632M40 454L56 438M40 266L56 250M40 90L56 74',
    'M100 690H760', 'M92 698L108 682M422 698L438 682M752 698L768 682',
  ];
  const ITEMS = [
    ['건물 구조체', 'struct'], ['내·외장 마감재', 'finish'], ['전기·기계 설비', 'mep'], ['집기·비품', 'furn'],
    ['재고자산', 'stock'], ['그을음·소화수 피해', 'soot'], ['잔존물 제거', 'debris'], ['인접 건물 피해', 'neigh', '배상책임'],
  ];
  const DRAW_AT = { site: [0.9, 1.2], struct: [1.2, 2.2], finish: [2.4, 1.4], mep: [2.8, 1.4], furn: [3.2, 1.4], stock: [3.4, 1.5], soot: [3.9, 1.2], debris: [4.0, 1.0], neigh: [4.2, 1.2] };
  const bp = { paths: [], hot: [], heat: [], dims: [], texts: [], rows: [] };
  function buildS6() {
    const svg = $('bldg');
    $('s6').style.display = 'block';
    const ns = 'http://www.w3.org/2000/svg';
    const mk = (tag, attrs, parent) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
    const defs = mk('defs', {}, svg);
    const f = mk('filter', { id: 'glow', x: '-30%', y: '-30%', width: '160%', height: '160%' }, defs);
    mk('feGaussianBlur', { stdDeviation: '3.2', result: 'b' }, f);
    const fm = mk('feMerge', {}, f); mk('feMergeNode', { in: 'b' }, fm); mk('feMergeNode', { in: 'b' }, fm); mk('feMergeNode', { in: 'SourceGraphic' }, fm);
    const rg = mk('radialGradient', { id: 'heatGrad' }, defs);
    mk('stop', { offset: '0', 'stop-color': 'rgba(255,120,40,0.55)' }, rg);
    mk('stop', { offset: '0.6', 'stop-color': 'rgba(200,60,15,0.18)' }, rg);
    mk('stop', { offset: '1', 'stop-color': 'rgba(120,30,10,0)' }, rg);
    const heatLayer = mk('g', { class: 'heat' }, svg);
    for (const [g, list] of Object.entries(GROUPS)) {
      const grp = mk('g', { id: 'g-' + g }, svg);
      list.forEach((d, i) => bp.paths.push({ g, i, n: list.length, el: mk('path', { d, class: g === 'soot' || g === 'finish' ? 'bp soft' : 'bp', pathLength: 1 }, grp) }));
    }
    DIMS.forEach((d) => bp.dims.push(mk('path', { d, class: 'dim', pathLength: 1 }, svg)));
    [['4,000', 34, 543], ['3,800', 34, 352], ['3,400', 34, 166]].forEach(([s, x, y]) => {
      bp.texts.push(mk('text', { class: 'dimt', x, y, transform: `rotate(-90 ${x} ${y})`, 'text-anchor': 'middle' }, svg));
      bp.texts[bp.texts.length - 1].textContent = s;
    });
    [['6,600', 265, 676], ['6,600', 595, 676]].forEach(([s, x, y]) => {
      const e = mk('text', { class: 'dimt', x, y, 'text-anchor': 'middle' }, svg); e.textContent = s; bp.texts.push(e);
    });
    const hotLayer = mk('g', {}, svg);
    ITEMS.forEach(([, g]) => {
      const src = $('g-' + g), bb = src.getBBox();
      bp.heat.push(mk('ellipse', { cx: bb.x + bb.width / 2, cy: bb.y + bb.height / 2, rx: bb.width / 2 + 60, ry: bb.height / 2 + 50, fill: 'url(#heatGrad)', opacity: 0 }, heatLayer));
      const hg = mk('g', { class: 'hot', opacity: 0 }, hotLayer);
      GROUPS[g].forEach((d) => mk('path', { d }, hg));
      bp.hot.push(hg);
    });
    const list = $('list6');
    ITEMS.forEach(([label, , small], i) => {
      const row = document.createElement('div');
      row.className = 'li6';
      row.innerHTML = `<svg width="34" height="34" viewBox="0 0 34 34"><rect class="box" x="1" y="1" width="32" height="32" rx="4"/><path class="ck" pathLength="1" d="M8 17.5 L14.5 24 L27 10"/></svg>` +
        `<span class="n">${String(i + 1).padStart(2, '0')}</span><span class="tx">${label}${small ? `<small>${small}</small>` : ''}</span>`;
      list.appendChild(row);
      bp.rows.push({ row, ck: row.querySelector('.ck') });
    });
    $('s6').style.display = 'none';
  }
  film.scene('s6', 59.6, 80.3, (lt, t) => {
    const T = t - 60;
    $('s6').style.opacity = env(t, 59.6, 80.3, 0.8, 0.7).toFixed(4);
    show($('s6eb'), T, 0.3, 99, { y: 10 });
    chars($('s6t'), T, 0.5, 99, { stagger: 0.05, y: 20, blur: 10 });
    show($('s6s'), T, 1.9, 99, { y: 12, blur: 6 });
    for (const p of bp.paths) {
      const [t0, d] = DRAW_AT[p.g];
      draw(p.el, T, t0 + (p.i / p.n) * d * 0.6, d, E.inOutCubic);
    }
    bp.dims.forEach((p, i) => draw(p, T, 1.0 + i * 0.15, 1.2));
    bp.texts.forEach((e) => (e.style.opacity = P(T, 2.0, 0.8).toFixed(3)));
    const cam = 1 + 0.035 * E.inOutSine(clamp(T / 20));
    $('bldg').style.transform = `scale(${cam.toFixed(5)})`;
    ITEMS.forEach((_, i) => {
      const t0 = 6.0 + i * 0.5;
      show(bp.rows[i].row, T, t0, 99, { x: 24, y: 0, blur: 5, fin: 0.6 });
      draw(bp.rows[i].ck, T, t0 + 0.12, 0.35, E.outCubic);
      const h = P(T, t0, 0.5, E.outCubic);
      const flick = 0.85 + 0.15 * FX.noise1(T * 3 + i * 5, 40 + i);
      bp.hot[i].setAttribute('opacity', (h * flick * 0.95).toFixed(3));
      bp.heat[i].setAttribute('opacity', (h * flick * 0.8).toFixed(3));
    });
    $('s6dim').style.opacity = P(T, 10.4, 0.9, E.inOutSine).toFixed(3);
    show($('s6b1'), T, 11.0, 14.8, { y: 22, blur: 12 });
    show($('s6b2'), T, 15.0, 19.7, { y: 22, blur: 12 });
  });

  /* ------------------------------------------------------ S7 the expert */
  const credIds = ['c1', 'c2', 'c3', 'c4'];
  film.scene('s7', 79.8, 96.3, (lt, t) => {
    const T = t - 80;
    $('s7').style.opacity = env(t, 79.8, 96.3, 0.8, 0.6).toFixed(4);
    $('s7wm').style.transform = `translate3d(${(-20 * T).toFixed(2)}px,0,0) scale(${(1 + 0.004 * T).toFixed(4)})`;
    chars($('s7h'), T, 0.4, 4.0, { stagger: 0.04, y: 22, blur: 10 });
    show($('s7role'), T, 4.3, 15.7, { y: 12 });
    show($('s7nm'), T, 4.5, 15.7, { y: 0, blur: 14, ls: 0.6, lsTo: 0.2, fin: 1.4 });
    grow($('s7rule'), T, 5.0, 1.0, 15.7);
    show($('s7lic'), T, 5.3, 15.7, { y: 10 });
    credIds.forEach((id, i) => {
      const t0 = 5.0 + i * 1.5;
      show($(id), T, t0, 15.7, { x: 36, y: 0, blur: 6 });
      $(id).querySelectorAll('path').forEach((p) => draw(p, T, t0 + 0.1, 1.2));
    });
    show($('s7f'), T, 11.4, 15.7, { y: 14, blur: 8 });
  });

  /* ------------------------------------------------------ S8 process */
  const STEP_T = [2.0, 4.0, 6.0, 8.0];
  film.scene('s8', 96.0, 112.4, (lt, t) => {
    const T = t - 96;
    const w = P(T, 0, 1.0, E.inOutQuart);
    $('s8').style.clipPath = w < 1 ? `inset(${((1 - w) * 100).toFixed(3)}% 0 0 0)` : 'none';
    $('s8').style.opacity = env(t, 96.0, 112.4, 0, 0.6).toFixed(4);
    show($('s8eb'), T, 0.5, 99, { y: 10 });
    chars($('s8t'), T, 0.6, 99, { stagger: 0.035, y: 20, blur: 10 });
    grow($('s8track'), T, 1.4, 1.2, 99);
    let fp = 0;
    for (let i = 1; i < 4; i++) fp += P(T, STEP_T[i] - 0.9, 0.9, E.inOutCubic) / 3;
    $('s8fill').style.transform = `scaleX(${fp.toFixed(4)})`;
    $('s8fill').style.opacity = T > STEP_T[0] ? 1 : 0;
    ['p1', 'p2', 'p3', 'p4'].forEach((id, i) => {
      const el = $(id), t0 = STEP_T[i];
      show(el.querySelector('.num'), T, t0, 99, { y: 30, blur: 10 });
      const np = P(T, t0 + 0.05, 0.5, E.outBack);
      setStyle(el.querySelector('.node'), { opacity: T < t0 ? 0 : Math.min(1, np * 2), transform: `scale(${Math.max(0, np).toFixed(4)})` });
      show(el.querySelector('.tt'), T, t0 + 0.2, 99, { y: 16 });
      show(el.querySelector('.dd'), T, t0 + 0.4, 99, { y: 12 });
    });
    show($('s8f'), T, 11.0, 99, { y: 12 });
  });

  /* -------------------------------------------------------- S9 timing */
  function buildRing() {
    const g = $('ticks'), ns = 'http://www.w3.org/2000/svg';
    for (let i = 0; i < 60; i++) {
      const a = (i / 60) * Math.PI * 2, r0 = i % 5 === 0 ? 346 : 352, r1 = 362;
      const l = document.createElementNS(ns, 'line');
      l.setAttribute('x1', 400 + r0 * Math.sin(a)); l.setAttribute('y1', 400 - r0 * Math.cos(a));
      l.setAttribute('x2', 400 + r1 * Math.sin(a)); l.setAttribute('y2', 400 - r1 * Math.cos(a));
      g.appendChild(l);
    }
  }
  film.scene('s9', 111.8, 120.4, (lt, t) => {
    const T = t - 112;
    $('s9').style.opacity = env(t, 111.8, 120.4, 0.7, 0.6).toFixed(4);
    draw($('ringArc'), T, 0.3, 7.6, E.inOutSine);
    $('ticks').style.opacity = P(T, 0.2, 1.2).toFixed(3);
    $('ring').style.transform = `scale(${(1 + 0.012 * T).toFixed(4)})`;
    chars($('s9a'), T, 0.5, 7.7, { stagger: 0.045, y: 20, blur: 10 });
    show($('s9b'), T, 2.5, 7.7, { y: 14, blur: 8 });
  });

  /* ------------------------------------------- S10 brand + end card */
  const m = {};
  function measureS10() {
    const s = $('stage').getBoundingClientRect();
    const sc = s.width / 1920;
    const rel = (el) => { const r = el.getBoundingClientRect(); return { x: (r.left - s.left) / sc, y: (r.top - s.top) / sc, w: r.width / sc, h: r.height / sc }; };
    const scene = $('s10'), prev = scene.style.display;
    scene.style.display = 'block';
    const b2 = rel($('s10b2')), line = rel($('s10b'));
    m.start = { x: b2.x, y: line.y };
    m.startW = b2.w;
    const rest = $('s10nB');
    m.restW = rest.scrollWidth;
    rest.style.maxWidth = '0px';
    const a = rel($('s10nA')), n = rel($('s10n'));
    m.name = { x: a.x, y: n.y };
    rest.style.maxWidth = '';
    scene.style.display = prev;
    const lines = $('logoLines');
    return fetch('../common/logo-outline.svg').then((r) => r.text()).then((svgText) => {
      const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
      const g = doc.querySelector('g');
      g.querySelectorAll('path').forEach((p) => p.setAttribute('pathLength', '1'));
      lines.appendChild(document.importNode(g, true));
      m.logoPaths = [...lines.querySelectorAll('path')];
      m.logoPaths.forEach((p) => (p.style.strokeWidth = '64'));
    });
  }
  film.scene('s10', 119.6, 144.0, (lt, t) => {
    const T = t - 120;
    $('s10').style.opacity = env(t, 119.6, 200, 0.8, 0).toFixed(4);
    // tagline
    show($('s10a'), T, 0.5, 4.9, { y: 18, blur: 10, fout: 0.8 });
    const lineIn = P(T, 1.5, 1.1, E.outQuart);
    const morph = T >= 4.5;
    setStyle($('s10b'), { opacity: T < 1.5 ? 0 : lineIn, transform: `translate3d(0,${((1 - lineIn) * 22).toFixed(2)}px,0)`, filter: blurCss((1 - lineIn) * 12) });
    const fadeSide = P(T, 4.3, 0.8, E.inQuad);
    setStyle($('s10b1'), { opacity: 1 - fadeSide, filter: blurCss(fadeSide * 8) });
    setStyle($('s10b3'), { opacity: 1 - fadeSide, filter: blurCss(fadeSide * 8) });
    $('s10b2').style.visibility = morph ? 'hidden' : 'visible';
    // "더하" → "더함", then glides into the brand name
    const mv = $('s10m');
    if (!morph || T > 7.2) {
      if (mv.style.display !== 'none') mv.style.display = 'none';
    } else {
      mv.style.display = 'block';
      const toC = P(T, 4.5, 1.2, E.inOutCubic);
      const cx = 960 - m.startW / 2;
      const x1 = lerp(m.start.x, cx, toC), y1 = m.start.y;
      const toN = P(T, 5.9, 1.3, E.inOutCubic);
      const s = lerp(1, 64 / 96, toN);
      const x = lerp(x1, m.name.x, toN), y = lerp(y1, m.name.y, toN);
      mv.style.left = '0px'; mv.style.top = '0px';
      mv.style.transformOrigin = '0 0';
      mv.style.transform = `translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0) scale(${s.toFixed(5)})`;
      const hm = P(T, 5.0, 0.7, E.inOutSine);
      setStyle($('s10ha'), { opacity: 1 - hm, filter: blurCss(hm * 6) });
      setStyle($('s10hm'), { opacity: hm, filter: blurCss((1 - hm) * 6) });
      mv.style.textShadow = `0 0 ${(28 * Math.sin(Math.PI * hm)).toFixed(1)}px rgba(232,208,138,0.55)`;
    }
    // brand name: "더함" + expanding "화재특종손해사정"
    const nameOn = T >= 7.2;
    const ex = P(T, 7.2, 1.3, E.inOutCubic);
    const endMove = P(T, 12.0, 1.4, E.inOutCubic);
    setStyle($('s10n'), {
      opacity: nameOn ? 1 : 0,
      transform: `translate3d(${(-440 * endMove).toFixed(2)}px,${(26 * endMove).toFixed(2)}px,0) scale(${lerp(1, 0.8, endMove).toFixed(4)})`,
    });
    $('s10nB').style.maxWidth = `${(m.restW * ex).toFixed(2)}px`;
    const edge = ex < 1 ? 'linear-gradient(90deg, #000 calc(100% - 56px), transparent)' : 'none';
    $('s10nB').style.webkitMaskImage = edge;
    $('s10nB').style.opacity = P(T, 7.4, 1.1).toFixed(3);
    // logo: outline draw → gold fill → shine
    const lw = $('logoWrap');
    const logoOn = T >= 5.9;
    setStyle(lw, {
      opacity: logoOn ? 1 : 0,
      transform: `translate3d(${(-440 * endMove).toFixed(2)}px,${(40 * endMove).toFixed(2)}px,0) scale(${lerp(1, 0.8, endMove).toFixed(4)})`,
    });
    if (logoOn) {
      m.logoPaths.forEach((p, i) => draw(p, T, 6.0 + i * 0.08, 1.7, E.inOutCubic));
      $('logoLines').style.opacity = (1 - P(T, 8.4, 0.9)).toFixed(3);
      const fill = P(T, 7.5, 1.1, E.inOutSine);
      setStyle($('logoImg'), { opacity: fill, filter: blurCss((1 - fill) * 6) });
      const sh = P(T, 8.9, 1.3, E.inOutSine);
      $('shineBar').style.transform = `translateX(${lerp(-120, 420, sh).toFixed(1)}%)`;
      $('shineBar').style.opacity = T > 8.9 && T < 10.3 ? 1 : 0;
    }
    show($('s10tag'), T, 9.0, 12.0, { y: 12, blur: 6 });
    // end card
    setStyle($('s10rep'), { opacity: P(T, 12.8, 0.9), transform: `translate3d(-440px,${(40 - 14 * P(T, 12.8, 0.9)).toFixed(2)}px,0)` });
    ['e1', 'e2', 'e3', 'e4', 'e5'].forEach((id, i) => show($(id), T, 12.6 + i * 0.25, 99, { x: 30, y: 0, blur: 6, fin: 0.9 }));
    show($('legal'), T, 13.8, 99, { y: 8, fin: 1.2 });
  });

  M.boot(film, async () => {
    buildS6();
    buildRing();
    burn1.init();
    burn2.init();
    await measureS10();
  });
})();
