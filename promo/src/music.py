#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music.py (v2) - original score for the 47.5 s 더함화재특종손해사정 brand film.

Premium, restrained corporate score: felt piano, warm string beds, deep clean
low hits, a soft pulse and a lot of air.  Everything is synthesised from
scratch with numpy + scipy (no samples, no downloads).  Deterministic: every
random source is a numpy Generator seeded from a CRC32 of its name, so two
renders are bit-identical.

Reads   src/timeline.json (v2: 96 BPM, beat 0.625 s, bar 2.5 s, t = 0 downbeat)
Writes  build/music.wav          48 kHz / 24-bit / stereo / exactly 47.500 s
        build/music_events.txt   every hit placed, with exact timestamps

Usage   python3 src/music.py            render
        python3 src/music.py --verify   render + numerical checks
                                        + build/music_spectrogram.png
        python3 src/music.py --verify-only   checks on the existing wav

Form
  hook    0-2.5    room tone + mains hum, power-strip spark at 0.625, smoke
                   hiss, sub swell into the first phrase
  opening 2.5-12.5 four bars; each "phrase" = clean low hit + felt piano,
                   each "note" = piano only.  The words play a motif:
                   Dm  A4 F4 D4 | Bbmaj7 A4 F4 C5 | Gm9 Bb4 G4 D5 | A C#5 A4 E5
                   (phrase ends climb C5 -> D5 -> E5 -> F5/A5 in the build)
                   string bed swelling underneath + felt clock pulse on beats
  build   12.5-15  Bbmaj7 -> A, string crescendo, airy riser, ticks
                   accelerating; 14.375-15.0 exact digital silence
  dropA   15-25    Dm | Bb | Gm A | F C : soft tuned kick every beat (sub
                   phase-locked to it), 8th string ostinato, taiko on bar
                   downbeats, felt accent per beat; lift at 22.5 (piano
                   A4 C5 E5 G5 on 복구 일상 제자리 회복, shimmer)
  dropB   25-35    F | C | Dm | Bb : piano melody (the motif turned major)
                   over a pad, gentle 8th pulse, kick on beats 1+3, UI ticks,
                   page whooshes; stops dead at 35.0
  outro   35-47.5  softboom, Fmaj9 without its 3rd + piano A4 (the missing
                   third is "added"), subdrop + light sweep, piano-harmonic
                   chime, ember crackle + last low F, fade to silence
"""
import json
import os
import subprocess
import sys
import time
import wave
import zlib

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d

# ---------------------------------------------------------------------------
# Timeline / grid
# ---------------------------------------------------------------------------
SR = 48000
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(SRC_DIR)
BUILD_DIR = os.path.join(PROJ, 'build')
with open(os.path.join(SRC_DIR, 'timeline.json'), encoding='utf-8') as fh:
    TL = json.load(fh)

DUR = float(TL['duration'])
N = int(round(DUR * SR))
BEAT = float(TL['beat'])
BAR = 4 * BEAT
SEC = {s['name']: (float(s['start']), float(s['end'])) for s in TL['sections']}
HITS = [(float(w['t']), w['hit'], w['text']) for w in TL['words'] if 'hit' in w]
UI = [(float(w['t']), w['ui'], w['text']) for w in TL['words'] if 'ui' in w]


def word_time(prefix, default):
    for w in TL['words']:
        if w['text'].startswith(prefix):
            return float(w['t'])
    return default


def hit_time(kind, default):
    return next((t for t, k, _ in HITS if k == kind), default)


HOOK0, HOOK1 = SEC['hook']
OPEN0, OPEN1 = SEC['opening']
BUILD0, BUILD1 = SEC['build']
A0, A1 = SEC['dropA']
B0, B1 = SEC['dropB']
OUT0, OUT1 = SEC['outro']
T_SPARK = hit_time('spark', HOOK0 + BEAT)          # 0.625
SWELL0 = hit_time('swell', BUILD1 - BEAT)          # 14.375 breath-in swell into drop A
CREST = SWELL0 - 0.175                             # 14.2   build strings + riser crest, then fall away
LIFT = word_time('복구', A0 + 3 * BAR)               # 22.5 lift to major
RING0 = hit_time('ringout', B1 - BEAT)             # 34.375 drop B ring-out chord (Bb -> F)

# opening / build harmony (string bed + low-hit tuning) and the word motif
OPEN_CHORDS = [(OPEN0, OPEN0 + BAR, 'Dm'), (OPEN0 + BAR, OPEN0 + 2 * BAR, 'Bbmaj7'),
               (OPEN0 + 2 * BAR, OPEN0 + 3 * BAR, 'Gm9'), (OPEN0 + 3 * BAR, BUILD0, 'A'),
               (BUILD0, BUILD0 + 2 * BEAT, 'Bbmaj7'), (BUILD0 + 2 * BEAT, A0, 'A')]
HIT_ROOT = {'Dm': 'D2', 'Bbmaj7': 'Bb1', 'Gm9': 'G1', 'A': 'A1'}
MOTIF = [['A4', 'F4', 'D4'],        # 사고는 / 예고 없이 / 옵니다.
         ['A4', 'F4', 'C5'],        # 불이 나고, / 연기가 / 번지고,
         ['Bb4', 'G4', 'D5'],       # 무엇이, / 얼마나 / 손상됐는지.
         ['C#5', 'A4', 'E5'],       # 설명할 / 근거가 / 필요합니다.   (rises)
         ['F5', 'A5']]              # 보이는 피해 / 너머까지.
# string bed voices (bass .. top); top voice holds an A pedal
OPEN_LINES = [('D2', 'Bb1', 'G1', 'A1', 'Bb1', 'A1'),
              ('A2', 'F2', 'D2', 'E2', 'F2', 'E2'),
              ('D3', 'D3', 'Bb2', 'C#3', 'D3', 'C#3'),
              ('F3', 'F3', 'F3', 'E3', 'F3', 'E3'),
              ('A3', 'A3', 'A3', 'A3', 'A3', 'A3')]

# drops
CHORDS = [(A0, A0 + BAR, 'Dm'), (A0 + BAR, A0 + 2 * BAR, 'Bb'),
          (A0 + 2 * BAR, A0 + 2 * BAR + 2 * BEAT, 'Gm'), (A0 + 2 * BAR + 2 * BEAT, LIFT, 'A'),
          (LIFT, LIFT + 2 * BEAT, 'F'), (LIFT + 2 * BEAT, A1, 'C'),
          (B0, B0 + BAR, 'F'), (B0 + BAR, B0 + 2 * BAR, 'C'), (B0 + 2 * BAR, B0 + 3 * BAR, 'Dm'),
          (B0 + 3 * BAR, RING0, 'Bb'), (RING0, B1, 'Fend')]
CH = {  # sub root | 8th ostinato tones (root, 5th, 8ve, 3rd) | drop-A strings | drop-B pad | pulse
    'Dm': dict(sub='D2', ost=('D3', 'A3', 'D4', 'F3'), strA=('D2', 'D3', 'F3', 'A3', 'D4'),
               padB=('D2', 'F3', 'A3', 'E4'), pulse=('D3', 'A3')),
    'Bb': dict(sub='Bb1', ost=('Bb2', 'F3', 'Bb3', 'D3'), strA=('Bb1', 'D3', 'F3', 'Bb3', 'D4'),
               padB=('Bb1', 'F3', 'A3', 'D4'), pulse=('Bb2', 'F3')),
    'Gm': dict(sub='G1', ost=('G2', 'D3', 'G3', 'Bb2'), strA=('G1', 'D3', 'G3', 'Bb3', 'D4')),
    'A': dict(sub='A1', ost=('A2', 'E3', 'A3', 'C#3'), strA=('A1', 'C#3', 'E3', 'A3', 'E4')),
    'F': dict(sub='F1', ost=('F3', 'C4', 'F4', 'A3'), strA=('F2', 'C4', 'F4', 'A4', 'C5'),
              padB=('F2', 'C3', 'A3', 'E4'), pulse=('F3', 'C4')),
    'C': dict(sub='C2', ost=('E3', 'C4', 'E4', 'G3'), strA=('C2', 'C4', 'E4', 'G4', 'C5'),
              padB=('C2', 'E3', 'G3', 'D4'), pulse=('E3', 'C4')),
    'Fend': dict(sub='F1', padB=('F2', 'C3', 'A3', 'F4')),     # ring-out: plain F major
}
RING_PIANO = [('F2', 0.45), ('C4', 0.5), ('F4', 0.52), ('A4', 0.56)]
BREATH_CHORD = [('D3', 0.5), ('A3', 0.5), ('D4', 0.55), ('F4', 0.55), ('A4', 0.5)]   # the drop's Dm
OST_PATTERN = [0, 0, 1, 0, 2, 0, 1, 3]            # per 8th within a bar
MEL_A = ['A4', 'C5', 'E5', 'G5']                  # 복구 / 일상 / 제자리 / 회복
MEL_B = {'F': ['A5', 'F5', 'C5'], 'C': ['E5', 'C5', 'G5'],
         'Dm': ['F5', 'D5', 'A5'], 'Bb': ['D5', 'F5', 'A5']}
OUTRO_PAD = [('F2', 0.9, 0.35), ('C3', 0.8, 0.6), ('G3', 0.65, 0.75), ('E4', 0.5, 0.9), ('C5', 0.2, 1.0)]


def chord_at(t):
    for a, b, c in CHORDS:
        if a - 1e-9 <= t < b - 1e-9:
            return c
    return CHORDS[-1][2]


def open_chord_at(t):
    for a, b, c in OPEN_CHORDS:
        if a - 1e-9 <= t < b - 1e-9:
            return c
    return OPEN_CHORDS[-1][2]


# ---------------------------------------------------------------------------
# Mix levels (linear, pre-master)
# ---------------------------------------------------------------------------
LV = dict(
    room=0.010, hum=0.0045, spark=0.42, subswell=0.08,
    lowhit=0.53, piano=0.87, strings_open=0.16, tick=0.28,
    riser=0.05, breath=0.10, kick=0.62, accent=0.30, air=0.08, taiko=0.36, ost=0.40,
    strings_a=0.13, sub=0.25, shimmer=0.035, impact=0.70, whoosh=0.10,
    pad_b=0.12, pulse=0.16, ui=0.06, page=0.05, ring=0.87,
    softboom=0.42, pad_o=0.09, subdrop=0.36, sweep=0.04, chime=0.16, ember=0.28,
)

EVENTS = []          # (t, category, name, note)
KICK_TIMES = []


def ev(t, cat, name, note=''):
    EVENTS.append((round(float(t), 6), cat, name, note))


# ---------------------------------------------------------------------------
# DSP helpers
# ---------------------------------------------------------------------------

def rng_for(name, idx=0):
    return np.random.default_rng((zlib.crc32(name.encode('utf-8')) * 1000003 + idx) & 0xFFFFFFFF)


def ns(t):
    return int(round(t * SR))


def tvec(n):
    return np.arange(n) / SR


def db(x):
    return 20.0 * np.log10(max(float(x), 1e-12))


def undb(d):
    return 10.0 ** (d / 20.0)


NOTE_IDX = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
            'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def nf(name):
    """note name ('Bb3') -> Hz, A4 = 440"""
    p, o = (name[:2], name[2:]) if len(name) > 2 else (name[:1], name[1:])
    midi = 12 * (int(o) + 1) + NOTE_IDX[p]
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def noise(rng, n):
    return rng.standard_normal(n)


def att(t, a):
    return 1.0 - np.exp(-t / max(a, 1e-6))


def panlaw(p):
    a = (float(np.clip(p, -1, 1)) + 1.0) * np.pi / 4.0
    return np.cos(a) * np.sqrt(2.0), np.sin(a) * np.sqrt(2.0)


def st(x):
    x = np.asarray(x, float)
    return np.vstack((x, x)) if x.ndim == 1 else x


def fade(x, fin=0.002, fout=0.005):
    x = np.array(x, dtype=float, copy=True)
    n = x.shape[-1]
    a = min(int(fin * SR), n // 2)
    b = min(int(fout * SR), n // 2)
    if a > 0:
        x[..., :a] *= np.sin(np.linspace(0, np.pi / 2, a, endpoint=False)) ** 2
    if b > 0:
        x[..., n - b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return x


def normpk(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def logterp(t, tp, vp):
    return np.exp(np.interp(t, tp, np.log(vp)))


_SOS = {}


def _sos(kind, fc, order):
    key = (kind, fc if np.isscalar(fc) else tuple(float(f) for f in fc), order)
    if key not in _SOS:
        _SOS[key] = signal.butter(order, fc, btype=kind, fs=SR, output='sos')
    return _SOS[key]


def hp(x, fc, order=2):
    return signal.sosfilt(_sos('highpass', float(fc), order), x, axis=-1)


def lp(x, fc, order=2):
    return signal.sosfilt(_sos('lowpass', float(fc), order), x, axis=-1)


def bp(x, f1, f2, order=2):
    return signal.sosfilt(_sos('bandpass', (float(f1), float(f2)), order), x, axis=-1)


def _rbj(kind, fc, q):
    w0 = 2 * np.pi * np.clip(fc, 12.0, 0.46 * SR) / SR
    cw, sw = np.cos(w0), np.sin(w0)
    al = sw / (2 * q)
    if kind == 'lp':
        b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = b0
    elif kind == 'hp':
        b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = b0
    else:  # band-pass, 0 dB peak
        b0 = al; b1 = 0 * cw; b2 = -al
    a0 = 1 + al
    return b0 / a0, b1 / a0, b2 / a0, (-2 * cw) / a0, (1 - al) / a0


def tvf(x, fc, q=0.707, kind='lp', block=32):
    """time-varying RBJ biquad; coefficients updated every `block` samples,
    state carried across blocks (smooth for smooth fc curves)"""
    x = np.asarray(x, float)
    mono = x.ndim == 1
    X = x[None, :] if mono else x
    n = X.shape[1]
    fcv = np.broadcast_to(np.asarray(fc, float), (n,))
    qv = np.broadcast_to(np.asarray(q, float), (n,))
    idx = np.arange(0, n, block)
    b0, b1, b2, a1, a2 = _rbj(kind, fcv[idx], qv[idx])
    b1 = np.broadcast_to(b1, b0.shape)
    Y = np.empty_like(X)
    zi = np.zeros((X.shape[0], 2))
    for i, s in enumerate(idx):
        e = min(s + block, n)
        Y[:, s:e], zi = signal.lfilter((b0[i], b1[i], b2[i]), (1.0, a1[i], a2[i]),
                                       X[:, s:e], axis=1, zi=zi)
    return Y[0] if mono else Y


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    return signal.lfilter([1 - a], [1, -a], x, axis=-1)


# --- band-limited oscillators ------------------------------------------------
def _phase(freq, n, ph0):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    dt = f / SR
    ph = ph0 + np.concatenate(([0.0], np.cumsum(dt[:-1])))
    return np.mod(ph, 1.0), dt


def _blep(ph, dt):
    out = np.zeros_like(ph)
    m = ph < dt
    x = ph[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = ph > 1.0 - dt
    x = (ph[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def saw(freq, n, ph0=0.0):
    ph, dt = _phase(freq, n, ph0)
    return 2.0 * ph - 1.0 - _blep(ph, dt)


def square(freq, n, ph0=0.0, pw=0.5):
    ph, dt = _phase(freq, n, ph0)
    s = np.where(ph < pw, 1.0, -1.0)
    s += _blep(ph, dt)
    s -= _blep(np.mod(ph + 1.0 - pw, 1.0), dt)
    return s


def sine(freq, n, ph0=0.0):
    ph, _ = _phase(freq, n, ph0)
    return np.sin(2 * np.pi * ph)


def unison_saw(freq, n, rng, voices=5, detune=0.12, spread=0.7, drift=False):
    """detuned PolyBLEP saw stack with stereo spread; freq scalar or array"""
    out = np.zeros((2, n))
    offs = np.linspace(-1, 1, voices) if voices > 1 else np.zeros(1)
    t = tvec(n)
    for o in offs:
        f = np.asarray(freq, float) * 2.0 ** (o * detune / 12.0)
        if drift:
            f = f * (1.0 + 0.0012 * np.sin(2 * np.pi * rng.uniform(0.05, 0.22) * t
                                           + rng.uniform(0, 2 * np.pi)))
        v = saw(f, n, rng.random())
        gl, gr = panlaw(o * spread)
        out[0] += gl * v
        out[1] += gr * v
    return out / np.sqrt(voices)


def freq_line(segs, t0, t1, glide=0.03):
    """piecewise pitch line (abs-time segments), causal glide in log-frequency"""
    s0 = ns(t0)
    n = ns(t1) - s0
    lf = np.full(n, np.nan)
    for a, b, hz in segs:
        i0, i1 = max(ns(a) - s0, 0), min(ns(b) - s0, n)
        if i1 > i0:
            lf[i0:i1] = np.log2(hz)
    first = lf[~np.isnan(lf)][0]
    lf[0] = first if np.isnan(lf[0]) else lf[0]
    idx = np.where(~np.isnan(lf), np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    lf = lf[idx]
    g = max(1, ns(glide))
    lf = signal.lfilter(np.ones(g) / g, [1.0], np.concatenate((np.full(g, lf[0]), lf)))[g:]
    return 2.0 ** lf


# --- buses ------------------------------------------------------------------
class Bus:
    def __init__(self):
        self.x = np.zeros((2, N))

    def add(self, sig, t, gain=1.0, pan=0.0):
        sig = np.asarray(sig, float)
        if sig.ndim == 1:
            gl, gr = panlaw(pan)
            sig = np.vstack((sig * gl, sig * gr))
        elif pan:
            gl, gr = panlaw(pan)
            sig = sig * np.array([[gl], [gr]])
        s = ns(t)
        if s < 0:
            sig, s = sig[:, -s:], 0
        e = min(N, s + sig.shape[1])
        if e > s:
            self.x[:, s:e] += gain * sig[:, :e - s]


def duck_env(times, depth, release=0.2, attack=0.004, hold=0.0):
    """sidechain gain curve (analytic, from exact trigger times)"""
    g = np.ones(N)
    L = ns(attack + hold + release)
    tt = tvec(L)
    down = np.where(tt < attack, np.sin(np.clip(tt / attack, 0, 1) * np.pi / 2) ** 2,
                    1.0 - smoothstep((tt - attack - hold) / release))
    curve = 1.0 - depth * down
    for t in times:
        s = ns(t)
        e = min(N, s + L)
        if e > s:
            g[s:e] = np.minimum(g[s:e], curve[:e - s])
    return g


def cut_mask(t_cut, fade_s=0.003, keep_before=True):
    m = np.ones(N)
    s = ns(t_cut)
    f = ns(fade_s)
    m[s - f:s] = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    m[s:] = 0.0
    return m if keep_before else 1.0 - m


# --- reverb / delay -----------------------------------------------------------
def make_ir(name, rt_low, rt_high, length, predelay, er=0.3, width=1.0,
            lp_fc=12000, hp_fc=80, build=0.004):
    """stereo exponentially-decaying noise IR, 4 bands with their own RT60
    (damped highs), early reflections, pre-delay; unit energy per channel"""
    rng = rng_for('ir-' + name)
    n = ns(length)
    t = tvec(n)
    edges = [(None, 250.0), (250.0, 1200.0), (1200.0, 4500.0), (4500.0, None)]
    rts = np.geomspace(rt_low, rt_high, len(edges))
    ir = np.zeros((2, n))
    for ch in range(2):
        w = noise(rng, n)
        for (lo, hi), rt in zip(edges, rts):
            if lo is None:
                b = lp(w, hi, 4)
            elif hi is None:
                b = hp(w, lo, 4)
            else:
                b = bp(w, lo, hi, 2)
            ir[ch] += b * 10.0 ** (-3.0 * t / rt)
        for _ in range(12):                      # sparse early reflections
            tr = rng.uniform(0.003, 0.07)
            ir[ch, ns(tr)] += er * rng.uniform(0.4, 1.0) * (1.0 - tr / 0.08) * rng.choice([-1, 1]) * 6
    ir *= att(t, build)
    ir = hp(lp(ir, lp_fc, 2), hp_fc, 2)
    m, s = (ir[0] + ir[1]) / 2, (ir[0] - ir[1]) / 2 * width
    ir = np.vstack((m + s, m - s))
    ir /= np.sqrt(np.mean(np.sum(ir ** 2, axis=1)))
    return np.pad(ir, ((0, 0), (ns(predelay), 0)))


def reverb(send, ir, t0=0.0, t1=None):
    s0 = ns(t0)
    s1 = N if t1 is None else min(N, ns(t1))
    out = np.zeros((2, N))
    for ch in range(2):
        y = signal.oaconvolve(send[ch, s0:s1], ir[ch])
        e = min(N, s0 + len(y))
        out[ch, s0:e] = y[:e - s0]
    return out


def pingpong(send, delay=0.375, fb=0.36, taps=6, lp_fc=4200, hp_fc=350):
    mono = hp(lp(send.mean(axis=0), lp_fc), hp_fc)
    out = np.zeros((2, N))
    D = ns(delay)
    cur = mono
    for k in range(1, taps + 1):
        g = fb ** (k - 1)
        ch = (k - 1) % 2
        s = k * D
        if s >= N:
            break
        out[ch, s:] += g * cur[:N - s]
        out[1 - ch, s:] += 0.22 * g * cur[:N - s]
        cur = onepole_lp(cur, 5200)
    return out


# ---------------------------------------------------------------------------
# Instruments


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------
def stereo_noise(rng, n):
    return np.vstack((noise(rng, n), noise(rng, n)))


def mains_hum(rng, n):
    """60 Hz mains hum (Korea) with harmonics, slight wobble"""
    t = tvec(n)
    x = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.6), (3, 0.32), (4, 0.2), (5, 0.12), (6, 0.08), (8, 0.04), (10, 0.03)]:
        x += a * np.sin(2 * np.pi * 60.0 * k * t + rng.uniform(0, 2 * np.pi))
    return normpk(x * (1 + 0.08 * np.sin(2 * np.pi * 0.9 * t)))


def spark(rng):
    """power-strip arc: sharp snap (3 micro-discharges) + plastic housing 'tak',
    Poisson crackle of micro-arcs, 120 Hz-pulsed sizzle, short unstable buzz,
    then a soft smoke hiss"""
    n = ns(1.9)
    t = tvec(n)
    out = np.zeros((2, n))
    for d, g in [(0.0, 1.0), (0.0009, 0.55), (0.0024, 0.3)]:
        k = ns(d)
        m = n - k
        tt = t[:m]
        for ch in range(2):
            b = hp(noise(rng, m), 400) * np.exp(-tt / 0.00035)
            b += 0.35 * bp(noise(rng, m), 2500, 9000) * np.exp(-tt / 0.0015)
            out[ch, k:] += g * b * att(tt, 0.00005)
    body = np.zeros(n)
    for f, tau, a in [(430, .012, .22), (940, .008, .15), (1720, .005, .10), (2890, .003, .06)]:
        body += a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
    out += st(body * att(t, 0.0002))
    # crackle: micro-arcs, rate falling ~450/s -> ~10/s over ~0.45 s
    src = hp(noise(rng, ns(0.5)), 1200)
    tc = 0.004
    while True:
        tc += rng.exponential(1.0 / (450.0 * np.exp(-tc / 0.11) + 10.0))
        if tc >= 0.47:
            break
        L = ns(rng.uniform(0.0002, 0.0014))
        o = int(rng.integers(0, len(src) - L))
        grain = src[o:o + L] * np.exp(-np.arange(L) / (L / 3.0))
        g = 0.32 * rng.lognormal(0, 0.7) * np.exp(-tc / 0.18)
        gl, gr = panlaw(rng.uniform(-0.5, 0.5))
        k = ns(tc)
        out[0, k:k + L] += gl * g * grain
        out[1, k:k + L] += gr * g * grain
    # arc sizzle (120 Hz pulsed) + unstable buzz
    irr = normpk(lp(noise(rng, n), 25))
    irr = np.clip(0.55 + 0.6 * irr, 0, 1)
    am = np.abs(np.sin(2 * np.pi * 60.0 * t)) ** 6
    env = att(t, 0.001) * np.exp(-t / 0.09) * (t < 0.42)
    sz = lp(hp(stereo_noise(rng, n), 2500), 11000)
    out += 0.22 * sz * (0.35 + 0.65 * am) * irr * env
    bz = bp(square(120.0 * (1 + 0.004 * irr), n, 0.0, 0.3), 220, 3500)
    out += st(0.10 * normpk(bz) * irr * att(t, 0.003) * np.exp(-t / 0.075) * (t < 0.4))
    # smoke hiss
    hs = lp(hp(stereo_noise(rng, n), 1500), 7000)
    out += 0.028 * hs * smoothstep((t - 0.12) / 0.35) * np.exp(-np.maximum(t - 0.4, 0) / 0.42)
    return fade(normpk(out), 0.0, 0.1)


def felt_tick(rng, pitch=1.0, bright=0.0, a=0.0002):
    """soft felt clock pulse (muffled wooden tock)"""
    n = ns(0.09)
    t = tvec(n)
    x = np.zeros(n)
    for f, tau, a in [(760, .022, 1.0), (1290, .014, .5), (2130, .008, .25), (3400, .004, .12 * (1 + 2 * bright))]:
        x += a * np.sin(2 * np.pi * f * pitch * t) * np.exp(-t / tau)
    x += 0.25 * lp(noise(rng, n), 2500) * np.exp(-t / 0.002)
    x = lp(x * att(t, a), 4000 + 4000 * bright)
    return fade(normpk(hp(x, 300)), 0, 0.01)


_PIANO = {}


def piano(note, vel=0.7, dur=2.0, var=0):
    """additive felt piano: stretched partials (inharmonicity), felt-soft and
    velocity-dependent spectrum, strike-point comb, two-stage decay, three
    detuned strings spread L/R, hammer knock + felt thud, damper release"""
    key = (note, round(vel, 3), round(dur, 3), var)
    if key in _PIANO:
        return _PIANO[key]
    f0 = nf(note)
    rng = rng_for('piano-' + note, var)
    n = ns(dur + 1.0)
    t = tvec(n)
    reg = f0 / 261.63
    Bc = float(np.clip(1.3e-4 * reg ** 1.1, 4e-5, 1.2e-3))
    kc = 2.2 + 5.0 * vel
    tau1, tau2 = 0.45 * reg ** -0.35, 3.4 * reg ** -0.6
    out = np.zeros((2, n))
    norm = 0.0
    for k in range(1, 40):
        fk = f0 * k * np.sqrt(1 + Bc * k * k)
        a = k ** -1.1 * np.exp(-((k - 1) / kc) ** 1.3) * (0.15 + 0.85 * abs(np.sin(np.pi * k / 7.3)))
        if fk > 13000 or (k > 3 * kc and a < 1e-4):
            break
        env = (0.62 * np.exp(-t / (tau1 / (1 + 0.28 * (k - 1))))
               + 0.38 * np.exp(-t / (tau2 / (1 + 0.22 * (k - 1)))))
        strings = ((-0.7, 0.8, 0.35), (0.0, 0.6, 0.6), (0.75, 0.35, 0.8)) if k <= 12 else ((0.0, 0.7, 0.7),)
        for cents, gl, gr in strings:
            s = a * env * np.sin(2 * np.pi * fk * 2 ** (cents / 1200) * t + rng.uniform(0, 2 * np.pi))
            out[0] += gl * s
            out[1] += gr * s
        norm += a
    out *= att(t, 0.001) / (1.2 * norm)
    out += st(0.8 * bp(noise(rng, n), 1500, 6000) * np.exp(-t / 0.0006)
              + 0.05 * lp(noise(rng, n), 300) * np.exp(-t / 0.015))
    out *= np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.16))
    gl, gr = panlaw(float(np.clip(0.22 * np.log2(reg), -0.45, 0.45)))
    out = hp(out * np.array([[gl], [gr]]), 50) * vel
    _PIANO[key] = fade(out, 0, 0.05)
    return _PIANO[key]


def low_hit(rng, f_p, vel=1.0, tail=1.0, mallet=1.0):
    """muted timpani / felt sub hit: clean membrane modes on a pitched
    principal (+ sub octave), soft felt mallet, no distortion"""
    n = ns(3.0)
    t = tvec(n)
    penv = 1 + 0.28 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f_p * penv) / SR) * np.exp(-t / (0.85 * tail))
    if f_p / 2 >= 32:
        x += 0.7 * np.sin(2 * np.pi * np.cumsum(f_p / 2 * penv) / SR) * np.exp(-t / (0.7 * tail))
    for r, a, tau in zip([1.5, 1.98, 2.44, 2.94, 3.43], [0.4, 0.28, 0.18, 0.1, 0.06], [0.45, 0.32, 0.22, 0.15, 0.1]):
        x += a * np.sin(2 * np.pi * np.cumsum(f_p * r * penv) / SR) * np.exp(-t / (tau * tail))
    x *= att(t, 0.0025)
    x += 0.35 * lp(noise(rng, n), 500) * np.exp(-t / 0.01)
    x += 0.06 * mallet * bp(noise(rng, n), 900, 3500) * np.exp(-t / 0.0015)
    return fade(normpk(lp(x, 2500)) * vel, 0, 0.3)


def kick_freq(tune, t):
    return tune * (1 + 1.5 * np.exp(-t / 0.028)) + 70 * np.exp(-t / 0.005)


def kick_phase(tune, t_rel):
    """phase (rad) of the kick body t_rel seconds after its onset"""
    return 2 * np.pi * np.sum(kick_freq(tune, tvec(ns(t_rel) + 1))) / SR


def soft_kick(rng, tune, vel=1.0, decay=0.15):
    """deep, round kick: gentle pitch envelope, soft beater, low-passed"""
    n = ns(0.6)
    t = tvec(n)
    body = np.sin(2 * np.pi * np.cumsum(kick_freq(tune, t)) / SR)
    body *= att(t, 0.0012) * np.exp(-np.maximum(t - 0.01, 0) / decay)
    x = lp(body + 0.12 * lp(noise(rng, n), 700) * np.exp(-t / 0.004), 1500)
    return fade(x * vel, 0, 0.1)


def taiko(rng, f0=64.0, vel=1.0):
    """low taiko-like drum: circular-membrane modes, pitch drop, soft stick"""
    n = ns(2.2)
    t = tvec(n)
    penv = 1 + 0.18 * np.exp(-t / 0.025)
    x = np.zeros(n)
    for r, a, tau in zip([1.0, 1.594, 2.136, 2.296, 2.653, 2.918], [1.0, 0.5, 0.35, 0.25, 0.18, 0.12],
                         [0.55, 0.3, 0.22, 0.2, 0.14, 0.11]):
        x += a * np.sin(2 * np.pi * np.cumsum(f0 * r * penv) / SR + rng.uniform(0, 0.3)) * np.exp(-t / tau)
    x *= att(t, 0.0015)
    x += 0.35 * bp(noise(rng, n), 250, 2500) * np.exp(-t / 0.006)
    x += 0.08 * hp(noise(rng, n), 1500) * np.exp(-t / 0.002)
    return fade(normpk(lp(x, 5000)) * vel, 0, 0.3)


_SPIC = {}


def spiccato(note, vel=1.0, dur=0.26):
    """short bowed-string ostinato note: detuned saws, bow-noise onset,
    enveloped low-pass, sine body"""
    key = (note, round(vel, 2))
    if key in _SPIC:
        return _SPIC[key]
    rng = rng_for('spic-' + note)
    f = nf(note)
    n = ns(dur + 0.25)
    t = tvec(n)
    x = unison_saw(f, n, rng, voices=3, detune=0.12, spread=0.5) + 0.35 * st(sine(f, n))
    fc = 650 + 2000 * vel * np.exp(-t / 0.05)
    x = tvf(tvf(x, fc, 0.6, 'lp', 16), fc, 0.8, 'lp', 16)
    env = att(t, 0.005) * np.exp(-t / 0.16) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.04))
    x = x * env + st(0.08 * bp(noise(rng, n), 1800, 5000) * np.exp(-t / 0.008))
    _SPIC[key] = fade(normpk(hp(x, 70)) * vel, 0, 0.02)
    return _SPIC[key]


def felt_pulse(note, vel=1.0):
    n = ns(0.5)
    t = tvec(n)
    f = nf(note)
    x = sine(f, n) + 0.18 * sine(2 * f, n) + 0.06 * sine(3 * f, n)
    x *= att(t, 0.003) * np.exp(-t / 0.11)
    x += 0.05 * lp(noise(rng_for('pulse-' + note), n), 1500) * np.exp(-t / 0.003)
    return fade(normpk(lp(x, 1800)) * vel, 0, 0.02)


def string_bed(name, lines, t0, t1, fc, amp, voices=6, detune=0.16, vib=0.0022, glide=0.12, hp_fc=45):
    """ensemble strings/pad: per line a detuned PolyBLEP saw section with slow
    drift and delayed vibrato, 24 dB low-pass, faint bow air"""
    rng = rng_for(name)
    n = ns(t1) - ns(t0)
    t = tvec(n)
    out = np.zeros((2, n))
    offs = np.linspace(-1, 1, voices)
    for segs, g, spread in lines:
        f = freq_line([(a, b, nf(m)) for a, b, m in segs], t0, t1, glide)
        for o in offs:
            fm = f * 2 ** (o * detune / 12)
            fm = fm * (1 + 0.0015 * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * t + rng.uniform(0, 6.28)))
            fm = fm * (1 + vib * smoothstep(t / 1.5) * np.sin(2 * np.pi * rng.uniform(4.6, 5.6) * t + rng.uniform(0, 6.28)))
            v = saw(fm, n, rng.random())
            gl, gr = panlaw(o * spread)
            out[0] += g * gl * v
            out[1] += g * gr * v
    out /= np.sqrt(voices)
    out = tvf(tvf(out, fc, 0.55, 'lp', 64), fc, 0.8, 'lp', 64)
    out += 0.006 * bp(stereo_noise(rng, n), 2500, 7000) * smoothstep(np.asarray(fc) / 3000.0)
    return hp(out * amp, hp_fc)


def air_riser(rng, dur, crest=None):
    """soft airy band-passed noise rising to `crest` s, then falling away"""
    n = ns(dur)
    t = tvec(n)
    crest = dur if crest is None else crest
    u = np.clip(t / crest, 0, 1)
    fc = 800.0 * (9000.0 / 800.0) ** (u ** 1.2)
    x = tvf(stereo_noise(rng, n), fc, 1.4, 'bp', 64)
    x *= 10.0 ** ((-30.0 + 30.0 * u ** 1.1) / 20.0) * np.where(t < crest, 1.0, np.exp(-(t - crest) / 0.15))
    return fade(normpk(hp(x, 400)), 0.05, 0.02)


def breath_in(dur):
    """reverse-reverb 'breath-in': the drop's Dm chord (felt piano + short pad)
    and a soft cymbal are reverberated (no pre-delay), reversed and cropped,
    so the swell rises smoothly and arrives exactly at the end of the clip"""
    rng = rng_for('breath')
    L = ns(1.6)
    tt = tvec(L)
    dry = np.zeros((2, L))
    for nm, v in BREATH_CHORD:
        p = piano(nm, v, 1.0)[:, :L]
        dry[:, :p.shape[1]] += p
    lines = [([(0.0, 1.6, nm)], g, sp) for nm, g, sp in [('D3', 0.8, 0.4), ('A3', 0.7, 0.7), ('F4', 0.6, 0.9)]]
    pad = string_bed('breath-pad', lines, 0.0, 1.6, np.full(L, 1400.0), att(tt, 0.01) * np.exp(-tt / 0.5))
    dry = lp(dry, 2500) + 0.5 * normpk(pad) * np.max(np.abs(dry))
    cym = lp(hp(stereo_noise(rng, L), 3000), 9000) * att(tt, 0.001) * np.exp(-tt / 0.6)
    ir = make_ir('breath', 2.2, 1.1, 2.8, 0.0, er=0.15, lp_fc=7000, hp_fc=120)
    wet = np.vstack([signal.oaconvolve(dry[ch], ir[ch]) for ch in range(2)])
    m = ns(dur)
    x = (normpk(wet[:, ::-1][:, -m:]) + 0.3 * normpk(dry[:, ::-1][:, -m:])
         + 0.15 * normpk(cym[:, ::-1][:, -m:]))
    u = tvec(m) / dur
    x *= smoothstep(u / 0.6)                  # starts from nothing, rises smoothly
    return fade(normpk(hp(x, 60)), 0.0, 0.004)


def soft_whoosh(rng, dur=1.2):
    """gentle downward air whoosh (starts on the hit, no pre-roll)"""
    n = ns(dur)
    t = tvec(n)
    fc = 6000.0 * (300.0 / 6000.0) ** (t / dur)
    x = tvf(tvf(stereo_noise(rng, n), fc, 1.0, 'lp', 64), fc, 0.7, 'lp', 64)
    return fade(normpk(x * att(t, 0.01) * np.exp(-t / (dur * 0.3))), 0.002, 0.05)


def page_whoosh(rng, pre=0.26, post=0.4):
    """subtle page-switch swish, peaks at `pre` seconds, pans L->R"""
    n = ns(pre + post)
    t = tvec(n)
    u = t / (pre + post)
    fc = np.where(t < pre, 700 * (4500 / 700) ** (t / pre), 4500 * (1800 / 4500) ** ((t - pre) / post))
    x = tvf(noise(rng, n), fc, 1.2, 'bp', 32)
    env = np.where(t < pre, smoothstep(t / pre) ** 1.5, np.exp(-(t - pre) / (post * 0.3)))
    th = (0.15 + 0.7 * u) * np.pi / 2
    x = normpk(x * env)
    return fade(np.vstack((x * np.cos(th), x * np.sin(th))) * np.sqrt(2), 0.01, 0.05)


def ui_tick(rng):
    n = ns(0.05)
    t = tvec(n)
    x = np.sin(2 * np.pi * 2800 * t) * np.exp(-t / 0.004) + 0.3 * np.sin(2 * np.pi * 5200 * t) * np.exp(-t / 0.002)
    x += 0.2 * hp(noise(rng, n), 3000) * np.exp(-t / 0.0006)
    return fade(normpk(hp(x * att(t, 0.0003), 800)), 0, 0.01)


def shimmer_layer(rng, segs, t0, t1):
    """high glassy chord tones with slow 8th tremolo"""
    n = ns(t1) - ns(t0)
    t = tvec(n)
    x = np.zeros((2, n))
    for v in range(3):
        f = freq_line([(a, b, nf(ns_[v])) for a, b, ns_ in segs], t0, t1, 0.03)
        for det, ch in ((-1.6, 0), (1.6, 1)):
            x[ch] += sine(f * 2 ** (det / 1200), n, rng.random()) + 0.15 * sine(2 * f, n, rng.random())
    x *= 1 - 0.25 * (0.5 + 0.5 * np.cos(2 * np.pi * (2 / BEAT) * t))
    return normpk(x)


def light_sweep(rng, dur=1.25):
    """airy noise band + faint glass partials sweeping up and panning L->R"""
    n = ns(dur + 0.4)
    t = tvec(n)
    u = np.clip(t / dur, 0, 1)
    x = tvf(noise(rng, n), 1800.0 * (11000.0 / 1800.0) ** u, 3.0, 'bp', 32)
    env = smoothstep(t / (0.65 * dur)) * np.where(
        t < 0.65 * dur, 1.0, np.cos(np.clip((t - 0.65 * dur) / (0.35 * dur + 0.35), 0, 1) * np.pi / 2) ** 2)
    glass = np.zeros(n)
    for nm, g in [('F6', 1.0), ('C7', 0.6), ('A7', 0.35)]:
        glass += g * sine(nf(nm) * 2 ** (u * 5 / 12), n, rng.random())
    x = (normpk(x) + 0.12 * glass) * env
    th = (0.1 + 0.8 * u) * np.pi / 2
    return fade(normpk(hp(np.vstack((x * np.cos(th), x * np.sin(th))) * np.sqrt(2), 900)), 0.01, 0.05)


def clean_subdrop(rng, dur=3.0, f0=70.0, f1=32.0, sweep=1.5):
    n = ns(dur)
    t = tvec(n)
    u = np.clip(t / sweep, 0, 1)
    ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** u) / SR
    env = att(t, 0.002) * (1.0 - 0.2 * u) * np.where(t < 1.3, 1.0, np.exp(-(t - 1.3) / 0.5))
    s = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * env           # clean 2nd harmonic for small speakers
    s += 0.35 * lp(noise(rng, n), 400) * att(t, 0.001) * np.exp(-t / 0.03)
    s += 0.6 * bp(noise(rng, n), 900, 3500) * np.exp(-t / 0.0012)
    return fade(normpk(hp(s, 22)), 0, 0.4)


def chime_harmonic(rng, note='F6', dur=4.0):
    """soft high piano harmonic: nearly pure partials, glassy, slow decay"""
    n = ns(dur)
    t = tvec(n)
    f = nf(note)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.6) + 0.12 * np.sin(2 * np.pi * 2.003 * f * t) * np.exp(-t / 0.7)
         + 0.04 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.35))
    x = x * att(t, 0.0012) + 0.08 * bp(noise(rng, n), 2000, 6000) * np.exp(-t / 0.0015)
    return fade(normpk(x), 0, 0.5)


def ember(rng, dur=1.6):
    """tiny, warm fire crackle (first crackle exactly at t = 0)"""
    n = ns(dur)
    t = tvec(n)
    out = np.zeros((2, n))
    src = lp(hp(noise(rng, ns(0.4)), 700), 6000)
    times, tc = [0.0], 0.0
    while True:
        tc += rng.exponential(1.0 / (14.0 * np.exp(-tc / 0.8) + 2.0))
        if tc > dur - 0.2:
            break
        times.append(tc)
    for i, tc in enumerate(times):
        L = ns(0.005) if i == 0 else ns(rng.uniform(0.0006, 0.004))
        o = int(rng.integers(0, len(src) - L))
        grain = src[o:o + L] * np.exp(-np.arange(L) / (L / 4.0))
        g = (1.6 if i == 0 else 0.5 * rng.lognormal(0, 0.5)) * np.exp(-tc / 0.9)
        gl, gr = panlaw(rng.uniform(-0.35, 0.35))
        k = ns(tc)
        out[0, k:k + L] += gl * g * grain
        out[1, k:k + L] += gr * g * grain
    out += 0.02 * lp(hp(stereo_noise(rng, n), 800), 4000) * np.exp(-t / 0.5)
    return fade(normpk(out), 0, 0.2), times


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def render_hook(B):
    n = ns(HOOK1)
    t = tvec(n)
    rng = rng_for('room')
    rt = hp(lp(stereo_noise(rng, n), 650), 45)
    rt *= smoothstep(t / 0.2) * np.where(t < T_SPARK + 0.3, 1.0, np.exp(-(t - T_SPARK - 0.3) / 0.4))
    B['hook'].add(fade(rt, 0, 0.05), 0.0, LV['room'])
    t_off = T_SPARK + 0.33                                   # breaker trips: hum dies
    nh = ns(t_off + 0.08)
    th = tvec(nh)
    hum = mains_hum(rng_for('hum'), nh) * smoothstep(th / 0.25)
    hum *= 1 + 0.6 * smoothstep((th - T_SPARK) / 0.01) * np.exp(-np.maximum(th - T_SPARK, 0) / 0.15)
    B['hook'].add(fade(hum, 0, 0.08), 0.0, LV['hum'], 0.1)
    ev(0.0, 'hook', 'room tone + mains hum', '60 Hz hum, faint room noise')
    sp = spark(rng_for('spark'))
    B['hook'].add(sp, T_SPARK, LV['spark'], -0.12)
    B['s_room'].add(sp, T_SPARK, LV['spark'] * 0.5, -0.12)
    ev(T_SPARK, 'KEY', 'spark', 'power-strip snap (탁) + crackle ~0.45 s + buzz, then smoke hiss')
    ev(t_off, 'hook', 'hum cuts out', 'breaker trips; everything decays to near silence by ~2.3 s')
    # low sub swell into the first phrase, dipping just before it
    t0 = 1.6
    n = ns(OPEN0) - ns(t0)
    tt = tvec(n)
    u = tt / (OPEN0 - t0)
    x = (sine(nf('D1'), n) + 0.45 * sine(nf('D2'), n)) * u ** 2.2
    x *= np.where(tt < (OPEN0 - t0) - 0.07, 1.0, np.cos(np.clip((tt - (OPEN0 - t0) + 0.07) / 0.07, 0, 1) * np.pi / 2) ** 2)
    B['hook'].add(x, t0, LV['subswell'])
    ev(t0, 'hook', 'sub swell', f'D1 swell into {OPEN0:.3f}')


def render_opening_and_build(B):
    # ---- words play the motif ---------------------------------------------------
    for t, kind, text in HITS:
        if not (OPEN0 <= t < SWELL0) or kind not in ('phrase', 'note'):
            continue
        bar = OPEN0 + np.floor((t - OPEN0) / BAR + 1e-9) * BAR
        pi = int(round((bar - OPEN0) / BAR))
        idx = int(round((t - bar) / BEAT))
        note = MOTIF[min(pi, len(MOTIF) - 1)][min(idx, 2)]
        last = idx == len(MOTIF[min(pi, len(MOTIF) - 1)]) - 1
        vel = (0.78 if kind == 'phrase' else 0.64) + (0.06 if pi >= 3 else 0.0)
        p = piano(note, vel, 1.9 if last else 1.2)
        B['piano'].add(p, t, LV['piano'])
        B['s_hall'].add(p, t, LV['piano'] * 0.45)
        if kind == 'phrase':
            root = HIT_ROOT[open_chord_at(t)]
            h = low_hit(rng_for('lowhit', pi), nf(root), 1.0 if pi < 4 else 1.1)
            B['hits'].add(h, t, LV['lowhit'])
            B['s_dark'].add(h, t, LV['lowhit'] * 0.25)
            ev(t, 'KEY', f'phrase "{text}"', f'low hit ({root}) + piano {note}')
        else:
            ev(t, 'KEY', f'note "{text}"', f'piano {note}')

    # ---- string bed: Dm | Bbmaj7 | Gm9 | A | Bbmaj7 A, swell + crescendo, crest at
    #      14.2 and a natural fall-away (short tail, filter closing) ----------------
    t0, t1 = OPEN0, A0
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    lines = []
    for vi, notes in enumerate(OPEN_LINES):
        segs = [(a, b, m) for (a, b, _), m in zip(OPEN_CHORDS, notes)]
        lines.append((segs, [1.0, 0.8, 0.7, 0.62, 0.5][vi], [0.2, 0.45, 0.65, 0.8, 0.9][vi]))
    fc = logterp(tt, [t0, t0 + 5, BUILD0, CREST, A0], [420, 700, 1100, 3600, 1500])
    amp = np.interp(tt, [t0, t0 + 2.5, t0 + 7.5, BUILD0, CREST], [0.0, 0.35, 0.7, 0.85, 1.2]) ** 1.3
    amp *= np.where(tt < CREST, 1.0, np.exp(-(tt - CREST) / 0.16))
    x = string_bed('strings-open', lines, t0, t1, fc, amp)
    x = fade(x, 0.05, 0.02)
    B['strings'].add(x, t0, LV['strings_open'])
    B['s_hall'].add(x, t0, LV['strings_open'] * 0.5)
    ev(t0, 'music', 'string bed in', f'Dm | Bbmaj7 | Gm9 | A | Bbmaj7 A; crescendo to {CREST:.3f}, then falls away')

    # ---- felt clock pulse on beats; accelerating through the build ----------------
    tr = rng_for('ticks')
    ticks = [(OPEN0 + i * BEAT, 1.0 if i % 4 == 0 else 0.8, 1.0 if i % 2 == 0 else 0.9)
             for i in range(int(round((BUILD0 - OPEN0) / BEAT)))]
    e8, e16 = BEAT / 2, BEAT / 4
    acc0 = BUILD0 + 2 * BEAT                     # 13.75
    ticks += [(BUILD0 + i * e8, 0.8, 1.0) for i in range(int(round((acc0 - BUILD0) / e8)))]
    ticks += [(acc0 + i * e16, v, 1.05) for i, v in enumerate([0.85, 0.7, 0.5, 0.3])]   # thin out by ~14.2
    for i, (t, v, p) in enumerate(ticks):
        tk = felt_tick(tr, p)
        B['ticks'].add(tk, t, LV['tick'] * v, 0.08 * (-1) ** i)
        B['s_hall'].add(tk, t, LV['tick'] * v * 0.15)
        ev(t, 'tick', 'felt tick' + (' (accelerating)' if t >= acc0 else ''))

    # ---- airy riser -----------------------------------------------------------------
    r0 = BUILD0 + BEAT
    rz = air_riser(rng_for('riser'), A0 - 0.1 - r0, CREST - r0)
    B['fx'].add(rz, r0, LV['riser'])
    B['s_hall'].add(rz, r0, LV['riser'] * 0.3)
    ev(r0, 'KEY', 'string crescendo + airy riser', f'soft ticks accelerate from {acc0:.3f}, thin out by {CREST + 0.02:.3f}')
    ev(CREST, 'KEY', 'build crest', 'strings + riser peak and fall away naturally (short tails)')

    # ---- breath-in: reversed piano/pad reverb + soft reversed cymbal into 15.000 --
    br = breath_in(A0 - SWELL0)
    B['fx'].add(br, SWELL0, LV['breath'])
    B['s_hall'].add(br, SWELL0, LV['breath'] * 0.15)
    ev(SWELL0, 'KEY', 'breath-in swell', f'reverse-reverb Dm piano + pad + soft reversed cymbal, arrives exactly at {A0:.3f}')


def render_drops(B):
    # ---- kicks (tuned to the bass root) + per-beat felt accent (cuts) --------------
    kA = [A0 + i * BEAT for i in range(int(round((A1 - A0) / BEAT)))]
    kB = [B0 + i * 2 * BEAT for i in range(int(round((B1 - B0) / (2 * BEAT))))]
    KICK_TIMES.extend(kA + kB)
    for i, t in enumerate(kA + kB):
        c = chord_at(t)
        v = (1.0 if i % 4 == 0 else 0.92) if t < A1 else 0.55
        B['kick'].add(soft_kick(rng_for('kick', i % 4), nf(CH[c]['sub']), v), t, LV['kick'])
        ev(t, 'kick', 'soft kick' + (' (tuned %s)' % CH[c]['sub']))
    ar = rng_for('accent')
    for i, t in enumerate(kA):
        B['ticks'].add(felt_tick(ar, 1.25, 0.6, 0.0002), t, LV['accent'] * (1.0 if i % 4 == 0 else 0.8), 0.1)
        n = ns(0.12)
        tt = tvec(n)
        puff = lp(hp(stereo_noise(ar, n), 4000), 12000) * att(tt, 0.0003) * np.exp(-tt / 0.018)
        B['ticks'].add(fade(puff, 0, 0.01), t, LV['air'])
        ev(t, 'KEY', f'cut "{next(w["text"] for w in TL["words"] if abs(w["t"] - t) < 1e-6)}"',
           'soft kick + felt accent' + (' + taiko' if abs((t - A0) / BAR - round((t - A0) / BAR)) < 1e-9 else ''))

    # ---- taiko on bar downbeats, soft impact + whoosh on 15.0 ------------------------
    for i, t in enumerate(np.arange(A0, A1 - 1e-9, BAR)):
        tk = taiko(rng_for('taiko', i), 62.0 if t < LIFT else 70.0, 1.0)
        B['hits'].add(tk, t, LV['taiko'])
        B['s_dark'].add(tk, t, LV['taiko'] * 0.2)
        ev(t, 'taiko', 'taiko (bar downbeat)')
    im = low_hit(rng_for('impact'), nf('D2'), 1.0, tail=1.2)
    B['hits'].add(im, A0, LV['impact'])
    B['s_dark'].add(im, A0, LV['impact'] * 0.3)
    wh = soft_whoosh(rng_for('whoosh'), 1.2)
    B['fx'].add(wh, A0, LV['whoosh'])
    B['s_hall'].add(wh, A0, LV['whoosh'] * 0.4)
    ev(A0, 'KEY', 'soft impact + whoosh', 'clean low hit (D) + taiko + downward air')

    # ---- 8th-note string ostinato (drop A) -----------------------------------------------
    for i, t in enumerate(np.arange(A0, A1 - 1e-9, BEAT / 2)):
        t = round(float(t), 6)
        c = chord_at(t)
        pos = int(round((t - (A0 + np.floor((t - A0) / BAR + 1e-9) * BAR)) / (BEAT / 2))) % 8
        note = CH[c]['ost'][OST_PATTERN[pos]]
        v = (1.0 if pos % 2 == 0 else 0.72) * (1.08 if t >= LIFT else 1.0)
        s = spiccato(note, round(v, 2))
        B['ost'].add(s, t, LV['ost'], -0.15 if pos % 2 else 0.15)
        B['s_hall'].add(s, t, LV['ost'] * 0.3)
        ev(t, 'ostinato', 'string 8th ' + note)

    # ---- string chord bed drop A --------------------------------------------------------
    chA = [(a, b, c) for a, b, c in CHORDS if a < A1 - 1e-9]
    lines = [([(a, b, CH[c]['strA'][v]) for a, b, c in chA], [0.9, 0.7, 0.65, 0.6, 0.5][v], [0.2, 0.5, 0.7, 0.85, 0.95][v])
             for v in range(5)]
    tA1 = A1 + 0.3                                   # short natural release into drop B
    n = ns(tA1) - ns(A0)
    tt = tvec(n) + A0
    fc = np.where(tt < LIFT, logterp(tt, [A0, LIFT], [1200, 1700]), logterp(tt, [LIFT, tA1], [2600, 3200]))
    fc = onepole_lp(fc, 20)
    amp = (smoothstep((tt - A0) / 0.3) * np.where(tt < LIFT, 0.85, 1.0)
           * np.where(tt < A1, 1.0, np.cos(np.clip((tt - A1) / 0.3, 0, 1) * np.pi / 2) ** 2))
    x = string_bed('strings-a', lines, A0, tA1, fc, amp)
    x *= (1 - 0.3 * (1 - duck_env(KICK_TIMES, 1.0, release=0.25)))[ns(A0):ns(A0) + x.shape[1]]
    x = fade(x, 0.002, 0.01)
    B['strings'].add(x, A0, LV['strings_a'])
    B['s_hall'].add(x, A0, LV['strings_a'] * 0.45)

    # ---- lift: piano melody + shimmer ------------------------------------------------------
    for i, note in enumerate(MEL_A):
        t = LIFT + i * BEAT
        p = piano(note, 0.72 + 0.03 * i, 1.4 if i < 3 else 1.1)
        B['piano'].add(p, t, LV['piano'])
        B['s_hall'].add(p, t, LV['piano'] * 0.5)
        ev(t, 'piano', 'piano ' + note, 'lift melody')
    sh = shimmer_layer(rng_for('shimmer'), [(LIFT, LIFT + 2 * BEAT, ('A5', 'C6', 'F6')),
                                            (LIFT + 2 * BEAT, A1, ('G5', 'C6', 'E6'))], LIFT, A1 + 0.2)
    n = sh.shape[1]
    tt = tvec(n)
    sh *= smoothstep(tt / 0.6) * np.where(tt < A1 - LIFT, 1.0, np.cos(np.clip((tt - (A1 - LIFT)) / 0.2, 0, 1) * np.pi / 2) ** 2)
    B['strings'].add(fade(sh, 0.005, 0.01), LIFT, LV['shimmer'])
    B['s_hall'].add(fade(sh, 0.005, 0.01), LIFT, LV['shimmer'] * 1.2)
    ev(LIFT, 'KEY', 'LIFT to F major', 'brighter strings, piano melody A4 C5 E5 G5, shimmer')

    # ---- drop B: pad, pulse, piano melody -------------------------------------------------
    chB = [(a, b, c) for a, b, c in CHORDS if a >= B0 - 1e-9]
    lines = [([(a, b, CH[c]['padB'][v]) for a, b, c in chB], [0.85, 0.7, 0.6, 0.5][v], [0.2, 0.55, 0.75, 0.9][v])
             for v in range(4)]
    tb1 = B1 + 1.0                                   # pad rings out into the outro
    n = ns(tb1) - ns(B0)
    tt = tvec(n) + B0
    amp = smoothstep((tt - B0) / 0.4) * np.interp(tt, [B0, RING0], [0.85, 1.0])
    amp *= np.where(tt < B1 - 0.1, 1.0, np.exp(-(tt - B1 + 0.1) / 0.35))      # natural decay 34.9 -> 35.8
    x = string_bed('pad-b', lines, B0, tb1, logterp(tt, [B0, RING0, tb1], [1500, 2100, 1300]), amp,
                   voices=6, detune=0.18, vib=0.0015)
    x *= (1 - 0.2 * (1 - duck_env(KICK_TIMES, 1.0, release=0.3)))[ns(B0):ns(B0) + n]
    B['strings'].add(fade(x, 0.01, 0.02), B0, LV['pad_b'])
    B['s_hall'].add(fade(x, 0.01, 0.02), B0, LV['pad_b'] * 0.5)
    B['s_space'].add(fade(x, 0.01, 0.02)[:, ns(RING0) - ns(B0):], RING0, LV['pad_b'] * 0.3)
    for i, t in enumerate(np.arange(B0, RING0 - 1e-9, BEAT / 2)):     # pulse stops before the ring-out
        t = round(float(t), 6)
        c = chord_at(t)
        note = CH[c]['pulse'][i % 2]
        v = 1.0 if i % 2 == 0 else 0.75
        B['pulse'].add(felt_pulse(note, v), t, LV['pulse'], 0.2 if i % 2 else -0.2)
        B['s_hall'].add(felt_pulse(note, v), t, LV['pulse'] * 0.2)
        ev(t, 'pulse', 'felt pulse ' + note)
    for bi, c in enumerate(['F', 'C', 'Dm', 'Bb']):
        for j, note in enumerate(MEL_B[c]):
            t = B0 + bi * BAR + j * BEAT
            last = (bi == 3 and j == 2)
            p = piano(note, 0.7 if j == 0 else 0.62, 2.0 if last else (1.6 if j == 2 else 1.0))
            B['piano'].add(p, t, LV['piano'] * 1.1)
            B['s_hall'].add(p, t, LV['piano'] * 0.45)
            B['s_delay'].add(p, t, LV['piano'] * 0.4)
            ev(t, 'piano', 'piano ' + note, 'drop B melody')
    ur = rng_for('ui')
    for t, kind, text in UI:
        if kind == 'tap':
            B['fx'].add(ui_tick(ur), t, LV['ui'], 0.2)
            ev(t, 'KEY', f'UI tap "{text}"', 'soft UI tick')
        elif kind == 'page':
            pw = page_whoosh(ur)
            B['fx'].add(pw, t - 0.26, LV['page'])
            B['s_hall'].add(pw, t - 0.26, LV['page'] * 0.3)
            ev(t, 'KEY', f'page whoosh "{text}"', 'swish PEAKS at this time (starts 0.26 s earlier)')
    # ---- ring-out: kick + pulse gone, Bb -> F chord decays naturally into the outro --
    for nm, v in RING_PIANO:
        p = piano(nm, v, 1.6)
        B['piano'].add(p, RING0, LV['ring'])
        B['s_hall'].add(p, RING0, LV['ring'] * 0.5)
        B['s_space'].add(p, RING0, LV['ring'] * 0.35)
    ev(RING0, 'KEY', 'ring-out', 'kick + pulse out; piano F2 C4 F4 A4 + pad on F, decaying 35.0-35.8 into the softboom')


def render_sub(B):
    """clean sine sub on the chord roots, phase-locked to each kick's tail so
    the kick hands over to the bass constructively (reset while ducked)"""
    t0, t1 = A0, B1 + 0.8
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    f = freq_line([(a, b, nf(CH[c]['sub'])) for a, b, c in CHORDS], t0, t1, 0.03)
    cph = 2 * np.pi * np.concatenate(([0.0], np.cumsum(f[:-1]))) / SR
    ph = np.zeros(n)
    kidx = [ns(k) - ns(t0) for k in KICK_TIMES]
    for j, k0 in enumerate(kidx):
        a = 0 if j == 0 else k0 + ns(0.02)
        b = n if j == len(kidx) - 1 else kidx[j + 1] + ns(0.02)
        r = k0 + ns(0.1)
        ph[a:b] = cph[a:b] - cph[k0] + kick_phase(f[r], 0.1) - (cph[r] - cph[k0])
    sub = (np.sin(ph) + 0.1 * np.sin(2 * ph)) * duck_env(KICK_TIMES, 1.0, release=0.14, hold=0.06)[ns(t0):ns(t1)]
    sub *= np.where(tt < A1, 1.0, 0.7) * smoothstep((tt - t0) / 0.02)
    sub *= np.where(tt < RING0, 1.0, np.exp(-(tt - RING0) / 0.3))         # ring-out: sub fades with the chord
    B['sub'].add(fade(sub, 0.002, 0.02), t0, LV['sub'])


def render_outro(B):
    for t, kind, text in HITS:
        if t < OUT0:
            continue
        if kind == 'softboom':
            h = low_hit(rng_for('softboom'), nf('F1'), 0.9, tail=1.3, mallet=0.7)
            B['outro'].add(h, t, LV['softboom'])
            B['s_space'].add(h, t, LV['softboom'] * 0.7)
            ev(t, 'KEY', f'softboom "{text}"', 'warm low hit (F)')
        elif kind == 'chord':
            n = ns(DUR) - ns(t)
            tt = tvec(n)
            lines = [([(t, DUR, nm)], g, sp) for nm, g, sp in OUTRO_PAD]
            env = smoothstep(tt / 1.4) * np.where(tt < 3.2, 1.0, np.cos(np.clip((tt - 3.2) / 6.8, 0, 1) * np.pi / 2) ** 2)
            fc = (650 + 750 * att(tt, 2.0)) * (1 + 0.12 * np.sin(2 * np.pi * 0.09 * tt))
            x = string_bed('pad-o', lines, t, DUR, fc, env, voices=6, detune=0.15, vib=0.0012)
            B['outro'].add(fade(x, 0.01, 0.01), t, LV['pad_o'])
            B['s_space'].add(fade(x, 0.01, 0.01), t, LV['pad_o'] * 0.7)
            p = piano('A4', 0.7, 4.0)
            B['outro'].add(p, t, LV['piano'])
            B['s_space'].add(p, t, LV['piano'] * 0.55)
            ev(t, 'KEY', f'chord "{text}"', 'Fmaj9 (no 3rd) pad + felt piano A4 = the missing third')
        elif kind == 'subdrop':
            sd = clean_subdrop(rng_for('subdrop'))
            B['outro'].add(sd, t, LV['subdrop'])
            ls = light_sweep(rng_for('sweep'), BAR / 2)
            B['outro'].add(ls, t, LV['sweep'])
            B['s_space'].add(ls, t, LV['sweep'] * 1.2)
            ev(t, 'KEY', 'subdrop (logo)', f'70->32 Hz clean sub + airy sweep L->R to {t + BAR / 2:.3f}')
        elif kind == 'chime':
            c = chime_harmonic(rng_for('chime'))
            B['outro'].add(c, t, LV['chime'], 0.15)
            B['s_space'].add(c, t, LV['chime'] * 0.8, 0.15)
            ev(t, 'KEY', 'chime', 'soft piano harmonic F6')
        elif kind == 'ember':
            e, times = ember(rng_for('ember'))
            B['outro'].add(e, t, LV['ember'], -0.1)
            B['s_space'].add(e, t, LV['ember'] * 0.3)
            p = piano('F2', 0.62, DUR - t - 0.3)
            B['outro'].add(p, t, LV['piano'] * 0.9)
            B['s_space'].add(p, t, LV['piano'] * 0.4)
            ev(t, 'KEY', 'ember', f'gentle crackle ({len(times)} pops) + last low piano F2')
    ev(DUR - 0.05, 'end', 'digital silence', 'fade complete; last 50 ms are zeros')


# ---------------------------------------------------------------------------
# Mix / master
# ---------------------------------------------------------------------------

def k_weight(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)


def loudness_blocks(x, win=0.4, hop=0.1):
    p = (k_weight(x) ** 2).sum(axis=0)
    c = np.concatenate(([0.0], np.cumsum(p)))
    W, H = ns(win), ns(hop)
    starts = np.arange(0, len(p) - W + 1, H)
    return starts, (c[starts + W] - c[starts]) / W


def lufs_integrated(x):
    _, ms = loudness_blocks(x)
    lk = -0.691 + 10 * np.log10(ms + 1e-20)
    g1 = ms[lk > -70]
    if len(g1) == 0:
        return -np.inf
    rel = -0.691 + 10 * np.log10(g1.mean()) - 10
    return -0.691 + 10 * np.log10(ms[(lk > -70) & (lk > rel)].mean())


def compressor(x, thresh_db=-15.0, ratio=1.8, attack=0.02, release=0.15, knee=6.0, B=32):
    p = np.mean(x ** 2, axis=0)
    a = np.exp(-1 / (0.015 * SR))
    lvl = 10 * np.log10(signal.lfilter([1 - a], [1, -a], p) + 1e-12)
    over = lvl - thresh_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    n = len(gr)
    nb = (n + B - 1) // B
    grb = np.pad(gr, (0, nb * B - n)).reshape(nb, B).max(axis=1)
    ca, cr = 1 - np.exp(-B / (attack * SR)), 1 - np.exp(-B / (release * SR))
    y = np.empty(nb)
    cur = 0.0
    for k in range(nb):
        v = grb[k]
        cur += (v - cur) * (ca if v > cur else cr)
        y[k] = cur
    g = 10 ** (-np.repeat(y, B)[:n] / 20)
    g = np.convolve(np.pad(g, (B // 2, B - 1 - B // 2), mode='edge'), np.ones(B) / B, mode='valid')
    return x * g, np.repeat(y, B)[:n]


def limiter(x, ceiling_db=-1.3, lookahead=0.003, release=0.12, B=16):
    c = undb(ceiling_db)
    n = x.shape[1]
    req = np.minimum(1.0, c / np.maximum(np.max(np.abs(x), axis=0), 1e-12))
    L = max(1, ns(lookahead))
    g = minimum_filter1d(req, size=2 * L + 1, mode='nearest')
    nb = (n + B - 1) // B
    gb = np.pad(g, (0, nb * B - n), constant_values=1.0).reshape(nb, B).min(axis=1)
    rc = 1.0 - np.exp(-B / (release * SR))
    y = np.empty(nb)
    cur = 1.0
    for k in range(nb):
        cur = min(gb[k], cur + (1.0 - cur) * rc)
        y[k] = cur
    gs = np.convolve(np.pad(np.repeat(y, B)[:n], (L // 2, L - 1 - L // 2), mode='edge'),
                     np.ones(L) / L, mode='valid')
    return x * gs, gs


def true_peak_db(x):
    return db(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=1))))


def render():
    t_start = time.time()
    names = ['hook', 'hits', 'piano', 'strings', 'ost', 'pulse', 'kick', 'sub', 'ticks', 'fx', 'outro',
             's_room', 's_dark', 's_hall', 's_space', 's_delay']
    B = {k: Bus() for k in names}
    render_hook(B)
    render_opening_and_build(B)
    render_drops(B)
    render_sub(B)
    render_outro(B)
    print(f'  instruments rendered   {time.time() - t_start:6.1f} s')

    IR = dict(room=make_ir('room', 0.5, 0.25, 0.9, 0.004, er=0.5, lp_fc=9000, hp_fc=150),
              dark=make_ir('dark', 4.0, 0.9, 4.8, 0.03, er=0.2, lp_fc=4000, hp_fc=40),
              hall=make_ir('hall', 2.6, 1.3, 3.4, 0.022, er=0.25, lp_fc=9000, hp_fc=120),
              space=make_ir('space', 4.8, 2.2, 5.6, 0.045, er=0.25, lp_fc=9000, hp_fc=90))
    ret = dict(room=reverb(B['s_room'].x, IR['room'], 0.0, OPEN0),
               dark=reverb(B['s_dark'].x, IR['dark'], OPEN0, B1),
               hall=reverb(B['s_hall'].x, IR['hall'], 0.0, B1 + 1.0),
               space=reverb(B['s_space'].x, IR['space'], RING0 - 0.01, DUR),
               delay=pingpong(lp(B['s_delay'].x, 1800, 4), delay=0.75 * BEAT, fb=0.3, taps=5, lp_fc=2200, hp_fc=400))
    print(f'  reverbs                {time.time() - t_start:6.1f} s')

    sc = duck_env(KICK_TIMES, 1.0, release=0.25)
    ret['hall'] *= 1 - 0.15 * (1 - sc)
    gains = dict(room=0.6, dark=0.4, hall=0.8, space=0.85, delay=1.3)
    for k in ret:
        ret[k] *= gains[k]

    # delay echoes of the drop-B melody fade out with the ring-out
    dfade = np.ones(N)
    d0, d1 = ns(B1 - 0.4), ns(B1 + 0.6)
    dfade[d0:d1] = np.cos(np.linspace(0, np.pi / 2, d1 - d0)) ** 2
    dfade[d1:] = 0.0
    ret['delay'] *= dfade
    stems = {k: B[k].x for k in ['hook', 'hits', 'piano', 'strings', 'ost', 'pulse', 'kick', 'sub', 'ticks', 'fx', 'outro']}
    for k, v in ret.items():
        stems['rev_' + k] = v
    stems = {k: hp(v, 20, 2) for k, v in stems.items()}
    mix = sum(stems.values())

    # ---- master: glue comp -> gain to -14 LUFS -> look-ahead limiter ----------
    pre = undb(-18.0 - 10 * np.log10(np.mean(mix[:, ns(A0):ns(A1)] ** 2)))
    mix, comp_gr = compressor(mix * pre)
    target, ceiling = -14.0, -1.25
    gain = 1.0
    for _ in range(6):
        y, lg = limiter(mix * gain, ceiling)
        lu = lufs_integrated(y)
        gain *= undb(target - lu)
        if abs(target - lu) < 0.03:
            break
    for _ in range(4):
        y, lg = limiter(mix * gain, ceiling)
        tp = true_peak_db(y)
        if tp <= -1.05:
            break
        ceiling -= (tp + 1.05) + 0.05
    fe = np.ones(N)
    f0, f1 = ns(DUR - 1.0), ns(DUR - 0.05)
    fe[f0:f1] = np.cos(np.linspace(0, np.pi / 2, f1 - f0)) ** 2
    fe[f1:] = 0.0
    y *= fe
    info = dict(gain_db=db(gain), ceiling=ceiling, lim_gr=lg, comp_gr=comp_gr,
                lufs=lufs_integrated(y), tp=true_peak_db(y))
    print(f'  master                 {time.time() - t_start:6.1f} s   '
          f'LUFS {info["lufs"]:.2f}  TP {info["tp"]:.2f} dBTP  gain {info["gain_db"]:+.1f} dB  '
          f'max lim GR {-db(lg.min()):.1f} dB  max comp GR {comp_gr.max():.1f} dB')
    stems = {k: v * pre * gain for k, v in stems.items()}
    return y, stems, info


def write_wav24(path, x):
    x = np.clip(x, -1.0, 1.0 - 2.0 ** -23)
    i = np.ascontiguousarray(np.round(x.T * 8388607.0).astype('<i4'))
    b = i.view(np.uint8).reshape(-1, 4)[:, :3]
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b.tobytes())


def read_wav24(path):
    with wave.open(path, 'rb') as w:
        n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = np.frombuffer(w.readframes(n), dtype=np.uint8).reshape(-1, 3)
    i = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8) | (raw[:, 2].astype(np.int32) << 16))
    i = np.where(i >= 1 << 23, i - (1 << 24), i)
    return (i.reshape(-1, ch).T / 8388608.0), sw


def write_events(path, info):
    evs = sorted(EVENTS, key=lambda e: (e[0], e[1] != 'KEY'))
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('# music_events.txt - hits placed in build/music.wav (generated by src/music.py, v2)\n')
        fh.write(f'# 48 kHz / 24-bit / stereo / {DUR:.3f} s   grid: {TL["bpm"]} BPM, beat {BEAT} s, bar {BAR} s\n')
        fh.write(f'# master: {info["lufs"]:.1f} LUFS integrated, true peak {info["tp"]:.2f} dBTP\n')
        fh.write('# columns: time_s  frame@30fps  sample@48k  category  name  [note]\n')
        fh.write('# every onset is placed on the exact sample round(t*48000); no pre-roll except where noted\n\n')
        fh.write('## SECTIONS\n')
        for s in TL['sections']:
            fh.write(f'{s["start"]:8.3f} - {s["end"]:7.3f}  {s["name"]}\n')
        fh.write('\n## KEY SYNC POINTS\n')
        for t, cat, name, note in evs:
            if cat == 'KEY':
                fh.write(f'{t:8.3f}  {t * 30:7.2f}  {ns(t):8d}  {name}' + (f'  -- {note}' if note else '') + '\n')
        fh.write('\n## ALL HITS (chronological)\n')
        for t, cat, name, note in evs:
            fh.write(f'{t:8.3f}  {t * 30:7.2f}  {ns(t):8d}  {cat:<11s} {name}' + (f'  -- {note}' if note else '') + '\n')


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify(wav_path, stems, info):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    y, sw = read_wav24(wav_path)
    print('\n=== VERIFY ===')
    print(f'file: {wav_path}  {y.shape[1]} samples = {y.shape[1] / SR:.6f} s  ({sw * 8}-bit, {y.shape[0]} ch)')
    print(f'NaN/Inf: {int(np.sum(~np.isfinite(y)))}   DC L/R: {np.mean(y[0]):+.2e} / {np.mean(y[1]):+.2e}')
    print(f'sample peak {db(np.max(np.abs(y))):.2f} dBFS   true peak {true_peak_db(y):.2f} dBTP   '
          f'integrated {lufs_integrated(y):.2f} LUFS')
    try:
        r = subprocess.run(['/usr/local/bin/ffmpeg', '-hide_banner', '-nostats', '-i', wav_path, '-af',
                            'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
        tail = r.stderr[r.stderr.rfind('Summary:'):]
        print('ffmpeg ebur128:', ' | '.join(l.strip() for l in tail.splitlines() if any(
            k in l for k in ('I:', 'LRA:', 'Peak:'))))
    except Exception as e:  # pragma: no cover
        print('ffmpeg check failed', e)

    def rms_db(a, b):
        return 10 * np.log10(np.mean(y[:, ns(a):ns(b)] ** 2) + 1e-30)

    def pk_db(a, b):
        return db(np.max(np.abs(y[:, ns(a):ns(b)])))

    print('\nsection RMS / peak / max short-term LUFS (3 s) / L-R correlation')
    starts, ms = loudness_blocks(y, 3.0, 0.1)
    st_l = -0.691 + 10 * np.log10(ms + 1e-20)
    extra = [('hook 1.6-2.3 decay', (1.6, 2.3)), ('DEAD AIR', (SIL0, A0)), ('pre-stop 34.8-35', (STOP - 0.2, STOP)),
             ('post-stop 35-35.3', (STOP, STOP + 0.3)), ('post-stop 35-35.6', (STOP, STOP + 0.6)),
             ('last 50 ms', (DUR - 0.05, DUR))]
    for name, (a, b) in list(SEC.items()) + extra:
        seg = y[:, ns(a):ns(b)]
        corr = np.corrcoef(seg[0], seg[1])[0, 1] if np.std(seg[0]) > 1e-9 else float('nan')
        sel = (starts / SR >= a) & ((starts + ns(3.0)) / SR <= b + 1e-9)
        stm = st_l[sel].max() if sel.any() else float('nan')
        print(f'  {name:<20s} {a:6.3f}-{b:6.3f}  RMS {rms_db(a, b):7.1f} dBFS  peak {pk_db(a, b):7.1f} dBFS  '
              f'ST-max {stm:6.1f}  corr {corr:+.2f}')
    lg = info['lim_gr']
    print('  limiter max GR per section: ' + '  '.join(
        f'{nm} {-db(lg[ns(a):ns(b)].min()):.1f}' for nm, (a, b) in SEC.items()) + ' dB')
    dz = y[:, ns(SIL0):ns(A0)]
    print(f'  dead air {SIL0:.3f}-{A0:.3f}: {dz.shape[1]} samples, max |x| = {np.max(np.abs(dz)):.3e}, '
          f'all zero: {bool(np.all(dz == 0))};  last 50 ms all zero: {bool(np.all(y[:, ns(DUR - 0.05):] == 0))}')
    print(f'  hard stop at {STOP:.3f}: level drop (RMS 200 ms before vs 300 ms after) = '
          f'{rms_db(STOP - 0.2, STOP) - rms_db(STOP, STOP + 0.3):.1f} dB')

    print('\nstem loudness per section (LUFS, 400 ms gated) and peak')
    for k, v in (stems or {}).items():
        cells = '  '.join(f'{nm} {lufs_integrated(v[:, ns(a):ns(b)]):6.1f}' for nm, (a, b) in SEC.items())
        print(f'  {k:<10s} {cells}   peak {db(np.max(np.abs(v))):6.1f}')

    # onsets (HF band causal, ~0.1-0.2 ms group delay; LF band zero-phase)
    #  - hits with HF content (HF level jumps >= 3 dB): onset strength =
    #    energy in the 2 ms after a candidate sample / energy in the 8 ms
    #    before it; onset = earliest local peak within 1 dB of the maximum
    #    (+-10 ms search)
    #  - low-only hits: Hilbert amplitude envelope of the <300 Hz band, onset =
    #    first crossing of 20 % of the rise from the pre-level to the local max
    mono = y.mean(axis=0)
    hf = hp(mono, 1000, 4)            # causal: zero-phase would pre-ring ahead of transients
    lf = signal.sosfiltfilt(_sos('lowpass', 300.0, 4), mono)
    env_lf = np.abs(signal.hilbert(lf))
    cum = np.concatenate(([0.0], np.cumsum(hf ** 2)))
    P, Q = ns(0.002), ns(0.008)

    def jump(sig, t):
        return 10 * np.log10((np.mean(sig[ns(t):ns(t + 0.02)] ** 2) + 1e-20)
                             / (np.mean(sig[ns(t - 0.02):ns(t - 0.001)] ** 2) + 1e-20))

    def onset(t):
        jh = jump(hf, t)
        if jh >= 3.0:
            ks = np.arange(ns(t - 0.01), ns(t + 0.01))
            r = 10 * np.log10(((cum[ks + P] - cum[ks]) / P + 1e-20) / ((cum[ks] - cum[ks - Q]) / Q + 1e-20))
            peaks = [i for i in range(1, len(r) - 1) if r[i] >= r[i - 1] and r[i] >= r[i + 1] and r[i] >= r.max() - 1.0]
            i = peaks[0] if peaks else int(np.argmax(r))
            return 'HF', ks[i] / SR, jh, r[i]
        pre = np.median(env_lf[ns(t - 0.04):ns(t - 0.005)])
        post = env_lf[ns(t - 0.02):ns(t + 0.04)]
        thr = pre + 0.2 * (post.max() - pre)
        return 'LF', (ns(t - 0.02) + np.argmax(post > thr)) / SR, jump(lf, t), 0.0

    print('\nonsets of every timeline hit (HF onset strength, or LF envelope for low-only hits)')
    worst = 0.0
    for t, kind, text in HITS:
        if kind == 'silence':
            ok = bool(np.all(y[:, ns(t):ns(A0)] == 0)) and np.max(np.abs(y[:, ns(t) - ns(0.01):ns(t) - ns(0.003)])) > 0
            print(f'  {t:7.3f} {kind:<9s} exact zero from here to {A0:.3f}: {ok}')
            continue
        k, to, jmp, rise = onset(t)
        worst = max(worst, abs(to - t))
        print(f'  {t:7.3f} {kind:<9s} onset {1000 * (to - t):+5.1f} ms  ({k}, 20 ms jump {jmp:+5.1f} dB'
              + (f', 2/8 ms ratio {rise:+5.1f} dB' if k == 'HF' else '') + f')  {text}')
    print(f'  worst |onset error| = {1000 * worst:.2f} ms')

    # spectrogram
    f, tt, Z = signal.stft(mono, SR, nperseg=4096, noverlap=4096 - 480)
    S = 20 * np.log10(np.abs(Z) + 1e-9)
    S -= S.max()
    fig, ax = plt.subplots(2, 1, figsize=(24, 10), gridspec_kw=dict(height_ratios=[3, 1]), sharex=True)
    ax[0].pcolormesh(tt, f[1:], S[1:], shading='auto', cmap='magma', vmin=-100, vmax=0)
    ax[0].set_yscale('log')
    ax[0].set_ylim(25, 20000)
    ax[0].set_ylabel('Hz')
    for s in TL['sections']:
        for a in ax:
            a.axvline(s['start'], color='cyan', lw=0.8, alpha=0.7)
        ax[0].text(s['start'] + 0.1, 16000, s['name'], color='cyan', fontsize=10)
    for t, k, _ in HITS:
        ax[0].axvline(t, ymin=0, ymax=0.06, color='lime', lw=1.2)
    ax[0].set_title('music.wav (v2) spectrogram (log freq), lime ticks = timeline hits')
    tw = np.arange(0, N, 480) / SR
    rms = np.sqrt(np.convolve(mono ** 2, np.ones(480) / 480, mode='same'))[::480]
    ax[1].plot(tw, 20 * np.log10(rms + 1e-9), lw=0.6, color='k')
    ax[1].set_ylim(-90, 0)
    ax[1].set_ylabel('RMS dBFS (10 ms)')
    ax[1].set_xlabel('s')
    ax[1].set_xlim(0, DUR)
    ax[1].set_xticks(np.arange(0, DUR + 0.1, BAR))
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    png = os.path.join(BUILD_DIR, 'music_spectrogram.png')
    fig.savefig(png, dpi=80)
    print('\nspectrogram:', png)


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    out = os.path.join(BUILD_DIR, 'music.wav')
    if '--verify-only' in sys.argv:          # checks on the existing render
        y, _ = read_wav24(out)
        verify(out, None, dict(lim_gr=np.ones(N)))
        return
    t0 = time.time()
    y, stems, info = render()
    write_wav24(out, y)
    write_events(os.path.join(BUILD_DIR, 'music_events.txt'), info)
    print(f'wrote {out}  ({time.time() - t0:.1f} s total)')
    if '--verify' in sys.argv:
        verify(out, stems, info)


if __name__ == '__main__':
    main()
