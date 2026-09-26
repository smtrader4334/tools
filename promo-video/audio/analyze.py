"""QA plots for a rendered soundtrack: short-term loudness + spectrogram with cue markers."""
import sys
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal as sg

path, out = sys.argv[1], sys.argv[2]
cues = [float(c) for c in sys.argv[3].split(',')] if len(sys.argv) > 3 else []
x, sr = sf.read(path, always_2d=True)
m = x.mean(1)
win = int(0.4 * sr); hop = int(0.1 * sr)
t, lv, pk = [], [], []
for i in range(0, len(m) - win, hop):
    seg = x[i:i + win]
    t.append((i + win / 2) / sr)
    lv.append(10 * np.log10(np.mean(seg ** 2) + 1e-12) - 0.691 + 3.0)
    pk.append(20 * np.log10(np.abs(seg).max() + 1e-9))
fig, ax = plt.subplots(2, 1, figsize=(22, 10), sharex=True, gridspec_kw={'height_ratios': [1, 1.4]})
ax[0].plot(t, lv, lw=0.9, label='momentary loudness (LUFS-ish)')
ax[0].plot(t, pk, lw=0.6, alpha=0.6, label='peak dBFS')
ax[0].set_ylim(-60, 2); ax[0].grid(alpha=0.3); ax[0].legend(loc='lower right')
for c in cues:
    ax[0].axvline(c, color='r', lw=0.6, alpha=0.6); ax[1].axvline(c, color='w', lw=0.5, alpha=0.5)
f, tt, Sxx = sg.spectrogram(m, sr, nperseg=4096, noverlap=3072)
ax[1].pcolormesh(tt, f, 10 * np.log10(Sxx + 1e-14), shading='auto', vmin=-130, vmax=-30, cmap='magma')
ax[1].set_yscale('symlog', linthresh=200); ax[1].set_ylim(20, 16000)
ax[1].set_xticks(np.arange(0, t[-1] + 1, 4))
plt.tight_layout(); plt.savefig(out, dpi=70)
print(out)
