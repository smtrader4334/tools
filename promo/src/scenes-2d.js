// Canvas 2D 모션그래픽 장면들 (드롭 A)
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const eOut = (u) => 1 - Math.pow(1 - clamp(u), 3);
const eOutExpo = (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(u)));
const eio = (u) => { u = clamp(u); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
const rnd = (n) => { const s = Math.sin(n * 91.345 + 7.13) * 47453.5453; return s - Math.floor(s); };
const F = (w, px) => `${w} ${px}px P, sans-serif`;
const GOLD = '#C9A84C', GOLD_L = '#F3DFA2';

function bg(ctx, W, H, top, bot) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, top); g.addColorStop(1, bot);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function glow(ctx, x, y, r, color) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
}
// 카메라 푸시
function push(ctx, W, H, u, amt = 0.06, rot = 0) {
  const s = 1 + amt * u;
  ctx.translate(W / 2, H / 2); ctx.rotate(rot); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
}

const SC = {};

// 측정: 줄자 날
SC.tape = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#16130f', '#050404');
  glow(ctx, W * 0.5, H * 0.45, Math.max(W, H) * 0.6, 'rgba(255,200,120,0.10)');
  ctx.save(); push(ctx, W, H, u, 0.05);
  ctx.translate(W / 2, H / 2); ctx.rotate(V ? -Math.PI / 2 - 0.12 : -0.12); ctx.translate(-W / 2, -H / 2);
  const L = Math.max(W, H) * 1.6;
  const bandH = V ? 170 : 190, y0 = H / 2 - bandH / 2 + (V ? 0 : 230);
  const x0 = W / 2 - L / 2;
  // 금속 테이프 곡면
  const g = ctx.createLinearGradient(0, y0, 0, y0 + bandH);
  g.addColorStop(0, '#8a6a08'); g.addColorStop(0.12, '#f4c81c'); g.addColorStop(0.5, '#ffd83a');
  g.addColorStop(0.82, '#e0b010'); g.addColorStop(1, '#6d5205');
  ctx.fillStyle = g; ctx.fillRect(x0, y0, L, bandH);
  // 눈금
  const unit = 26; // 1cm = 26px
  const off = (t * 520) % (unit * 10);
  ctx.fillStyle = '#111';
  ctx.textBaseline = 'top';
  for (let i = -20; i < L / unit + 20; i++) {
    const x = x0 + i * unit - off;
    const mm10 = i % 10 === 0, mm5 = i % 5 === 0;
    const len = mm10 ? bandH * 0.42 : mm5 ? bandH * 0.3 : bandH * 0.18;
    ctx.fillRect(x, y0 + 6, mm10 ? 4 : 2.5, len);
    ctx.fillRect(x, y0 + bandH - 6 - len * 0.6, mm10 ? 4 : 2.5, len * 0.6);
    for (let k = 1; k < 5; k++) ctx.fillRect(x + k * unit / 5, y0 + 6, 1.4, bandH * 0.1);
    if (mm10) {
      const n = 120 + Math.round((i * unit - off + 10000 * unit) / unit / 10) - 1000;
      ctx.font = F(800, bandH * 0.3);
      ctx.fillStyle = (n % 10 === 0) ? '#c0121b' : '#111';
      ctx.fillText(String(n), x + 8, y0 + bandH * 0.46);
      ctx.fillStyle = '#111';
    }
  }
  // 광택 하이라이트
  const sh = ctx.createLinearGradient(x0, 0, x0 + L, 0);
  const p = 0.3 + 0.4 * u;
  sh.addColorStop(clamp(p - 0.08), 'rgba(255,255,255,0)'); sh.addColorStop(p, 'rgba(255,255,255,0.28)'); sh.addColorStop(clamp(p + 0.08), 'rgba(255,255,255,0)');
  ctx.fillStyle = sh; ctx.fillRect(x0, y0, L, bandH);
  // 케이스
  const cx = V ? W / 2 - H * 0.36 : W * 0.08 - 60, cw = 420;
  ctx.fillStyle = '#0d0d0f';
  ctx.beginPath(); ctx.roundRect(cx - cw, y0 - 150, cw, bandH + 300, 60); ctx.fill();
  ctx.fillStyle = '#23232a'; ctx.fillRect(cx - 14, y0 - 20, 14, bandH + 40);
  ctx.restore();
  // 피사계 심도 (가장자리 어둡게)
  const dv = ctx.createLinearGradient(0, 0, V ? 0 : W, V ? H : 0);
  dv.addColorStop(0, 'rgba(0,0,0,0.55)'); dv.addColorStop(0.3, 'rgba(0,0,0,0)'); dv.addColorStop(0.75, 'rgba(0,0,0,0)'); dv.addColorStop(1, 'rgba(0,0,0,0.6)');
  ctx.fillStyle = dv; ctx.fillRect(0, 0, W, H);
};

// 도면: 청사진 선이 그려짐
SC.blueprint = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#0d3f7a', '#072a55');
  ctx.save(); push(ctx, W, H, u, 0.08, -0.03 + 0.03 * u);
  ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = 1;
  for (let x = -200; x < W + 200; x += 32) { ctx.beginPath(); ctx.moveTo(x, -200); ctx.lineTo(x, H + 200); ctx.stroke(); }
  for (let y = -200; y < H + 200; y += 32) { ctx.beginPath(); ctx.moveTo(-200, y); ctx.lineTo(W + 200, y); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(255,255,255,0.14)';
  for (let x = -200; x < W + 200; x += 160) { ctx.beginPath(); ctx.moveTo(x, -200); ctx.lineTo(x, H + 200); ctx.stroke(); }
  for (let y = -200; y < H + 200; y += 160) { ctx.beginPath(); ctx.moveTo(-200, y); ctx.lineTo(W + 200, y); ctx.stroke(); }
  // 평면도 (단위 = 칸)
  const k = V ? 64 : 68, ox = W / 2 - 12 * k, oy = H / 2 - 6.5 * k;
  const segs = [
    [0, 0, 24, 0], [24, 0, 24, 13], [24, 13, 0, 13], [0, 13, 0, 0],
    [10, 0, 10, 5], [10, 8, 10, 13], [10, 7, 17, 7], [20, 7, 24, 7], [17, 7, 17, 13],
    [4, 13, 4, 9], [0, 9, 3, 9],
  ];
  const draw = eOut(u * 1.5);
  ctx.lineCap = 'square';
  const total = segs.length;
  segs.forEach((s, i) => {
    const p = clamp(draw * total - i * 0.55);
    if (p <= 0) return;
    const [a, b, c, d] = s;
    ctx.strokeStyle = 'rgba(236,245,255,0.95)'; ctx.lineWidth = i < 4 ? 9 : 5;
    ctx.beginPath(); ctx.moveTo(ox + a * k, oy + b * k); ctx.lineTo(ox + (a + (c - a) * p) * k, oy + (b + (d - b) * p) * k); ctx.stroke();
  });
  // 문 호
  const pd = clamp(draw * 2 - 1);
  ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(236,245,255,0.8)';
  if (pd > 0) { ctx.beginPath(); ctx.arc(ox + 10 * k, oy + 5 * k, 3 * k, Math.PI / 2 - 0.0, Math.PI / 2 + pd * Math.PI / 2 * 0.001 + 0.0001); ctx.stroke(); ctx.beginPath(); ctx.arc(ox + 10 * k, oy + 8 * k, 3 * k, -Math.PI / 2, -Math.PI / 2 + pd * Math.PI / 2); ctx.stroke(); }
  // 치수선
  ctx.fillStyle = 'rgba(236,245,255,0.9)'; ctx.font = F(600, 26); ctx.textAlign = 'center';
  const dm = clamp(draw * 1.6 - 0.5);
  if (dm > 0) {
    ctx.globalAlpha = dm; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(ox, oy - 40); ctx.lineTo(ox + 24 * k, oy - 40); ctx.stroke();
    ctx.fillText('7,200', ox + 12 * k, oy - 52);
    ctx.save(); ctx.translate(ox - 44, oy + 6.5 * k); ctx.rotate(-Math.PI / 2); ctx.fillText('3,900', 0, -8); ctx.restore();
    ctx.beginPath(); ctx.moveTo(ox - 40, oy); ctx.lineTo(ox - 40, oy + 13 * k); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  ctx.restore();
};

// 산정: 숫자 롤링
SC.numbers = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#0b0b16', '#04040a');
  ctx.save(); push(ctx, W, H, u, 0.05);
  const cols = V ? 7 : 12, cw = V ? 150 : 150, fs = V ? 120 : 130;
  const x0 = W / 2 - (cols * cw) / 2 + cw / 2;
  ctx.font = F(700, fs); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (let c = 0; c < cols; c++) {
    const sp = 900 + rnd(c) * 1600;
    const settle = 0.25 + rnd(c + 3) * 0.5;
    const off = (u < settle ? t * sp : settle * 0.5 * sp) + rnd(c + 9) * 1000;
    const rowH = fs * 1.25;
    const base = Math.floor(off / rowH);
    for (let r = -6; r <= 6; r++) {
      const y = H / 2 + r * rowH - (off % rowH);
      const digit = Math.abs(base + r + c * 7) % 10;
      const dist = Math.abs(y - H / 2) / (H / 2);
      const center = dist < 0.08;
      ctx.globalAlpha = clamp(1 - dist * 1.1) * (center ? 1 : 0.35);
      ctx.fillStyle = center ? GOLD_L : '#9a9ab0';
      ctx.fillText(String(digit), x0 + c * cw, y);
    }
  }
  ctx.globalAlpha = 1;
  ctx.fillStyle = 'rgba(201,168,76,0.12)';
  ctx.fillRect(0, H / 2 - fs * 0.62, W, fs * 1.24);
  ctx.restore();
  const vg = ctx.createLinearGradient(0, 0, 0, H);
  vg.addColorStop(0, 'rgba(4,4,10,1)'); vg.addColorStop(0.3, 'rgba(4,4,10,0)'); vg.addColorStop(0.7, 'rgba(4,4,10,0)'); vg.addColorStop(1, 'rgba(4,4,10,1)');
  ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
};

// 누락: 견적서에서 빠진 항목에 빨간 펜 동그라미
SC.missing = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#2a2622', '#110f0d');
  ctx.save(); push(ctx, W, H, u, 0.07, 0);
  const pw = V ? 900 : 1100, ph = V ? 1300 : 1250;
  const px = W / 2 - pw / 2, py = V ? 396 : -24;
  ctx.translate(W / 2, H / 2); ctx.rotate(-0.06); ctx.translate(-W / 2, -H / 2);
  ctx.shadowColor = 'rgba(0,0,0,0.6)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 20;
  ctx.fillStyle = '#f4f1ea'; ctx.fillRect(px, py, pw, ph);
  ctx.shadowColor = 'transparent';
  ctx.fillStyle = '#1b1b1f'; ctx.font = F(800, 52); ctx.textBaseline = 'alphabetic';
  ctx.fillText('손해액 산출 내역', px + 70, py + 120);
  ctx.fillStyle = '#9a958c'; ctx.fillRect(px + 70, py + 150, pw - 140, 3);
  const rows = [['철거 · 폐기물', '1,840,000'], ['전기 배선', ''], ['도배 32.4㎡', '1,296,000'], ['장판 18.0㎡', '1,080,000'], ['주방 가구', '2,350,000'], ['소방 설비', '']];
  ctx.font = F(600, 44);
  rows.forEach(([a, b], i) => {
    const y = py + 250 + i * 118;
    ctx.fillStyle = '#26262b'; ctx.textAlign = 'left'; ctx.fillText(a, px + 70, y);
    ctx.textAlign = 'right';
    if (b) { ctx.fillStyle = '#26262b'; ctx.fillText(b, px + pw - 70, y); }
    else { ctx.fillStyle = '#c9c4ba'; ctx.fillText('—', px + pw - 70, y); }
    ctx.fillStyle = '#e1dcd2'; ctx.fillRect(px + 70, y + 34, pw - 140, 2);
  });
  ctx.textAlign = 'left';
  // 빨간 펜 동그라미 (전기 배선 행)
  const cyr = py + 250 + 1 * 118 - 14, cxr = px + pw / 2;
  const prog = eOut((u - 0.05) / 0.55);
  if (prog > 0) {
    ctx.strokeStyle = '#d4202a'; ctx.lineWidth = 9; ctx.lineCap = 'round';
    ctx.beginPath();
    const n = 60;
    for (let i = 0; i <= n * prog; i++) {
      const a = -2.6 + (i / n) * Math.PI * 2.15;
      const rx = pw / 2 - 30 + Math.sin(i * 0.3) * 4, ry = 64 + Math.cos(i * 0.21) * 5;
      const x = cxr + Math.cos(a) * rx, y = cyr + Math.sin(a) * ry;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
  }
  ctx.restore();
  glow(ctx, W * 0.3, H * 0.2, Math.max(W, H) * 0.8, 'rgba(255,220,170,0.08)');
};

// 근거: 서류·현장 사진이 쌓임
SC.documents = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#231a13', '#0e0a07');
  // 나무 결
  ctx.globalAlpha = 0.18;
  for (let i = 0; i < 60; i++) { ctx.fillStyle = i % 2 ? '#3b2a1b' : '#1a120b'; ctx.fillRect(0, (i / 60) * H + Math.sin(i) * 6, W, H / 60 * (0.4 + rnd(i))); }
  ctx.globalAlpha = 1;
  ctx.save(); push(ctx, W, H, u, 0.05);
  const items = [
    { k: 'doc', x: -0.16, y: 0.02, r: -0.08 }, { k: 'photo', x: 0.14, y: -0.06, r: 0.1 },
    { k: 'doc', x: 0.05, y: 0.08, r: 0.04 }, { k: 'photo', x: -0.2, y: -0.12, r: -0.14 },
    { k: 'photo', x: 0.22, y: 0.14, r: 0.18 }, { k: 'doc', x: -0.02, y: -0.02, r: -0.02 },
  ];
  items.forEach((it, i) => {
    const t0 = i * 0.06;
    const p = eOutExpo((u - t0) / 0.28);
    if (p <= 0) return;
    const sw = it.k === 'doc' ? (V ? 560 : 620) : (V ? 480 : 520), sh = it.k === 'doc' ? sw * 1.35 : sw * 0.75;
    const cx = W / 2 + it.x * (V ? W * 1.6 : W), cy = H / 2 + it.y * H;
    ctx.save();
    ctx.translate(cx, cy - (1 - p) * H * 0.2); ctx.rotate(it.r + (1 - p) * 0.3); ctx.scale(1 + (1 - p) * 0.25, 1 + (1 - p) * 0.25);
    ctx.globalAlpha = clamp(p * 3);
    ctx.shadowColor = 'rgba(0,0,0,0.55)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 18 * p + 4;
    ctx.fillStyle = it.k === 'doc' ? '#f3f0e8' : '#fbfbf8';
    ctx.fillRect(-sw / 2, -sh / 2, sw, sh);
    ctx.shadowColor = 'transparent';
    if (it.k === 'doc') {
      ctx.fillStyle = '#2b2b30'; ctx.fillRect(-sw / 2 + 50, -sh / 2 + 60, sw * 0.45, 22);
      for (let l = 0; l < 11; l++) { ctx.fillStyle = '#cfcac0'; ctx.fillRect(-sw / 2 + 50, -sh / 2 + 130 + l * 44, (sw - 100) * (0.6 + 0.4 * rnd(l + i)), 12); }
      ctx.strokeStyle = 'rgba(200,30,40,0.8)'; ctx.lineWidth = 6;
      ctx.beginPath(); ctx.arc(sw / 2 - 110, sh / 2 - 110, 54, 0, Math.PI * 2); ctx.stroke();
    } else {
      const ix = -sw / 2 + 22, iy = -sh / 2 + 22, iw = sw - 44, ih = sh - 44;
      const g = ctx.createLinearGradient(ix, iy + ih, ix + iw, iy);
      g.addColorStop(0, '#1a0f0a'); g.addColorStop(0.5, i % 2 ? '#5b2b12' : '#2a2a30'); g.addColorStop(1, i % 2 ? '#c46a22' : '#6a655e');
      ctx.fillStyle = g; ctx.fillRect(ix, iy, iw, ih);
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      for (let b = 0; b < 5; b++) ctx.fillRect(ix + iw * (0.1 + b * 0.18), iy + ih * (0.3 + rnd(b + i) * 0.4), iw * 0.08, ih);
    }
    ctx.restore();
  });
  ctx.restore();
};

// 협상: 두 면이 맞선다
function slabs(ctx, t, u, W, H, V, merge) {
  bg(ctx, W, H, '#08080d', '#030306');
  const push_ = merge ? 0 : Math.sin(u * Math.PI) * 18;
  const gap = merge ? (1 - eOutExpo(u / 0.5)) * 14 : 14 + Math.sin(t * 60) * 1.5;
  const mid = (V ? H : W) / 2 + (merge ? 0 : -push_ * 2 + 40 * u);
  ctx.save();
  const shake = merge ? 0 : Math.sin(t * 90) * 2.5;
  ctx.translate(V ? shake : 0, V ? 0 : shake);
  // 회색 (보험사)
  const gA = V ? ctx.createLinearGradient(0, 0, 0, mid) : ctx.createLinearGradient(0, 0, mid, 0);
  gA.addColorStop(0, '#1c1c22'); gA.addColorStop(1, '#4a4a55');
  ctx.fillStyle = gA;
  V ? ctx.fillRect(0, 0, W, mid - gap / 2) : ctx.fillRect(0, 0, mid - gap / 2, H);
  // 금색 (당신 편)
  const gB = V ? ctx.createLinearGradient(0, mid, 0, H) : ctx.createLinearGradient(mid, 0, W, 0);
  gB.addColorStop(0, '#e8cf85'); gB.addColorStop(0.35, '#b8913a'); gB.addColorStop(1, '#4a3712');
  ctx.fillStyle = gB;
  V ? ctx.fillRect(0, mid + gap / 2, W, H) : ctx.fillRect(mid + gap / 2, 0, W, H);
  // 경계 빛
  const lg = merge ? eOut(u / 0.6) : 0.35 + 0.25 * Math.sin(t * 40);
  if (V) { const g = ctx.createLinearGradient(0, mid - 120, 0, mid + 120); g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(0.5, `rgba(255,240,200,${0.8 * lg})`); g.addColorStop(1, 'rgba(255,240,200,0)'); ctx.fillStyle = g; ctx.fillRect(0, mid - 120, W, 240); }
  else { const g = ctx.createLinearGradient(mid - 120, 0, mid + 120, 0); g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(0.5, `rgba(255,240,200,${0.8 * lg})`); g.addColorStop(1, 'rgba(255,240,200,0)'); ctx.fillStyle = g; ctx.fillRect(mid - 120, 0, 240, H); }
  if (merge) {
    const m = eOut((u - 0.2) / 0.7);
    ctx.fillStyle = `rgba(20,18,40,${0.55 * m})`; ctx.fillRect(0, 0, W, H);
    glow(ctx, W / 2, H / 2, Math.max(W, H) * 0.7 * (0.4 + m), `rgba(232,208,138,${0.35 * m})`);
  } else {
    // 불꽃
    for (let i = 0; i < 26; i++) {
      const a = rnd(i) * Math.PI * 2, sp = 200 + rnd(i + 1) * 700, life = (u * 0.5 + rnd(i + 2)) % 1;
      const x = (V ? rnd(i + 3) * W : mid) + (V ? Math.cos(a) * sp * life * 0.3 : Math.cos(a) * sp * life);
      const y = (V ? mid : rnd(i + 3) * H) + (V ? Math.sin(a) * sp * life : Math.sin(a) * sp * life * 0.3 + 300 * life * life);
      ctx.fillStyle = `rgba(255,220,150,${(1 - life) * 0.9})`;
      ctx.fillRect(x, y, 4, 4);
    }
  }
  ctx.restore();
}
SC.negotiate = (ctx, t, u, W, H, V) => slabs(ctx, t, u, W, H, V, false);
SC.agree = (ctx, t, u, W, H, V) => slabs(ctx, t, u, W, H, V, true);

// 제자리: 집 선이 그려지고 창에 불이 켜짐
SC.home = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#14132a', '#06060f');
  ctx.save(); push(ctx, W, H, u, 0.05);
  const s = V ? 1.25 : 1.05;
  const cx = W / 2, by = H / 2 + 280 * s;
  const w = 560 * s, h = 360 * s, rh = 260 * s;
  const pts = [[cx - w / 2, by], [cx - w / 2, by - h], [cx, by - h - rh], [cx + w / 2, by - h], [cx + w / 2, by], [cx - w / 2 - 80, by], [cx + w / 2 + 80, by]];
  const path = [[0, 1], [1, 2], [2, 3], [3, 4], [5, 6]];
  const p = eOut(u / 0.55);
  ctx.strokeStyle = GOLD_L; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.shadowColor = 'rgba(232,208,138,0.6)'; ctx.shadowBlur = 24;
  path.forEach(([a, b], i) => {
    const q = clamp(p * path.length - i);
    if (q <= 0) return;
    const [x1, y1] = pts[a], [x2, y2] = pts[b];
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 + (x2 - x1) * q, y1 + (y2 - y1) * q); ctx.stroke();
  });
  ctx.shadowBlur = 0;
  // 창
  const wl = eOut((u - 0.45) / 0.3);
  const ww = 150 * s, wh = 130 * s, wx = cx - ww / 2, wy = by - h + 60 * s;
  if (wl > 0) {
    glow(ctx, cx, wy + wh / 2, 520 * s * wl, `rgba(255,190,90,${0.35 * wl})`);
    ctx.fillStyle = `rgba(255,205,120,${0.95 * wl})`; ctx.fillRect(wx, wy, ww, wh);
    ctx.fillStyle = `rgba(90,60,20,${0.6 * wl})`; ctx.fillRect(cx - 3, wy, 6, wh); ctx.fillRect(wx, wy + wh / 2 - 3, ww, 6);
  }
  ctx.strokeStyle = GOLD_L; ctx.lineWidth = 5; if (p > 0.9) ctx.strokeRect(wx, wy, ww, wh);
  ctx.restore();
};

// 당신 편: 검정 + 금빛
SC.gold = (ctx, t, u, W, H, V) => {
  bg(ctx, W, H, '#050407', '#000000');
  glow(ctx, W / 2, H / 2, Math.max(W, H) * 0.55, `rgba(201,168,76,${0.16 + 0.06 * u})`);
  for (let i = 0; i < 40; i++) {
    const x = rnd(i) * W, y = ((rnd(i + 1) * H - t * (30 + rnd(i + 2) * 60)) % H + H) % H;
    ctx.fillStyle = `rgba(243,223,162,${0.15 + 0.35 * rnd(i + 5)})`;
    ctx.beginPath(); ctx.arc(x, y, 1.2 + rnd(i + 3) * 2.2, 0, Math.PI * 2); ctx.fill();
  }
};

export function draw2D(ctx, key, t, u, W, H, V) {
  const f = SC[key];
  if (!f) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); return; }
  ctx.save(); f(ctx, t, clamp(u), W, H, V); ctx.restore();
}
