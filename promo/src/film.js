// 더함 브랜드 필름 v2 — 프레임 단위 렌더러 (96 BPM, 1박 = 0.625초, 47.5초)
// window.renderFrame(t) 가 t초의 화면을 결정적으로 그린다. (render.mjs 가 매 프레임 호출)
import { initGL, drawGL, hasGL } from './scenes-gl.js';
import { draw2D } from './scenes-2d.js';

const Q = new URLSearchParams(location.search);
const V = Q.get('fmt') === 'v';
const W = V ? 1080 : 1920;
const H = V ? 1920 : 1080;
const $ = (id) => document.getElementById(id);
const BEAT = 0.625;
const bt = (b) => b * BEAT;

// ---------------------------------------------------------------- utils
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, u) => a + (b - a) * u;
const lin = (t, a, b) => clamp((t - a) / (b - a));
const eOutExpo = (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(u)));
const eOut = (u) => 1 - Math.pow(1 - clamp(u), 3);
const eInOut = (u) => { u = clamp(u); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
const S = (h, v) => (V && v !== undefined ? v : h);

// ---------------------------------------------------------------- stage
const stage = $('stage');
stage.style.width = W + 'px';
stage.style.height = H + 'px';
const c2 = $('c2'), fx = $('fx'), gl = $('gl');
for (const c of [c2, fx]) { c.width = W; c.height = H; }
const ctx = c2.getContext('2d');
const fctx = fx.getContext('2d');
gl.width = Math.round(W / 2); gl.height = Math.round(H / 2);
gl.style.display = 'none';
initGL(gl);

// 단어 하나가 흐림 속에서 떠오르는 모션
function reveal(u, dist = 26, blur = 10) {
  const e = eOut(u);
  return `opacity:${clamp(u * 1.6)};transform:translateY(${(1 - eOutExpo(u)) * dist}px);filter:blur(${(1 - e) * blur}px)`;
}

// ---------------------------------------------------------------- footage (src/footage.py → build/footage/<fmt>/<장면>/NNN.jpg)
let FOOTAGE = {};
const imgCache = new Map();
async function footageFrame(key, idx) {
  const url = `../build/footage/${V ? 'v' : 'h'}/${key}/${String(idx + 1).padStart(3, '0')}.jpg`;
  let im = imgCache.get(url);
  if (!im) { im = new Image(); im.src = url; imgCache.set(url, im); }
  await im.decode();
  if (imgCache.size > 40) imgCache.delete(imgCache.keys().next().value);
  return im;
}
async function drawFootage(key, lt, push) {
  const f = FOOTAGE[key];
  if (!f) return false;
  const im = await footageFrame(key, Math.min(f.frames - 1, Math.floor(lt * 30 + 1e-6)));
  const s = 1 + push;
  ctx.save();
  ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
  ctx.drawImage(im, 0, 0, W, H);
  ctx.restore();
  if (f.dim) { ctx.fillStyle = `rgba(4,8,16,${f.dim})`; ctx.fillRect(0, 0, W, H); }
  return true;
}
function glTo2D(key, lt, u) {
  if (!drawGL(key, lt, u)) return false;
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(gl, 0, 0, W, H);
  return true;
}

// ---------------------------------------------------------------- 오프닝·빌드업: 배경 위에 문장이 박자마다 한 단어씩 쌓임
const PHRASES = [
  { t0: bt(4), t1: bt(8), bg: 'op1', br: 2, words: [['사고는', 4], ['예고 없이', 5], ['옵니다.', 6]] },
  { t0: bt(8), t1: bt(12), bg: 'op2', br: 1, words: [['불이 나고,', 8], ['연기가', 9], ['번지고,', 10]] },
  { t0: bt(12), t1: bt(16), bg: 'op3', br: 2, words: [['무엇이,', 12], ['얼마나', 13], ['손상됐는지.', 14]] },
  { t0: bt(16), t1: bt(20), bg: 'op4', br: 2, words: [['설명할', 16], ['<span class="blue">근거가</span>', 17], ['필요합니다.', 18]] },
  { t0: bt(20), t1: bt(24), bg: 'build', br: 1, words: [['보이는 피해', 20], ['너머까지.', 21]], build: true },
];
const phraseEl = $('phraseIn');
function renderPhrase(t) {
  const p = PHRASES.find((p) => t >= p.t0 && t < p.t1);
  if (!p) { phraseEl.innerHTML = ''; return null; }
  let out = 1 - lin(t, p.t1 - 0.15, p.t1);
  if (p.build) out = 1 - eInOut(lin(t, 14.2, 14.75));
  const html = p.words.map(([w, b], i) => {
    const u = (t - bt(b)) / 0.5;
    const st = u < 0 ? 'opacity:0' : reveal(u);
    return (V && i === p.br ? '<br>' : ' ') + `<span class="w" style="${st}">${w}</span>`;
  }).join('');
  phraseEl.innerHTML = html;
  phraseEl.style.fontSize = S(p.build ? 124 : 112, p.build ? 116 : 104) + 'px';
  let sc = 1;
  if (p.build) sc = 1 + 0.035 * eInOut(lin(t, bt(21), 14.75));
  phraseEl.style.opacity = out;
  phraseEl.style.transform = `scale(${sc})`;
  return p;
}

// ---------------------------------------------------------------- 드롭 A: 한 박자에 한 단어
const DROP_A = [
  ['불.', 'fire'], ['연기.', 'smoke'], ['그을음.', 'soot'], ['소방수.', 'hose'],
  ['현장.', 'site'], ['측정.', 'tape'], ['도면.', 'blueprint'], ['약관.', 'policy'],
  ['누락.', 'missing'], ['근거.', 'evidence'], ['산정.', 'numbers'], ['설명.', 'explain'],
  ['복구.', 'rebuild'], ['일상.', 'room'], ['제자리.', 'keys'], ['회복.', 'sunrise'],
].map(([text, bg], i) => ({ t: bt(24 + i), text, bg }));
const wordEl = $('word');
function renderWord(t) {
  const c = DROP_A.find((c) => t >= c.t && t < c.t + BEAT);
  if (!c) { wordEl.innerHTML = ''; return null; }
  const u = (t - c.t) / 0.3;
  wordEl.innerHTML = c.text;
  wordEl.style.fontSize = S(190, 168) + 'px';
  wordEl.style.transform = `scale(${1.05 - 0.05 * eOutExpo(u)})`;
  wordEl.style.opacity = clamp(u * 4);
  return c;
}

// ---------------------------------------------------------------- 드롭 B: 최신 홈페이지 · 대표 · 선임권 페이지를 폰 안에서
const rig = $('phoneRig'), phone = $('phone');
const hl = $('hl'), tap = $('tap'), tapRing = $('tapRing'), kw = $('kw'), kwSub = $('kwSub');
const PG = { home: { el: $('pg-home') }, sm: { el: $('pg-sm') }, dk: { el: $('pg-dk') } };
const VH = 794; // 상태바 아래 페이지 뷰포트 높이
// 글자 장면: 머리말 → 1줄 → 2줄(→3줄) 순서로 위에서 아래로. 마지막 줄이 나온 뒤 1.2초 이상 유지
const SC = [
  { t0: bt(40), t1: bt(43), lines: [['근거를 찾고,', 40], ['회복의 방향을.', 41]] },
  { t0: bt(43), t1: bt(46), eyebrow: '화재 손해', lines: [['타버린 곳 너머,', 43], ['손해의 범위를 살핍니다.', 44]] },
  { t0: bt(46), t1: bt(49), eyebrow: '유승민 대표 · 재물손해사정사', list: true,
    lines: [['현직 손실보상심의위원', 46], ['보험사 조사회사 지점장 출신', 46.5], ['건축기사 · 건설안전기사', 47]] },
  { t0: bt(49), t1: bt(52), eyebrow: '이도경 이사 · 손해사정사 선임권 상담', lines: [['손해사정사 선택,', 49], ['고객님의 <span class="blue">권리</span>입니다.', 50]] },
  { t0: bt(52), t1: 35.0, eyebrow: '부산 · 울산 · 경남', lines: [['가까운 현장에서,', 52], ['함께 시작합니다.', 53]] },
];

// 폰 안 동작: 페이지 · 스크롤 · 하이라이트 · 탭
const DB = [
  { b: 40, page: 'home', scroll: 0, hl: { sel: 'h1' } },
  { b: 43, page: 'home', scroll: { sel: '[id$="-trigger-fire"]', mode: 'top' }, tap: { sel: '[id$="-trigger-fire"]' }, hl: { sel: '[id$="-trigger-fire"]' } },
  { b: 44, page: 'home', hl: { sel: 'h3', text: '타버린 곳', up: 1 } },
  { b: 46, page: 'sm', scroll: { sel: 'h3', text: '보험사 조사회사' }, hl: { sel: 'h3', text: '현직 손실보상', up: 1 } },
  { b: 46.5, page: 'sm', hl: { sel: 'h3', text: '보험사 조사회사', up: 1 } },
  { b: 47, page: 'sm', hl: { sel: 'h3', text: '건축기사', up: 1 } },
  { b: 49, page: 'dk', scroll: { sel: '#appointment-title', at: 380 }, hl: { sel: '#appointment-title' } },
  { b: 52, page: 'home', scroll: { sel: '#co-regions-title', mode: 'top' }, hl: { sel: '#co-regions-title' } },
  { b: 54, page: 'home', tap: { sel: 'a.co-dock-kakao' }, hl: { sel: 'a.co-dock-kakao' } },
];
for (let i = 0; i < DB.length; i++) { DB[i].t = bt(DB[i].b); DB[i].end = DB[i + 1] ? bt(DB[i + 1].b) : 35.0; }

function find(page, spec) {
  const d = PG[page].doc;
  let els = [...d.querySelectorAll(spec.sel)];
  if (spec.text) els = els.filter((e) => (e.innerText || '').replace(/\s+/g, ' ').includes(spec.text));
  let el = els[spec.i || 0];
  for (let k = 0; k < (spec.up || 0) && el && el.parentElement; k++) el = el.parentElement;
  return el;
}

function precompute() {
  for (const k of Object.keys(PG)) {
    const p = PG[k];
    p.win.scrollTo(0, 0);
    const hdr = p.doc.querySelector('header') || p.doc.querySelector('a.brand')?.closest('div,header');
    p.top = hdr ? hdr.getBoundingClientRect().bottom : 64;
    const dock = p.doc.querySelector('a.co-dock-kakao, a.kakao-action');
    p.bottom = dock ? dock.getBoundingClientRect().top - 8 : VH;
    p.max = p.doc.documentElement.scrollHeight - VH;
  }
  let last = {};
  for (const c of DB) {
    const p = PG[c.page];
    let target = last[c.page] ?? 0;
    if (c.scroll !== undefined) {
      if (c.scroll === 0) target = 0;
      else {
        p.win.scrollTo(0, 0);
        const r = find(c.page, c.scroll).getBoundingClientRect();
        target = c.scroll.at !== undefined ? r.top - c.scroll.at : c.scroll.mode === 'top' ? r.top - p.top - 90 : r.top + r.height / 2 - (p.top + p.bottom) / 2;
        target = clamp(Math.round(target), 0, p.max);
      }
    }
    c.target = target; last[c.page] = target;
  }
  for (const k of Object.keys(PG)) PG[k].win.scrollTo(0, 0);
}

function scrollFor(i, t) {
  const c = DB[i], prev = DB[i - 1], next = DB[i + 1];
  let y = c.target;
  if (prev && prev.page === c.page && prev.target !== c.target && t < c.t + 0.05)
    y = lerp(prev.target, c.target, eInOut(lin(t, c.t - 0.17, c.t + 0.05)));
  if (next && next.page === c.page && next.target !== c.target && t > next.t - 0.17)
    y = lerp(c.target, next.target, eInOut(lin(t, next.t - 0.17, next.t + 0.05)));
  return y;
}

function renderSceneText(t) {
  const sc = SC.find((s) => t >= s.t0 && t < s.t1);
  kwSub.style.display = 'none';
  if (!sc) { kw.innerHTML = ''; return; }
  const base = sc.list ? S(66, 62) : S(112, 100);
  const ebFS = S(34, 38);
  const st = (b, extra = 0) => { const u = (t - bt(b) - extra) / 0.45; return u < 0 ? 'opacity:0' : reveal(u, 22, 8); };
  const bar = '<span style="display:inline-block;width:.16em;height:.86em;background:var(--blue);border-radius:2px;margin-right:.42em;vertical-align:-.06em"></span>';
  const linesHTML = (withStyle) => sc.lines.map(([w, b], i) =>
    `<div style="white-space:nowrap;${sc.list ? 'margin-top:.28em;' : ''}${withStyle ? st(b, sc.eyebrow && i === 0 ? 0.08 : 0) : ''}">${sc.list ? bar : ''}${w}</div>`).join('');
  // 가장 긴 줄 기준으로 한 번에 크기를 정해 장면 내내 고정
  kw.style.fontSize = base + 'px';
  kw.innerHTML = linesHTML(false);
  const w0 = kw.scrollWidth, maxW = S(800, 960);
  const fs = w0 > maxW ? base * maxW / w0 : base;
  kw.style.fontSize = fs + 'px';
  const eb = sc.eyebrow ? `<div style="font-size:${ebFS}px;color:var(--blue-l);font-weight:600;letter-spacing:.01em;line-height:1.3;margin-bottom:${S(22, 24)}px;white-space:nowrap;${st(sc.lines[0][1])}">${sc.eyebrow}</div>` : '';
  kw.innerHTML = eb + linesHTML(true);
  const out = 1 - lin(t, sc.t1 - 0.12, sc.t1);
  const kfade = 1 - eInOut(lin(t, 34.4, 34.8));
  kw.style.opacity = (sc.t1 >= 35 ? 1 : out) * kfade;
  kw.style.filter = 'none'; kw.style.transform = 'none';
  const kwW = kw.scrollWidth, kwH = kw.scrollHeight;
  kw.style.textAlign = V ? 'center' : 'left';
  kw.style.left = S(1060, (W - kwW) / 2) + 'px';
  kw.style.top = S(H / 2 - kwH / 2, 400 - kwH / 2) + 'px';
}

function renderPhone(t) {
  const on = t >= 25 && t < 35;
  rig.style.visibility = on ? 'visible' : 'hidden';
  if (!on) { for (const k of Object.keys(PG)) PG[k].el.style.visibility = 'hidden'; hl.style.display = tap.style.display = tapRing.style.display = 'none'; return; }
  const i = Math.max(0, DB.findIndex((c) => t >= c.t && t < c.end));
  const c = DB[i], prev = DB[i - 1];

  // 페이지 전환: 새 페이지가 오른쪽에서 밀려 들어옴
  const sw = prev && prev.page !== c.page ? eInOut(lin(t, c.t - 0.08, c.t + 0.26)) : 1;
  for (const k of Object.keys(PG)) {
    const el = PG[k].el;
    if (k === c.page) { el.style.visibility = 'visible'; el.style.transform = `translateX(${(1 - sw) * 100}%)`; el.style.zIndex = 1; }
    else if (sw < 1 && prev && k === prev.page) { el.style.visibility = 'visible'; el.style.transform = `translateX(${-sw * 30}%)`; el.style.zIndex = 0; }
    else el.style.visibility = 'hidden';
  }
  PG[c.page].win.scrollTo(0, Math.round(scrollFor(i, t)));
  const next = DB[i + 1];
  if (next && next.page !== c.page) PG[next.page].win.scrollTo(0, next.target);
  if (sw < 1 && prev) PG[prev.page].win.scrollTo(0, prev.target);

  // 폰 배치 + 등장 · 퇴장
  const s = S(1.2, 1.22);
  const pw = 418 * s, ph = 872 * s;
  let px = S(620 - pw / 2, 540 - pw / 2), py = S(64, H - ph - 120);
  const ein = eOutExpo(lin(t, 25.0, 25.45));
  const eout = eInOut(lin(t, 34.45, 35.0));
  py += (1 - ein) * H * 0.6 + eout * H * 0.35;
  phone.style.transform = `translate(${px}px,${py + Math.sin(t * 1.1) * 4}px) scale(${s * (1 - 0.04 * eout)})`;
  phone.style.opacity = clamp(ein * 2) * (1 - eInOut(lin(t, 34.6, 35.0)));

  // 하이라이트
  if (c.hl && sw >= 1 && t < 34.45) {
    const el = find(c.page, c.hl);
    const r = el.getBoundingClientRect();
    const pad = 7;
    const fresh = !prev || prev.page !== c.page || JSON.stringify(prev.hl) !== JSON.stringify(c.hl);
    const u = (t - c.t) / 0.2;
    hl.style.display = 'block';
    hl.style.left = r.left - pad + 'px'; hl.style.top = r.top + 50 - pad + 'px';
    hl.style.width = r.width + pad * 2 - 6 + 'px'; hl.style.height = r.height + pad * 2 - 6 + 'px';
    hl.style.opacity = fresh ? clamp(u) : 1;
    hl.style.transform = `scale(${fresh ? 1 + 0.04 * (1 - eOutExpo(u)) : 1})`;
  } else hl.style.display = 'none';

  // 탭 터치
  const tc = DB.find((b) => b.tap && t >= b.t - 0.08 && t < b.t + 0.45);
  if (tc && tc.page === c.page && t < 34.45) {
    const r = find(tc.page, tc.tap).getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + 50 + r.height / 2;
    const u = t - tc.t;
    tap.style.display = tapRing.style.display = 'block';
    tap.style.left = tapRing.style.left = cx + 'px';
    tap.style.top = tapRing.style.top = cy + 'px';
    tap.style.opacity = u < 0 ? clamp((u + 0.08) / 0.05) : clamp(1 - (u - 0.12) / 0.12);
    const ur = clamp(u / 0.4);
    tapRing.style.opacity = u < 0 ? 0 : 0.85 * (1 - ur);
    tapRing.style.transform = `scale(${1 + 1.5 * eOut(ur)})`;
  } else { tap.style.display = 'none'; tapRing.style.display = 'none'; }

  renderSceneText(t);
}

// ---------------------------------------------------------------- 엔딩: 큰 한 줄 → (사라짐) → 로고 → 한 줄 → 상호 → 연락처 → 고지
const endcard = $('endcard'), logoWrap = $('logoWrap'), sheen = $('logoSheen'), tagline = $('tagline'), tagSmall = $('tagSmall');
const brand = $('brandname'), official = $('official'), contacts = $('contacts'), disclaimer = $('disclaimer');
contacts.innerHTML = V
  ? '<b>손해사정</b> 유승민 대표 010-3589-7193<br><b>선임권</b> 이도경 이사 010-2506-0717<br><span class="blue"><b class="blue">카카오톡 상담</b></span>'
  : '<b>손해사정</b> 유승민 대표 010-3589-7193<span class="sep">|</span><b>선임권</b> 이도경 이사 010-2506-0717<br><span class="blue"><b class="blue">카카오톡 상담</b></span>';
const L = {
  logoH: S(210, 260), logoCY: S(270, 600),
  tagY: S(440, 820), tagFS: S(58, 62), lineFS: S(150, 124),
  brandY: S(512, 905), brandFS: S(32, 40),
  offY: S(560, 962), offFS: S(24, 30),
  conY: S(660, 1080), conFS: S(34, 42),
  disY: S(1010, 1800), disFS: S(20, 26),
};
function renderOutro(t) {
  const on = t >= 35;
  endcard.style.display = on && t >= 38.6 ? 'block' : 'none';
  tagline.style.display = on && t >= bt(57) && t < 38.6 ? 'block' : 'none';
  if (!on) return;
  if (t >= bt(57) && t < 38.6) {
    const u1 = (t - bt(57)) / 0.55, u2 = (t - bt(59)) / 0.55;
    const br = V ? '<br>' : ' ';
    tagline.innerHTML = `<span style="display:inline-block;${reveal(u1, 26, 10)}">빠진 것을,</span>${br}` +
      `<span class="blue" style="display:inline-block;${u2 < 0 ? 'opacity:0' : reveal(u2, 26, 10)}">더합니다.</span>`;
    tagline.style.fontSize = L.lineFS + 'px';
    tagline.style.lineHeight = 1.15;
    tagline.style.top = H / 2 - tagline.scrollHeight / 2 + 'px';
    const f = eInOut(lin(t, 37.95, 38.5));
    tagline.style.opacity = 1 - f;
    tagline.style.filter = f > 0.02 ? `blur(${f * 8}px)` : 'none';
    tagline.style.transform = `scale(${1 - 0.03 * f})`;
  }
  if (t < 38.6) return;
  const lw = L.logoH * 1328 / 1151;
  logoWrap.style.width = lw + 'px'; logoWrap.style.height = L.logoH + 'px';
  logoWrap.style.marginLeft = -lw / 2 + 'px';
  logoWrap.style.top = L.logoCY - L.logoH / 2 + 'px';
  const lu = t - bt(62);
  logoWrap.style.opacity = clamp(lu / 0.8);
  logoWrap.style.transform = `scale(${lerp(0.94, 1, eOut(clamp(lu / 1.8)))})`;
  logoWrap.style.filter = lu < 0.7 ? `blur(${10 * (1 - clamp(lu / 0.7))}px)` : 'none';
  sheen.style.backgroundPosition = `${lerp(160, -60, eInOut(lin(t, 39.1, 40.4)))}% 0`;
  const place = (el, y, fs, t0, extra) => {
    el.style.top = y + 'px'; el.style.fontSize = fs + 'px';
    const u = lin(t, t0, t0 + 0.7);
    el.style.opacity = u; el.style.transform = `translateY(${(1 - eOut(u)) * 12}px)`;
    if (extra) extra(u);
  };
  place(tagSmall, L.tagY - L.tagFS * 0.6, L.tagFS, bt(63));
  place(brand, L.brandY, L.brandFS, bt(64), (u) => { brand.style.letterSpacing = lerp(0.3, 0.14, eOut(u)) + 'em'; });
  place(official, L.offY, L.offFS, bt(64) + 0.3);
  place(contacts, L.conY, L.conFS, bt(66));
  place(disclaimer, L.disY, L.disFS, bt(67));
}

// ---------------------------------------------------------------- 배경
function navyBG(t) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#0E1B2E'); g.addColorStop(1, '#050A13');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  const gx = S(W * 0.74, W * 0.5) + Math.sin(t * 0.6) * 50, gy = S(H * 0.42, H * 0.2);
  const r = ctx.createRadialGradient(gx, gy, 0, gx, gy, 900);
  r.addColorStop(0, 'rgba(40,90,245,0.22)'); r.addColorStop(1, 'rgba(40,90,245,0)');
  ctx.fillStyle = r; ctx.fillRect(0, 0, W, H);
}
function outroBG(t) {
  const g = ctx.createRadialGradient(W / 2, L.logoCY, 0, W / 2, L.logoCY, Math.max(W, H) * 0.8);
  const k = clamp((t - 38.6) / 1.5);
  g.addColorStop(0, `rgba(16,30,48,${0.9 * k})`); g.addColorStop(1, 'rgba(16,30,48,0)');
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}

async function renderBG(t, phrase, word) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  if (t < 2.5) {
    // 훅: 어둠 속 성냥 점화 (실사). 클립이 없으면 CG 멀티탭
    if (!(await drawFootage('hook', t, 0.06 * eInOut(t / 2.5)))) glTo2D('strip', t, t / 2.5);
    const f = lin(t, 2.15, 2.5);
    if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, W, H); }
    return 'hook';
  }
  if (phrase) {
    const lt = t - phrase.t0, u = lt / (phrase.t1 - phrase.t0);
    if (phrase.bg === 'build') {
      if (!(await drawFootage('build', Math.min(lt, 2.49), 0.1 * eInOut(u)))) glTo2D('flashlight', lt, u);
      const d = eInOut(lin(t, 14.2, 14.85));
      if (d > 0) { ctx.fillStyle = `rgba(0,0,0,${d})`; ctx.fillRect(0, 0, W, H); }
    } else await drawFootage(phrase.bg, lt, 0.07 * eInOut(u));
    if (phrase.bg === 'op1') { const f = 1 - lin(t, 2.5, 2.85); if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, W, H); } }
    return 'opening';
  }
  if (word) {
    const lt = t - word.t, u = lt / BEAT;
    if (!(await drawFootage(word.bg, lt, 0.05 * u))) {
      if (hasGL(word.bg)) glTo2D(word.bg, lt, u); else draw2D(ctx, word.bg, lt, u, W, H, V);
    }
    return 'dropA';
  }
  if (t >= 25 && t < 35) {
    navyBG(t);
    const d = eInOut(lin(t, 34.5, 35.0));
    if (d > 0) { ctx.fillStyle = `rgba(0,0,0,${d})`; ctx.fillRect(0, 0, W, H); }
    return 'dropB';
  }
  if (t >= 35) { outroBG(t); return 'outro'; }
  return 'black';
}

// ---------------------------------------------------------------- fx
const grainC = document.createElement('canvas'); grainC.width = grainC.height = 384;
const gctx = grainC.getContext('2d');
const gimg = gctx.createImageData(384, 384);
function grain(frame, alpha) {
  let s = (frame * 9301 + 49297) % 233280;
  const d = gimg.data;
  for (let i = 0; i < d.length; i += 4) {
    s = (s * 9301 + 49297) % 233280;
    const v = (s / 233280) * 255;
    d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255;
  }
  gctx.putImageData(gimg, 0, 0);
  fctx.save();
  fctx.globalAlpha = alpha; fctx.globalCompositeOperation = 'overlay';
  fctx.fillStyle = fctx.createPattern(grainC, 'repeat');
  fctx.translate((frame * 131) % 384, (frame * 71) % 384);
  fctx.fillRect(-384, -384, W + 768, H + 768);
  fctx.restore();
}
function vignette(a) {
  const g = fctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.38, W / 2, H / 2, Math.hypot(W, H) * 0.6);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  fctx.fillStyle = g; fctx.fillRect(0, 0, W, H);
}
// 엔딩의 불씨 (훅의 스파크와 수미상관)
function ember(t) {
  const t0 = bt(70);
  if (t < t0 || t > t0 + 2.6) return;
  const a = t - t0;
  const x = W / 2 + Math.sin(a * 2.3) * 14, y = S(H - 70, H - 260) - a * S(150, 220);
  const life = clamp(1 - a / 2.6) * clamp(a / 0.15);
  const fl = 0.75 + 0.25 * Math.sin(a * 31) * Math.sin(a * 13);
  const g = fctx.createRadialGradient(x, y, 0, x, y, 26);
  g.addColorStop(0, `rgba(255,214,150,${0.95 * life * fl})`);
  g.addColorStop(0.18, `rgba(255,140,50,${0.55 * life * fl})`);
  g.addColorStop(1, 'rgba(255,90,20,0)');
  fctx.fillStyle = g; fctx.fillRect(x - 30, y - 30, 60, 60);
}

// ---------------------------------------------------------------- main
function nextFrame() { return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); }

window.renderFrame = async (t) => {
  const frame = Math.round(t * 30);
  const phrase = renderPhrase(t);
  const word = renderWord(t);
  const mode = await renderBG(t, phrase, word);
  renderPhone(t);
  renderOutro(t);
  fctx.clearRect(0, 0, W, H);
  if (mode === 'hook') { vignette(0.5); grain(frame, 0.05); }
  if (mode === 'opening' || mode === 'dropA') { vignette(0.38); grain(frame, 0.04); }
  if (mode === 'dropB') grain(frame, 0.03);
  ember(t);
  if (t >= 46.25) { fctx.fillStyle = `rgba(0,0,0,${eInOut(lin(t, 46.25, 47.5))})`; fctx.fillRect(0, 0, W, H); }
  await nextFrame();
  return mode;
};

// ---------------------------------------------------------------- boot
async function loadPage(p) {
  const el = p.el;
  await new Promise((r) => (el.contentDocument && el.contentDocument.readyState === 'complete' ? r() : el.addEventListener('load', r, { once: true })));
  p.win = el.contentWindow; p.doc = el.contentDocument;
  const d = p.doc;
  // 실제 기기처럼 Pretendard/Noto Sans KR 서체 공급, 전환 애니메이션·스크롤 등장효과는 프레임 결정성을 위해 끔
  const st = d.createElement('style');
  const pre = '../../node_modules/pretendard/dist/web/static/woff2/Pretendard-';
  st.textContent = [['300', 'Light'], ['400', 'Regular'], ['500', 'Medium'], ['600', 'SemiBold'], ['700', 'Bold'], ['800', 'ExtraBold']]
    .map(([w, n]) => `@font-face{font-family:Pretendard;font-weight:${w};src:url(${pre}${n}.woff2) format('woff2')}`).join('') +
    '*,*::before,*::after{transition:none!important;animation-duration:0s!important;animation-delay:0s!important;scroll-behavior:auto!important;caret-color:transparent!important}' +
    '[class*="reveal"]{opacity:1!important;transform:none!important;filter:none!important}' +
    'html,body{scrollbar-width:none}::-webkit-scrollbar{display:none}';
  d.head.appendChild(st);
  for (const w of ['400', '500', '700']) {
    const l = d.createElement('link'); l.rel = 'stylesheet';
    l.href = new URL(`../../node_modules/@fontsource/noto-sans-kr/${w}.css`, p.win.location.href).href; d.head.appendChild(l);
  }
  await new Promise((r) => setTimeout(r, 250));
  await Promise.all(['400', '500', '600', '700'].map((w) => d.fonts.load(`${w} 16px Pretendard`, '손해의 근거를 찾고 0123456789')));
  await d.fonts.ready;
}

async function boot() {
  await document.fonts.ready;
  await Promise.all(['500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 40px P`, '가나다0')));
  for (const k of Object.keys(PG)) await loadPage(PG[k]);
  precompute();
  if (Q.get('cg') !== '1') {
    try { const r = await fetch(`../build/footage/${V ? 'v' : 'h'}/manifest.json`); if (r.ok) FOOTAGE = await r.json(); } catch (e) { /* CG 사용 */ }
  }
  window.filmReady = true;
}
window.filmBoot = boot();
