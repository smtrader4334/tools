"""
Cut a film's full soundtrack into its vertical-short edit (common/shorts.json).
Segments are joined at bar lines with short equal-power crossfades centred on
each cut, so every cue stays in sync with the picture.

    python3 audio/short_cut.py fire ../build/fire-audio.wav ../build/fire-short-audio.wav
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
import score_lib as S

film, src, out = sys.argv[1:4]
edit = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'common', 'shorts.json')))[film]
x, sr = sf.read(src, dtype='float32', always_2d=True)
assert sr == S.SR
X = 0.12  # half crossfade length (s)
total = sum(b - a for a, b in edit)
y = np.zeros((int(round(total * sr)) + 1, 2), dtype=np.float32)
acc = 0.0
for k, (a, b) in enumerate(edit):
    pre = X if k > 0 else 0.0
    post = X if k < len(edit) - 1 else 0.0
    s0, s1 = int(round((a - pre) * sr)), int(round((b + post) * sr))
    seg = x[max(0, s0):s1].copy()
    n = len(seg)
    g = np.ones(n, dtype=np.float32)
    fi, fo = int(2 * pre * sr), int(2 * post * sr)
    if fi:
        g[:fi] = np.sin(np.linspace(0, np.pi / 2, fi)) ** 1
    if fo:
        g[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo))
    o = int(round((acc - pre) * sr))
    y[o:o + n] += seg[:len(y) - o] * g[:len(y) - o, None]
    acc += b - a
# gentle fade-in and a 1.2 s fade-out matching the picture
t = np.arange(len(y)) / sr
y *= (np.clip(t / 0.25, 0, 1) * np.clip((total - t) / 1.2, 0, 1) ** 1.5)[:, None]
lu = S.loudness(y)
y = S.limiter(y * S.db(-15.0 - lu), -1.0)
S.write(out, y)
print('duration %.2f s  LUFS %.2f' % (len(y) / sr, S.loudness(y)))
