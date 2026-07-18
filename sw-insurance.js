const CACHE = 'insurance-calc-v4';
const STATIC = [
  '/tools/manifest-insurance.json',
  '/tools/icon-insurance-192.png',
  '/tools/icon-insurance-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    // 옛 버전 캐시(v3 이하) 전부 삭제
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
    // 이미 열려 있는 창들을 강제로 새로고침 → 즉시 최신 반영
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => { try { c.navigate(c.url); } catch (_) {} });
  })());
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // HTML은 항상 네트워크 우선 → 최신 내용 즉시 반영
  if (url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // 아이콘·manifest 등 정적 파일은 캐시 우선
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
