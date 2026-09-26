"""
Tiny scoring toolkit: MIDI parts rendered through FluidSynth with the
MuseScore General soundfont (MIT / public-domain / CC0 samples), synthesized
sound design, algorithmic reverb and mastering — all in numpy.

Times are in seconds throughout. Parts are written at 60 BPM with 1000 ticks
per beat, so one tick is one millisecond.
"""
import os
import subprocess
import tempfile

import mido
import numpy as np
import soundfile as sf
from scipy import signal as sg

SR = 48000
SF2 = os.environ.get('SF2', '/usr/share/sounds/sf2/MuseScore_General_Full.sf2')
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
NOTE.update({'Db': 1, 'Eb': 3, 'Gb': 6, 'Ab': 8, 'Bb': 10})


def n(name):
    """'D4' -> 62, 'Bb2' -> 46."""
    if isinstance(name, int):
        return name
    pitch = name[:-1] if name[-1].isdigit() else name
    octave = int(name[len(pitch):])
    return 12 * (octave + 1) + NOTE[pitch]


def hz(note):
    return 440.0 * 2 ** ((n(note) - 69) / 12)


# --------------------------------------------------------------- MIDI parts
class Part:
    def __init__(self, name, program, pan=64, volume=100, seed=0, humanize=0.008):
        self.name, self.program, self.pan, self.volume = name, program, pan, volume
        self.ev = []
        self.rng = np.random.default_rng(seed)
        self.humanize = humanize

    def _t(self, t, exact):
        if exact or self.humanize <= 0:
            return max(0.0, t)
        return max(0.0, t + float(self.rng.normal(0, self.humanize)))

    def note(self, t, pitch, dur, vel=64, exact=False):
        t0 = self._t(t, exact)
        v = int(np.clip(vel + (0 if exact else self.rng.integers(-3, 4)), 1, 127))
        p = n(pitch)
        self.ev.append((t0, 1, mido.Message('note_on', note=p, velocity=v)))
        self.ev.append((t0 + dur, 0, mido.Message('note_off', note=p, velocity=0)))
        return self

    def chord(self, t, pitches, dur, vel=64, strum=0.0, exact=False):
        for i, p in enumerate(pitches):
            self.note(t + i * strum, p, dur, vel, exact)
        return self

    def seq(self, t, pitches, step, dur=None, vel=64, accents=None):
        for i, p in enumerate(pitches):
            if p is None:
                continue
            v = vel + (accents[i % len(accents)] if accents else 0)
            self.note(t + i * step, p, dur or step * 0.95, v)
        return self

    def cc(self, t, ctl, val):
        self.ev.append((max(0.0, t), 2, mido.Message('control_change', control=ctl, value=int(np.clip(val, 0, 127)))))
        return self

    def ramp(self, t0, t1, v0, v1, ctl=11, curve=1.0):
        steps = max(2, int((t1 - t0) / 0.04))
        for i in range(steps + 1):
            u = i / steps
            self.cc(t0 + (t1 - t0) * u, ctl, v0 + (v1 - v0) * (u ** curve))
        return self

    def pedal(self, t0, t1):
        return self.cc(t0, 64, 127).cc(t1, 64, 0)

    def midi(self, path):
        mid = mido.MidiFile(ticks_per_beat=1000)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=1_000_000, time=0))
        head = [mido.Message('program_change', program=self.program, time=0),
                mido.Message('control_change', control=7, value=self.volume, time=0),
                mido.Message('control_change', control=10, value=self.pan, time=0),
                mido.Message('control_change', control=91, value=0, time=0),
                mido.Message('control_change', control=93, value=0, time=0)]
        has_expr = any(m.type == 'control_change' and m.control == 11 and t <= 0.001 for t, _, m in self.ev)
        if not has_expr:
            head.append(mido.Message('control_change', control=11, value=127, time=0))
        tr.extend(head)
        last = 0
        for t, _, msg in sorted(self.ev, key=lambda e: (e[0], e[1])):
            tick = int(round(t * 1000))
            tr.append(msg.copy(time=tick - last))
            last = tick
        tr.append(mido.MetaMessage('end_of_track', time=2000))
        mid.save(path)

    def render(self, length, gain=0.5):
        with tempfile.TemporaryDirectory() as d:
            mp, wp = os.path.join(d, 'p.mid'), os.path.join(d, 'p.wav')
            self.midi(mp)
            subprocess.run(['fluidsynth', '-ni', '-q', '-R', '0', '-C', '0', '-g', str(gain), '-r', str(SR),
                            '-O', 'float', '-T', 'wav', '-F', wp, SF2, mp], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            x, sr = sf.read(wp, dtype='float32', always_2d=True)
        assert sr == SR
        return fit(x, length)


def fit(x, length):
    N = int(round(length * SR))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if len(x) >= N:
        return x[:N].copy()
    return np.concatenate([x, np.zeros((N - len(x), x.shape[1]), dtype=x.dtype)])


# ------------------------------------------------------------------- DSP
def sos(kind, f, order=2):
    return sg.butter(order, f, kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return sg.sosfilt(sos(kind, f, order), x, axis=0).astype(np.float32)


def biquad_shelf(x, f0, gain_db, kind='low', S=0.9):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    c = np.cos(w0)
    if kind == 'low':
        b = [A * ((A + 1) - (A - 1) * c + 2 * np.sqrt(A) * alpha), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - 2 * np.sqrt(A) * alpha)]
        a = [(A + 1) + (A - 1) * c + 2 * np.sqrt(A) * alpha, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - 2 * np.sqrt(A) * alpha]
    else:
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * alpha), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * alpha)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * alpha, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * alpha]
    return sg.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0).astype(np.float32)


def peak_eq(x, f0, gain_db, q=1.0):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    b = np.array([1 + alpha * A, -2 * c, 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * c, 1 - alpha / A])
    return sg.lfilter(b / a[0], a / a[0], x, axis=0).astype(np.float32)


def sweep_filter(x, kind, f_start, f_end, q=1.2, block=256):
    """Time-varying resonant filter (exponential cutoff sweep) on a mono signal."""
    out = np.zeros_like(x)
    zi = np.zeros(2)
    nb = int(np.ceil(len(x) / block))
    for i in range(nb):
        u = i / max(1, nb - 1)
        f = f_start * (f_end / f_start) ** u
        f = min(f, SR * 0.45)
        w0 = 2 * np.pi * f / SR
        alpha = np.sin(w0) / (2 * q)
        c = np.cos(w0)
        if kind == 'bp':
            b = np.array([alpha, 0, -alpha]); a = np.array([1 + alpha, -2 * c, 1 - alpha])
        elif kind == 'lp':
            b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]); a = np.array([1 + alpha, -2 * c, 1 - alpha])
        else:
            b = np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2]); a = np.array([1 + alpha, -2 * c, 1 - alpha])
        b, a = b / a[0], a / a[0]
        seg = x[i * block:(i + 1) * block]
        y, zi = sg.lfilter(b, a, seg, zi=zi)
        out[i * block:(i + 1) * block] = y
    return out


def make_ir(rt60=3.0, pre=0.025, seed=3, bands=((0, 400, 1.15), (400, 2500, 1.0), (2500, 7000, 0.7), (7000, 20000, 0.42)), er=True):
    """Stereo algorithmic reverb impulse: band-split decaying noise + early reflections."""
    rng = np.random.default_rng(seed)
    L = int((rt60 * 1.25 + pre) * SR)
    t = np.arange(L) / SR
    ir = np.zeros((L, 2), dtype=np.float64)
    for lo, hi, mul in bands:
        noise = rng.standard_normal((L, 2))
        if lo <= 0:
            nb = sg.sosfilt(sos('lowpass', hi, 4), noise, axis=0)
        elif hi >= 20000:
            nb = sg.sosfilt(sos('highpass', lo, 4), noise, axis=0)
        else:
            nb = sg.sosfilt(sos('bandpass', [lo, hi], 3), noise, axis=0)
        env = np.exp(-6.91 * np.maximum(t - pre, 0) / (rt60 * mul))
        ir += nb * env[:, None]
    fade_in = np.clip((t - pre) / 0.012, 0, 1)
    ir *= fade_in[:, None]
    if er:
        for k in range(14):
            d = pre * 0.4 + rng.uniform(0.004, 0.075)
            g = 0.55 * np.exp(-d * 18) * rng.uniform(0.5, 1.0)
            i = int(d * SR)
            ir[i, k % 2] += g * rng.choice([-1, 1]) * 2.2
    ir /= np.sqrt((ir ** 2).sum() / 2)
    return ir.astype(np.float32)


def convolve(x, ir):
    return np.stack([sg.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1).astype(np.float32)


def db(x):
    return 10 ** (x / 20)


def compressor(x, thresh_db=-18, ratio=2.0, attack=0.02, release=0.25, knee=6, block=64):
    """Feed-forward RMS compressor evaluated per block, gain interpolated per sample."""
    nb = len(x) // block
    xb = x[:nb * block].astype(np.float64).reshape(nb, block, -1)
    lvl = 10 * np.log10(np.mean(xb ** 2, axis=(1, 2)) + 1e-12)
    over = lvl - thresh_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio), (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    bs = block / SR
    a_att, a_rel = np.exp(-bs / attack), np.exp(-bs / release)
    g = np.zeros(nb)
    s = 0.0
    for i in range(nb):
        v = gr[i]
        a = a_att if v > s else a_rel
        s = a * s + (1 - a) * v
        g[i] = s
    centers = (np.arange(nb) + 0.5) * block
    gain = db(-np.interp(np.arange(len(x)), centers, g))
    return (x * gain[:, None]).astype(np.float32)


def limiter(x, ceiling_db=-1.0, lookahead=0.004, release=0.12):
    """Look-ahead peak limiter with 4x oversampled peak detection."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    ceil = db(ceiling_db)
    up = sg.resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(axis=1)[:4 * len(x)].reshape(-1, 4).max(axis=1)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    la = max(2, int(lookahead * SR))
    g = minimum_filter1d(need, size=2 * la + 1)
    g = uniform_filter1d(g, size=la)
    a = np.exp(-1 / (release * SR))
    out = np.empty_like(g)
    s = 1.0
    for i in range(len(g)):
        v = g[i]
        s = v if v < s else a * s + (1 - a) * v
        out[i] = s
    return (x * out[:, None]).astype(np.float32)


def loudness(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x.astype(np.float64))


# ----------------------------------------------------------- sound design
def noise(N, color='white', seed=0, ch=2):
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((N, ch)).astype(np.float32)
    if color == 'white':
        return w
    if color == 'pink':
        b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
        y = sg.lfilter(b, a, w, axis=0)
        return (y / np.std(y)).astype(np.float32)
    y = np.cumsum(w, axis=0)
    y = sg.sosfilt(sos('highpass', 20, 1), y, axis=0)
    return (y / np.std(y)).astype(np.float32)


def env_curve(N, pts):
    """Piecewise-linear envelope from [(time_s, value), ...]."""
    t = np.arange(N) / SR
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys).astype(np.float32)


def boom(dur=4.0, f0=62, f1=32, level=1.0, click=0.35, seed=1):
    N = int(dur * SR)
    t = np.arange(N) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 3.2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 1.25) * np.clip(t / 0.004, 0, 1)
    body += 0.35 * np.sin(2 * ph) * np.exp(-t * 3.0)
    nz = noise(N, 'white', seed, 1)[:, 0]
    tr = filt(nz, 'lowpass', 1800) * np.exp(-t * 40) * click
    tail = filt(noise(N, 'brown', seed + 1, 1)[:, 0], 'lowpass', 160) * np.exp(-t * 1.6) * 0.25
    x = (body + tr + tail) * level
    return np.stack([x, x], 1).astype(np.float32)


def thud(level=0.6, f=85, seed=2):
    N = int(0.9 * SR)
    t = np.arange(N) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t * 30))) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x += filt(noise(N, 'white', seed, 1)[:, 0], 'bandpass', [150, 1200]) * np.exp(-t * 60) * 0.6
    x *= level
    return np.stack([x, x], 1).astype(np.float32)


def whoosh(dur=1.2, f0=400, f1=3500, level=0.5, seed=3, peak=0.6, q=0.9):
    N = int(dur * SR)
    t = np.arange(N) / SR
    nz = noise(N, 'pink', seed, 2)
    y = np.stack([sweep_filter(nz[:, c], 'bp', f0, f1, q) for c in range(2)], 1)
    e = np.where(t < peak * dur, (t / (peak * dur)) ** 2, np.exp(-(t - peak * dur) / (0.18 * dur)))
    y = y * e[:, None]
    return (y / (np.abs(y).max() + 1e-9) * level).astype(np.float32)


def riser(dur=2.0, level=0.45, seed=4, f0=300, f1=9000):
    N = int(dur * SR)
    t = np.arange(N) / SR
    nz = noise(N, 'white', seed, 2)
    y = np.stack([sweep_filter(nz[:, c], 'bp', f0, f1, 1.6) for c in range(2)], 1)
    e = (t / dur) ** 2.4
    y = y * e[:, None]
    y[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))[:, None]
    return (y / (np.abs(y).max() + 1e-9) * level).astype(np.float32)


def reverse_cymbal(dur=2.2, level=0.35, seed=5):
    N = int(dur * SR)
    t = np.arange(N) / SR
    nz = noise(N, 'white', seed, 2)
    y = filt(nz, 'highpass', 3500, 2)
    y = filt(y, 'lowpass', 14000, 2)
    e = np.exp(-(dur - t) * 2.4)
    y = y * e[:, None]
    y[-int(0.008 * SR):] *= np.linspace(1, 0, int(0.008 * SR))[:, None]
    return (y / (np.abs(y).max() + 1e-9) * level).astype(np.float32)


def tick(level=0.25, f=2600, seed=6):
    N = int(0.08 * SR)
    t = np.arange(N) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 180) * 0.6
    x += filt(noise(N, 'white', seed, 1)[:, 0], 'highpass', 3000) * np.exp(-t * 400)
    x *= level
    return np.stack([x, x], 1).astype(np.float32)


def paper(level=0.35, dur=0.7, seed=7):
    N = int(dur * SR)
    t = np.arange(N) / SR
    nz = noise(N, 'white', seed, 2)
    y = filt(nz, 'bandpass', [1800, 7000], 2)
    grain = 0.6 + 0.4 * np.abs(filt(noise(N, 'white', seed + 1, 1)[:, 0], 'lowpass', 60))
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * grain
    return (y * e[:, None] / (np.abs(y).max() + 1e-9) * level).astype(np.float32)


def fire_bed(dur, intensity, seed=8):
    """Crackling fire: low roar + flame breath + sparse crackles. intensity(t) -> 0..1 array."""
    N = int(dur * SR)
    t = np.arange(N) / SR
    k = intensity(t).astype(np.float32)
    rng = np.random.default_rng(seed)
    roar = filt(noise(N, 'brown', seed, 2), 'lowpass', 220) * 0.55
    breath_mod = 0.6 + 0.4 * filt(np.abs(noise(N, 'white', seed + 1, 1)[:, 0]), 'lowpass', 1.5)[:, None] * 3
    breath = filt(noise(N, 'pink', seed + 2, 2), 'bandpass', [300, 1600]) * 0.22 * breath_mod
    crack = np.zeros((N, 2), dtype=np.float32)
    rate = 26.0
    count = int(dur * rate * 1.3)
    times = np.sort(rng.uniform(0, dur, count))
    for tt in times:
        i = int(tt * SR)
        if i >= N or rng.random() > k[i] * 0.95 + 0.05:
            continue
        L = int(rng.uniform(0.0008, 0.006) * SR)
        burst = rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4))
        amp = rng.uniform(0.15, 1.0) ** 2 * (1.6 if rng.random() < 0.08 else 0.7)
        pan = rng.uniform(0.15, 0.85)
        j = min(N, i + L)
        crack[i:j, 0] += burst[:j - i] * amp * (1 - pan)
        crack[i:j, 1] += burst[:j - i] * amp * pan
    crack = filt(crack, 'bandpass', [900, 7500], 2) * 1.8
    y = (roar + breath) * k[:, None] + crack
    return y.astype(np.float32)


def supersaw_pad(notes, dur, level=0.2, cutoff=1800, attack=1.5, release=2.0, voices=5, detune=0.12, seed=9):
    """Warm detuned-saw pad (band-limited via additive partials)."""
    N = int((dur + release) * SR)
    t = np.arange(N) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros((N, 2), dtype=np.float64)
    for note in notes:
        f0 = hz(note)
        for v in range(voices):
            cents = (v - (voices - 1) / 2) / max(1, (voices - 1) / 2) * detune * 100
            f = f0 * 2 ** (cents / 1200)
            ph0 = rng.uniform(0, 2 * np.pi)
            kmax = int(min(40, (cutoff * 2.2) // f))
            w = np.zeros(N)
            for k in range(1, max(2, kmax)):
                w += np.sin(2 * np.pi * f * k * t + ph0 * k) / k * np.exp(-(k * f / cutoff) ** 2)
            pan = 0.5 + (v - (voices - 1) / 2) / voices * 0.8
            out[:, 0] += w * (1 - pan)
            out[:, 1] += w * pan
    e = np.clip(t / attack, 0, 1) ** 1.5
    e *= np.where(t > dur, np.exp(-(t - dur) / (release / 4)), 1.0)
    out *= e[:, None]
    out = out / (np.abs(out).max() + 1e-9) * level
    return out.astype(np.float32)


def drone(notes, dur, level=0.25, attack=3.0, release=3.0, lfo=0.07):
    N = int((dur + release) * SR)
    t = np.arange(N) / SR
    out = np.zeros(N)
    for i, note in enumerate(notes):
        f = hz(note)
        out += (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t + 0.3)) * (1 + 0.15 * np.sin(2 * np.pi * lfo * t + i))
    e = np.clip(t / attack, 0, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / (release / 4)), 1.0)
    out = out * e
    out = out / (np.abs(out).max() + 1e-9) * level
    return np.stack([out, out], 1).astype(np.float32)


def norm_active(x, target):
    """Scale so the loudness of the active (non-silent) 400 ms blocks hits `target` LUFS-ish."""
    blk = min(int(0.4 * SR), len(x))
    nb = len(x) // blk
    e = (x[:nb * blk].astype(np.float64) ** 2).reshape(nb, blk, 2).mean(axis=(1, 2))
    lv = 10 * np.log10(e + 1e-12)
    act = lv > lv.max() - 30
    cur = 10 * np.log10(e[act].mean() + 1e-12) - 0.691 + 3.0
    return (x * db(target - cur)).astype(np.float32)


# ---------------------------------------------------------------- mixing
class Mix:
    def __init__(self, length):
        self.N = int(round(length * SR))
        self.dry = np.zeros((self.N, 2), dtype=np.float32)
        self.buses = {}
        self.length = length

    def add(self, x, t0=0.0, gain_db=0.0, send=0.0, bus='hall', width=1.0):
        i = int(round(t0 * SR))
        if i >= self.N:
            return
        x = x.astype(np.float32) * db(gain_db)
        if width != 1.0:
            m, s = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
            x = np.stack([m + s * width, m - s * width], 1)
        j = min(self.N, i + len(x))
        self.dry[i:j] += x[:j - i]
        if send > 0:
            b = self.buses.setdefault(bus, np.zeros((self.N, 2), dtype=np.float32))
            b[i:j] += x[:j - i] * send

    def render(self, irs, returns_db):
        out = self.dry.copy()
        for name, b in self.buses.items():
            out += convolve(b, irs[name]) * db(returns_db.get(name, 0))
        return out


def master(x, target_lufs=-16.0, ceiling_db=-1.0, fade_out=None):
    x = filt(x, 'highpass', 28, 2)
    x = peak_eq(x, 280, -1.5, 0.8)
    x = biquad_shelf(x, 9000, 1.5, 'high')
    x = compressor(x, thresh_db=-20, ratio=1.8, attack=0.03, release=0.3)
    for _ in range(2):
        lu = loudness(x)
        x = x * db(target_lufs - lu)
        x = limiter(x, ceiling_db)
    if fade_out:
        t0, t1 = fade_out
        N = len(x)
        t = np.arange(N) / SR
        g = np.clip((t1 - t) / (t1 - t0), 0, 1) ** 1.6
        x = x * g[:, None]
    return x.astype(np.float32)


def write(path, x):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    sf.write(path, x, SR, subtype='PCM_24')
