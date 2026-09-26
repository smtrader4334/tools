#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music.py - original score for the 46 s 더함화재특종손해사정 brand film.

Everything is synthesised from scratch with numpy + scipy: no samples, no
downloads.  Deterministic: every random source is a numpy Generator seeded
from a CRC32 of its name, so two renders are bit-identical.

Reads   src/timeline.json   (120 BPM grid, word events with "hit", sections)
Writes  build/music.wav          48 kHz / 24-bit / stereo / exactly 46.000 s
        build/music_events.txt   every hit placed, with exact timestamps

Usage   python3 src/music.py            render
        python3 src/music.py --verify   render + numerical checks
                                        + build/music_spectrogram.png

Form (1 beat = 0.5 s, 1 bar = 2 s, t = 0 is a downbeat)
  hook    0-2     room tone, water drop at 1.00, black at 1.50
  opening 2-12    impacts on every word, D-minor drone, clock ticks,
                  count-down whirr + lock, heartbeat pause, bigboom 11.5
  build   12-16   smaller impacts, riser + accelerating snare/ticks,
                  dead air 15.5-16.0
  dropA   16-24   Dm Bb | Gm A | F C  (lift to major at 22.0)
  dropB   24-36   F C | Dm Bb | F C  pluck motif, hard stop at 36.0
  outro   36-46   softboom, boom + Fmaj9(no3) pad + felt-piano A4 (the
                  "missing" third is added), subdrop logo, drip bookend
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


def word_time(prefix, default):
    for w in TL['words']:
        if w['text'].startswith(prefix):
            return float(w['t'])
    return default


HOOK0, HOOK1 = SEC['hook']
OPEN0, OPEN1 = SEC['opening']
BUILD0, BUILD1 = SEC['build']
A0, A1 = SEC['dropA']
B0, B1 = SEC['dropB']
OUT0, OUT1 = SEC['outro']
T_DRIP_HOOK = HOOK0 + 1.0            # 1.00  water drop
T_BLACK = HOOK0 + 1.5                # 1.50  picture cuts to black
SIL0 = BUILD1 - BEAT                 # 15.50 dead air start
RISE0 = max(t for t, _, _ in HITS if BUILD0 <= t < BUILD1)   # 13.5
LIFT = word_time('복구', A0 + 6.0)    # 22.0  restoration: lift to major
GOLD = word_time('당신 편', A1 - BEAT)  # 23.5 gold title card
STOP = B1                            # 36.0  music stops dead

# chord map for the drops (start, end, chord)
CHORDS = [(A0, A0 + 2, 'Dm'), (A0 + 2, A0 + 4, 'Bb'), (A0 + 4, A0 + 5, 'Gm'),
          (A0 + 5, LIFT, 'A'), (LIFT, LIFT + 1, 'F'), (LIFT + 1, A1, 'C'),
          (B0, B0 + 2, 'F'), (B0 + 2, B0 + 4, 'C'), (B0 + 4, B0 + 6, 'Dm'),
          (B0 + 6, B0 + 8, 'Bb'), (B0 + 8, B0 + 10, 'F'), (B0 + 10, B1, 'C')]
CH = {
    'Dm': dict(bass='D2', stab=['A3', 'D4', 'F4'], arp=('A4', 'D5', 'F5', 'E5'),
               pad=('F3', 'A3', 'D4')),
    'Bb': dict(bass='Bb1', stab=['Bb3', 'D4', 'F4'], arp=('F4', 'Bb4', 'D5', 'C5'),
               pad=('F3', 'Bb3', 'D4')),
    'Gm': dict(bass='G1', stab=['Bb3', 'D4', 'G4']),
    'A': dict(bass='A1', stab=['A3', 'C#4', 'E4']),
    'F': dict(bass='F1', stab=['A3', 'C4', 'F4'], hi=['A3', 'C4', 'F4', 'A4', 'C5'],
              arp=('C5', 'F5', 'A5', 'G5'), pad=('F3', 'A3', 'C4'),
              shimmer=('A5', 'C6', 'F6')),
    'C': dict(bass='C2', stab=['G3', 'C4', 'E4'], hi=['G3', 'C4', 'E4', 'G4', 'C5'],
              arp=('G4', 'C5', 'E5', 'D5'), pad=('E3', 'G3', 'C4'),
              shimmer=('G5', 'C6', 'E6')),
}


def chord_at(t):
    for a, b, c in CHORDS:
        if a - 1e-9 <= t < b - 1e-9:
            return c
    return CHORDS[-1][2]


# ---------------------------------------------------------------------------
# Mix levels (linear, pre-master; instruments are normalised to ~peak 1)
# ---------------------------------------------------------------------------
LV = dict(
    roomtone=0.013, drip=0.50,
    boom=0.72, lock=0.42, countdown=0.11, heartbeat=0.46, tick=0.50,
    drone=0.22, tension=0.010,
    kick=0.80, clap=0.65, snare=0.55, hat=0.27, ohat=0.15, crash=0.25,
    bass_sub=0.38, bass_reese=0.24, stab=0.70, arp=0.48, padbed=0.25,
    shimmer=0.12, gold=0.15, riser_noise=0.075, riser_tone=0.060, riser_saw=0.035,
    whoosh=0.12, revcym=0.08, swell=0.10,
    pad=0.13, piano=0.30, subdrop=0.50, sweep=0.05,
)

EVENTS = []          # (t, category, name, note)
HIT_QUEUE = []       # impacts on the hits bus (for choke / duck handling)
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
def drip(rng):
    """water drop into a plastic basin: contact click, Minnaert bubble with
    rising pitch (van den Doel), rebound droplet, basin body modes, splash"""
    n = ns(0.5)
    t = tvec(n)
    out = np.zeros(n)
    out += 0.20 * bp(noise(rng, n), 2000, 9000) * np.exp(-t / 0.0005)
    d = ns(0.0012)
    tb = t[:n - d]
    f = 620.0 + 1130.0 * (1.0 - np.exp(-tb / 0.014))      # 620 -> ~1190 (15 ms) -> ~1620 Hz (30 ms)
    amp = att(tb, 0.0006) * np.exp(-tb / 0.024)
    out[d:] += np.sin(2 * np.pi * np.cumsum(f) / SR) * amp
    d2 = ns(0.047)                                          # tiny rebound droplet
    tb2 = t[:n - d2]
    f2 = 1250.0 + 1350.0 * (1.0 - np.exp(-tb2 / 0.008))
    out[d2:] += 0.15 * np.sin(2 * np.pi * np.cumsum(f2) / SR) * att(tb2, 0.0005) * np.exp(-tb2 / 0.011)
    for fm, tau, a in [(212, .060, .085), (486, .045, .07), (853, .030, .05),
                       (1377, .022, .035), (2210, .014, .022), (3390, .008, .014)]:
        out += a * np.sin(2 * np.pi * fm * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / tau) * att(t, 0.0004)
    out += 0.03 * hp(noise(rng, n), 3500) * att(t, 0.002) * np.exp(-t / 0.010)
    out = hp(out, 120)
    return fade(normpk(out), 0.0, 0.03)


def tick(rng, pitch=1.0, metal=0.5):
    """dry clock tick: short click exciting wooden + metallic modes"""
    n = ns(0.07)
    t = tvec(n)
    out = np.zeros(n)
    for f, tau, a in [(1180, .010, .45), (2150, .007, 1.0), (3320, .005, .6)]:
        out += a * np.sin(2 * np.pi * f * pitch * (1 + rng.normal(0, 0.004)) * t) * np.exp(-t / tau)
    for f, tau, a in [(4870, .014, .5), (6630, .011, .4), (8950, .006, .25)]:
        out += metal * a * np.sin(2 * np.pi * f * pitch * (1 + rng.normal(0, 0.004)) * t) * np.exp(-t / tau)
    out += 0.8 * hp(noise(rng, n), 3000) * np.exp(-t / 0.0005)
    out = hp(out * att(t, 0.00015), 700)
    return fade(normpk(out), 0.0, 0.01)


BOOM_P = {
    'boom':  dict(L=1.5, f1=(46.5, 49.5), f0=(100, 118), sweep=0.042, hold=0.03, tau=(0.28, 0.34),
                  satd=1.8, drive=(2.6, 3.6), mlp=(2800, 4200), mg=0.55, crack=0.22,
                  air=(0.10, 0.15), airtau=0.11, width=0.35, a=0.0012),
    'small': dict(L=1.3, f1=(47.0, 50.0), f0=(96, 110), sweep=0.04, hold=0.025, tau=(0.22, 0.26),
                  satd=1.6, drive=(2.4, 3.0), mlp=(3000, 3800), mg=0.48, crack=0.2,
                  air=(0.09, 0.12), airtau=0.09, width=0.3, a=0.0012),
    'big':   dict(L=3.4, f1=(41.2, 41.2), f0=(150, 150), sweep=0.06, hold=0.08, tau=(0.62, 0.62),
                  satd=2.2, drive=(4.2, 4.2), mlp=(5200, 5200), mg=0.72, crack=0.3,
                  air=(0.22, 0.22), airtau=0.32, width=0.85, a=0.001),
    'drop':  dict(L=2.2, f1=(36.7, 36.7), f0=(150, 150), sweep=0.05, hold=0.03, tau=(0.30, 0.30),
                  satd=2.0, drive=(4.0, 4.0), mlp=(5500, 5500), mg=0.62, crack=0.3,
                  air=(0.2, 0.2), airtau=0.22, width=0.8, a=0.001),
    'soft':  dict(L=2.4, f1=(43.65, 43.65), f0=(72, 72), sweep=0.06, hold=0.05, tau=(0.5, 0.5),
                  satd=1.3, drive=(1.2, 1.2), mlp=(900, 900), mg=0.22, crack=0.0,
                  air=(0.025, 0.025), airtau=0.25, width=0.3, a=0.004),
    'warm':  dict(L=2.2, f1=(43.65, 43.65), f0=(96, 96), sweep=0.045, hold=0.03, tau=(0.42, 0.42),
                  satd=1.6, drive=(2.0, 2.0), mlp=(1900, 1900), mg=0.40, crack=0.07,
                  air=(0.06, 0.06), airtau=0.18, width=0.45, a=0.002),
}


def boom(rng, kind='boom', vel=1.0):
    """cinematic impact: pitched sub drop + distorted mid punch + crack + air.
    returns (sub mono, rest stereo, reverb-send stereo)"""
    P = BOOM_P[kind]
    u = lambda v: rng.uniform(*v)
    f1, f0, tau, drive, mlp, air = u(P['f1']), u(P['f0']), u(P['tau']), u(P['drive']), u(P['mlp']), u(P['air'])
    n = ns(P['L'])
    t = tvec(n)
    f = f1 + (f0 - f1) * np.exp(-t / P['sweep'])
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = att(t, P['a']) * np.exp(-np.maximum(t - P['hold'], 0) / tau)
    sub = np.tanh(P['satd'] * sub * env) / np.tanh(P['satd'])

    fm = 58 + 330 * np.exp(-t / 0.014)
    body = np.sin(2 * np.pi * np.cumsum(fm) / SR) * np.exp(-t / 0.06)

    def mid_layer():
        nz = bp(noise(rng, n), 180, 3200) * np.exp(-t / 0.02)
        m = np.tanh(drive * (0.9 * body + 0.8 * nz)) * np.exp(-t / 0.12) * att(t, 0.0003)
        return hp(lp(m, mlp), 80)

    mL, mR = mid_layer(), mid_layer()
    M, S = (mL + mR) / 2, (mL - mR) / 2 * P['width']
    mid = np.vstack((M + S, M - S))
    crack = hp(noise(rng, n), 1800) * np.exp(-t / 0.0012) * att(t, 0.0001)
    aenv = att(t, 0.0008) * np.exp(-t / P['airtau'])
    airs = lp(hp(np.vstack((noise(rng, n), noise(rng, n))), 4500), 15000) * aenv
    rest = P['mg'] * mid + P['crack'] * st(crack) + air * airs
    if kind == 'big':   # extra weight + debris wash for the biggest hit
        ft = 52 + 70 * np.exp(-t / 0.03)
        tom = np.sin(2 * np.pi * np.cumsum(ft) / SR) * att(t, 0.001) * np.exp(-t / 0.22)
        wash = lp(np.vstack((noise(rng, n), noise(rng, n))), 2600) * att(t, 0.01) * np.exp(-t / 0.9)
        rest = rest + 0.35 * st(tom) + 0.10 * wash
    if kind == 'drop':
        wash = lp(np.vstack((noise(rng, n), noise(rng, n))), 3500) * att(t, 0.005) * np.exp(-t / 0.35)
        rest = rest + 0.08 * wash
    send = 0.9 * mid + 0.25 * airs + 0.15 * st(lp(sub, 200))
    return (fade(sub * vel, 0, 0.05), fade(rest * vel, 0, 0.05), fade(send * vel, 0, 0.05))


def queue_hit(t, parts, name, choke=(0.06, 0.35), sends=None, choke_at=None):
    """impacts are summed later so that each one can choke the previous tail"""
    HIT_QUEUE.append(dict(t=t, sub=parts[0], rest=parts[1], send=parts[2], name=name,
                          choke=choke, sends=sends or {'hall': 1.0}, choke_at=choke_at))


def lock_click(rng):
    """dry mechanical counter lock / stamp: latch clicks + metal ring + thunk"""
    n = ns(0.3)
    t = tvec(n)
    out = np.zeros(n)
    for d, g, b in [(0.0, 1.0, 1.0), (0.011, 0.55, 0.8), (0.026, 0.2, 0.7)]:
        k = ns(d)
        tt = t[:n - k]
        out[k:] += g * bp(noise(rng, n - k), 1500 * b, 9000) * np.exp(-tt / 0.0006)
    for f, tau, a in [(1873, .05, .30), (3121, .03, .22), (4652, .02, .15), (6980, .012, .08)]:
        out += a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau) * att(t, 0.0002)
    fb = 120 + 90 * np.exp(-t / 0.008)
    out += 0.9 * np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-t / 0.028) * att(t, 0.0003)
    out += 0.4 * lp(noise(rng, n), 500) * np.exp(-t / 0.012)
    return fade(normpk(hp(out, 60)), 0.0, 0.02)


def countdown(rng, dur=0.44):
    """numbers rolling down: decelerating digital blips with falling pitch
    over a band-passed descending whirr"""
    n = ns(dur + 0.06)
    t = tvec(n)
    out = np.zeros(n)
    times, tb = [], 0.0
    while tb < dur - 0.012:
        times.append(tb)
        tb += 1.0 / (46.0 * (12.0 / 46.0) ** (tb / dur))
    m = ns(0.014)
    tm = tvec(m)
    for tb in times:
        u = tb / dur
        f = 2600.0 * (620.0 / 2600.0) ** u
        b = (np.sin(2 * np.pi * f * tm) + 0.35 * np.sin(4 * np.pi * f * tm)
             + 0.12 * np.sin(2 * np.pi * 3.01 * f * tm))
        b *= att(tm, 0.0002) * np.exp(-tm / 0.0026)
        b += 0.25 * noise(rng, m) * np.exp(-tm / 0.0004)
        s = ns(tb)
        e = min(n, s + m)
        out[s:e] += (0.75 + 0.25 * u) * b[:e - s]
    u = np.clip(t / dur, 0, 1)
    fw = 520.0 * (140.0 / 520.0) ** u
    w = tvf(saw(fw, n), fw * 4.0, 3.0, 'bp')
    out += w * np.sin(np.pi * u) ** 1.5 * 0.45
    return fade(normpk(hp(out, 250)), 0.001, 0.01), times


def heartbeat(rng):
    n = ns(0.9)
    t = tvec(n)
    out = np.zeros(n)
    for d, g in [(0.0, 1.0), (0.19, 0.62)]:
        k = ns(d)
        tt = t[:n - k]
        f = 48 + 40 * np.exp(-tt / 0.03)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * att(tt, 0.004) * np.exp(-tt / 0.085)
        s += 0.3 * lp(noise(rng, n - k), 180) * att(tt, 0.002) * np.exp(-tt / 0.03)
        out[k:] += g * s
    return fade(normpk(out), 0, 0.05)


def kick_freq(tune, t):
    return tune + tune * 2.6 * np.exp(-t / 0.022) + 260 * np.exp(-t / 0.0035)


def kick_phase(tune, t_rel):
    """phase (rad) of the kick body t_rel seconds after its onset"""
    return 2 * np.pi * np.sum(kick_freq(tune, tvec(ns(t_rel) + 1))) / SR


def kick(rng, vel=1.0, tune=55.0, decay=0.08):
    """tight kick tuned to the bass root: fast pitch envelope, soft-clipped
    body, short click"""
    n = ns(0.45)
    t = tvec(n)
    body = np.sin(2 * np.pi * np.cumsum(kick_freq(tune, t)) / SR)
    env = att(t, 0.0004) * np.exp(-np.maximum(t - 0.012, 0) / decay)
    b = np.tanh(2.0 * body * env) / np.tanh(2.0)
    click = bp(noise(rng, n), 1500, 7000) * np.exp(-t / 0.0018)
    k = b + 0.22 * click + 0.08 * np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 0.0015)
    return fade(k * vel, 0, 0.06)


def clap(rng, vel=1.0):
    n = ns(0.45)
    t = tvec(n)
    out = np.zeros((2, n))
    for ch in range(2):
        nz = bp(noise(rng, n), 900, 5200)
        env = np.zeros(n)
        for o, g in zip([0.0, 0.0085, 0.0165, 0.025], [0.7, 0.8, 0.9, 1.0]):
            k = ns(max(0.0, o + rng.normal(0, 0.0006)))
            env[k:] += g * att(t[:n - k], 0.0002) * np.exp(-t[:n - k] / 0.0035)
        k = ns(0.025)
        env[k:] += 0.7 * np.exp(-t[:n - k] / 0.085)
        out[ch] = nz * env
    fb = 200 + 60 * np.exp(-t / 0.01)
    out += 0.3 * np.sin(2 * np.pi * np.cumsum(fb) / SR) * att(t, 0.0005) * np.exp(-t / 0.035)
    out = np.tanh(2.2 * normpk(hp(out, 180))) / np.tanh(2.2)       # denser, lower crest
    return fade(out * vel, 0, 0.03)


def snare(rng, vel=1.0, pitch=1.0, tail=0.06):
    n = ns(0.28)
    t = tvec(n)
    f = 190 * pitch * (1 + 0.6 * np.exp(-t / 0.008))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * att(t, 0.0003) * np.exp(-t / 0.045)
    nz = bp(noise(rng, n), 1200 * pitch, 11000) * att(t, 0.0002) * np.exp(-t / tail)
    s = np.tanh(1.6 * (0.55 * body + 0.9 * nz))
    return fade(normpk(hp(s, 150)) * vel, 0, 0.02)


HAT_METAL = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]


def hat(rng, decay=0.03, bright=1.0):
    n = ns(decay * 7 + 0.01)
    t = tvec(n)
    m = sum(square(f * 1.72, n, rng.random()) for f in HAT_METAL)
    m = bp(m, 7000 * bright, 16500)
    nz = hp(noise(rng, n), 7500 * bright, 2)
    x = (0.55 * normpk(nz) + 0.45 * normpk(m)) * att(t, 0.0002) * np.exp(-t / decay)
    return fade(np.tanh(1.8 * normpk(lp(x, 17000))) / np.tanh(1.8), 0, 0.004)


def crash(rng, dur=2.2):
    n = ns(dur)
    t = tvec(n)
    out = np.zeros((2, n))
    for ch in range(2):
        freqs = np.exp(rng.uniform(np.log(2500), np.log(12000), 40))
        m = np.zeros(n)
        for f in freqs:
            m += rng.uniform(0.2, 1) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / rng.uniform(0.3, 1.1))
        nz = hp(noise(rng, n), 3000)
        env = 0.45 * np.exp(-t / 0.05) + 0.55 * np.exp(-t / (0.32 * dur))
        out[ch] = (normpk(nz) + 0.35 * normpk(m)) * env * att(t, 0.0005)
    return fade(normpk(lp(out, 14000)), 0, 0.2)


def whoosh_down(rng, dur=1.0):
    n = ns(dur)
    t = tvec(n)
    x = np.vstack((noise(rng, n), noise(rng, n)))
    fc = 9000.0 * (260.0 / 9000.0) ** (t / dur)
    x = tvf(tvf(x, fc, 1.3, 'lp', 64), fc, 0.7, 'lp', 64)
    return fade(normpk(x * att(t, 0.004) * np.exp(-t / (dur * 0.3))), 0, 0.05)


def reverse_swell(rng, dur, lp_fc=3000.0):
    n = ns(dur)
    t = tvec(n)
    x = lp(np.vstack((noise(rng, n), noise(rng, n))), lp_fc)
    x *= np.exp(-(dur - t) / (dur * 0.28))
    return fade(normpk(x), 0.01, 0.002)


def noise_riser(rng, dur):
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    x = np.vstack((noise(rng, n), noise(rng, n)))
    fc = 350.0 * (13000.0 / 350.0) ** (u ** 1.15)
    x = tvf(x, fc, 1.4, 'lp', 64)
    x = tvf(x, fc * 0.15, 0.7, 'hp', 64)
    x *= 10.0 ** ((-32.0 + 32.0 * u ** 0.9) / 20.0)
    return fade(normpk(x), 0.02, 0.002)


def shepard_riser(rng, dur, base=55.0, octaves=1.5, comps=8, center=520.0, sigma=1.1):
    """Shepard-style rising tone in A (octave-spaced partials under a fixed
    log-frequency Gaussian) with a slight L/R detune for width"""
    n = ns(dur)
    t = tvec(n)
    r = octaves * (t / dur) ** 1.3
    out = np.zeros((2, n))
    for ch, det in ((0, -0.003), (1, 0.003)):
        for k in range(comps):
            f = base * 2.0 ** (k + r) * (1 + det)
            w = np.exp(-0.5 * (np.log2(f / center) / sigma) ** 2) * (f < 9000)
            out[ch] += w * np.sin(2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6.28))
    out *= (t / dur) ** 2
    return fade(normpk(out), 0.05, 0.002)


def stab(rng, freqs, dur=0.2, bright=1.0):
    """plucky detuned-saw chord stab through an enveloped 24 dB low-pass"""
    n = ns(dur + 0.35)
    t = tvec(n)
    x = np.zeros((2, n))
    for f in freqs:
        x += unison_saw(f, n, rng, voices=3, detune=0.09, spread=0.75)
    fc = 380 + 3600 * bright * np.exp(-t / 0.08)
    x = tvf(tvf(x, fc, 0.6, 'lp', 16), fc, 1.0, 'lp', 16)
    env = att(t, 0.002) * np.exp(-t / 0.17) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.05))
    x = np.tanh(1.6 * normpk(hp(x * env, 180))) / np.tanh(1.6)
    return fade(x, 0, 0.02)


def pluck(rng, f, dur=0.36, bright=1.0):
    n = ns(dur)
    t = tvec(n)
    x = (0.6 * saw(f * 2 ** (0.05 / 12), n, rng.random()) + 0.6 * saw(f * 2 ** (-0.05 / 12), n, rng.random())
         + 0.35 * square(f, n, rng.random(), 0.3) + 0.5 * sine(f, n))
    fc = 1.5 * f + 4200 * bright * np.exp(-t / 0.045)
    x = tvf(tvf(x, fc, 0.8, 'lp', 16), fc, 0.7, 'lp', 16)
    x *= att(t, 0.0015) * np.exp(-t / 0.11)
    return fade(normpk(hp(x, 250)), 0, 0.02)


def bell_note(f, n, t, amps=(1.0, 0.3, 0.22, 0.1, 0.06), ratios=(1.0, 2.0, 2.76, 4.07, 5.4),
              taus=(1.8, 1.0, 0.6, 0.35, 0.2)):
    y = np.zeros(n)
    for a, r, tau in zip(amps, ratios, taus):
        if f * r < 18000:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
    return y * att(t, 0.001)


def gold_chime(rng):
    """bright strummed C-major bell chord + high sparkle grains"""
    n = ns(3.0)
    t = tvec(n)
    out = np.zeros((2, n))
    for i, (nm, pan) in enumerate([('G5', -0.4), ('C6', -0.12), ('E6', 0.15), ('G6', 0.42)]):
        k = ns(0.014 * i)
        y = np.zeros(n)
        y[k:] = bell_note(nf(nm), n - k, t[:n - k]) * (1.0 - 0.1 * i)
        gl, gr = panlaw(pan)
        out[0] += gl * y
        out[1] += gr * y
    m = ns(0.03)
    tm = tvec(m)
    for _ in range(36):
        tg = rng.uniform(0.0, 0.9) ** 1.6
        k = ns(tg)
        f = rng.uniform(5000, 11000)
        g = 0.12 * np.exp(-tg / 0.4) * np.sin(2 * np.pi * f * tm) * att(tm, 0.0005) * np.exp(-tm / 0.008)
        gl, gr = panlaw(rng.uniform(-0.8, 0.8))
        e = min(n, k + m)
        out[0, k:e] += gl * g[:e - k]
        out[1, k:e] += gr * g[:e - k]
    return fade(normpk(hp(out, 300)), 0, 0.3)


def felt_piano(rng, f0, dur=7.0):
    """additive felt piano: stretched (inharmonic) partials, felt-soft spectrum,
    two-stage decay, three detuned strings (L/R), hammer thump"""
    n = ns(dur)
    t = tvec(n)
    Bc = 0.00035
    out = np.zeros((2, n))
    strings = [(-0.7, (1.0, 0.25)), (0.0, (0.7, 0.7)), (0.8, (0.25, 1.0))]
    for k in range(1, 26):
        fk = f0 * k * np.sqrt(1 + Bc * k * k)
        if fk > 15000:
            break
        a = (1.0 / k ** 1.2) * np.exp(-((k - 1) / 5.0) ** 1.4)
        env = 0.55 * np.exp(-t / (0.55 / (1 + 0.25 * (k - 1)))) + 0.45 * np.exp(-t / (3.6 / (1 + 0.45 * (k - 1))))
        for cents, (gl, gr) in strings:
            s = a * env * np.sin(2 * np.pi * fk * 2 ** (cents / 1200) * t + rng.uniform(0, 6.28))
            out[0] += gl * s
            out[1] += gr * s
    out *= att(t, 0.006)
    thump = lp(noise(rng, n), 350) * att(t, 0.001) * np.exp(-t / 0.025)
    out += 0.15 * st(thump) * np.max(np.abs(out))
    return fade(normpk(hp(out, 70)), 0, 0.3)


def subdrop(rng, dur=3.0, f0=80.0, f1=35.0, sweep=1.5):
    n = ns(dur)
    t = tvec(n)
    u = np.clip(t / sweep, 0, 1)
    f = f0 * (f1 / f0) ** u
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = att(t, 0.006) * (1.0 - 0.2 * u) * np.where(t < 1.3, 1.0, np.exp(-(t - 1.3) / 0.45))
    s *= env
    s = s + 0.25 * s * np.abs(s) + 0.15 * np.tanh(3 * s)       # 2nd/3rd harmonics for small speakers
    ft = 60 + 70 * np.exp(-t / 0.02)
    thump = np.sin(2 * np.pi * np.cumsum(ft) / SR) * att(t, 0.001) * np.exp(-t / 0.06)
    thump += 0.4 * lp(noise(rng, n), 250) * att(t, 0.001) * np.exp(-t / 0.035)
    s += 0.45 * thump
    return fade(normpk(hp(s, 22)), 0, 0.4)


def light_sweep(rng, dur=1.5):
    """airy noise band + faint glass partials sweeping up and panning L->R"""
    n = ns(dur + 0.35)
    t = tvec(n)
    u = np.clip(t / dur, 0, 1)
    fc = 1800.0 * (11000.0 / 1800.0) ** u
    x = tvf(noise(rng, n), fc, 3.0, 'bp', 32)
    env = smoothstep(t / (0.65 * dur)) * np.where(t < 0.65 * dur, 1.0, np.cos(np.clip((t - 0.65 * dur) / (0.35 * dur + 0.3), 0, 1) * np.pi / 2) ** 2)
    glass = np.zeros(n)
    for nm, g in [('F6', 1.0), ('C7', 0.6), ('A7', 0.35)]:
        glass += g * sine(nf(nm) * 2 ** (u * 5 / 12), n, rng.random())
    x = normpk(x) + 0.12 * glass
    x *= env
    th = (0.1 + 0.8 * u) * np.pi / 2
    out = np.vstack((x * np.cos(th), x * np.sin(th))) * np.sqrt(2)
    return fade(normpk(hp(out, 900)), 0.01, 0.05)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def render_hook(B):
    rng = rng_for('roomtone')
    n = ns(T_BLACK)
    t = tvec(n)
    x = hp(lp(np.vstack((noise(rng, n), noise(rng, n))), 650), 45)
    x *= (1.0 + 0.15 * np.sin(2 * np.pi * 0.7 * t + 1.0)) * smoothstep(t / 0.45)
    B['hook'].add(fade(x, 0.0, 0.012), HOOK0, LV['roomtone'])
    ev(HOOK0, 'hook', 'room tone', 'barely audible filtered noise, fades in')
    ev(T_BLACK, 'hook', 'room tone cut', 'cut to black: only the drip reverb tail remains')
    d = drip(rng_for('drip', 1))
    B['hook'].add(d, T_DRIP_HOOK, LV['drip'])
    B['s_room'].add(d, T_DRIP_HOOK, LV['drip'] * 0.6)
    ev(T_DRIP_HOOK, 'KEY', 'drip', 'water drop into plastic basin (톡); bubble peak ~+3 ms')


def render_opening_and_build(B):
    # ---- impacts from the timeline -------------------------------------
    phrase_first = {OPEN0, OPEN0 + 2, OPEN0 + 4, OPEN0 + 6, OPEN0 + 8}
    vr = rng_for('boomvel')
    small_i = 0
    for i, (t, kind, text) in enumerate(HITS):
        if not (OPEN0 <= t < BUILD1):
            continue
        if kind == 'boom' and t < BUILD0:
            v = (1.0 if t in phrase_first else 0.9) + vr.uniform(-0.03, 0.03)
            if text.endswith('?'):
                v = 1.0
            queue_hit(t, boom(rng_for('boom', i), 'boom', v), f'boom  "{text}"')
        elif kind == 'boom':
            v = 0.74 + 0.05 * small_i + vr.uniform(-0.02, 0.02)
            small_i += 1
            queue_hit(t, boom(rng_for('boom', i), 'small', v), f'boom (build) "{text}"')
        elif kind == 'bigboom':
            queue_hit(t, boom(rng_for('bigboom', i), 'big', 1.2), f'BIGBOOM "{text}"',
                      choke=(0.3, 0.55), sends={'hall': 1.6})
            sw = reverse_swell(rng_for('swell', i), 0.32)
            B['fx'].add(sw, t - 0.32, LV['swell'])
            B['s_hall'].add(sw, t - 0.32, LV['swell'] * 0.5)
            ev(t - 0.32, 'fx', 'reverse swell start', f'sucks into bigboom at {t:.3f}')
        elif kind == 'lock':
            lk = lock_click(rng_for('lock', i))
            z = np.zeros_like(lk)
            queue_hit(t, (z, st(lk) * (LV['lock'] / LV['boom']), st(lk) * 0.05 * (LV['lock'] / LV['boom'])),
                      f'lock  "{text}"', choke=(0.0, 0.2))
            # count-down whirr leading into the lock
            t_cd = t - BEAT + 0.03
            cd, blips = countdown(rng_for('countdown'), dur=BEAT - 0.06)
            B['ticks'].add(cd, t_cd, LV['countdown'])
            B['s_plate'].add(cd, t_cd, LV['countdown'] * 0.25)
            ev(t_cd, 'fx', 'count-down whirr start', f'{len(blips)} blips, pitch falling, decelerating')
            for b in blips:
                ev(t_cd + b, 'countdown', 'blip')
    # heartbeat in the tense pause (first beat with no word after 8.5)
    t_hb = OPEN0 + 7.0      # 9.0
    hb = st(heartbeat(rng_for('hb'))) * (LV['heartbeat'] / LV['boom'])
    queue_hit(t_hb, (np.zeros(hb.shape[1]), hb, hb * 0.4), 'heartbeat lub', choke=(0.0, 1.0))
    ev(t_hb + 0.19, 'hits', 'heartbeat dub', 'second (quieter) heartbeat thump')

    # ---- clock ticks ------------------------------------------------------
    tr = rng_for('ticks')
    ticks = []
    t = OPEN0
    while t < BUILD0 - 1e-9:
        on = int(round(t / BEAT)) % 2 == 0
        ticks.append((t, 1.0, 1.0 if on else 0.86, 0.12 if on else -0.12, 'tick' if on else 'tock'))
        if t >= OPEN0 + 6.0 - 1e-9:
            ticks.append((t + BEAT / 2, 0.42, 1.25, 0.0, 'tick (off-beat)'))
        t += BEAT
    grid = ([(BUILD0 + 0.25 * i, 0.8 + 0.02 * i) for i in range(int((RISE0 + 1.0 - BUILD0) / 0.25))]
            + [(RISE0 + 1.0 + 0.125 * i, 0.9) for i in range(4)]
            + [(RISE0 + 1.5 + 0.0625 * i, 0.95 + 0.01 * i) for i in range(8)])
    for i, (t, v) in enumerate(grid):
        ticks.append((t, v, 1.0 + 0.25 * ((t - BUILD0) / (SIL0 - BUILD0)), 0.1 * (-1) ** i, 'tick (build)'))
    for t, v, p, pan, name in ticks:
        tk = tick(tr, p, 0.5 if p < 1.2 else 0.7)
        B['ticks'].add(tk, t, LV['tick'] * v, pan)
        B['s_plate'].add(tk, t, LV['tick'] * v * 0.12, pan)
        ev(t, 'tick', name)

    # ---- drone: Dm | Bb/D | Gm/D | A  (continuous voices, glide) --------
    t0, t1 = OPEN0, SIL0
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    lines = [([(2.0, 12.0, 'D2'), (12.0, 15.5, 'A1')], 0.3, 1.0),
             ([(2.0, 8.0, 'A2'), (8.0, 10.0, 'Bb2'), (10.0, 12.0, 'G2'), (12.0, 15.5, 'E2')], 0.6, 0.8),
             ([(2.0, 10.0, 'D3'), (10.0, 12.0, 'Bb2'), (12.0, 15.5, 'A2')], 0.7, 0.7),
             ([(2.0, 10.0, 'F3'), (10.0, 12.0, 'D3'), (12.0, 15.5, 'E3')], 0.8, 0.6)]
    rng = rng_for('drone')
    x = np.zeros((2, n))
    for segs, spread, g in lines:
        f = freq_line([(a - OPEN0 + t0, b - OPEN0 + t0, nf(m)) for a, b, m in segs], t0, t1, 0.09)
        x += g * unison_saw(f, n, rng, voices=5, detune=0.10, spread=spread, drift=True)
    up = smoothstep((tt - BUILD0) / 1.5)            # build adds A3 + C#4 on top
    for nm, g in [('A3', 0.45), ('C#4', 0.4)]:
        x += g * up * unison_saw(nf(nm), n, rng, voices=5, detune=0.12, spread=0.9, drift=True)
    fc = logterp(tt, [2.0, 8.0, 12.0, RISE0, SIL0], [200, 380, 560, 900, 4200])
    fc *= 1 + 0.12 * np.sin(2 * np.pi * 0.11 * (tt - 2.0))
    q = np.interp(tt, [2.0, 12.0, SIL0], [0.8, 0.9, 1.6])
    x = tvf(tvf(x, fc, 0.6, 'lp', 64), fc, q, 'lp', 64)
    x *= np.interp(tt, [2.0, 3.0, 6.0, 11.5, 12.0, SIL0], [0.0, 0.3, 0.55, 0.9, 0.9, 1.1]) ** 1.2
    hit_t = [h['t'] for h in HIT_QUEUE]
    x *= duck_env(hit_t, 0.45, release=0.4)[ns(t0):ns(t1)]
    x = fade(hp(x, 35), 0.05, 0.002)
    B['music'].add(x, t0, LV['drone'])
    B['s_hall'].add(x, t0, LV['drone'] * 0.35)
    ev(t0, 'music', 'drone in', 'D-minor drone swells from silence')

    # high "tinnitus" tension A5 from the question (8.0) into the build
    t0b = OPEN0 + 6.0
    n = ns(SIL0) - ns(t0b)
    tt = tvec(n)
    y = np.vstack((sine(nf('A5') - 0.7, n), sine(nf('A5') + 0.7, n)))
    y += 0.25 * np.vstack((sine(nf('A6') + 0.4, n), sine(nf('A6') - 0.4, n)))
    y *= smoothstep(tt / 2.5) * (1 + 0.25 * smoothstep((tt - 4.0) / 3.5))
    B['music'].add(fade(y, 0.1, 0.002), t0b, LV['tension'])

    # ---- build: riser + accelerating snare roll ----------------------------
    dur = SIL0 - RISE0
    rz = noise_riser(rng_for('riser'), dur)
    B['fx'].add(rz, RISE0, LV['riser_noise'])
    B['s_hall'].add(rz, RISE0, LV['riser_noise'] * 0.3)
    sh = shepard_riser(rng_for('shepard'), dur)
    B['music'].add(sh, RISE0, LV['riser_tone'])
    B['s_hall'].add(sh, RISE0, LV['riser_tone'] * 0.3)
    n = ns(dur)
    tt = tvec(n)
    u = tt / dur
    rs = unison_saw(110.0 * 2 ** u, n, rng_for('risesaw'), voices=5, detune=0.15, spread=0.9)
    fc = 500.0 * (6000.0 / 500.0) ** (u ** 1.3)
    rs = tvf(tvf(rs, fc, 0.7, 'lp', 64), fc, 1.0, 'lp', 64) * u ** 1.5
    B['music'].add(fade(hp(rs, 120), 0.05, 0.002), RISE0, LV['riser_saw'])
    ev(RISE0, 'fx', 'riser start', 'noise sweep + Shepard tone + rising saw; hard cut at 15.5')
    roll = ([RISE0 + 0.25 * i for i in range(4)] + [RISE0 + 1.0 + 0.125 * i for i in range(4)]
            + [RISE0 + 1.5 + 0.0625 * i for i in range(8)])
    rr = rng_for('roll')
    for i, t in enumerate(roll):
        u = (t - RISE0) / dur
        s = snare(rr, 0.3 + 0.7 * u ** 1.3, 1.0 + 0.55 * u, 0.06 - 0.025 * u)
        pan = rr.uniform(-0.12, 0.12)
        B['drums'].add(s, t, LV['snare'], pan)
        B['s_plate'].add(s, t, LV['snare'] * 0.35, pan)
        ev(t, 'snare roll', 'snare', ['8th', '16th', '32nd'][0 if i < 4 else (1 if i < 8 else 2)])
    ev(SIL0, 'KEY', 'DEAD AIR', f'total digital silence {SIL0:.3f}-{BUILD1:.3f}')


def render_drops(B):
    # ---- kick / clap / hats ----------------------------------------------------
    kicks = np.round(np.arange(A0, B1 - 1e-9, BEAT), 6)
    KICK_TIMES.extend(kicks.tolist())
    for i, t in enumerate(kicks):
        tune = nf(CH[chord_at(t)]['bass'])
        B['kick'].add(kick(rng_for('kick', i % 4), 1.0 if i % 2 == 0 else 0.96, tune), t, LV['kick'])
        ev(t, 'kick', 'kick')
    claps = np.round(np.arange(A0 + BEAT, B1 - 1e-9, 2 * BEAT), 6)
    for i, t in enumerate(claps):
        c = clap(rng_for('clap', i % 6))
        B['drums'].add(c, t, LV['clap'])
        B['s_plate'].add(c, t, LV['clap'] * 0.3)
        if abs(t - (B1 - BEAT)) < 1e-6:
            B['s_tail'].add(c, t, LV['clap'] * 0.3)
        ev(t, 'clap', 'clap')
    hr = rng_for('hats')
    hats_dark = [hat(hr, 0.028, 1.0) for _ in range(8)]
    hats_bright = [hat(hr, 0.034, 1.12) for _ in range(8)]
    ohats = [hat(hr, 0.16, 1.0) for _ in range(4)]
    pat = [0.55, 0.36, 0.9, 0.42]
    for i, t in enumerate(np.round(np.arange(A0, B1 - 1e-9, BEAT / 4), 6)):
        v = pat[i % 4] + hr.uniform(-0.05, 0.05)
        if t >= B0 + 8.0:
            v *= 1.1
        bank = hats_dark if t < LIFT else hats_bright
        B['hats'].add(bank[i % 8], t, LV['hat'] * v, 0.18)
        B['s_plate'].add(bank[i % 8], t, LV['hat'] * v * 0.06, 0.18)
        ev(t, 'hat', 'closed hat')
    for i, t in enumerate(np.round(np.arange(B0 + 4.0 + BEAT / 2, B1 - 1e-9, BEAT), 6)):
        v = 0.7 if t < B0 + 8.0 else 1.0
        B['hats'].add(ohats[i % 4], t, LV['ohat'] * v, -0.2)
        ev(t, 'hat', 'open hat (off-beat)')

    # ---- crashes / impacts / whooshes -------------------------------------------
    for t, g, name in [(A0, 1.0, 'crash (drop A)'), (LIFT, 0.55, 'soft crash (lift)'),
                       (B0, 0.85, 'crash (drop B)'), (B0 + 8.0, 0.7, 'crash'),
                       (B1 - BEAT, 1.0, 'crash (final accent)')]:
        c = crash(rng_for('crash', int(t * 100)))
        B['drums'].add(c, t, LV['crash'] * g)
        B['s_plate'].add(c, t, LV['crash'] * g * 0.25)
        if abs(t - (B1 - BEAT)) < 1e-6:
            B['s_tail'].add(c, t, LV['crash'] * g * 0.25)
        ev(t, 'KEY' if t in (A0, LIFT, B0) else 'fx', name)
    queue_hit(A0, boom(rng_for('dropimpact'), 'drop', 1.0), 'IMPACT drop A', choke=(0.1, 0.4),
              sends={'hall': 1.2}, choke_at=A0 + BEAT)
    wd = whoosh_down(rng_for('whoosh'), 1.1)
    B['fx'].add(wd, A0, LV['whoosh'])
    B['s_hall'].add(wd, A0, LV['whoosh'] * 0.4)
    ev(A0, 'fx', 'whoosh (downward)', 'accent on the first hard cut')
    rc = reverse_swell(rng_for('revcym'), 0.55, 9000.0)
    rc = hp(rc, 2500)
    B['fx'].add(rc, LIFT - 0.55, LV['revcym'])
    ev(LIFT - 0.55, 'fx', 'reverse cymbal start', f'into the lift at {LIFT:.3f}')

    # ---- bass: reese + sub, pumped by the kick ------------------------------------
    t0, t1 = A0, B1
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    f = freq_line([(a, b, nf(CH[c]['bass'])) for a, b, c in CHORDS], t0, t1, 0.025)
    br = rng_for('bass')
    # sub sine phase-locked to each kick's tail (same pitch, same phase) so the
    # kick hands over to the bass constructively; the phase reset happens while
    # the sub is fully ducked (inaudible)
    cph = 2 * np.pi * np.concatenate(([0.0], np.cumsum(f[:-1]))) / SR
    ph = np.zeros(n)
    kidx = [ns(k) - ns(t0) for k in KICK_TIMES if t0 <= k < t1]
    for j, k0 in enumerate(kidx):
        a = 0 if j == 0 else k0 + ns(0.02)
        b = n if j == len(kidx) - 1 else kidx[j + 1] + ns(0.02)
        r = k0 + ns(0.1)
        off = kick_phase(f[r], 0.1) - (cph[r] - cph[k0])
        ph[a:b] = cph[a:b] - cph[k0] + off
    sub = np.tanh(1.3 * np.sin(ph)) / np.tanh(1.3)
    L = saw(f * 2 ** (0.13 / 12), n, br.random()) + 0.5 * saw(2 * f * 2 ** (0.06 / 12), n, br.random())
    R = saw(f * 2 ** (-0.13 / 12), n, br.random()) + 0.5 * saw(2 * f * 2 ** (-0.07 / 12), n, br.random())
    reese = np.vstack((L, R)) * 0.5
    imp = np.zeros(n)
    for t in np.arange(A0, B1 - 1e-9, BEAT / 4):
        step = int(round((t - A0) / (BEAT / 4))) % 4
        if t < B0:
            a = {2: 1.0}.get(step, 0.0) * (1.4 if t >= LIFT else 1.0)
        else:
            a = {1: 0.5, 2: 0.9, 3: 0.6}.get(step, 0.0) * (1.0 + 0.4 * smoothstep((t - (B1 - 4)) / 3.5))
        if a:
            imp[ns(t) - ns(t0)] = a
    k = np.exp(-1.0 / (0.075 * SR))
    fenv = signal.lfilter([1.0], [1.0, -k], imp)
    fenv = np.convolve(fenv, np.ones(ns(0.003)) / ns(0.003), mode='full')[:n]
    base = np.interp(tt, [A0, LIFT - 0.01, LIFT, B0, B1 - 4, B1], [170, 190, 260, 220, 240, 330])
    fc = base + 750 * fenv
    reese = tvf(tvf(reese, fc, 0.8, 'lp', 32), fc, 1.05, 'lp', 32)
    reese = np.tanh(2.4 * reese / (np.max(np.abs(reese)) + 1e-9))
    reese = hp(lp(reese, 3200), 120)
    M, S = (reese[0] + reese[1]) / 2, hp((reese[0] - reese[1]) / 2, 250)
    reese = np.vstack((M + S, M - S))
    sub *= duck_env(KICK_TIMES, 1.0, release=0.12, hold=0.06)[ns(t0):ns(t1)]
    reese *= duck_env(KICK_TIMES, 0.8, release=0.18, hold=0.04)[ns(t0):ns(t1)]
    B['bass'].add(fade(sub, 0.002, 0.003), t0, LV['bass_sub'])
    B['bass'].add(fade(reese / (np.max(np.abs(reese)) + 1e-9), 0.002, 0.003), t0, LV['bass_reese'])

    # ---- stabs --------------------------------------------------------------------
    sr = rng_for('stabs')
    stabs = []
    for bar in np.arange(A0, A1 - 1e-9, BAR):
        for step in (2, 6, 10, 14, 15):
            stabs.append((bar + step * BEAT / 4, step))
    for bar in np.arange(B0 + 4.0, B1 - 1e-9, BAR):
        for step in ((2, 10, 15) if bar < B0 + 8.0 else (2, 6, 10, 12, 14, 15)):
            stabs.append((bar + step * BEAT / 4, step))
    for t, step in stabs:
        t = round(float(t), 6)
        if t >= B1 - 1e-9:
            continue
        c = chord_at(t + BEAT / 4 + 1e-6) if step == 15 else chord_at(t)   # pickup anticipates
        lift = t >= LIFT - BEAT / 4 - 1e-9
        notes = CH[c]['hi'] if (lift and 'hi' in CH[c]) else CH[c]['stab']
        if t < A1:
            bright = (1.25 if lift else 0.55 + 0.3 * (t - A0) / (LIFT - A0))
        else:
            bright = 0.6 + 0.6 * smoothstep((t - B0) / (B1 - B0))
        v = 0.7 if step == 15 else 1.0
        final = abs(t - (B1 - BEAT)) < 1e-6
        if final:
            notes, bright, v = CH[c]['hi'], 1.4, 1.2
        s = stab(sr, [nf(m) for m in notes], 0.4 if final else 0.18, bright) * v
        g = LV['stab'] * (0.8 if t >= B0 else 1.0)
        B['stabs'].add(s, t, g)
        B['s_plate'].add(s, t, g * 0.25)
        B['s_delay'].add(s, t, g * 0.35)
        if final:
            B['s_tail'].add(s, t, g * 0.4)
        ev(t, 'KEY' if final else 'stab', 'stab ' + c, 'final accent "싸웁니다"' if final else '')

    # ---- drop B pluck motif (16ths, 3-3-2 feel) ----------------------------------
    motif = {0: (0, 1.0), 3: (1, 0.75), 6: (2, 0.85), 8: (3, 0.95), 10: (1, 0.7), 11: (0, 0.65), 14: (2, 0.8)}
    pr = rng_for('arp')
    for bar in np.arange(B0, B1 - 1e-9, BAR):
        for step, (deg, v) in motif.items():
            t = round(float(bar + step * BEAT / 4), 6)
            c = chord_at(t)
            f = nf(CH[c]['arp'][deg])
            bright = 0.55 + 0.5 * smoothstep((t - B0) / (B1 - B0 - 0.5))
            p = pluck(pr, f, 0.36, bright) * v
            pan = 0.25 * np.sin(step * 0.9)
            B['arp'].add(p, t, LV['arp'], pan)
            B['s_delay'].add(p, t, LV['arp'] * 0.6, pan)
            B['s_plate'].add(p, t, LV['arp'] * 0.25, pan)
            ev(t, 'pluck', 'pluck ' + CH[c]['arp'][deg])

    # ---- drop B pad bed (sidechained), voice-led --------------------------------
    t0, t1 = B0, B1
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    rng = rng_for('padbed')
    x = np.zeros((2, n))
    for v in range(3):
        segs = [(a, b, nf(CH[c]['pad'][v])) for a, b, c in CHORDS if a >= B0 - 1e-9]
        x += unison_saw(freq_line(segs, t0, t1, 0.08), n, rng, voices=5, detune=0.14, spread=0.9, drift=True)
    fc = logterp(tt, [B0, B0 + 8, B1], [900, 1300, 2600])
    x = tvf(tvf(x, fc, 0.6, 'lp', 64), fc, 0.8, 'lp', 64)
    x *= smoothstep((tt - B0) / 1.0) * np.interp(tt, [B0, B0 + 8, B1], [0.7, 0.85, 1.1])
    x *= (1 - 0.65 * (1 - duck_env(KICK_TIMES, 1.0, release=0.22)))[ns(t0):ns(t1)]
    B['pads'].add(fade(hp(normpk(x), 150), 0.01, 0.003), t0, LV['padbed'])
    B['s_space_a'].add(fade(hp(normpk(x), 150), 0.01, 0.003), t0, LV['padbed'] * 0.3)

    # ---- restoration shimmer (22-24) ----------------------------------------------
    t0, t1 = LIFT, A1 + 0.35
    n = ns(t1) - ns(t0)
    tt = tvec(n) + t0
    rng = rng_for('shimmer')
    x = np.zeros((2, n))
    for v in range(3):
        segs = [(a, b, nf(CH[c]['shimmer'][v])) for a, b, c in CHORDS if LIFT - 1e-9 <= a < A1]
        f = freq_line(segs, t0, t1, 0.02)
        for det, ch in ((-1.6, 0), (1.6, 1)):
            x[ch] += sine(f * 2 ** (det / 1200), n, rng.random()) + 0.18 * sine(2 * f, n, rng.random())
    trem = 1 - 0.3 * (0.5 + 0.5 * np.cos(2 * np.pi * 8.0 * (tt - t0)))
    x *= trem * smoothstep((tt - t0) / 0.08) * np.where(tt < A1, 1.0, np.cos(np.clip((tt - A1) / 0.35, 0, 1) * np.pi / 2) ** 2)
    x *= (1 - 0.5 * (1 - duck_env(KICK_TIMES, 1.0, release=0.2)))[ns(t0):ns(t1)]
    B['pads'].add(fade(normpk(x), 0.005, 0.01), t0, LV['shimmer'])
    B['s_space_a'].add(fade(normpk(x), 0.005, 0.01), t0, LV['shimmer'] * 1.2)
    ev(LIFT, 'KEY', 'LIFT to major', 'brighter stabs, filter open, shimmer layer in (복구)')

    # ---- gold sweetener 23.5 ----------------------------------------------------------
    g = gold_chime(rng_for('gold'))
    B['fx'].add(g, GOLD, LV['gold'])
    B['s_space_a'].add(g, GOLD, LV['gold'] * 0.8)
    ev(GOLD, 'KEY', 'gold sweetener', 'bell chord + sparkle ("당신 편")')

    # ---- drop B late build 34-35.5 -------------------------------------------------------
    tb0 = B1 - 2.0
    rz = noise_riser(rng_for('riser2'), 2.0)
    B['fx'].add(rz, tb0, LV['riser_noise'] * 0.5)
    ev(tb0, 'fx', 'riser (drop B)', 'noise swell into the dead stop at 36.0')
    sn = rng_for('snare2')
    times = [tb0 + 0.25 * i for i in range(4)] + [tb0 + 1.0 + 0.125 * i for i in range(4)]
    for i, t in enumerate(times):
        u = (t - tb0) / 1.5
        s = snare(sn, 0.35 + 0.5 * u, 1.05 + 0.3 * u, 0.05)
        B['drums'].add(s, t, LV['snare'] * 0.8, sn.uniform(-0.1, 0.1))
        B['s_plate'].add(s, t, LV['snare'] * 0.25)
        ev(t, 'snare fill', 'snare')
    ev(STOP, 'KEY', 'STOP DEAD', 'music hard-cuts on the downbeat; only a short reverb tail of 35.5')


def render_outro(B):
    for i, (t, kind, text) in enumerate(HITS):
        if t < OUT0:
            continue
        if kind == 'softboom':
            queue_hit(t, boom(rng_for('softboom', i), 'soft', 0.8), f'softboom "{text}"',
                      choke=(0.25, 0.5), sends={'space': 0.9})
        elif kind == 'boom':
            queue_hit(t, boom(rng_for('warmboom', i), 'warm', 0.72), f'boom (warm) "{text}"',
                      choke=(0.15, 0.6), sends={'space': 1.0})
            render_outro_pad(B, t)
        elif kind == 'subdrop':
            sd = subdrop(rng_for('subdrop'))
            z = np.zeros(sd.shape[-1])
            queue_hit(t, (sd * LV['subdrop'] / LV['boom'], np.vstack((z, z)), np.vstack((z, z))),
                      f'SUBDROP (logo) "{text}"', choke=(1.0, 1.0), sends={})
            ls = light_sweep(rng_for('sweep'))
            B['outro'].add(ls, t, LV['sweep'])
            B['s_space_o'].add(ls, t, LV['sweep'] * 1.2)
            ev(t, 'fx', 'light sweep', f'airy sweep L->R {t:.2f}-{t + 1.5:.2f}')
        elif kind == 'drip':
            d = drip(rng_for('drip', 1))                      # identical to the hook drop
            B['outro'].add(d, t, LV['drip'] * 0.9)
            B['s_space_o'].add(d, t, LV['drip'] * 0.75)
            B['s_room'].add(d, t, LV['drip'] * 0.3)
            ev(t, 'KEY', 'drip (bookend)', 'same drop as 1.00, long spacious reverb')
    ev(DUR - 0.05, 'end', 'digital silence', 'fade complete; last 50 ms are zeros')


def render_outro_pad(B, t0):
    """Fmaj9 without its third (F C G E C) - the felt piano adds the missing A"""
    t1 = DUR
    n = ns(t1) - ns(t0)
    tt = tvec(n)
    rng = rng_for('outropad')
    x = np.zeros((2, n))
    for nm, g, sp in [('F2', 0.9, 0.35), ('C3', 0.8, 0.6), ('G3', 0.7, 0.75), ('E4', 0.55, 0.9), ('C5', 0.22, 1.0)]:
        x += g * unison_saw(nf(nm), n, rng, voices=6, detune=0.15, spread=sp, drift=True)
    fc = (650 + 750 * att(tt, 2.0)) * (1 + 0.15 * np.sin(2 * np.pi * 0.09 * tt))
    x = tvf(tvf(x, fc, 0.6, 'lp', 64), fc, 0.85, 'lp', 64)
    env = smoothstep(tt / 1.4) * np.where(tt < 3.0, 1.0, np.cos(np.clip((tt - 3.0) / 5.1, 0, 1) * np.pi / 2) ** 2)
    x = fade(hp(normpk(x) * env, 55), 0.01, 0.01)
    B['outro'].add(x, t0, LV['pad'])
    B['s_space_o'].add(x, t0, LV['pad'] * 0.7)
    ev(t0, 'music', 'pad in', 'Fmaj9 (no 3rd), detuned saws, low-pass, space reverb')
    p = felt_piano(rng_for('piano'), nf('A4'))
    B['outro'].add(p, t0, LV['piano'], 0.1)
    B['s_space_o'].add(p, t0, LV['piano'] * 0.5, 0.1)
    ev(t0, 'KEY', 'felt piano A4', 'the "missing" third of the chord (더합니다)')


# ---------------------------------------------------------------------------
# Hits bus (choke + duck), mix, master
# ---------------------------------------------------------------------------
def flush_hits(B):
    q = sorted(HIT_QUEUE, key=lambda h: h['t'])
    onsets = [h['t'] for h in q]
    for i, h in enumerate(q):
        t = h['t']
        nxt = h['choke_at'] if h['choke_at'] is not None else next((o for o in onsets[i + 1:] if o > t + 0.01), None)
        sub, rest = st(h['sub']), h['rest']
        L = max(sub.shape[1], rest.shape[1])
        sub = np.pad(sub, ((0, 0), (0, L - sub.shape[1])))
        rest = np.pad(rest, ((0, 0), (0, L - rest.shape[1])))
        if nxt is not None and ns(nxt - t) < L:
            cs, cr = h['choke']
            k0 = max(0, ns(nxt - t - 0.01))
            ramp = np.cos(np.linspace(0, np.pi / 2, ns(0.03))) ** 2
            for arr, lvl in ((sub, cs), (rest, cr)):
                g = np.ones(L)
                k1 = min(L, k0 + len(ramp))
                g[k0:k1] = lvl + (1 - lvl) * ramp[:k1 - k0]
                g[k1:] = lvl
                arr *= g
        B['hits'].add(sub + rest, t, LV['boom'])
        for bus, amt in h['sends'].items():
            B['s_' + bus if bus != 'space' else 's_space_o'].add(h['send'], t, LV['boom'] * 0.5 * amt)
        ev(t, 'KEY', h['name'])
    return onsets


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
    names = ['hook', 'hits', 'ticks', 'kick', 'drums', 'hats', 'bass', 'stabs', 'arp', 'pads', 'music', 'fx', 'outro',
             's_room', 's_hall', 's_plate', 's_space_a', 's_space_o', 's_delay', 's_tail']
    B = {k: Bus() for k in names}
    render_hook(B)
    render_opening_and_build(B)
    render_drops(B)
    render_outro(B)
    hit_onsets = flush_hits(B)
    print(f'  instruments rendered   {time.time() - t_start:6.1f} s')

    IR = dict(room=make_ir('room', 0.55, 0.28, 0.9, 0.004, er=0.5, lp_fc=9000, hp_fc=150),
              hall=make_ir('hall', 4.2, 0.9, 4.8, 0.03, er=0.2, lp_fc=5000, hp_fc=50),
              plate=make_ir('plate', 1.4, 0.95, 2.0, 0.012, er=0.1, lp_fc=11000, hp_fc=180),
              space=make_ir('space', 4.8, 2.0, 5.5, 0.045, er=0.25, lp_fc=9000, hp_fc=90))
    ret = dict(
        room=reverb(B['s_room'].x, IR['room']),
        hall=reverb(B['s_hall'].x, IR['hall'], 0.0, B1),
        plate=reverb(B['s_plate'].x, IR['plate'], OPEN0, STOP),
        space_a=reverb(B['s_space_a'].x, IR['space'], A0, STOP),
        space_o=reverb(B['s_space_o'].x, IR['space'], OUT0, DUR),
        delay=pingpong(B['s_delay'].x),
        tail=reverb(B['s_tail'].x, IR['plate'], STOP - 1.0, STOP),
    )
    print(f'  reverbs                {time.time() - t_start:6.1f} s')

    sc = duck_env(KICK_TIMES, 1.0, release=0.2)
    hd = duck_env(hit_onsets, 1.0, release=0.3)
    ret['plate'] *= 1 - 0.35 * (1 - sc)
    ret['delay'] *= 1 - 0.3 * (1 - sc)
    ret['space_a'] *= 1 - 0.4 * (1 - sc)
    ret['hall'] *= 1 - 0.5 * (1 - hd)
    ret['tail'] *= (1.0 - cut_mask(STOP)) * 0.25
    ret['room'] *= 0.55
    ret['hall'] *= 0.75
    ret['plate'] *= 0.8
    ret['space_a'] *= 0.8
    ret['space_o'] *= 0.9
    ret['delay'] *= 1.2

    m_sil = np.ones(N)
    m_sil[ns(SIL0) - ns(0.002):ns(SIL0)] = np.cos(np.linspace(0, np.pi / 2, ns(0.002))) ** 2
    m_sil[ns(SIL0):ns(BUILD1)] = 0.0
    m_stop = cut_mask(STOP)
    stems = {}
    for k in ['hook', 'hits', 'ticks', 'kick', 'drums', 'hats', 'bass', 'stabs', 'arp', 'pads', 'music', 'fx', 'outro']:
        stems[k] = B[k].x
    for k, v in ret.items():
        stems['rev_' + k] = v
    for k, v in stems.items():
        v = hp(v, 20, 2) * m_sil
        if k in ('ticks', 'kick', 'drums', 'hats', 'bass', 'stabs', 'arp', 'pads', 'music', 'fx',
                 'rev_plate', 'rev_delay', 'rev_space_a', 'rev_hall'):
            v = v * m_stop
        stems[k] = v
    mix = sum(stems.values())

    # ---- master: glue comp -> gain to -14 LUFS -> look-ahead limiter ----------
    # pre-normalise so the glue compressor sees a known level (drop A RMS -> -18 dBFS)
    pre = undb(-18.0 - 10 * np.log10(np.mean(mix[:, ns(A0):ns(A1)] ** 2)))
    mix, comp_gr = compressor(mix * pre)
    target, ceiling = -14.0, -1.25
    gain = 1.0
    for _ in range(5):
        y, lg = limiter(mix * gain, ceiling)
        lu = lufs_integrated(y)
        gain *= undb(target - lu)
        if abs(target - lu) < 0.05:
            break
    for _ in range(4):
        y, lg = limiter(mix * gain, ceiling)
        tp = true_peak_db(y)
        if tp <= -1.0:
            break
        ceiling -= (tp + 1.0) + 0.05
    # hard gates after the limiter: dead air + final fade to digital silence
    y *= m_sil
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
        fh.write('# music_events.txt - hits placed in build/music.wav (generated by src/music.py)\n')
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
        seg = y[:, ns(a):ns(b)]
        return 10 * np.log10(np.mean(seg ** 2) + 1e-30)

    def pk_db(a, b):
        return db(np.max(np.abs(y[:, ns(a):ns(b)])) if ns(b) > ns(a) else 0)

    print('\nsection RMS / peak / max short-term LUFS (3 s) / L-R correlation')
    starts, ms = loudness_blocks(y, 3.0, 0.1)
    st_l = -0.691 + 10 * np.log10(ms + 1e-20)
    for name, (a, b) in list(SEC.items()) + [('hook 0-1.0', (0.0, 1.0)), ('DEAD AIR 15.5-16', (SIL0, BUILD1)),
                                            ('after stop 36-36.4', (STOP, STOP + 0.4)), ('last 50 ms', (DUR - 0.05, DUR))]:
        seg = y[:, ns(a):ns(b)]
        corr = np.corrcoef(seg[0], seg[1])[0, 1] if np.std(seg[0]) > 1e-9 else float('nan')
        sel = (starts / SR >= a) & ((starts + ns(3.0)) / SR <= b + 1e-9)
        stm = st_l[sel].max() if sel.any() else float('nan')
        print(f'  {name:<20s} {a:6.2f}-{b:6.2f}  RMS {rms_db(a, b):7.1f} dBFS  peak {pk_db(a, b):7.1f} dBFS  '
              f'ST-max {stm:6.1f}  corr {corr:+.2f}')
    lg = info['lim_gr']
    print('  limiter max GR per section: ' + '  '.join(
        f'{nm} {-db(lg[ns(a):ns(b)].min()):.1f}' for nm, (a, b) in SEC.items()) + ' dB')
    print(f'  max |x| in dead air: {np.max(np.abs(y[:, ns(SIL0):ns(BUILD1)])):.3e}  '
          f'max |x| last 50 ms: {np.max(np.abs(y[:, ns(DUR - 0.05):])):.3e}')

    print('\nstem loudness in drop windows (LUFS, 400 ms gated) ')
    for k, v in stems.items():
        la = lufs_integrated(v[:, ns(A0):ns(A1)])
        lb = lufs_integrated(v[:, ns(B0):ns(B1)])
        lo = lufs_integrated(v[:, ns(OPEN0):ns(OPEN1)])
        lbu = lufs_integrated(v[:, ns(BUILD0):ns(SIL0)])
        lou = lufs_integrated(v[:, ns(OUT0):ns(OUT1)])
        print(f'  {k:<12s} opening {lo:7.1f}  build {lbu:7.1f}  dropA {la:7.1f}  dropB {lb:7.1f}  outro {lou:7.1f}'
              f'   peak {db(np.max(np.abs(v))):6.1f} dBFS')

    # onset check: power spectral flux (hop 1.33 ms) + threshold crossing
    mono = y.mean(axis=0)
    nfft, hop = 512, 64
    f, tt, Z = signal.stft(mono, SR, nperseg=nfft, noverlap=nfft - hop, boundary='even', padded=True)
    P = np.abs(Z) ** 2
    flux = np.maximum(np.diff(P, axis=1), 0).sum(axis=0)
    tflux = tt[1:]
    hf = hp(mono, 1000, 4)
    lf = lp(mono, 300, 4)
    env_hf = np.sqrt(np.convolve(hf ** 2, np.ones(ns(0.0005)) / ns(0.0005), mode='same'))
    env_lf = np.sqrt(np.convolve(lf ** 2, np.ones(ns(0.004)), mode='full')[:len(lf)] / ns(0.004))

    def crossing(env, t, db_over):
        pre = np.median(env[ns(t - 0.04):ns(t - 0.004)]) + 1e-7
        post = env[ns(t - 0.02):ns(t + 0.03)]
        thr = max(pre * undb(db_over), 0.2 * post.max())
        return (ns(t - 0.02) + np.argmax(post > thr)) / SR

    def jump(sig, t):
        a = np.mean(sig[ns(t):ns(t + 0.02)] ** 2) + 1e-20
        b = np.mean(sig[ns(t - 0.02):ns(t - 0.001)] ** 2) + 1e-20
        return 10 * np.log10(a / b)

    def check(t):
        sel = (tflux > t - 0.03) & (tflux < t + 0.03)
        tf = tflux[sel][np.argmax(flux[sel])]
        return tf, crossing(env_hf, t, 10), jump(hf, t), crossing(env_lf, t, 6), jump(lf, t)

    targets = [(T_DRIP_HOOK, 'drip (hook)')] + [(t, k) for t, k, _ in HITS] + \
              [(A0, 'drop impact'), (A0 + BEAT, 'kick dropA'), (LIFT, 'lift kick'), (GOLD, 'gold'),
               (B0, 'dropB kick'), (B1 - BEAT, 'final accent')]
    print('\nonsets: target | flux-peak dt | HF(>1k) onset dt, 20 ms jump | LF(<300) onset dt, jump')
    for t, k in sorted(targets):
        tf, th, jh, tl, jl = check(t)
        print(f'  {t:7.3f} {k:<14s} flux {1000 * (tf - t):+6.1f} ms | HF {1000 * (th - t):+6.1f} ms {jh:+6.1f} dB'
              f' | LF {1000 * (tl - t):+6.1f} ms {jl:+6.1f} dB')

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
    ax[0].set_title('music.wav spectrogram (log freq), lime ticks = timeline hits')
    tw = np.arange(0, N, 480) / SR
    rms = np.sqrt(np.convolve(mono ** 2, np.ones(480) / 480, mode='same'))[::480]
    ax[1].plot(tw, 20 * np.log10(rms + 1e-9), lw=0.6, color='k')
    ax[1].set_ylim(-90, 0)
    ax[1].set_ylabel('RMS dBFS (10 ms)')
    ax[1].set_xlabel('s')
    ax[1].set_xlim(0, DUR)
    ax[1].set_xticks(np.arange(0, DUR + 0.1, 2))
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    png = os.path.join(BUILD_DIR, 'music_spectrogram.png')
    fig.savefig(png, dpi=80)
    print('\nspectrogram:', png)


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    t0 = time.time()
    y, stems, info = render()
    out = os.path.join(BUILD_DIR, 'music.wav')
    write_wav24(out, y)
    write_events(os.path.join(BUILD_DIR, 'music_events.txt'), info)
    print(f'wrote {out}  ({time.time() - t0:.1f} s total)')
    if '--verify' in sys.argv:
        verify(out, stems, info)


if __name__ == '__main__':
    main()
