"""
Original score + sound design for the 누수 선임권 film (76 s, 120 BPM, G major).

Water drops open the piece as pitched "plips" that become the groove's
downbeat at 10 s. Cue times match leak/scenes.js (every cue on a 0.5 s beat).
The sonic logo is the fire film's Fadd9 signature, transposed to Gadd9.

    python3 audio/leak_score.py build/leak-audio.wav
"""
import sys
import numpy as np
import score_lib as S
from score_lib import Part, n

LEN = 78.0
norm_active = S.norm_active

# bar = 2 s at 120 BPM
PROG = {  # start: (pad voicing, bass root, arp pattern)
    'Em': (['E3', 'G3', 'B3', 'D4'], 'E2', ['E4', 'B4', 'G4', 'B4', 'D5', 'B4', 'G4', 'B4']),
    'C': (['E3', 'G3', 'C4', 'D4'], 'C2', ['C4', 'G4', 'E4', 'G4', 'D5', 'G4', 'E4', 'G4']),
    'G': (['D3', 'G3', 'B3', 'D4'], 'G1', ['G3', 'D4', 'B4', 'D4', 'A4', 'D4', 'B4', 'D4']),
    'D': (['D3', 'F#3', 'A3', 'E4'], 'D2', ['D4', 'A4', 'F#4', 'A4', 'E5', 'A4', 'F#4', 'A4']),
    'D/F#': (['D3', 'F#3', 'A3', 'D4'], 'F#1', ['F#3', 'D4', 'A4', 'D4', 'F#4', 'D4', 'A4', 'D4']),
    'G/B': (['D3', 'G3', 'B3', 'D4'], 'B1', ['B3', 'D4', 'G4', 'D4', 'B4', 'D4', 'G4', 'D4']),
}
SONG = [(10, 'Em'), (12, 'C'), (14, 'G'), (16, 'D'), (18, 'Em'), (20, 'C'), (22, 'D'),
        (24, 'C'), (26, 'D'), (28, 'Em'), (30, 'G/B'), (32, 'C'), (34, 'D'),
        (36, 'Em'), (38, 'C'), (40, 'G'), (42, 'D'), (44, 'Em'), (46, 'C'), (48, 'G'), (50, 'D'),
        (52, 'C'), (54, 'G'), (56, 'D/F#'), (58, 'Em'), (60, 'C'), (62, 'D')]


def compose():
    P = {}
    piano = P['piano'] = Part('piano', 0, pan=58, seed=21)
    pad = P['pad'] = Part('pad', 49, pan=64, seed=22, humanize=0.0)
    warm = P['warm'] = Part('warm', 89, pan=64, seed=23, humanize=0.0)
    pizz = P['pizz'] = Part('pizz', 45, pan=72, seed=24, humanize=0.004)
    mar = P['mar'] = Part('mar', 12, pan=46, seed=25, humanize=0.0)
    kal = P['kal'] = Part('kal', 108, pan=70, seed=26, humanize=0.0)
    cel = P['cel'] = Part('cel', 8, pan=54, seed=27, humanize=0.0)
    glock = P['glock'] = Part('glock', 9, pan=74, seed=28, humanize=0.0)
    harp = P['harp'] = Part('harp', 46, pan=40, seed=29, humanize=0.0)
    bass = P['bass'] = Part('bass', 43, pan=70, seed=30, humanize=0.0)

    # ---------------- intro 0–10: pad + drop-echo notes
    warm.cc(0, 11, 0)
    warm.chord(0.5, ['E3', 'B3', 'D4', 'F#4'], 9.6, 50)
    warm.ramp(0.3, 3.5, 0, 90).ramp(8.5, 9.95, 90, 70)
    for t, p_ in [(2.5, 'B5'), (4.5, 'E6'), (6.0, 'G5'), (7.0, 'D6'), (8.0, 'B5'), (8.5, 'A5'), (9.0, 'G5'), (9.5, 'F#5')]:
        kal.note(t, p_, 1.2, 58, exact=True)
    piano.note(6.0, 'E3', 3.8, 34).note(6.0, 'B3', 3.8, 30)
    piano.pedal(5.95, 9.95)

    # ---------------- groove sections
    pad.cc(0, 11, 0)
    for i, (t0, c) in enumerate(SONG):
        voicing, root, arp = PROG[c]
        dur = (SONG[i + 1][0] if i + 1 < len(SONG) else 64) - t0
        big = t0 >= 24
        piano.seq(t0, arp, 0.25, 0.24, 36 + (6 if big else 0), accents=[8, 0, 3, 0, 5, 0, 3, 0])
        if dur > 2.01:
            piano.seq(t0 + 2, arp, 0.25, 0.24, 36 + (6 if big else 0), accents=[8, 0, 3, 0, 5, 0, 3, 0])
        piano.pedal(t0 + 0.01, t0 + dur - 0.03)
        pad.chord(t0, voicing, dur + 0.03, 48)
        for q in range(int(dur / 0.5)):
            if q % 2 == 0 or t0 >= 36:
                pizz.note(t0 + q * 0.5, n(root) + 12, 0.3, 64 + (10 if q == 0 else 0))
        if t0 >= 24:
            bass.note(t0, root, dur + 0.03, 52)
    pad.ramp(10.0, 12.0, 0, 70).ramp(23.0, 24.2, 70, 96).ramp(35.5, 36.2, 96, 84).ramp(52.0, 54.0, 84, 104).ramp(62.0, 63.95, 104, 60)
    bass.cc(23.9, 11, 88)

    # L2 labels and question
    for t, p_ in [(16.5, 'F#5'), (17.0, 'A5'), (17.5, 'D6'), (18.0, 'E6')]:
        mar.note(t, p_, 0.6, 70, exact=True)
    glock.note(19.5, 'B5', 1.5, 46, exact=True)
    # L3 lift: the right to appoint
    for i, p_ in enumerate(['D3', 'F#3', 'A3', 'D4', 'F#4', 'A4', 'D5']):
        harp.note(23.4 + i * 0.08, p_, 1.2, 60 + i * 3, exact=True)
    cel.note(24.0, 'E6', 1.8, 60, exact=True).note(24.0, 'B5', 1.8, 52, exact=True)
    glock.note(28.0, 'E6', 1.5, 44, exact=True)
    cel.note(29.5, 'G6', 1.5, 54, exact=True)
    cel.note(33.0, 'D6', 1.5, 56, exact=True).note(33.5, 'E6', 1.5, 50, exact=True)
    # L4 timing: zone reveals
    for i, p_ in enumerate(['G4', 'B4', 'D5', 'G5']):
        mar.note(40.0 + i * 0.125, p_, 0.5, 64 + i * 4, exact=True)
    for i, p_ in enumerate(['A4', 'D5']):
        mar.note(43.5 + i * 0.25, p_, 0.5, 66, exact=True)
    piano.note(47.0, 'C2', 1.8, 60, exact=True).note(47.0, 'C3', 1.8, 52, exact=True)
    mar.note(47.0, 'E5', 0.8, 60, exact=True).note(47.25, 'C5', 0.8, 56, exact=True)
    for i, p_ in enumerate(['D4', 'F#4', 'A4', 'D5', 'F#5']):
        harp.note(50.0 + i * 0.07, p_, 1.8, 62 + i * 3, exact=True)
    # L5 cards
    for t, p_ in [(55.0, 'B5'), (56.0, 'D6'), (57.0, 'A6')]:
        cel.note(t, p_, 1.4, 58, exact=True)
        mar.note(t, n(p_) - 12, 0.6, 58, exact=True)
    glock.note(60.0, 'D6', 1.6, 44, exact=True)

    # ---------------- L6: breakdown -> sonic logo (Gadd9) -> outro
    for t0, ch, root in [(64, ['E3', 'G3', 'B3', 'D4'], 'E2'), (66, ['C3', 'G3', 'C4', 'D4'], 'C2')]:
        pad.chord(t0, ch, 2.03, 44)
        bass.note(t0, root, 2.03, 46)
    for t, p_, d, v in [(64.3, 'B4', 0.7, 44), (64.9, 'E5', 1.1, 48), (66.0, 'D5', 0.5, 44), (66.5, 'C5', 0.5, 42), (67.0, 'B4', 1.0, 44), (68.0, 'A4', 0.5, 42)]:
        piano.note(t, p_, d, v)
    piano.pedal(64.2, 65.95).pedal(66.0, 68.45)
    pad.ramp(64.0, 66.0, 60, 76).ramp(66.0, 68.45, 76, 100)
    piano.chord(68.5, ['G1', 'G2'], 4.0, 70, exact=True)
    piano.chord(68.5, ['D3', 'G3', 'B3', 'D4', 'A4', 'B4'], 4.0, 60, strum=0.012, exact=True)
    piano.pedal(68.48, 73.0)
    pad.cc(68.45, 11, 98)
    pad.chord(68.5, ['G2', 'D3', 'G3', 'B3', 'D4', 'G4', 'B4'], 4.2, 56)
    pad.ramp(69.5, 73.0, 98, 76)
    bass.cc(68.45, 11, 100)
    bass.note(68.5, 'G1', 4.2, 64)
    for i, p_ in enumerate(['D6', 'G6', 'A6', 'B6', 'D7']):
        cel.note(68.5 + i * 0.06, p_, 2.5, 60, exact=True)
    glock.note(68.5, 'D7', 2.0, 44, exact=True)
    for t0, ch, root, d in [(72.5, ['C3', 'E3', 'G3', 'C4'], 'C2', 1.5), (74.0, ['B2', 'D3', 'G3', 'B3'], 'G1', 2.5)]:
        pad.chord(t0, ch, d, 42)
        bass.note(t0, root, d, 42)
    pad.ramp(74.0, 75.9, 80, 0)
    bass.ramp(74.0, 75.9, 100, 0)
    for t, p_, d, v in [(72.5, 'E5', 1.0, 38), (73.5, 'D5', 1.0, 36), (74.5, 'B4', 1.5, 32)]:
        piano.note(t, p_, d, v)
    piano.pedal(73.05, 76.5)
    return P


LEVELS = {
    'piano': (-21.5, 0.32), 'pad': (-25.0, 0.40), 'warm': (-27.0, 0.40), 'pizz': (-26.0, 0.30), 'mar': (-26.5, 0.38),
    'kal': (-25.5, 0.45), 'cel': (-28.0, 0.52), 'glock': (-31.0, 0.52), 'harp': (-26.5, 0.45), 'bass': (-27.0, 0.26),
}
RIDE = [(0, -1), (9.9, -1), (10.1, 0), (63.8, 0), (64.2, -1), (78, -1)]


def ride(x):
    t = np.arange(len(x)) / S.SR
    ts, gs = zip(*RIDE)
    return (x * S.db(np.interp(t, ts, gs))[:, None]).astype(np.float32)


def plip(freq, level=0.5, seed=0):
    """Water-drop 'plip': fast upward pitch glide into a decaying sine, plus a tiny click."""
    N = int(0.6 * S.SR)
    t = np.arange(N) / S.SR
    f = freq * (0.55 + 0.45 * (1 - np.exp(-t * 90)))
    x = np.sin(2 * np.pi * np.cumsum(f) / S.SR) * np.exp(-t * 11) * np.clip(t / 0.0015, 0, 1)
    x += S.filt(S.noise(N, 'white', seed, 1)[:, 0], 'bandpass', [2000, 7000]) * np.exp(-t * 400) * 0.25
    x *= level
    return np.stack([x, x], 1).astype(np.float32)


def snap(seed=0):
    N = int(0.12 * S.SR)
    t = np.arange(N) / S.SR
    x = S.filt(S.noise(N, 'white', seed, 1)[:, 0], 'bandpass', [1400, 4200]) * np.exp(-t * 38)
    x += np.sin(2 * np.pi * 220 * t) * np.exp(-t * 60) * 0.3
    return np.stack([x, x], 1).astype(np.float32)


def hat(seed=0):
    N = int(0.05 * S.SR)
    t = np.arange(N) / S.SR
    x = S.filt(S.noise(N, 'white', seed, 1)[:, 0], 'highpass', 7500) * np.exp(-t * 110)
    return np.stack([x, x], 1).astype(np.float32)


def sound_design(mix):
    drops = [(2.5, 'B5'), (4.5, 'E6'), (6.0, 'G5'), (7.0, 'D6'), (8.0, 'B5'), (8.5, 'A5'), (9.0, 'G5'), (9.5, 'F#5')]
    for i, (t, p_) in enumerate(drops):
        mix.add(norm_active(plip(S.hz(p_), seed=100 + i), -29.0), t, send=0.5)
    mix.add(norm_active(S.reverse_cymbal(1.5, seed=101), -31.0), 8.5, send=0.4)
    mix.add(norm_active(S.boom(3.0, 70, 40, seed=102, click=0.05), -31.0), 10.0, send=0.3)
    # the circle wipe and scene transitions
    mix.add(norm_active(S.whoosh(1.0, 400, 3500, peak=0.5, seed=103), -34.0), 9.6, send=0.35)
    mix.add(norm_active(S.whoosh(1.0, 300, 2500, peak=0.55, seed=104), -35.0), 22.5, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(1.0, seed=105), -31.0), 23.0, send=0.4)
    mix.add(norm_active(S.whoosh(1.0, 500, 4500, peak=0.5, seed=106), -34.0), 35.5, send=0.35)
    mix.add(norm_active(S.whoosh(1.0, 300, 2500, peak=0.55, seed=107), -35.0), 52.3, send=0.35)
    mix.add(norm_active(S.whoosh(1.0, 300, 2000, peak=0.55, seed=108), -35.0), 63.3, send=0.35)
    # water trickle in the section drawing
    mix.add(norm_active(plip(S.hz('E6'), seed=109), -33.0), 15.6, send=0.5)
    mix.add(norm_active(plip(S.hz('B5'), seed=110), -34.0), 16.1, send=0.5)
    # groove percussion: soft kick on 1 & 3, snap on 2 & 4, shaker/hat on eighths
    kick = S.thud(0.8, 58, seed=111)
    for b in range(int((63.5 - 10.0) / 0.5)):
        t = 10.0 + b * 0.5
        beat = b % 4
        if beat in (0, 2):
            mix.add(norm_active(kick, -33.0), t, send=0.08)
        if beat in (1, 3) and t >= 18.0:
            mix.add(norm_active(snap(seed=200 + b), -37.0), t, send=0.25)
        mix.add(norm_active(hat(seed=300 + b), -41.0 if t < 36 else -39.5), t + 0.25, send=0.1)
        if 36.0 <= t < 52.0:
            mix.add(norm_active(hat(seed=500 + b), -45.0), t + 0.125, send=0.1)
            mix.add(norm_active(hat(seed=600 + b), -45.0), t + 0.375, send=0.1)
    mix.add(norm_active(S.reverse_cymbal(1.0, seed=112), -32.0), 49.0, send=0.4)
    mix.add(norm_active(S.riser(2.2, seed=113, f0=250, f1=7000), -32.0), 66.3, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(1.8, seed=114), -30.0), 66.7, send=0.45)
    mix.add(norm_active(S.boom(4.5, 62, 32, seed=115, click=0.1), -28.0), 68.5, send=0.4)


def build(out):
    parts = compose()
    mix = S.Mix(LEN)
    for name, part in parts.items():
        x = part.render(LEN)
        if np.abs(x).max() < 1e-5:
            print('WARNING silent stem', name)
            continue
        tgt, send = LEVELS[name]
        x = norm_active(x, tgt)
        if name == 'piano':
            x = S.filt(x, 'lowpass', 7000, 2)  # softer, felt-like top end
        if name in ('bass', 'pizz'):
            x = S.filt(x, 'highpass', 35, 2)
        x = ride(x)
        mix.add(x, 0.0, send=send)
        print(f'{name:6s} peak {20 * np.log10(np.abs(x).max() + 1e-9):6.1f} dBFS')
    sound_design(mix)
    irs = {'hall': S.make_ir(2.6, pre=0.025, seed=9)}
    y = mix.render(irs, {'hall': -3.5})
    y = S.master(y, target_lufs=-15.0, ceiling_db=-1.0, fade_out=(74.8, 76.0))
    S.write(out, y)
    print('LUFS', round(S.loudness(y), 2), 'peak', round(20 * np.log10(np.abs(y).max()), 2))


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'build/leak-audio.wav')
