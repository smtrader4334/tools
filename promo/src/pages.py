"""드롭 B 폰 화면에 쓸 최신 페이지를 실제 배포 사이트에서 내려받는다 → build/site/*.html"""
import os, urllib.request, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'build', 'site'); os.makedirs(OUT, exist_ok=True)
BASE = os.environ.get('THEHAM_SITE', 'https://theham-consult.pages.dev')
PAGES = {'home.html': '/theham/', 'sm.html': '/sm-consult.html', 'dk.html': '/dk-consult.html'}
for name, path in PAGES.items():
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=60).read()
    open(os.path.join(OUT, name), 'wb').write(data)
    print(name, BASE + path, len(data), hashlib.md5(data).hexdigest()[:10])
