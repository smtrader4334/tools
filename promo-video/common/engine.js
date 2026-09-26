/*
 * Deterministic timeline engine for frame-by-frame video rendering.
 *
 * Every visual state is a pure function of time `t` (seconds), so any frame
 * can be rendered in any order: the renderer calls `film.seek(t)` and takes a
 * screenshot. Opening the page in a normal browser plays it in real time
 * (space = play/pause, arrow keys = seek, ?t=12.5 jumps to a timestamp).
 */
(function (global) {
  'use strict';

  const E = {
    lin: (t) => t,
    inQuad: (t) => t * t,
    outQuad: (t) => 1 - (1 - t) * (1 - t),
    inOutQuad: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
    inCubic: (t) => t * t * t,
    outCubic: (t) => 1 - Math.pow(1 - t, 3),
    inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outQuart: (t) => 1 - Math.pow(1 - t, 4),
    inOutQuart: (t) => (t < 0.5 ? 8 * t ** 4 : 1 - Math.pow(-2 * t + 2, 4) / 2),
    outQuint: (t) => 1 - Math.pow(1 - t, 5),
    inOutQuint: (t) => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2),
    outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    inOutExpo: (t) =>
      t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,
    inSine: (t) => 1 - Math.cos((t * Math.PI) / 2),
    outSine: (t) => Math.sin((t * Math.PI) / 2),
    inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
    outBack: (t) => {
      const c1 = 1.4, c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    },
  };

  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, t) => a + (b - a) * t;
  // Eased progress of a tween that starts at t0 and lasts d seconds.
  const P = (t, t0, d, e = E.outCubic) => e(clamp((t - t0) / d));
  // Fade-in/hold/fade-out envelope between tin and tout.
  function env(t, tin, tout, fin = 0.8, fout = 0.6, ei = E.outCubic, eo = E.inCubic) {
    if (t < tin || t > tout) return 0;
    const a = fin > 0 ? ei(clamp((t - tin) / fin)) : 1;
    const b = fout > 0 ? 1 - eo(clamp((t - (tout - fout)) / fout)) : 1;
    return Math.min(a, b);
  }
  // Damped spring settling from `from` to `to`, starting at t0.
  function spring(t, t0, from, to, freq = 1.6, damp = 4.2) {
    if (t <= t0) return from;
    const x = t - t0;
    return to + (from - to) * Math.exp(-damp * x) * Math.cos(2 * Math.PI * freq * x);
  }

  function setStyle(el, o) {
    if (!el) return;
    const s = el.style;
    const hidden = o.opacity !== undefined && o.opacity <= 0.001;
    const vis = hidden ? 'hidden' : 'visible';
    if (s.visibility !== vis) s.visibility = vis;
    if (hidden) return;
    if (o.opacity !== undefined) s.opacity = o.opacity.toFixed(4);
    if (o.transform !== undefined) s.transform = o.transform;
    if (o.filter !== undefined) s.filter = o.filter;
  }

  const blurCss = (b) => (b > 0.05 ? `blur(${b.toFixed(2)}px)` : 'none');

  /*
   * Standard text/element entrance + exit.
   * o.y: entrance rise (px), o.blur: entrance blur (px), o.scale: entrance scale,
   * o.fin/o.fout: durations, o.yOut/o.blurOut: exit drift, o.ls: letter-spacing
   * tightening in em.
   */
  function show(el, t, tin, tout, o = {}) {
    if (!el) return 0;
    const fin = o.fin ?? 1.0, fout = o.fout ?? 0.7;
    if (t < tin || t > tout) { setStyle(el, { opacity: 0 }); return 0; }
    const pi = P(t, tin, fin, o.ei || E.outQuart);
    const po = tout - t < fout ? P(t, tout - fout, fout, o.eo || E.inQuad) : 0;
    const y = (1 - pi) * (o.y ?? 26) - po * (o.yOut ?? 10);
    const x = (1 - pi) * (o.x ?? 0);
    const blur = (1 - pi) * (o.blur ?? 10) + po * (o.blurOut ?? 6);
    const sc = o.scale !== undefined ? lerp(o.scale, 1, pi) * (1 + po * (o.scaleOut ?? 0)) : 1 + po * (o.scaleOut ?? 0);
    const opacity = pi * (1 - po) * (o.alpha ?? 1);
    setStyle(el, {
      opacity,
      transform: `translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0)` + (sc !== 1 ? ` scale(${sc.toFixed(4)})` : ''),
      filter: blurCss(blur),
    });
    if (o.ls !== undefined) el.style.letterSpacing = `${lerp(o.ls, o.lsTo ?? 0, E.outCubic(pi)).toFixed(4)}em`;
    return opacity;
  }

  // Wrap every character in a span so it can be animated individually.
  function splitChars(el) {
    if (el._chars) return el._chars;
    const chars = [];
    const walk = (node) => {
      for (const child of [...node.childNodes]) {
        if (child.nodeType === 3) {
          const frag = document.createDocumentFragment();
          for (const ch of child.textContent) {
            if (ch === ' ') { frag.appendChild(document.createTextNode(' ')); continue; }
            const sp = document.createElement('span');
            sp.className = 'ch';
            sp.textContent = ch;
            frag.appendChild(sp);
            chars.push(sp);
          }
          node.replaceChild(frag, child);
        } else if (child.nodeType === 1 && child.tagName !== 'BR') {
          walk(child);
        }
      }
    };
    walk(el);
    el._chars = chars;
    return chars;
  }

  // Per-character staggered entrance; the whole element exits together.
  function chars(el, t, tin, tout, o = {}) {
    if (!el) return;
    const cs = splitChars(el);
    const fout = o.fout ?? 0.7;
    if (t < tin || t > tout) { setStyle(el, { opacity: 0 }); return; }
    const po = tout - t < fout ? P(t, tout - fout, fout, E.inQuad) : 0;
    setStyle(el, {
      opacity: 1 - po,
      transform: `translate3d(0,${(-po * (o.yOut ?? 10)).toFixed(2)}px,0)`,
      filter: blurCss(po * (o.blurOut ?? 6)),
    });
    const st = o.stagger ?? 0.04, d = o.fin ?? 0.9;
    for (let i = 0; i < cs.length; i++) {
      const p = P(t, tin + i * st, d, o.ei || E.outQuart);
      const c = cs[i].style;
      const op = p.toFixed(4);
      if (c.opacity !== op) c.opacity = op;
      const tr = `translate3d(0,${((1 - p) * (o.y ?? 18)).toFixed(2)}px,0)` + (o.scale ? ` scale(${lerp(o.scale, 1, p).toFixed(4)})` : '');
      if (c.transform !== tr) c.transform = tr;
      const f = blurCss((1 - p) * (o.blur ?? 8));
      if (c.filter !== f) c.filter = f;
    }
  }

  // Mask reveal: `el` sits in an overflow:hidden parent and slides up into view.
  function maskUp(el, t, tin, tout, o = {}) {
    if (!el) return;
    const fin = o.fin ?? 1.1, fout = o.fout ?? 0.6;
    if (t < tin || t > tout) { setStyle(el, { opacity: 0 }); return; }
    const pi = P(t, tin, fin, o.ei || E.outExpo);
    const po = tout - t < fout ? P(t, tout - fout, fout, E.inCubic) : 0;
    setStyle(el, {
      opacity: 1,
      transform: `translate3d(0,${((1 - pi) * 105 - po * 105).toFixed(3)}%,0)`,
      filter: 'none',
    });
  }

  // Hairline that grows along its axis (transform-origin set in CSS).
  function grow(el, t, tin, dur, tout, o = {}) {
    if (!el) return;
    if (t < tin || (tout !== undefined && t > tout)) { setStyle(el, { opacity: 0 }); return; }
    const p = P(t, tin, dur, o.ease || E.inOutQuart);
    const po = tout !== undefined && tout - t < (o.fout ?? 0.6) ? P(t, tout - (o.fout ?? 0.6), o.fout ?? 0.6, E.inQuad) : 0;
    setStyle(el, {
      opacity: 1 - po,
      transform: o.vertical ? `scaleY(${p.toFixed(4)})` : `scaleX(${p.toFixed(4)})`,
    });
  }

  // Stroke-draw for SVG shapes that carry pathLength="1".
  function draw(path, t, tin, dur, ease = E.inOutCubic) {
    const p = P(t, tin, dur, ease);
    path.style.strokeDasharray = '1 1';
    path.style.strokeDashoffset = (1 - p).toFixed(5);
    return p;
  }

  class Film {
    constructor({ duration, fps = 30, width = 1920, height = 1080 }) {
      Object.assign(this, { duration, fps, width, height });
      this.scenes = [];
      this.layers = [];
      this.t = 0;
    }
    scene(id, start, end, update) {
      const el = document.getElementById(id);
      if (!el) throw new Error('missing scene #' + id);
      el.style.display = 'none';
      this.scenes.push({ id, el, start, end, update });
      return this;
    }
    layer(fn) { this.layers.push(fn); return this; }
    seek(t) {
      this.t = t;
      for (const s of this.scenes) {
        const on = t >= s.start && t < s.end;
        if (on) {
          if (s.el.style.display !== 'block') s.el.style.display = 'block';
          s.update(t - s.start, t, s);
        } else if (s.el.style.display !== 'none') {
          s.el.style.display = 'none';
        }
      }
      for (const fn of this.layers) fn(t);
    }
    // Real-time preview for humans; the renderer never calls this.
    preview() {
      const q = new URLSearchParams(location.search);
      let t = parseFloat(q.get('t') || '0');
      let playing = !q.has('t');
      let last = performance.now();
      const hud = document.createElement('div');
      hud.style.cssText = 'position:fixed;left:12px;bottom:10px;z-index:9999;font:12px monospace;color:#fff8;pointer-events:none';
      document.body.appendChild(hud);
      const tick = (now) => {
        if (playing) t += (now - last) / 1000;
        last = now;
        if (t > this.duration) t = 0;
        this.seek(t);
        hud.textContent = `${t.toFixed(2)}s / ${this.duration}s  [space] play/pause  [←/→] ±2s`;
        requestAnimationFrame(tick);
      };
      addEventListener('keydown', (e) => {
        if (e.code === 'Space') playing = !playing;
        if (e.code === 'ArrowRight') t = Math.min(this.duration, t + 2);
        if (e.code === 'ArrowLeft') t = Math.max(0, t - 2);
      });
      requestAnimationFrame(tick);
    }
  }

  // Scale the fixed 1920x1080 stage to fit the browser window when previewing.
  function fitStage(stage, w = 1920, h = 1080) {
    const fit = () => {
      const s = Math.min(innerWidth / w, innerHeight / h);
      stage.style.transform = s < 1 || s > 1 ? `scale(${s})` : '';
      stage.style.transformOrigin = '0 0';
    };
    if (!navigator.webdriver) { fit(); addEventListener('resize', fit); }
  }

  // Called by each film once its assets are ready.
  function boot(film, init) {
    global.__film = film;
    global.__ready = (async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((im) => (im.decode ? im.decode().catch(() => {}) : null)));
      if (init) await init();
      film.seek(0);
      if (!navigator.webdriver) film.preview();
      return true;
    })();
  }

  global.M = { E, clamp, lerp, P, env, spring, show, chars, splitChars, maskUp, grow, draw, setStyle, Film, fitStage, boot, blurCss };
})(window);
