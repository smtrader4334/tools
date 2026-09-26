#!/usr/bin/env bash
# 더함 브랜드 필름 전체 빌드: 음악 → 실사 클립 → 영상(16:9, 9:16) → 합치기 → 포스터
# 준비: (promo 폴더에서) npm install ; pip install numpy scipy ; ffmpeg 필요
set -euo pipefail
cd "$(dirname "$0")"
FFMPEG="${FFMPEG:-ffmpeg}"
mkdir -p build

python3 src/music.py
python3 src/footage.py      # Mixkit 무료 클립 내려받아 장면별 프레임 추출 (없으면 CG 장면으로 렌더)
node src/render.mjs --fmt h
node src/render.mjs --fmt v

for f in h v; do
  name=$([ "$f" = h ] && echo 16x9 || echo 9x16)
  "$FFMPEG" -y -loglevel error -i "build/video-$f.mp4" -i build/music.wav \
    -map 0:v -map 1:a -c:v libx264 -preset slow -crf 20 -maxrate 14M -bufsize 28M -pix_fmt yuv420p \
    -c:a aac -b:a 256k -shortest -movflags +faststart \
    "theham-brand-film-$name.mp4"
  "$FFMPEG" -y -loglevel error -ss 43.0 -i "build/video-$f.mp4" -frames:v 1 -q:v 2 "poster-$name.jpg"
done
echo "done: theham-brand-film-16x9.mp4 / theham-brand-film-9x16.mp4"
