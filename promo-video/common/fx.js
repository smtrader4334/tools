/*
 * Canvas effects: embers, smoke, dust, burning text, water drops/ripples.
 * All effects are stateless: draw(ctx, t) depends only on t and a seed, so
 * frames can be rendered out of order and in parallel.
 */
(function (global) {
  'use strict';
  const TAU = Math.PI * 2;
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, t) => a + (b - a) * t;

  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hash3(a, b = 0, c = 0) {
    let h = 2166136261 >>> 0;
    h = Math.imul(h ^ (a | 0), 16777619);
    h = Math.imul(h ^ (b | 0), 16777619);
    h = Math.imul(h ^ (c | 0), 16777619);
    h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995); h ^= h >>> 15;
    return (h >>> 0) / 4294967296;
  }
  const smooth = (f) => f * f * (3 - 2 * f);
  function noise1(x, seed = 0) {
    const i = Math.floor(x), f = x - i;
    return lerp(hash3(i, seed, 11), hash3(i + 1, seed, 11), smooth(f));
  }
  function noise2(x, y, seed = 0) {
    const i = Math.floor(x), j = Math.floor(y), fx = smooth(x - i), fy = smooth(y - j);
    const a = hash3(i, j, seed), b = hash3(i + 1, j, seed), c = hash3(i, j + 1, seed), d = hash3(i + 1, j + 1, seed);
    return lerp(lerp(a, b, fx), lerp(c, d, fx), fy);
  }
  function fbm2(x, y, seed = 0, oct = 5) {
    let s = 0, amp = 0.5, f = 1, n = 0;
    for (let o = 0; o < oct; o++) { s += amp * noise2(x * f, y * f, seed + o * 31); n += amp; amp *= 0.5; f *= 2.03; }
    return s / n;
  }

  function canvas(w, h) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    return c;
  }
  function radialSprite(size, stops) {
    const c = canvas(size, size), g = c.getContext('2d');
    const gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    for (const [o, col] of stops) gr.addColorStop(o, col);
    g.fillStyle = gr; g.fillRect(0, 0, size, size);
    return c;
  }

  /* ---------------------------------------------------------------- embers */
  class Embers {
    constructor(o = {}) {
      this.o = Object.assign({
        count: 240, seed: 7, x0: -100, x1: 2020, yBase: 1130, life: [3.5, 8.5], speed: [60, 170],
        acc: [0, 18], drift: [6, 48], freq: [0.12, 0.55], size: [0.9, 2.8], wind: 10, bokeh: 16,
      }, o);
      const r = rng(this.o.seed), O = this.o;
      this.p = [];
      for (let i = 0; i < O.count; i++) {
        const depth = r();
        this.p.push({
          life: lerp(O.life[0], O.life[1], r()), phase: r(), depth,
          sp: lerp(O.speed[0], O.speed[1], r()) * (0.55 + depth * 0.75),
          acc: lerp(O.acc[0], O.acc[1], r()),
          dr: lerp(O.drift[0], O.drift[1], r()), fr: lerp(O.freq[0], O.freq[1], r()), ph: r() * TAU,
          size: lerp(O.size[0], O.size[1], Math.pow(r(), 1.8)) * (0.6 + depth * 0.9),
          bright: 0.55 + 0.45 * r(),
        });
      }
      this.b = [];
      for (let i = 0; i < O.bokeh; i++) {
        this.b.push({ life: lerp(7, 13, r()), phase: r(), sp: lerp(25, 70, r()), size: lerp(14, 46, r()), dr: lerp(20, 80, r()), fr: lerp(0.05, 0.15, r()), ph: r() * TAU, a: lerp(0.05, 0.14, r()) });
      }
      this.glow = radialSprite(64, [[0, 'rgba(255,236,190,1)'], [0.12, 'rgba(255,188,96,0.85)'], [0.38, 'rgba(255,112,32,0.28)'], [1, 'rgba(255,60,0,0)']]);
      this.disc = radialSprite(128, [[0, 'rgba(255,170,90,0.9)'], [0.55, 'rgba(255,140,60,0.75)'], [0.8, 'rgba(255,120,40,0.35)'], [1, 'rgba(255,100,30,0)']]);
    }
    draw(ctx, t, k = 1, o = {}) {
      if (k <= 0.002) return;
      const O = this.o, H = o.yBase ?? O.yBase;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.lineCap = 'round';
      for (let i = 0; i < this.p.length; i++) {
        const q = this.p[i], L = q.life, tt = t + q.phase * L, cyc = Math.floor(tt / L), age = tt - cyc * L, u = age / L;
        const x0 = lerp(O.x0, O.x1, hash3(i, cyc, 1));
        const y = H - q.sp * age - 0.5 * q.acc * age * age - hash3(i, cyc, 2) * 60;
        const x = x0 + q.dr * Math.sin(TAU * q.fr * age + q.ph) + O.wind * age + (noise1(age * 0.9 + i * 3.1, i) - 0.5) * 36;
        const vy = -(q.sp + q.acc * age);
        const vx = q.dr * TAU * q.fr * Math.cos(TAU * q.fr * age + q.ph) + O.wind;
        const flick = 0.5 + 0.5 * noise1(t * 7 + i * 7.3, i + 99);
        const a = Math.pow(Math.sin(Math.PI * u), 0.55) * flick * k * q.bright;
        if (a < 0.01) continue;
        const s = q.size * (1 - 0.45 * u);
        ctx.globalAlpha = a * 0.75;
        ctx.drawImage(this.glow, x - s * 7, y - s * 7, s * 14, s * 14);
        const hot = 1 - u;
        const cr = 255, cg = Math.round(lerp(90, 225, hot * hot)), cb = Math.round(lerp(25, 150, hot * hot * hot));
        ctx.strokeStyle = `rgb(${cr},${cg},${cb})`;
        ctx.lineWidth = s * 0.9;
        ctx.globalAlpha = a;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - vx * 0.03, y - vy * 0.03); ctx.stroke();
      }
      for (let i = 0; i < this.b.length; i++) {
        const q = this.b[i], L = q.life, tt = t + q.phase * L, cyc = Math.floor(tt / L), age = tt - cyc * L, u = age / L;
        const x = lerp(O.x0, O.x1, hash3(i, cyc, 5)) + q.dr * Math.sin(TAU * q.fr * age + q.ph);
        const y = H + 40 - q.sp * age - hash3(i, cyc, 6) * 300;
        const a = Math.sin(Math.PI * u) * q.a * k;
        ctx.globalAlpha = a;
        ctx.drawImage(this.disc, x - q.size, y - q.size, q.size * 2, q.size * 2);
      }
      ctx.restore();
    }
  }

  /* ----------------------------------------------------------------- smoke */
  class Smoke {
    constructor(o = {}) {
      this.o = Object.assign({ count: 14, seed: 3, x0: -200, x1: 2100, yBase: 1250, rise: [25, 60], life: [12, 20], size: [520, 980], alpha: 0.07, tint: [190, 160, 140], textures: 4 }, o);
      const r = rng(this.o.seed), O = this.o;
      this.tex = [];
      for (let k = 0; k < O.textures; k++) this.tex.push(this.makeTex(160, O.seed * 13 + k * 7, O.tint));
      this.p = [];
      for (let i = 0; i < O.count; i++) {
        this.p.push({ life: lerp(O.life[0], O.life[1], r()), phase: r(), rise: lerp(O.rise[0], O.rise[1], r()), size: lerp(O.size[0], O.size[1], r()), rot: r() * TAU, w: (r() - 0.5) * 0.06, tex: Math.floor(r() * O.textures), drift: (r() - 0.5) * 30 });
      }
    }
    makeTex(n, seed, tint) {
      const c = canvas(n, n), g = c.getContext('2d'), img = g.createImageData(n, n), d = img.data;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const dx = x / n - 0.5, dy = y / n - 0.5, r = Math.sqrt(dx * dx + dy * dy) * 2;
        const fall = clamp(1 - r); const f = fbm2(x / n * 4, y / n * 4, seed, 5);
        const a = clamp((f - 0.35) * 2.2) * fall * fall;
        const i = (y * n + x) * 4;
        d[i] = tint[0]; d[i + 1] = tint[1]; d[i + 2] = tint[2]; d[i + 3] = Math.round(a * 255);
      }
      g.putImageData(img, 0, 0);
      return c;
    }
    draw(ctx, t, k = 1, mode = 'screen') {
      if (k <= 0.002) return;
      const O = this.o;
      ctx.save();
      ctx.globalCompositeOperation = mode;
      for (let i = 0; i < this.p.length; i++) {
        const q = this.p[i], L = q.life, tt = t + q.phase * L, cyc = Math.floor(tt / L), age = tt - cyc * L, u = age / L;
        const x = lerp(O.x0, O.x1, hash3(i, cyc, 21)) + q.drift * age;
        const y = O.yBase - q.rise * age - hash3(i, cyc, 22) * 400;
        const s = q.size * (0.7 + 0.8 * u);
        ctx.globalAlpha = Math.sin(Math.PI * u) * O.alpha * k;
        ctx.setTransform(1, 0, 0, 1, x, y);
        ctx.rotate(q.rot + q.w * age);
        ctx.drawImage(this.tex[q.tex], -s / 2, -s / 2, s, s);
      }
      ctx.restore();
    }
  }

  /* ------------------------------------------------------------------ dust */
  class Dust {
    constructor(o = {}) {
      this.o = Object.assign({ count: 70, seed: 5, w: 1920, h: 1080, color: '232,208,138', size: [0.8, 2.2], speed: 10, alpha: 0.5 }, o);
      const r = rng(this.o.seed), O = this.o;
      this.p = [];
      for (let i = 0; i < O.count; i++) this.p.push({ x: r() * O.w, y: r() * O.h, vx: (r() - 0.5) * O.speed, vy: (r() - 0.7) * O.speed, s: lerp(O.size[0], O.size[1], r()), tw: lerp(0.2, 0.8, r()), ph: r() * TAU, a: lerp(0.3, 1, r()) });
      this.sprite = radialSprite(32, [[0, `rgba(${O.color},1)`], [0.3, `rgba(${O.color},0.5)`], [1, `rgba(${O.color},0)`]]);
    }
    draw(ctx, t, k = 1) {
      if (k <= 0.002) return;
      const O = this.o;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (const q of this.p) {
        const x = ((q.x + q.vx * t) % O.w + O.w) % O.w, y = ((q.y + q.vy * t) % O.h + O.h) % O.h;
        const a = (0.55 + 0.45 * Math.sin(TAU * q.tw * t + q.ph)) * q.a * O.alpha * k;
        ctx.globalAlpha = a;
        ctx.drawImage(this.sprite, x - q.s * 4, y - q.s * 4, q.s * 8, q.s * 8);
      }
      ctx.restore();
    }
  }

  /* ------------------------------------------------------------ burn text */
  // Renders text lines on canvas; from `burnStart` the glyphs burn away
  // left-to-right with a glowing edge and release ember particles.
  class BurnText {
    constructor(o) {
      this.o = Object.assign({ w: 1920, h: 1080, step: 2, burnStart: 10, sweep: 2.0, jitter: 0.5, edge: 0.45, life: [1.4, 3.0], seed: 11, color: [244, 239, 230] }, o);
    }
    init() {
      const O = this.o;
      const src = canvas(O.w, O.h), g = src.getContext('2d');
      g.fillStyle = `rgb(${O.color.join(',')})`;
      g.textAlign = 'center';
      g.textBaseline = 'alphabetic';
      for (const L of O.lines) {
        g.font = L.font;
        if (L.spacing) g.letterSpacing = L.spacing;
        g.fillText(L.text, L.x, L.y);
      }
      this.src = src;
      const full = g.getImageData(0, 0, O.w, O.h).data;
      let x0 = O.w, y0 = O.h, x1 = 0, y1 = 0;
      for (let y = 0; y < O.h; y++) for (let x = 0; x < O.w; x++) {
        if (full[(y * O.w + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      }
      x0 = Math.max(0, x0 - 4); y0 = Math.max(0, y0 - 4); x1 = Math.min(O.w - 1, x1 + 4); y1 = Math.min(O.h - 1, y1 + 4);
      const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
      Object.assign(this, { x0, y0, bw, bh });
      this.alpha = new Uint8Array(bw * bh);
      this.delay = new Float32Array(bw * bh);
      for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
        const i = y * bw + x;
        this.alpha[i] = full[((y + y0) * O.w + (x + x0)) * 4 + 3];
        const n = fbm2((x + x0) * 0.012, (y + y0) * 0.012, O.seed, 4);
        this.delay[i] = O.burnStart + (x / bw) * O.sweep + (n - 0.5) * 2 * O.jitter + (1 - y / bh) * 0.15;
      }
      this.buf = canvas(bw, bh);
      this.bctx = this.buf.getContext('2d');
      this.img = this.bctx.createImageData(bw, bh);
      const r = rng(O.seed + 1);
      this.parts = [];
      for (let y = 0; y < bh; y += O.step) for (let x = 0; x < bw; x += O.step) {
        const i = y * bw + x;
        if (this.alpha[i] < 110) continue;
        this.parts.push({ x: x + x0, y: y + y0, d: this.delay[i], life: lerp(O.life[0], O.life[1], r()), vx: (r() - 0.35) * 40, vy: -lerp(30, 120, r()), ph: r() * TAU, fr: lerp(0.4, 1.4, r()), amp: lerp(4, 22, r()), s: lerp(0.8, 2.0, r()) });
      }
      this.glow = radialSprite(32, [[0, 'rgba(255,220,160,1)'], [0.25, 'rgba(255,150,60,0.6)'], [1, 'rgba(255,80,10,0)']]);
    }
    // alpha/blur apply to the intact text (entrance animation)
    draw(ctx, t, alpha = 1, blur = 0) {
      const O = this.o;
      if (alpha <= 0.001) return;
      if (t < O.burnStart - O.jitter - O.edge - 0.05) {
        ctx.save();
        ctx.globalAlpha = alpha;
        if (blur > 0.05) ctx.filter = `blur(${blur.toFixed(2)}px)`;
        ctx.drawImage(this.src, 0, 0);
        ctx.restore();
        return;
      }
      const d = this.img.data, A = this.alpha, D = this.delay, edge = O.edge, c = O.color;
      for (let i = 0, n = A.length; i < n; i++) {
        const a0 = A[i], j = i * 4;
        if (a0 === 0) { d[j + 3] = 0; continue; }
        const rem = D[i] - t;
        if (rem <= 0) { d[j + 3] = 0; continue; }
        if (rem < edge) {
          const h = 1 - rem / edge, hh = Math.pow(h, 0.8);
          d[j] = lerp(c[0], 255, hh); d[j + 1] = lerp(c[1], lerp(200, 90, hh), hh); d[j + 2] = lerp(c[2], 20, hh);
          d[j + 3] = a0 * alpha * (rem < 0.08 ? rem / 0.08 : 1);
        } else {
          d[j] = c[0]; d[j + 1] = c[1]; d[j + 2] = c[2]; d[j + 3] = a0 * alpha;
        }
      }
      this.bctx.putImageData(this.img, 0, 0);
      ctx.save();
      ctx.drawImage(this.buf, this.x0, this.y0);
      ctx.globalCompositeOperation = 'lighter';
      for (const p of this.parts) {
        const age = t - p.d;
        if (age < 0 || age > p.life) continue;
        const u = age / p.life;
        const x = p.x + p.vx * age + Math.sin(TAU * p.fr * age + p.ph) * p.amp * u;
        const y = p.y + p.vy * age - 14 * age * age;
        const a = Math.pow(1 - u, 1.4) * alpha;
        const s = p.s * (1 - 0.5 * u);
        ctx.globalAlpha = a * 0.8;
        ctx.drawImage(this.glow, x - s * 4, y - s * 4, s * 8, s * 8);
      }
      ctx.restore();
    }
  }

  /* ------------------------------------------------------ drops & ripples */
  function drawDrop(ctx, x, y, r, alpha, stretch = 1) {
    if (alpha <= 0.001) return;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(1, stretch);
    ctx.globalAlpha = alpha;
    const g = ctx.createRadialGradient(-r * 0.35, r * 0.1, r * 0.1, 0, 0, r * 1.2);
    g.addColorStop(0, 'rgba(235,248,255,0.95)');
    g.addColorStop(0.5, 'rgba(140,200,235,0.55)');
    g.addColorStop(1, 'rgba(80,150,210,0.25)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(0, -r * 2.1);
    ctx.bezierCurveTo(r * 0.55, -r * 1.05, r, -r * 0.35, r, r * 0.25);
    ctx.arc(0, r * 0.25, r, 0, Math.PI, false);
    ctx.bezierCurveTo(-r, -r * 0.35, -r * 0.55, -r * 1.05, 0, -r * 2.1);
    ctx.fill();
    ctx.globalAlpha = alpha * 0.9;
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.beginPath();
    ctx.ellipse(-r * 0.38, r * 0.05, r * 0.16, r * 0.3, -0.3, 0, TAU);
    ctx.fill();
    ctx.restore();
  }
  // Concentric rings from an impact at time t0 (perspective ellipses).
  function drawRipples(ctx, t, t0, x, y, o = {}) {
    const age = t - t0;
    if (age < 0) return;
    const rings = o.rings ?? 4, speed = o.speed ?? 170, life = o.life ?? 3.2, persp = o.persp ?? 0.28, color = o.color ?? '170,215,240';
    ctx.save();
    for (let k = 0; k < rings; k++) {
      const a0 = age - k * (o.gap ?? 0.22);
      if (a0 < 0 || a0 > life) continue;
      const u = a0 / life;
      const r = speed * a0 * (1 - 0.25 * u) + 4;
      const a = Math.pow(1 - u, 1.6) * (1 - k * 0.18) * (o.alpha ?? 0.9);
      ctx.globalAlpha = a;
      ctx.strokeStyle = `rgba(${color},1)`;
      ctx.lineWidth = lerp(2.4, 0.8, u) * (o.width ?? 1);
      ctx.beginPath();
      ctx.ellipse(x, y, r, r * persp, 0, 0, TAU);
      ctx.stroke();
    }
    ctx.restore();
  }

  global.FX = { rng, hash3, noise1, noise2, fbm2, canvas, radialSprite, Embers, Smoke, Dust, BurnText, drawDrop, drawRipples, TAU, clamp, lerp };
})(window);
