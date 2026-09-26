#!/usr/bin/env node
/*
 * Frame-accurate renderer: opens a film page in headless Chromium, seeks the
 * timeline frame by frame and pipes screenshots into ffmpeg.
 *
 *   node render.mjs fire --out build/fire-video.mkv            # full film
 *   node render.mjs fire --stills 3,22.5,40 --dir build/stills # QA frames
 *   node render.mjs fire --from 60 --to 80 --out build/part.mkv
 *
 * Output of a full render is a lossless RGB intermediate; build.sh converts
 * it to the final H.264/AAC file together with the soundtrack.
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));

async function loadPlaywright() {
  try { return await import('playwright'); } catch {}
  const globalRoot = execSync('npm root -g').toString().trim();
  const require = createRequire(path.join(globalRoot, 'noop.js'));
  return require('playwright');
}

function parseArgs(argv) {
  const a = { film: argv[0], fps: 30, workers: 3, dir: 'build/stills' };
  for (let i = 1; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, '');
    a[k] = argv[i + 1]; i++;
  }
  a.fps = Number(a.fps); a.workers = Number(a.workers);
  return a;
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.json': 'application/json' };
function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

async function openPage(browser, url) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('[page error]', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('[console]', m.text()); });
  await page.goto(url);
  await page.waitForFunction(() => window.__ready !== undefined);
  await page.evaluate(() => window.__ready);
  return page;
}

async function capture(page, t) {
  await page.evaluate((tt) => window.__film.seek(tt), t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1920, height: 1080 } });
}

function ffmpegSink(out, fps) {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264rgb', '-qp', '0', '-preset', 'ultrafast', '-pix_fmt', 'rgb24', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  return { ff, done };
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (!a.film) throw new Error('usage: node render.mjs <film> [--out file | --stills t1,t2]');
  const { chromium } = await loadPlaywright();
  const srv = await serve();
  const url = `http://127.0.0.1:${srv.address().port}/${a.film}/index.html`;
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb', '--font-render-hinting=none'] });
  try {
    if (a.stills) {
      fs.mkdirSync(a.dir, { recursive: true });
      const page = await openPage(browser, url);
      for (const s of a.stills.split(',')) {
        const t = Number(s);
        const buf = await capture(page, t);
        const f = path.join(a.dir, `${a.film}_${t.toFixed(2).padStart(7, '0')}.png`);
        fs.writeFileSync(f, buf);
        console.log(f);
      }
      return;
    }
    const probe = await openPage(browser, url);
    const duration = await probe.evaluate(() => window.__film.duration);
    await probe.close();
    const from = Number(a.from ?? 0), to = Number(a.to ?? duration);
    const f0 = Math.round(from * a.fps), f1 = Math.round(to * a.fps);
    const n = f1 - f0, W = Math.max(1, Math.min(a.workers, n));
    const out = path.resolve(a.out || `build/${a.film}-video.mkv`);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const segs = [];
    const t0 = Date.now();
    let doneFrames = 0;
    await Promise.all([...Array(W)].map(async (_, w) => {
      const s0 = f0 + Math.floor((n * w) / W), s1 = f0 + Math.floor((n * (w + 1)) / W);
      const seg = out.replace(/\.mkv$/, `.part${w}.mkv`);
      segs[w] = seg;
      const page = await openPage(browser, url);
      const { ff, done } = ffmpegSink(seg, a.fps);
      for (let f = s0; f < s1; f++) {
        const buf = await capture(page, f / a.fps);
        if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
        doneFrames++;
        if (doneFrames % 150 === 0) {
          const el = (Date.now() - t0) / 1000;
          console.log(`${doneFrames}/${n} frames  ${(doneFrames / el).toFixed(1)} fps  eta ${((n - doneFrames) / (doneFrames / el)).toFixed(0)}s`);
        }
      }
      ff.stdin.end();
      await done;
      await page.close();
    }));
    const list = out.replace(/\.mkv$/, '.txt');
    fs.writeFileSync(list, segs.map((s) => `file '${s}'`).join('\n'));
    execSync(`ffmpeg -y -loglevel error -f concat -safe 0 -i "${list}" -c copy "${out}"`);
    for (const s of segs) fs.unlinkSync(s);
    fs.unlinkSync(list);
    console.log(`rendered ${n} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${out}`);
  } finally {
    await browser.close();
    srv.close();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
