// PWA 설치용 서비스워커 — 캐싱 없음 (항상 최신 파일 사용)
self.addEventListener('install', function(){ self.skipWaiting(); });
self.addEventListener('activate', function(e){ e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function(){});
