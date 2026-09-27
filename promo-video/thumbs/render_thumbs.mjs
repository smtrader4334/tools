#!/usr/bin/env node
/*
 * 썸네일 렌더러: thumbs/index.html 의 각 보드를 JPG로 저장합니다.
 *   node thumbs/render_thumbs.mjs      # → out/thumbs/*.jpg
 * 가로 1280×720(유튜브 썸네일·홈페이지 정지 화면), 세로 1080×1920(쇼츠·릴스 커버).
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'out', 'thumbs');
const BOARDS = {
  company: 'theham-company-thumb.jpg',
  fire: 'theham-fire-thumb.jpg',
  leak: 'theham-leak-thumb.jpg',
  'company-v': 'theham-company-short-cover.jpg',
  'fire-v': 'theham-fire-short-cover.jpg',
  'leak-v': 'theham-leak-short-cover.jpg',
};

const require = createRequire(path.join(execSync('npm root -g').toString().trim(), 'noop.js'));
const { chromium } = require('playwright');
const MIME = { '.html': 'text/html', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const srv = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0, '127.0.0.1');
await new Promise((r) => srv.once('listening', r));

const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 2000 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${srv.address().port}/thumbs/index.html`);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map((im) => im.decode().catch(() => {}))));
  fs.mkdirSync(OUT, { recursive: true });
  for (const [id, name] of Object.entries(BOARDS)) {
    const file = path.join(OUT, name);
    await page.locator('#' + id).screenshot({ path: file, type: 'jpeg', quality: 92 });
    console.log(path.relative(ROOT, file));
  }
} finally {
  await browser.close();
  srv.close();
}
