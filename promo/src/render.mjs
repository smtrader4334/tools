// 사용법:
//   node src/render.mjs --fmt h --preview 0.3,2.1,16.2      # 특정 시점 PNG 미리보기
//   node src/render.mjs --fmt h                              # 전체 렌더 → build/theham-film-h.mp4
//   (--fmt v 는 9:16 세로 버전)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROMO = path.resolve(HERE, '..');
const ROOT = path.resolve(PROMO, '..'); // 저장소 루트 (theham-consult.html 위치)
const BUILD = path.join(PROMO, 'build');
fs.mkdirSync(BUILD, { recursive: true });

const args = process.argv.slice(2);
const arg = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const FMT = arg('--fmt', 'h');
const PREVIEW = arg('--preview', null);
const FROM = parseFloat(arg('--from', '0'));
const TO = parseFloat(arg('--to', '46'));
const FPS = 30;
const [W, H] = FMT === 'v' ? [1080, 1920] : [1920, 1080];
const FFMPEG = process.env.FFMPEG || 'ffmpeg';

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.woff': 'font/woff', '.otf': 'font/otf', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

const browser = await chromium.launch({
  executablePath: process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', '--font-render-hinting=none'],
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
// 구글 폰트 등 외부 요청은 즉시 차단 (서체는 로컬 파일로 주입)
await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.goto(`http://127.0.0.1:${PORT}/promo/src/film.html?fmt=${FMT}`);
await page.waitForFunction(() => window.filmReady === true, null, { timeout: 60000 });

async function frame(t) {
  await page.evaluate((t) => window.renderFrame(t), t);
}

if (PREVIEW) {
  const dir = path.join(BUILD, 'preview'); fs.mkdirSync(dir, { recursive: true });
  for (const s of PREVIEW.split(',')) {
    const t = parseFloat(s);
    const t0 = Date.now();
    await frame(t);
    const f = path.join(dir, `${FMT}_${t.toFixed(2)}.png`);
    await page.screenshot({ path: f });
    console.log(f, Date.now() - t0, 'ms');
  }
} else {
  const out = path.join(BUILD, `video-${FMT}.mp4`);
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n0 = Math.round(FROM * FPS), n1 = Math.round(TO * FPS);
  const tStart = Date.now();
  for (let n = n0; n < n1; n++) {
    await frame(n / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (n % 60 === 0) console.log(`frame ${n}/${n1}  ${((Date.now() - tStart) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('video →', out);
}
await browser.close();
server.close();
