/*
 * 누수 사고 손해사정사 선임권 — 76 s @ 30 fps (music at 120 BPM: every cue on a 0.5 s beat)
 *
 *   0–10    L1 a drop from the ceiling stain → "생각보다 복잡합니다"
 *  10–23    L2 apartment section: leak path + what is at stake
 *  23–36    L3 the right to appoint (보험업법 제185조 · 감독규정 제9-16조)
 *  36–53    L4 timing: who bears the adjusting cost, and when
 *  53–64    L5 what changes when you appoint
 *  64–76    L6 call to action → end card
 */
(() => {
  const { E, P, env, show, chars, grow, draw, setStyle, lerp, clamp, blurCss } = M;
  const $ = (id) => document.getElementById(id);
  const TAU = Math.PI * 2;
  const film = new M.Film({ duration: 76, fps: 30 });
  const V = !!window.VERTICAL, W = V ? 1080 : 1920, H = V ? 1920 : 1080;
  M.fitStage($('stage'), W, H);
  for (const c of [$('fxBack'), $('fxFront')]) { c.width = W; c.height = H; }

  const back = $('fxBack'), bctx = back.getContext('2d');
  const front = $('fxFront'), fctx = front.getContext('2d');

  /* ---------------------------------------------------------- caustics */
  // low-res caustic network (iterated turbulence), upscaled and screened in at low opacity
  const CW = V ? 144 : 256, CH = V ? 256 : 144;
  const cc = FX.canvas(CW, CH), cctx = cc.getContext('2d'), cimg = cctx.createImageData(CW, CH);
  function caustics(ctx, t, k) {
    if (k <= 0.002) return;
    const d = cimg.data, time = t * 0.32 + 23.0, inten = 0.005;
    for (let y = 0; y < CH; y++) for (let x = 0; x < CW; x++) {
      const px = (x / CW) * TAU * (V ? 0.95 : 1.7) - 250.0, py = (y / CH) * TAU * (V ? 1.7 : 0.95) - 250.0;
      let ix = px, iy = py, c = 1.0;
      for (let n = 0; n < 5; n++) {
        const tt = time * (1.0 - 3.5 / (n + 1));
        const nx = px + Math.cos(tt - ix) + Math.sin(tt + iy);
        const ny = py + Math.sin(tt - iy) + Math.cos(tt + ix);
        ix = nx; iy = ny;
        c += 1.0 / Math.hypot(px / (Math.sin(ix + tt) / inten), py / (Math.cos(iy + tt) / inten));
      }
      c = 1.17 - Math.pow(c / 5, 1.4);
      const v = Math.min(1, Math.pow(Math.abs(c), 8.0));
      const i = (y * CW + x) * 4;
      d[i] = 170; d[i + 1] = 215; d[i + 2] = 250; d[i + 3] = v * 255;
    }
    cctx.putImageData(cimg, 0, 0);
    ctx.save();
    ctx.globalAlpha = 0.085 * k;
    ctx.globalCompositeOperation = 'screen';
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(cc, 0, 0, W, H);
    ctx.restore();
  }

  /* ------------------------------------------------ L1: drops & stain */
  const CEIL = V ? 330 : 150, FLOOR = V ? 1560 : 880, DX = V ? 780 : 1440;
  const IMPACTS = [2.5, 4.5, 6.0, 7.0, 8.0, 8.5, 9.0, 9.5];
  const FALL = 0.5, G = (2 * (FLOOR - CEIL - 14)) / (FALL * FALL);
  const stainN = Array.from({ length: 361 }, (_, i) => FX.fbm2(Math.cos((i / 360) * TAU) * 2.2 + 5, Math.sin((i / 360) * TAU) * 2.2 + 5, 77, 4));
  function stain(ctx, t) {
    const p = P(t, 1.2, 9.5, E.outCubic);
    const rx = 540 * p, ry = rx * 0.16;
    if (rx < 2) return;
    ctx.save();
    ctx.translate(DX, CEIL);
    ctx.scale(1, ry / rx);
    ctx.beginPath();
    for (let i = 0; i <= 180; i++) {
      const ang = (i / 180) * Math.PI;
      const nv = 0.8 + 0.4 * stainN[Math.round((ang / TAU) * 360)];
      const x = Math.cos(ang) * rx * nv, y = Math.sin(ang) * rx * nv;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.closePath();
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
    g.addColorStop(0, 'rgba(110,150,195,0.34)');
    g.addColorStop(0.72, 'rgba(95,135,180,0.22)');
    g.addColorStop(1, 'rgba(120,165,210,0.42)');
    ctx.fillStyle = g;
    ctx.fill();
    ctx.restore();
  }
  function drawL1(ctx, t) {
    const k = env(t, 0, 10.6, 0.6, 0.6);
    if (k <= 0) return;
    ctx.save();
    ctx.globalAlpha = k;
    // ceiling + floor hairlines grow from the centre
    const c = P(t, 0.3, 1.4, E.inOutCubic), f = P(t, 0.6, 1.4, E.inOutCubic);
    ctx.strokeStyle = 'rgba(232,226,210,0.32)';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(DX - DX * c, CEIL); ctx.lineTo(DX + (W - DX) * c, CEIL); ctx.stroke();
    ctx.strokeStyle = 'rgba(232,226,210,0.16)';
    ctx.beginPath(); ctx.moveTo(DX - DX * f, FLOOR); ctx.lineTo(DX + (W - DX) * f, FLOOR); ctx.stroke();
    // crack
    const cr = P(t, 0.8, 0.6);
    if (cr > 0) {
      ctx.strokeStyle = 'rgba(232,226,210,0.45)';
      ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.moveTo(DX - 40 * cr, CEIL); ctx.lineTo(DX - 18 * cr, CEIL + 5 * cr); ctx.lineTo(DX - 4 * cr, CEIL + 2 * cr); ctx.lineTo(DX + 10 * cr, CEIL + 7 * cr); ctx.lineTo(DX + 34 * cr, CEIL + 3 * cr); ctx.stroke();
    }
    stain(ctx, t);
    // drops: hang, fall, splash
    IMPACTS.forEach((ti, i) => {
      const prev = i ? IMPACTS[i - 1] : 0.6;
      const release = ti - FALL, form = Math.max(release - Math.min(0.9, (ti - prev) * 0.85), 0.8);
      if (t >= form && t < release) {
        const g = P(t, form, release - form, E.inOutSine);
        FX.drawDrop(ctx, DX, CEIL + 6 + 10 * g, 2 + 7.5 * g, 0.95);
      } else if (t >= release && t < ti) {
        const u = t - release;
        FX.drawDrop(ctx, DX, CEIL + 16 + 0.5 * G * u * u, 9.5, 0.95, 1.25);
      }
      if (t >= ti && t < ti + 3.2) {
        FX.drawRipples(ctx, t, ti, DX, FLOOR, { rings: 4, speed: 210, life: 2.9, persp: 0.16, color: '150,205,240', alpha: 0.85 });
        const a = 1 - P(t, ti, 0.45, E.outQuad);
        if (a > 0) {
          const gl = ctx.createRadialGradient(DX, FLOOR, 0, DX, FLOOR, 160);
          gl.addColorStop(0, `rgba(150,205,240,${0.28 * a})`);
          gl.addColorStop(1, 'rgba(150,205,240,0)');
          ctx.fillStyle = gl;
          ctx.fillRect(DX - 170, FLOOR - 170, 340, 340);
          for (let s = 0; s < 6; s++) {
            const ang = -Math.PI / 2 + (s - 2.5) * 0.36 + (FX.hash3(i, s, 3) - 0.5) * 0.25;
            const v0 = 190 + 150 * FX.hash3(i, s, 4), u = t - ti;
            const x = DX + Math.cos(ang) * v0 * u, y = FLOOR - 4 + Math.sin(ang) * v0 * u + 900 * u * u;
            if (y > FLOOR) continue;
            ctx.fillStyle = `rgba(190,225,250,${0.9 * a})`;
            ctx.beginPath(); ctx.arc(x, y, 2.4, 0, TAU); ctx.fill();
          }
        }
      }
    });
    ctx.restore();
  }

  film.layer((t) => {
    bctx.clearRect(0, 0, W, H);
    fctx.clearRect(0, 0, W, H);
    const k1 = env(t, 0, 10.6, 1.0, 0.6);
    caustics(bctx, t, k1 * 0.8);
    drawL1(bctx, t);
    const k3 = env(t, 23.0, 36.3, 1.0, 0.6), k5 = env(t, 53.0, 64.3, 1.0, 0.6);
    caustics(fctx, t, (k3 + k5) * 0.9);
    const fade = Math.max(1 - P(t, 0, 0.8, E.outQuad), P(t, 74.8, 1.2, E.inOutSine));
    setStyle($('fade'), { opacity: fade });
  });

  film.scene('l1', 0, 10.6, (lt, t) => {
    show($('l1t1'), t, 2.5, 5.6, { y: 18, blur: 12, fin: 1.2 });
    show($('l1t2a'), t, 6.0, 9.9, { y: 18, blur: 12 });
    show($('l1t2b'), t, 7.5, 9.9, { y: 18, blur: 12 });
  });

  /* ------------------------------------------- L2: apartment section */
  const ns = 'http://www.w3.org/2000/svg';
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
  const R = (x, y, w, h) => `M${x} ${y}h${w}v${h}h${-w}z`;
  const hatch = (x, y, w, h, step = 16) => { let d = ''; for (let i = -h; i < w; i += step) { const x0 = x + Math.max(0, i), y0 = y + (i < 0 ? -i : 0), len = Math.min(w - Math.max(0, i), h - (i < 0 ? -i : 0)); d += `M${x0} ${y0 + 0}l${len} ${len}`; } return d; };
  const apt = { lines: [], hatch: [], water: [], labels: [] };
  function buildApt() {
    const svg = $('apt');
    const defs = mk('defs', {}, svg);
    const f = mk('filter', { id: 'wglow', x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
    mk('feGaussianBlur', { stdDeviation: '2.5', result: 'b' }, f);
    const fm = mk('feMerge', {}, f); mk('feMergeNode', { in: 'b' }, fm); mk('feMergeNode', { in: 'SourceGraphic' }, fm);
    const base = mk('g', {}, svg);
    const L = (d, cls = 'ln') => apt.lines.push(mk('path', { d, class: cls, pathLength: 1 }, base));
    // slabs and walls
    [R(20, 0, 1040, 26), R(20, 290, 1040, 44), R(20, 600, 1040, 30), R(20, 26, 22, 264), R(1038, 26, 22, 264), R(20, 334, 22, 266), R(1038, 334, 22, 266)].forEach((d) => L(d));
    apt.hatch.push(mk('path', { d: hatch(20, 0, 1040, 26) + hatch(20, 290, 1040, 44) + hatch(20, 600, 1040, 30), class: 'hatch' }, base));
    // pipe in the slab
    L('M300 306H820M300 318H820');
    L('M560 312m-13 0a13 13 0 1 0 26 0a13 13 0 1 0 -26 0');
    // upper unit: bathtub, faucet, vanity
    L('M440 290V238Q440 226 452 226H688Q700 226 700 238V290M456 290V244Q456 240 460 240H680Q684 240 684 244V290');
    L('M664 226V204H692');
    L(R(760, 200, 130, 90) + 'M760 226H890');
    L(R(772, 106, 106, 72), 'ln soft');
    // lower unit: ceiling finish, wallpaper, flooring
    L('M42 352H1038', 'ln soft');
    L('M50 352V592M1030 352V592', 'ln soft');
    let planks = 'M42 592H1038';
    for (let x = 90; x < 1030; x += 64) planks += `M${x} 592v8`;
    L(planks, 'ln soft');
    // sofa, lamp, tv
    L('M120 592V522Q120 508 134 508H330Q344 508 344 522V592M136 548H328M120 560H102V540Q102 530 112 530H120M344 560H362V540Q362 530 352 530H344');
    L('M600 592V470M584 470H616L608 440H592Z');
    L(R(760, 540, 220, 52) + R(806, 424, 128, 84) + 'M870 508V540');
    const tx = (x, y, s, cls) => { const e = mk('text', { x, y, class: cls }, base); e.textContent = s; return e; };
    apt.units = [tx(58, 62, 'UPPER UNIT', 'unit'), tx(58, 392, 'LOWER UNIT', 'unit')];
    // water
    const wg = mk('g', {}, svg);
    apt.stainEl = mk('ellipse', { cx: 566, cy: 353, rx: 0, ry: 13, fill: 'rgba(47,127,184,0.28)' }, wg);
    apt.puddle = mk('ellipse', { cx: 566, cy: 591, rx: 0, ry: 6, fill: 'rgba(47,127,184,0.32)' }, wg);
    apt.water.push(mk('path', { d: 'M560 325L552 334L567 342L558 352', class: 'water', pathLength: 1 }, wg));
    apt.water.push(mk('path', { d: 'M1030 354C1024 380 1036 400 1028 426C1022 446 1034 462 1029 484', class: 'water', pathLength: 1 }, wg));
    apt.drip = mk('path', { d: 'M566 362V584', class: 'drip' }, wg);
    // labels with leader lines
    const lab = mk('g', {}, svg);
    [
      [572, 312, 300, '누수 원인', '배관 · 방수층'],
      [700, 356, 400, '천장 · 벽지', '얼룩 · 곰팡이 · 도배'],
      [934, 470, 500, '가구 · 가전', '집기 손상'],
      [930, 596, 600, '바닥재', '마루 · 장판 들뜸'],
    ].forEach(([x, y, ly, title, sub]) => {
      const g = mk('g', { opacity: 0 }, lab);
      const lead = mk('path', { d: `M${x} ${y}L1120 ${ly}H1170`, class: 'lead', pathLength: 1 }, g);
      mk('circle', { cx: x, cy: y, r: 6, class: 'dot' }, g);
      const t1 = mk('text', { x: 1186, y: ly + 8, class: 'lbl' }, g); t1.textContent = title;
      const t2 = mk('text', { x: 1188, y: ly + 42, class: 'lbs' }, g); t2.textContent = sub;
      apt.labels.push({ g, lead });
    });
  }
  film.scene('l2', 10.0, 23.4, (lt, t) => {
    const T = t;
    const w = P(T, 10.0, 0.9, E.inOutCubic);
    $('l2').style.clipPath = w < 1 ? `circle(${(w * 2400).toFixed(1)}px at ${DX}px ${FLOOR}px)` : 'none';
    $('l2').style.opacity = env(T, 10.0, 23.4, 0, 0.6).toFixed(4);
    show($('l2eb'), T, 10.7, 99, { y: 10 });
    chars($('l2t'), T, 10.9, 99, { stagger: 0.04, y: 20, blur: 10 });
    show($('l2s'), T, 12.0, 99, { y: 12, blur: 6 });
    apt.lines.forEach((p, i) => draw(p, T, 11.4 + (i / apt.lines.length) * 1.8, 1.4));
    apt.hatch.forEach((h) => (h.style.opacity = P(T, 12.6, 1.0).toFixed(3)));
    apt.units.forEach((u) => (u.style.opacity = P(T, 13.2, 0.8).toFixed(3)));
    draw(apt.water[0], T, 14.8, 0.8, E.inOutSine);
    apt.stainEl.setAttribute('rx', (170 * P(T, 15.3, 1.6, E.outCubic)).toFixed(1));
    draw(apt.water[1], T, 15.8, 1.6, E.inOutSine);
    const dr = P(T, 15.6, 0.3);
    apt.drip.style.opacity = dr.toFixed(3);
    apt.drip.style.strokeDashoffset = (-(T - 15.6) * 60).toFixed(1);
    apt.puddle.setAttribute('rx', (150 * P(T, 16.2, 1.8, E.outCubic)).toFixed(1));
    apt.labels.forEach((l, i) => {
      const t0 = 16.5 + i * 0.5;
      l.g.setAttribute('opacity', P(T, t0, 0.5).toFixed(3));
      draw(l.lead, T, t0, 0.6, E.outCubic);
    });
    show($('l2q'), T, 19.5, 99, { y: 14, blur: 8 });
  });

  /* --------------------------------------------------- L3: the right */
  film.scene('l3', 22.8, 36.4, (lt, t) => {
    $('l3').style.opacity = env(t, 22.8, 36.4, 0.6, 0.01).toFixed(4);
    show($('l3eb'), t, 23.5, 27.4, { y: 12 });
    chars($('l3h'), t, 24.0, 27.4, { stagger: 0.045, y: 26, blur: 12, fin: 1.0 });
    const law = $('law');
    show(law, t, 27.8, 32.6, { y: 30, blur: 10, fin: 1.1 });
    show(law.querySelector('.hd'), t, 28.0, 32.6, { y: 10, fout: 0.01 });
    show(law.querySelector('.bd'), t, 28.4, 32.6, { y: 14, blur: 6, fout: 0.01 });
    show(law.querySelector('.chip'), t, 29.4, 32.6, { y: 8, scale: 0.9, fout: 0.01 });
    show($('l3f'), t, 32.8, 35.9, { y: 18, blur: 10 });
  });

  /* ---------------------------------------------------- L4: timing */
  const NODES = V ? [120, 370, 660, 950] : [300, 700, 1120, 1540], LY = V ? 660 : 560;
  const TX0 = V ? 60 : 200, TX1 = V ? 1030 : 1720, ZA = NODES[2] - NODES[1], ZC = TX1 - NODES[3];
  const B7 = NODES[1] + ZA * 0.55;
  const tl = {};
  function buildTimeline() {
    const svg = $('tl');
    if (V) svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    tl.track = mk('line', { x1: TX0, y1: LY, x2: TX1, y2: LY, class: 'track', pathLength: 1 }, svg);
    tl.zoneA = mk('rect', { x: NODES[1], y: LY - 12, width: 0, height: 24, rx: 12, class: 'zoneA' }, svg);
    tl.zoneC = mk('rect', { x: NODES[3], y: LY - 12, width: 0, height: 24, rx: 12, class: 'zoneC' }, svg);
    tl.br = mk('path', { d: `M${NODES[1]} ${LY + 38}v12H${B7}v-12`, class: 'br', pathLength: 1 }, svg);
    tl.brT = mk('text', { x: (NODES[1] + B7) / 2, y: LY + 90, class: 'nlbl', style: 'font-size:26px;fill:#2F7FB8' }, svg);
    tl.brT.textContent = '접수 후 7일';
    tl.nodes = NODES.map((x) => mk('circle', { cx: x, cy: LY, r: 14, class: 'node' }, svg));
    tl.labels = ['사고 발생', '보험 접수', '보험사 조사 착수', '조사 완료'].map((s, i) => {
      const e = mk('text', { x: NODES[i], y: LY - 34, class: 'nlbl' }, svg);
      e.textContent = s;
      return e;
    });
  }
  film.scene('l4', 36.0, 53.4, (lt, t) => {
    const w = P(t, 36.0, 0.9, E.inOutQuart);
    $('l4').style.clipPath = w < 1 ? `inset(${((1 - w) * 100).toFixed(3)}% 0 0 0)` : 'none';
    $('l4').style.opacity = env(t, 36.0, 53.4, 0, 0.6).toFixed(4);
    show($('l4eb'), t, 36.7, 99, { y: 10 });
    chars($('l4t'), t, 36.9, 99, { stagger: 0.05, y: 20, blur: 10 });
    draw(tl.track, t, 38.0, 1.4, E.inOutCubic);
    tl.nodes.forEach((c, i) => {
      const p = P(t, 38.2 + i * 0.3, 0.5, E.outBack);
      c.setAttribute('r', (14 * Math.max(0, p)).toFixed(2));
      tl.labels[i].style.opacity = P(t, 38.4 + i * 0.3, 0.6).toFixed(3);
    });
    tl.zoneA.setAttribute('width', (ZA * P(t, 40.0, 0.8, E.inOutCubic)).toFixed(1));
    show($('cA'), t, 40.2, 99, { y: 24, blur: 8 });
    draw(tl.br, t, 43.5, 0.6, E.outCubic);
    tl.brT.style.opacity = P(t, 43.7, 0.5).toFixed(3);
    show($('cB'), t, 43.7, 99, { y: -20, blur: 8 });
    tl.zoneC.setAttribute('width', (ZC * P(t, 47.0, 0.6, E.inOutCubic)).toFixed(1));
    show($('cC'), t, 47.2, 99, { y: 24, blur: 8 });
    show($('l4c'), t, 50.0, 99, { y: 12, blur: 8 });
  });

  /* ---------------------------------------------- L5: what changes */
  film.scene('l5', 52.8, 64.4, (lt, t) => {
    $('l5').style.opacity = env(t, 52.8, 64.4, 0.6, 0.6).toFixed(4);
    show($('l5eb'), t, 53.4, 99, { y: 10 });
    chars($('l5t'), t, 53.6, 99, { stagger: 0.05, y: 20, blur: 10 });
    ['k1', 'k2', 'k3'].forEach((id, i) => {
      const t0 = 55.0 + i * 1.0;
      show($(id), t, t0, 99, { y: 40, blur: 8, fin: 1.1 });
      $(id).querySelectorAll('path').forEach((p) => draw(p, t, t0 + 0.2, 1.2));
    });
    show($('l5f'), t, 60.0, 99, { y: 12, blur: 8 });
  });

  /* ------------------------------------------- L6: CTA + end card */
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
  film.scene('l6', 63.8, 76.0, (lt, t) => {
    $('l6').style.opacity = env(t, 63.8, 99, 0.6, 0).toFixed(4);
    show($('l6a'), t, 64.3, 67.6, { y: 16, blur: 10 });
    chars($('l6b'), t, 64.9, 67.6, { stagger: 0.04, y: 22, blur: 10 });
    const on = t >= 67.7;
    $('logoWrap').style.opacity = on ? 1 : 0;
    if (on) {
      logo.paths.forEach((p, i) => draw(p, t, 67.8 + i * 0.07, 1.3, E.inOutCubic));
      $('logoLines').style.opacity = (1 - P(t, 69.2, 0.8)).toFixed(3);
      const fill = P(t, 68.5, 1.0, E.inOutSine);
      setStyle($('logoImg'), { opacity: fill, filter: blurCss((1 - fill) * 6) });
    }
    show($('l6n'), t, 68.8, 99, { y: 14, blur: 8 });
    show($('l6rep'), t, 69.3, 99, { y: 10 });
    ['e1', 'e2', 'e3', 'e4', 'e5'].forEach((id, i) => show($(id), t, 69.0 + i * 0.25, 99, { x: 30, y: 0, blur: 6, fin: 0.9 }));
    show($('legal'), t, 70.2, 99, { y: 8, fin: 1.2 });
  });

  M.boot(film, async () => {
    if (V) {
      film.setEdit((await fetch('../common/shorts.json').then((r) => r.json())).leak);
      $('l6b').innerHTML = '보험 접수 직후<br><em>가장 먼저</em> 연락하세요.';
      document.querySelector('.law .bd').innerHTML = document.querySelector('.law .bd').innerHTML.replace('<br>', ' ');
    }
    $('l2').style.display = 'block';
    buildApt();
    $('l2').style.display = 'none';
    buildTimeline();
    await loadLogo();
  });
})();
