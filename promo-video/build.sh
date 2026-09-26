#!/usr/bin/env bash
# Build a finished film:  ./build.sh fire   |   ./build.sh leak
#   1. render every frame from <film>/index.html (headless Chromium)
#   2. render the original score  (audio/<film>_score.py)
#   3. encode H.264 (BT.709) + AAC into out/<name>.mp4, plus a poster frame
# Set SKIP_VIDEO=1 or SKIP_AUDIO=1 to reuse an existing intermediate.
# Files are kept under MAX_MIB (default 29) so they can be sent through chat apps.
set -euo pipefail
cd "$(dirname "$0")"

film=${1:?usage: ./build.sh fire|leak}
case "$film" in
  fire) name=theham-fire-brand-film; poster=24.5 ;;
  leak) name=theham-leak-appointment-right; poster=26.5 ;;
  *) echo "unknown film: $film" >&2; exit 1 ;;
esac

mkdir -p build out
[ "${SKIP_VIDEO:-0}" = 1 ] || node render.mjs "$film" --workers "${WORKERS:-3}" --out "build/$film-video.mkv"
[ "${SKIP_AUDIO:-0}" = 1 ] || (cd audio && python3 "${film}_score.py" "../build/$film-audio.wav")

VF="scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p"
X264=(-c:v libx264 -preset slow -profile:v high -level 4.1 -x264-params "keyint=60:min-keyint=30:aq-mode=3")
COLOR=(-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv)
IN=(-i "build/$film-video.mkv" -i "build/$film-audio.wav" -map 0:v:0 -map 1:a:0 -shortest)

ffmpeg -y -loglevel error "${IN[@]}" -vf "$VF" "${X264[@]}" -crf "${CRF:-17}" "${COLOR[@]}" \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart "out/$name.mp4"

max=$(( ${MAX_MIB:-29} * 1048576 ))
if [ "$(stat -c %s "out/$name.mp4")" -gt "$max" ]; then
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "build/$film-video.mkv")
  vk=$(python3 -c "print(int(($max * 8 / $dur - 192000) / 1000 * 0.965))")
  ffmpeg -y -loglevel error -i "build/$film-video.mkv" -vf "$VF" "${X264[@]}" -b:v "${vk}k" \
    -pass 1 -passlogfile "build/$film-2pass" -an -f mp4 /dev/null
  ffmpeg -y -loglevel error "${IN[@]}" -vf "$VF" "${X264[@]}" -b:v "${vk}k" \
    -pass 2 -passlogfile "build/$film-2pass" "${COLOR[@]}" \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart "out/$name.mp4"
fi

node render.mjs "$film" --stills "$poster" --dir build/poster >/dev/null
ffmpeg -y -loglevel error -i build/poster/"$film"_*.png -q:v 2 "out/$name.jpg"
rm -rf build/poster
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "out/$name.mp4"
