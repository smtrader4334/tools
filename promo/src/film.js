// 더함 브랜드 필름 — 프레임 단위 렌더러.
// window.renderFrame(t) 가 t초의 화면을 결정적으로 그린다. (render.mjs 가 매 프레임 호출)
import { initGL, drawGL, hasGL } from './scenes-gl.js';
import { draw2D } from './scenes-2d.js';

const Q = new URLSearchParams(location.search);
const V = Q.get('fmt') === 'v';
const W = V ? 1080 : 1920;
const H = V ? 1920 : 1080;
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- utils
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, u) => a + (b - a) * u;
const lin = (t, a, b) => clamp((t - a) / (b - a));
const eOutExpo = (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u));
const eOutCubic = (u) => 1 - Math.pow(1 - u, 3);
const eInCubic = (u) => u * u * u;
const eInOut = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const S = (h, v) => (V && v !== undefined ? v : h); // 포맷별 값

// ---------------------------------------------------------------- stage
const stage = $('stage');
stage.style.width = W + 'px';
stage.style.height = H + 'px';
const c2 = $('c2'), fx = $('fx'), gl = $('gl');
for (const c of [c2, fx]) { c.width = W; c.height = H; }
const ctx = c2.getContext('2d');
const fctx = fx.getContext('2d');
const GLS = 0.5; // WebGL 내부 해상도 배율 (업스케일)
gl.width = Math.round(W * GLS); gl.height = Math.round(H * GLS);
gl.style.display = 'none';
initGL(gl);

// ---------------------------------------------------------------- word cues
const buildLine = (words, n, br = []) =>
  words.map((w, i) => (br.includes(i) ? '<br>' : '') + `<span class="${i < n ? '' : 'ghost'}">${w}</span>`).join(' ');

const OPEN = 205, BIG = S(230, 200);
const CUES = [
  { t: 2.0, html: '누구에게나', hit: 1 },
  { t: 2.5, html: '그날은', hit: 1 },
  { t: 3.0, html: '옵니다.', hit: 1, end: 3.75 },
  { t: 4.0, html: '물이 새고,', hit: 1 },
  { t: 4.5, html: '불이 나고,', hit: 1 },
  { t: 5.0, html: '보험사에', hit: 1 },
  { t: 5.5, html: '전화합니다.', hit: 1 },
  { t: 6.0, html: '며칠 뒤,', hit: 1 },
  { t: 6.5, html: '통보된 금액', hit: 1 },
  { t: 7.0, money: true, hit: 1, end: 8.0 },
  { t: 8.0, html: buildLine(['이게,', '맞나요?'], 1), hit: 1 },
  { t: 8.5, html: buildLine(['이게,', '맞나요?'], 2), hit: 1, anim: 'add', end: 10.0, push: 0.05 },
  { t: 10.0, html: S('보험사 손해사정사는', '보험사<br>손해사정사는'), hit: 1, end: 11.0, push: 0.02 },
  { t: 11.0, html: S('<span class="red">보험사</span><span class="ghost"> 직원입니다.</span>', '<span class="red">보험사</span><br><span class="ghost">직원입니다.</span>'), hit: 1 },
  { t: 11.5, html: S('<span class="red">보험사</span> 직원입니다.', '<span class="red">보험사</span><br>직원입니다.'), hit: 2, anim: 'add', end: 12.0 },
  // build
  ...[1, 2, 3, 4].map((n, i) => ({
    t: 12.0 + i * 0.5,
    html: buildLine(['그럼,', '누가', '내 편에', '서죠?'], n, V ? [2] : []),
    hit: 1, anim: i ? 'add' : 'slam', size: S(170, 190),
    end: i === 3 ? 15.5 : undefined, build: i === 3,
  })),
  // drop A — 한 박자에 한 단어
  ...[
    ['불.', 'fire'], ['물.', 'water'], ['그을음.', 'soot'], ['균열.', 'crack'],
    ['현장.', 'flashlight'], ['측정.', 'tape'], ['도면.', 'blueprint'], ['산정.', 'numbers'],
    ['누락.', 'missing'], ['근거.', 'documents'], ['협상.', 'negotiate'], ['합의.', 'agree'],
    ['복구.', 'paint'], ['일상.', 'sunlight'], ['제자리.', 'home'], ['<span class="gold">당신 편.</span>', 'gold'],
  ].map(([html, bg], i) => ({ t: 16 + i * 0.5, html, bg, anim: 'cut', size: BIG, shadow: bg !== 'gold' })),
];
for (let i = 0; i < CUES.length; i++) {
  const c = CUES[i];
  if (c.end === undefined) c.end = CUES[i + 1] ? Math.min(CUES[i + 1].t, c.t + 2) : c.t + 0.5;
}

// ---------------------------------------------------------------- word layer
const wordEl = $('word'), wordsEl = $('words');
function fitSize(el, html, base, maxW) {
  el.style.fontSize = base + 'px';
  el.innerHTML = html.replace(/class="ghost"/g, '');
  const w = el.scrollWidth;
  const s = w > maxW ? base * (maxW / w) : base;
  return s;
}
const MAXW = S(1640, 960);

function money(t) {
  const a = 8400000, b = 3200000;
  const u = eInOut(lin(t, 7.06, 7.44));
  let v = lerp(a, b, u);
  v = t >= 7.44 ? b : Math.round(v / 10000) * 10000;
  return '₩' + v.toLocaleString('en-US');
}

function renderWords(t) {
  const c = CUES.find((c) => t >= c.t && t < c.end);
  if (!c) { wordEl.style.opacity = 0; wordEl.innerHTML = ''; return null; }
  const u = t - c.t;
  const base = c.size || (c.bg ? BIG : OPEN);
  let html = c.money ? money(t) : c.html;
  let size = fitSize(wordEl, c.money ? '₩8,400,000' : html, base, MAXW);
  wordEl.innerHTML = html;
  wordEl.style.fontSize = size + 'px';
  wordEl.className = c.shadow ? 'shadow' : '';
  if (c.money && t >= 7.5) wordEl.style.color = 'var(--red)'; else wordEl.style.color = '';

  let sc = 1, op = 1, bl = 0;
  const anim = c.anim || 'slam';
  if (anim === 'slam') { sc = 1 + 0.16 * (1 - eOutExpo(u / 0.22)); bl = 9 * (1 - clamp(u / 0.08)); op = clamp(u / 0.03 + 0.2); }
  if (anim === 'add') { sc = 1 + 0.025 * (1 - eOutExpo(u / 0.2)); }
  if (anim === 'cut') { sc = 1.07 - 0.07 * eOutExpo(u / 0.25); }
  if (c.money && t >= 7.5) sc *= 1 + 0.07 * (1 - eOutExpo((t - 7.5) / 0.2));
  if (c.push) sc *= 1 + c.push * eOutCubic(clamp(u / (c.end - c.t)));

  // 쾅: 흔들림
  let sx = 0, sy = 0;
  if (c.hit) {
    const amp = (c.hit === 2 ? 22 : 9) * Math.exp(-u * 13);
    const k = Math.floor(t * 60);
    sx = (hash(k) - 0.5) * 2 * amp; sy = (hash(k + 7.3) - 0.5) * 2 * amp;
  }
  // 빌드업: 서서히 밀고 들어가며 떨림 → 32분 음표 스트로브
  if (c.build) {
    const g = eInCubic(lin(t, 13.9, 15.5));
    sc *= 1 + 0.26 * g;
    const amp = 10 * g; const k = Math.floor(t * 60);
    sx += (hash(k + 3) - 0.5) * 2 * amp; sy += (hash(k + 9) - 0.5) * 2 * amp;
    if (t >= 15.0) op = Math.floor((t - 15.0) / 0.0625) % 2 === 0 ? 1 : 0.18;
  }
  wordEl.style.opacity = op;
  wordEl.style.filter = bl > 0.05 ? `blur(${bl}px)` : 'none';
  wordEl.style.transform = `translate(${sx}px,${sy}px) scale(${sc})`;
  return c;
}

// 예시 금액 표기
const note = $('note');
function renderNote(t) {
  const on = t >= 6.5 && t < 10.0;
  note.style.display = on ? 'block' : 'none';
  if (!on) return;
  note.textContent = '※ 연출된 예시 금액입니다';
  note.style.fontSize = S(22, 30) + 'px';
  note.style.left = '0'; note.style.width = '100%'; note.style.textAlign = 'center';
  note.style.top = (H - S(80, 150)) + 'px';
}

// ---------------------------------------------------------------- drop B: 실제 홈페이지 폰 화면
const site = $('site'), phone = $('phone'), rig = $('phoneRig');
const hl = $('hl'), tap = $('tap'), tapRing = $('tapRing'), kw = $('kw'), kwSub = $('kwSub');
let sw, sd, stickyBottom = 180;
const VH = 794; // 상태바 아래 실제 뷰포트 높이

const B = [
  { t: 24.0, kw: '그냥', scroll: 0, hl: ['.hero-question em'] },
  { t: 24.5, kw: '받으시겠습니까?', hl: ['.hero-question em'] },
  { t: 25.0, kw: '지점장', hl: ['.hero-cred'] },
  { t: 25.5, kw: '출신.', hl: ['.hero-cred'] },
  { t: 26.0, kw: '건축기사.', scroll: ['.cred-list li', 1], hl: ['.cred-list li', 1] },
  { t: 26.5, kw: '건설안전기사.', hl: ['.cred-list li', 1] },
  { t: 27.0, kw: '손실보상', hl: ['.cred-list li', 2] },
  { t: 27.5, kw: '심의위원.', hl: ['.cred-list li', 2] },
  { t: 28.0, kw: '화재.', scroll: ['.tab-nav', 0, 'top'], tap: ['.tab-btn', 0], hl: ['.tab-btn', 0] },
  { t: 28.5, kw: '조사.', scroll: ['#tab-fire .process-list'], hl: ['#tab-fire .process-list li', 0] },
  { t: 29.0, kw: '산정.', hl: ['#tab-fire .process-list li', 1] },
  { t: 29.5, kw: '협상.', hl: ['#tab-fire .process-list li', 2] },
  { t: 30.0, kw: '수령.', hl: ['#tab-fire .process-list li', 3] },
  { t: 30.5, kw: '누수.', scroll: ['.tab-nav', 0, 'top'], tap: ['.tab-btn', 1], hl: ['.tab-btn', 1] },
  { t: 31.0, kw: '선임권.', scroll: ['#tab-leak .info-card'], hl: ['#tab-leak .info-card'] },
  { t: 31.5, kw: '<span class="gold">0원.</span>', big: true, sub: '보험사 조사 착수 전 선임 시<br>손해사정 비용 → 보험회사 전액 부담', scroll: ['.cost-row', 0], hl: ['.cost-row', 0], end: 32.5 },
  { t: 32.5, kw: '빠를수록.', scroll: ['.timing-box'], hl: ['.timing-box'] },
  { t: 33.0, kw: '유리합니다.', hl: ['.timing-box'] },
  { t: 33.5, kw: '지금,', scroll: ['#tab-leak .kakao-btn'], hl: ['#tab-leak .kakao-btn'] },
  { t: 34.0, kw: '카톡으로.', tap: ['#tab-leak .kakao-btn'], hl: ['#tab-leak .kakao-btn'] },
  ...[1, 2, 3].map((n, i) => ({
    t: 34.5 + i * 0.5, kw: buildLine(['당신', '편에서', '싸웁니다.'], n, [2]), add: i > 0,
    scroll: i === 0 ? 0 : undefined, hl: ['.hero-cred'], end: i === 2 ? 36.0 : undefined,
  })),
];
for (let i = 0; i < B.length; i++) if (B[i].end === undefined) B[i].end = B[i + 1] ? B[i + 1].t : 36;
const TAB_SWITCH = 30.58;

function q(sel, i = 0) { return sd.querySelectorAll(sel)[i]; }

function setTab(type) {
  const btns = sd.querySelectorAll('.tab-btn');
  const want = type === 'fire' ? 0 : 1;
  if (!btns[want].classList.contains('active')) sw.switchTab(btns[want], type);
}

// 각 컷의 목표 스크롤 위치를 미리 계산 (탭 상태별)
function precompute() {
  sw.scrollTo(0, 3000);
  stickyBottom = sd.querySelector('.tab-wrap').getBoundingClientRect().bottom;
  let target = 0;
  for (const c of B) {
    const tab = c.t >= TAB_SWITCH ? 'leak' : 'fire';
    setTab(tab);
    sw.scrollTo(0, 0);
    const max = sd.documentElement.scrollHeight - VH;
    if (c.scroll !== undefined) {
      if (c.scroll === 0) target = 0;
      else {
        const [sel, i = 0, mode] = c.scroll;
        const r = q(sel, i).getBoundingClientRect();
        if (mode === 'top') target = r.top - 150; // 탭이 화면 위쪽에 붙기 직전
        else target = r.top + r.height / 2 - (stickyBottom + VH) / 2;
        target = clamp(Math.round(target), 0, max);
      }
    }
    c.target = target;
  }
  setTab('fire');
  sw.scrollTo(0, 0);
}

function renderPhone(t) {
  const on = t >= 24 && t < 36;
  rig.style.visibility = on ? 'visible' : 'hidden';
  if (!on) return;
  const i = B.findIndex((c) => t >= c.t && t < c.end);
  const c = B[Math.max(0, i)];

  // 탭 상태
  setTab(t >= TAB_SWITCH ? 'leak' : 'fire');

  // 스크롤: 박자 직전에 휙 넘어가서 박자에 안착
  let y = B[0].target;
  let vel = 0;
  for (let k = 1; k < B.length; k++) {
    const p = B[k - 1].target, n = B[k].target;
    if (p === n) continue;
    const a = B[k].t - 0.17, b = B[k].t + 0.05;
    if (t >= b) y = n;
    else if (t > a) { const u = lin(t, a, b); y = lerp(p, n, eInOut(u)); vel = Math.abs(n - p) / (b - a); }
  }
  sw.scrollTo(0, Math.round(y));
  site.style.filter = vel > 1500 ? `blur(${Math.min(2.2, vel / 4000)}px)` : 'none';

  // 폰 배치 + 등장
  const s = S(1.2, 1.2);
  const pw = 418 * s, ph = 872 * s;
  let px = S(620 - pw / 2, 540 - pw / 2), py = S(64, H - ph - 110);
  const ein = eOutExpo(lin(t, 24.0, 24.42));
  py += (1 - ein) * H * 0.75;
  const rot = (1 - ein) * 7;
  const floatY = Math.sin(t * 1.3) * 5;
  phone.style.transform = `translate(${px}px,${py + floatY}px) rotate(${rot}deg) scale(${s})`;

  // 하이라이트
  if (c.hl) {
    const el = q(c.hl[0], c.hl[1] || 0);
    const r = el.getBoundingClientRect();
    const pad = 8;
    const prev = B[i - 1];
    const fresh = !prev || !prev.hl || prev.hl.join() !== c.hl.join();
    const u = t - c.t;
    const pop = fresh ? eOutExpo(clamp(u / 0.16)) : 1;
    const g = 1 + 0.06 * (1 - pop);
    hl.style.display = 'block';
    hl.style.left = r.left - pad + 'px'; hl.style.top = r.top + 50 - pad + 'px';
    hl.style.width = r.width + pad * 2 - 6 + 'px'; hl.style.height = r.height + pad * 2 - 6 + 'px';
    hl.style.transform = `scale(${g})`;
    hl.style.opacity = fresh ? clamp(u / 0.06) : 1;
  } else hl.style.display = 'none';

  // 탭 터치
  const tc = B.find((b) => b.tap && t >= b.t - 0.08 && t < b.t + 0.45);
  if (tc) {
    const r = q(tc.tap[0], tc.tap[1] || 0).getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + 50 + r.height / 2;
    const u = t - tc.t;
    tap.style.display = 'block'; tapRing.style.display = 'block';
    tap.style.left = tapRing.style.left = cx + 'px';
    tap.style.top = tapRing.style.top = cy + 'px';
    tap.style.opacity = u < 0 ? clamp((u + 0.08) / 0.05) : clamp(1 - (u - 0.12) / 0.12);
    tap.style.transform = `scale(${u < 0 ? 1.15 : 0.9})`;
    const ur = clamp(u / 0.4);
    tapRing.style.opacity = u < 0 ? 0 : 0.9 * (1 - ur);
    tapRing.style.transform = `scale(${1 + 1.6 * eOutCubic(ur)})`;
  } else { tap.style.display = 'none'; tapRing.style.display = 'none'; }

  // 키워드
  const u = t - c.t;
  let base = c.big ? S(300, 230) : S(150, 150);
  const maxW = S(820, 960);
  kw.style.fontSize = base + 'px';
  kw.innerHTML = c.kw.replace(/class="ghost"/g, '');
  const w0 = kw.scrollWidth;
  const size = w0 > maxW ? base * maxW / w0 : base;
  kw.style.fontSize = size + 'px';
  kw.innerHTML = c.kw;
  const kwW = kw.scrollWidth, kwH = kw.scrollHeight;
  const fresh = !c.add;
  const sc = fresh ? 1 + 0.12 * (1 - eOutExpo(u / 0.22)) : 1 + 0.02 * (1 - eOutExpo(u / 0.2));
  const kx = S(1040, (W - kwW) / 2), ky = S(H / 2 - kwH / 2 - (c.sub ? 50 : 0), S(0, c.sub ? 360 : 440) - kwH / 2);
  kw.style.left = kx + 'px'; kw.style.top = ky + 'px';
  kw.style.transformOrigin = V ? '50% 50%' : '0% 50%';
  kw.style.transform = `scale(${sc})`;
  kw.style.opacity = fresh ? clamp(u / 0.03 + 0.2) : 1;
  kw.style.textAlign = V ? 'center' : 'left';
  if (c.sub) {
    kwSub.style.display = 'block';
    kwSub.innerHTML = c.sub;
    kwSub.style.fontSize = S(34, 36) + 'px';
    kwSub.style.lineHeight = 1.45;
    kwSub.style.textAlign = V ? 'center' : 'left';
    kwSub.style.left = S(kx + 8, 0) + 'px';
    kwSub.style.width = V ? W + 'px' : 'auto';
    kwSub.style.top = ky + kwH + S(10, 16) + 'px';
    kwSub.style.opacity = clamp((u - 0.12) / 0.2);
  } else kwSub.style.display = 'none';
}

// ---------------------------------------------------------------- outro
const endcard = $('endcard'), logoWrap = $('logoWrap'), sheen = $('logoSheen');
const brand = $('brandname'), cta = $('cta'), ring = $('ring'), tagline = $('tagline');
const LOGO_H = S(250, 300), LOGO_CY = S(372, 770);
const TAG_Y = S(602, 1045), TAG_FS = 64, LINE_FS = S(190, 150);

function renderOutro(t) {
  const on = t >= 36;
  endcard.style.display = on && t >= 38.9 ? 'block' : 'none';
  tagline.style.display = on && t >= 36.5 ? 'block' : 'none';
  if (!on) return;
  // 브랜드 한 줄
  if (t >= 36.5) {
    const n = t >= 37.5 ? 2 : 1;
    const html = V
      ? buildLine(['빠진 것을,', '<span class="goldtxt">더합니다.</span>'], n, [1])
      : buildLine(['빠진 것을,', '<span class="goldtxt">더합니다.</span>'], n);
    tagline.innerHTML = html;
    tagline.style.fontSize = LINE_FS + 'px';
    tagline.style.lineHeight = 1.08;
    const hgt = tagline.scrollHeight;
    const u1 = t - 36.5, u2 = t - 37.5;
    let sc = 1, op = 1, bl = 0;
    if (n === 1) { sc = 1 + 0.05 * (1 - eOutExpo(u1 / 0.5)); op = clamp(u1 / 0.12); bl = 6 * (1 - clamp(u1 / 0.2)); }
    else sc = 1 + 0.02 * (1 - eOutExpo(u2 / 0.25));
    // 39.0 로고 등장과 함께 태그라인이 아래로 내려가며 작아짐
    const m = eInOut(lin(t, 38.85, 39.75));
    const finalScale = TAG_FS / LINE_FS * (V ? 1.25 : 1);
    sc *= lerp(1, finalScale, m);
    const cy = lerp(H / 2, TAG_Y, m);
    tagline.style.top = cy - hgt / 2 + 'px';
    tagline.style.transform = `scale(${sc})`;
    tagline.style.transformOrigin = '50% 50%';
    tagline.style.opacity = op;
    tagline.style.filter = bl > 0.05 ? `blur(${bl}px)` : 'none';
    if (V && m > 0.5) tagline.innerHTML = '빠진 것을, <span class="goldtxt">더합니다.</span>';
  }
  if (t < 38.9) return;
  // 로고
  const lw = LOGO_H * 1328 / 1151;
  logoWrap.style.width = lw + 'px'; logoWrap.style.height = LOGO_H + 'px';
  logoWrap.style.marginLeft = -lw / 2 + 'px';
  logoWrap.style.top = LOGO_CY - LOGO_H / 2 + 'px';
  const lu = t - 39.0;
  logoWrap.style.opacity = clamp(lu / 0.7);
  logoWrap.style.transform = `scale(${lerp(0.92, 1, eOutCubic(clamp(lu / 1.8)))})`;
  logoWrap.style.filter = lu < 0.6 ? `blur(${10 * (1 - clamp(lu / 0.6))}px)` : 'none';
  sheen.style.backgroundPosition = `${lerp(160, -60, eInOut(lin(t, 39.35, 40.7)))}% 0`;
  // 상호
  brand.style.fontSize = S(32, 40) + 'px';
  brand.style.top = S(672, 1128) + 'px';
  const bu = lin(t, 40.5, 41.3);
  brand.style.opacity = bu;
  brand.style.letterSpacing = lerp(0.34, 0.14, eOutCubic(bu)) + 'em';
  // 상담
  cta.style.fontSize = S(26, 32) + 'px';
  cta.style.top = S(738, 1208) + 'px';
  cta.style.opacity = lin(t, 41.5, 42.2);
  // 물방울 파문 (44.0)
  if (t >= 44.0) {
    const ru = lin(t, 44.0, 45.8);
    const r = lerp(20, S(900, 900), eOutCubic(ru));
    ring.style.display = 'block';
    ring.style.width = ring.style.height = r * 2 + 'px';
    ring.style.left = W / 2 - r + 'px'; ring.style.top = LOGO_CY - r + 'px';
    ring.style.opacity = 0.7 * (1 - ru);
  } else ring.style.display = 'none';
}

// ---------------------------------------------------------------- backgrounds + fx
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
  fctx.globalAlpha = alpha;
  fctx.globalCompositeOperation = 'overlay';
  fctx.fillStyle = fctx.createPattern(grainC, 'repeat');
  fctx.translate((frame * 131) % 384, (frame * 71) % 384);
  fctx.fillRect(-384, -384, W + 768, H + 768);
  fctx.restore();
}
function vignette(a) {
  const g = fctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.hypot(W, H) * 0.6);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  fctx.fillStyle = g; fctx.fillRect(0, 0, W, H);
}

function navyBG(t) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#15142B'); g.addColorStop(1, '#07070F');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  const gx = S(W * 0.72, W * 0.5) + Math.sin(t * 0.7) * 60, gy = S(H * 0.4, H * 0.22);
  const r = ctx.createRadialGradient(gx, gy, 0, gx, gy, S(900, 900));
  r.addColorStop(0, 'rgba(201,168,76,0.20)'); r.addColorStop(1, 'rgba(201,168,76,0)');
  ctx.fillStyle = r; ctx.fillRect(0, 0, W, H);
  const r2 = ctx.createRadialGradient(S(600, 540), S(H / 2, H * 0.62), 0, S(600, 540), S(H / 2, H * 0.62), 700);
  r2.addColorStop(0, 'rgba(70,64,150,0.30)'); r2.addColorStop(1, 'rgba(70,64,150,0)');
  ctx.fillStyle = r2; ctx.fillRect(0, 0, W, H);
}

function glTo2D(key, lt, u) {
  // WebGL 결과를 2D 캔버스 하나에 합성 (캔버스 겹침으로 인한 잔상 방지)
  if (!drawGL(key, lt, u)) return false;
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(gl, 0, 0, W, H);
  return true;
}

// 실사 클립 프레임 (src/footage.py 가 만든 build/footage/<fmt>/<장면>/NN.jpg). 없으면 CG 장면 사용
let FOOTAGE = {};
const imgCache = new Map();
async function footageFrame(key, idx) {
  const url = `../build/footage/${V ? 'v' : 'h'}/${key}/${String(idx + 1).padStart(2, '0')}.jpg`;
  let im = imgCache.get(url);
  if (!im) { im = new Image(); im.src = url; imgCache.set(url, im); }
  await im.decode();
  if (imgCache.size > 40) imgCache.delete(imgCache.keys().next().value);
  return im;
}

async function renderBG(t, cue) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  if (t < 1.5) { glTo2D('hook', t, t / 1.5); return 'hook'; }
  if (t >= 16 && t < 24 && cue && cue.bg) {
    const lt = t - cue.t, u = lt / 0.5;
    const f = FOOTAGE[cue.bg];
    if (f) {
      const im = await footageFrame(cue.bg, Math.min(f.frames - 1, Math.floor(lt * 30 + 1e-6)));
      const s = 1 + 0.05 * u; // 느린 푸시인
      ctx.save();
      ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
      ctx.drawImage(im, 0, 0, W, H);
      ctx.restore();
      if (f.dim) { ctx.fillStyle = `rgba(0,0,0,${f.dim})`; ctx.fillRect(0, 0, W, H); }
    } else if (hasGL(cue.bg)) glTo2D(cue.bg, lt, u);
    else draw2D(ctx, cue.bg, lt, u, W, H, V);
    return 'dropA';
  }
  if (t >= 24 && t < 36) { navyBG(t); return 'dropB'; }
  return 'black';
}

// ---------------------------------------------------------------- main
function nextFrame() { return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); }

window.renderFrame = async (t) => {
  const frame = Math.round(t * 30);
  const cue = renderWords(t);
  renderNote(t);
  const mode = await renderBG(t, cue);
  renderPhone(t);
  renderOutro(t);
  // fx
  fctx.clearRect(0, 0, W, H);
  if (mode === 'hook' || mode === 'dropA') { vignette(0.55); grain(frame, 0.10); }
  if (mode === 'dropB') grain(frame, 0.05);
  if (t >= 45.0) { fctx.fillStyle = `rgba(0,0,0,${eInOut(lin(t, 45.0, 46.0))})`; fctx.fillRect(0, 0, W, H); }
  await nextFrame();
  return mode;
};

// ---------------------------------------------------------------- boot
async function boot() {
  await document.fonts.ready;
  await Promise.all(['800', '700', '600', '500'].map((w) => document.fonts.load(`${w} 40px P`, '가나다₩0')));
  await new Promise((r) => (site.contentDocument && site.contentDocument.readyState === 'complete' && site.contentWindow.switchTab ? r() : site.addEventListener('load', r, { once: true })));
  sw = site.contentWindow; sd = site.contentDocument;
  // 실제 폰과 같은 서체(Noto Sans/Serif KR)를 로컬 파일로 공급, 전환 애니메이션은 프레임 결정성을 위해 끔
  const css = ['300', '400', '500', '700'].map((w) => `../promo/node_modules/@fontsource/noto-sans-kr/${w}.css`)
    .concat(['400', '600', '700'].map((w) => `../promo/node_modules/@fontsource/noto-serif-kr/${w}.css`));
  for (const href of css) {
    const l = sd.createElement('link'); l.rel = 'stylesheet'; l.href = new URL(href, sw.location.href).href; sd.head.appendChild(l);
  }
  const st = sd.createElement('style');
  st.textContent = '*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important;caret-color:transparent!important}html,body{scrollbar-width:none}::-webkit-scrollbar{display:none}';
  sd.head.appendChild(st);
  await new Promise((r) => setTimeout(r, 300));
  await sd.fonts.ready;
  await Promise.all(['300', '400', '500', '700'].map((w) => sd.fonts.load(`${w} 16px "Noto Sans KR"`, '보험사가 제시한 금액 0123456789')));
  await sd.fonts.ready;
  precompute();
  if (Q.get('cg') !== '1') {
    try { const r = await fetch(`../build/footage/${V ? 'v' : 'h'}/manifest.json`); if (r.ok) FOOTAGE = await r.json(); } catch (e) { /* CG 사용 */ }
  }
  window.filmReady = true;
}
window.filmBoot = boot();
