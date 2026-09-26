"""Mixkit 무료 클립을 내려받아 드롭 A 배경용 프레임(30fps, 0.5초)으로 잘라 둔다.
결과: build/footage/{h,v}/<장면>/NN.jpg + manifest.json  (film.js 가 있으면 실사, 없으면 CG 사용)"""
import json, os, subprocess, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PROMO = os.path.dirname(HERE)
FF = os.environ.get('FFMPEG', 'ffmpeg')
cfg = {k: v for k, v in json.load(open(os.path.join(HERE, 'footage.json'))).items() if not k.startswith('_')}
src_dir = os.path.join(PROMO, 'footage'); os.makedirs(src_dir, exist_ok=True)
N = 16  # 0.5초 + 여유 1프레임

for key, c in cfg.items():
    fn = os.path.join(src_dir, f"{c['id']}-720.mp4")
    if not os.path.exists(fn):
        url = f"https://assets.mixkit.co/videos/{c['id']}/{c['id']}-720.mp4"
        print('download', url)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        open(fn, 'wb').write(urllib.request.urlopen(req, timeout=120).read())

for fmt, (W, H) in {'h': (1920, 1080), 'v': (1080, 1920)}.items():
    root = os.path.join(PROMO, 'build', 'footage', fmt)
    man = {}
    for key, c in cfg.items():
        out = os.path.join(root, key); os.makedirs(out, exist_ok=True)
        sp = c.get('speed', 1.0); vx = c.get('vx', 0.5); gain = c.get('gain', 1.0)
        if fmt == 'h':
            geo = f'scale={W}:{H}:flags=lanczos'
        else:
            geo = f"scale=-2:{H}:flags=lanczos,crop={W}:{H}:'max(0,min(iw-{W},iw*{vx}-{W}/2))':0"
        vf = (f'setpts=PTS/{sp},fps=30,{geo},'
              f'eq=contrast=1.06:saturation=0.88:gamma={1/gain:.3f},'
              f'unsharp=5:5:0.6')
        subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str(c['in']), '-i', os.path.join(src_dir, f"{c['id']}-720.mp4"),
                        '-vf', vf, '-frames:v', str(N), '-q:v', '3', os.path.join(out, '%02d.jpg')], check=True)
        n = len([f for f in os.listdir(out) if f.endswith('.jpg')])
        man[key] = {'frames': n, 'dim': c.get('dim', 0)}
        print(fmt, key, n)
    json.dump(man, open(os.path.join(root, 'manifest.json'), 'w'), indent=1)
