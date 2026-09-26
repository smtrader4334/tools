"""
Original score + sound design for the company film (122 s, 120 BPM, D major).

The piece opens in B minor over the four accident icons, brightens into
D major when "손해사정" is defined at 12 s, builds through the practice areas,
drops to a breakdown for the region map and lands on the brand's add9 sonic
logo (Dadd9 here; the fire film uses Fadd9, the leak film Gadd9) when the logo
draws at 110 s. Cue times match company/scenes.js (every cue on a 0.5 s beat).

    python3 audio/company_score.py build/company-audio.wav
"""
import sys
import numpy as np
import score_lib as S
from score_lib import Part, n

LEN = 124.0
norm_active = S.norm_active

# bar = 2 s at 120 BPM
PROG = {  # name: (pad voicing, bass root, arp pattern)
    'D': (['D3', 'F#3', 'A3', 'E4'], 'D2', ['D4', 'A4', 'F#4', 'A4', 'E5', 'A4', 'F#4', 'A4']),
    'D/F#': (['D3', 'F#3', 'A3', 'D4'], 'F#1', ['F#3', 'D4', 'A3', 'D4', 'F#4', 'D4', 'A3', 'D4']),
    'A': (['C#3', 'E3', 'A3', 'B3'], 'A1', ['A3', 'E4', 'C#4', 'E4', 'B4', 'E4', 'C#4', 'E4']),
    'Asus': (['D3', 'E3', 'A3', 'B3'], 'A1', ['A3', 'E4', 'D4', 'E4', 'B4', 'E4', 'D4', 'E4']),
    'Bm': (['D3', 'F#3', 'B3', 'C#4'], 'B1', ['B3', 'F#4', 'D4', 'F#4', 'C#5', 'F#4', 'D4', 'F#4']),
    'G': (['D3', 'G3', 'B3', 'F#4'], 'G1', ['G3', 'D4', 'B3', 'D4', 'A4', 'D4', 'B3', 'D4']),
    'Em': (['E3', 'G3', 'B3', 'D4'], 'E2', ['E4', 'B4', 'G4', 'B4', 'D5', 'B4', 'G4', 'B4']),
    'F#m': (['C#3', 'F#3', 'A3', 'E4'], 'F#1', ['F#3', 'C#4', 'A3', 'C#4', 'E4', 'C#4', 'A3', 'C#4']),
}
SONG = [
    # C2 definition (light)
    (12, 'G'), (14, 'D'), (16, 'A'), (18, 'Bm'), (20, 'G'), (22, 'D'), (24, 'Asus'),
    # C3 who adjusts
    (26, 'Em'), (28, 'G'), (30, 'D'), (32, 'A'), (34, 'Em'), (36, 'Asus'),
    # C4 practice areas (full)
    (38, 'D'), (40, 'A'), (42, 'Bm'), (44, 'G'), (46, 'D'), (48, 'A'), (50, 'Bm'), (52, 'G'),
    (54, 'Em'), (56, 'D/F#'), (58, 'G'), (60, 'Asus'),
    # C5 standard (medium)
    (62, 'Bm'), (64, 'G'), (66, 'D'), (68, 'A'), (70, 'Bm'), (72, 'G'), (74, 'Em'), (76, 'A'), (78, 'Asus'),
    # C6 people (full)
    (80, 'G'), (82, 'A'), (84, 'F#m'), (86, 'Bm'), (88, 'G'), (90, 'A'), (92, 'D'), (94, 'D/F#'),
    # C7 region (breakdown)
    (96, 'Bm'), (98, 'G'), (100, 'Em'), (102, 'G'), (104, 'Asus'),
    # C8 brand line
    (106, 'G'), (108, 'Asus'),
]
END_OF_SONG = 110.0
FULL = [(38, 62), (80, 96)]
MEDIUM = [(62, 80)]
BREAK = [(96, 110)]


def within(t, spans):
    return any(a <= t < b for a, b in spans)


def compose():
    P = {}
    piano = P['piano'] = Part('piano', 0, pan=58, seed=41)
    pad = P['pad'] = Part('pad', 49, pan=64, seed=42, humanize=0.0)
    warm = P['warm'] = Part('warm', 89, pan=64, seed=43, humanize=0.0)
    pizz = P['pizz'] = Part('pizz', 45, pan=72, seed=44, humanize=0.004)
    mar = P['mar'] = Part('mar', 12, pan=46, seed=45, humanize=0.0)
    cel = P['cel'] = Part('cel', 8, pan=54, seed=46, humanize=0.0)
    glock = P['glock'] = Part('glock', 9, pan=74, seed=47, humanize=0.0)
    harp = P['harp'] = Part('harp', 46, pan=40, seed=48, humanize=0.0)
    bass = P['bass'] = Part('bass', 43, pan=70, seed=49, humanize=0.0)
    cello = P['cello'] = Part('cello', 42, pan=52, seed=50, humanize=0.0)

    # ---------------- C1 intro 0–12: B minor, four icons, the question
    warm.cc(0, 11, 0)
    warm.chord(0.5, ['B2', 'F#3', 'C#4', 'D4'], 11.4, 50)
    warm.ramp(0.3, 4.0, 0, 88).ramp(10.5, 11.95, 88, 66)
    piano.note(1.0, 'B2', 5.5, 40).note(1.0, 'F#3', 5.5, 34)
    piano.pedal(0.95, 6.9)
    for i, p_ in enumerate(['F#5', 'A5', 'B5', 'D6']):  # 화재 · 누수 · 배상책임 · 자연재해
        cel.note(3.0 + i * 0.5, p_, 1.6, 58, exact=True)
        mar.note(3.0 + i * 0.5, n(p_) - 12, 0.6, 54, exact=True)
    piano.note(7.5, 'G2', 4.4, 42).note(7.5, 'D3', 4.4, 36).note(7.5, 'B3', 4.4, 32)
    piano.note(9.5, 'A4', 1.0, 34).note(10.5, 'F#4', 1.4, 32)
    piano.pedal(7.45, 11.95)
    glock.note(7.5, 'F#6', 1.8, 42, exact=True)
    cello.cc(0, 11, 0)
    cello.note(7.5, 'G2', 4.4, 56)
    cello.ramp(7.5, 9.5, 0, 80).ramp(10.5, 11.95, 80, 40)

    # ---------------- groove sections 12–110
    pad.cc(0, 11, 0)
    for i, (t0, c) in enumerate(SONG):
        voicing, root, arp = PROG[c]
        dur = (SONG[i + 1][0] if i + 1 < len(SONG) else END_OF_SONG) - t0
        full, med, brk = within(t0, FULL), within(t0, MEDIUM), within(t0, BREAK)
        vel = 34 + (8 if full else 4 if med else 0)
        if brk:
            # breakdown: half-time arpeggio, no pizzicato
            piano.seq(t0, arp[::2], 0.5, 0.48, vel - 2, accents=[6, 0, 3, 0])
        else:
            piano.seq(t0, arp, 0.25, 0.24, vel, accents=[8, 0, 3, 0, 5, 0, 3, 0])
        piano.pedal(t0 + 0.01, t0 + dur - 0.03)
        pad.chord(t0, voicing, dur + 0.03, 48)
        if not brk and t0 < 106:
            for q in range(int(dur / 0.5)):
                if q % 2 == 0 or full:
                    pizz.note(t0 + q * 0.5, n(root) + 12, 0.3, 62 + (10 if q == 0 else 0))
        if full or med or t0 >= 106:
            bass.note(t0, root, dur + 0.03, 50 if med else 54)
        if full:
            cello.note(t0, n(root) + 12, dur + 0.03, 50)
    pad.ramp(12.0, 14.0, 0, 64).ramp(25.0, 26.2, 64, 84).ramp(37.0, 38.2, 84, 100)
    pad.ramp(61.0, 62.2, 100, 86).ramp(79.0, 80.2, 86, 102).ramp(95.0, 96.4, 102, 70)
    pad.ramp(106.0, 109.9, 70, 104)
    bass.cc(37.9, 11, 88)
    cello.ramp(37.5, 38.5, 40, 70).ramp(61.5, 62.0, 70, 0).ramp(79.5, 80.5, 0, 72).ramp(95.5, 96.0, 72, 0)

    # C2 definition + three steps + conclusion
    glock.note(12.8, 'D6', 1.6, 44, exact=True)
    for t, p_ in [(16.0, 'A5'), (17.0, 'B5'), (18.0, 'C#6')]:
        mar.note(t, p_, 0.6, 66, exact=True)
        cel.note(t, n(p_) + 12, 1.2, 50, exact=True)
    for i, p_ in enumerate(['D4', 'F#4', 'A4', 'D5', 'F#5', 'A5']):
        harp.note(21.0 + i * 0.07, p_, 1.6, 58 + i * 3, exact=True)
    # C3 the two paths
    cel.note(28.5, 'B5', 1.4, 48, exact=True)
    for i, p_ in enumerate(['D5', 'F#5', 'A5', 'D6']):
        cel.note(30.0 + i * 0.08, p_, 2.0, 56, exact=True)
    for i, p_ in enumerate(['E4', 'G4', 'B4', 'E5', 'G5']):
        harp.note(34.0 + i * 0.07, p_, 1.8, 60 + i * 3, exact=True)
    # C4 four cards
    for t0, notes in [(42.0, ['B4', 'D5', 'F#5']), (45.0, ['G4', 'B4', 'D5']), (48.0, ['A4', 'C#5', 'E5']), (51.0, ['B4', 'D5', 'F#5'])]:
        for i, p_ in enumerate(notes):
            mar.note(t0 + i * 0.125, p_, 0.5, 62 + i * 4, exact=True)
        cel.note(t0 + 0.25, n(notes[-1]) + 12, 1.2, 46, exact=True)
    glock.note(54.0, 'A6', 1.8, 42, exact=True)
    # C5 three standards
    for t, p_ in [(66.0, 'F#5'), (68.0, 'A5'), (70.0, 'D6')]:
        cel.note(t, p_, 1.6, 56, exact=True)
        mar.note(t, n(p_) - 12, 0.6, 56, exact=True)
    # C6 two people
    for t, notes in [(83.0, ['C#5', 'E5', 'A5']), (85.0, ['C#5', 'F#5', 'A5'])]:
        for i, p_ in enumerate(notes):
            harp.note(t + i * 0.08, p_, 1.4, 58 + i * 4, exact=True)
    # C7 map: headquarters pulse and the four cities
    glock.note(98.0, 'D6', 2.0, 46, exact=True)
    for i, p_ in enumerate(['F#5', 'A5', 'B5', 'D6']):
        mar.note(99.5 + i * 0.5, p_, 0.6, 58, exact=True)

    # ---------------- C8: brand line -> sonic logo (Dadd9) -> outro
    for t, p_, d, v in [(106.5, 'F#4', 0.9, 44), (107.5, 'A4', 0.9, 44), (108.0, 'B4', 1.0, 46), (109.0, 'E5', 0.9, 44)]:
        piano.note(t, p_, d, v)
    piano.chord(110.0, ['D1', 'D2'], 4.5, 72, exact=True)
    piano.chord(110.0, ['A2', 'D3', 'F#3', 'A3', 'E4', 'F#4'], 4.5, 62, strum=0.012, exact=True)
    piano.pedal(109.98, 115.0)
    pad.cc(109.95, 11, 100)
    pad.chord(110.0, ['D2', 'A2', 'D3', 'F#3', 'A3', 'E4', 'F#4'], 5.0, 56)
    pad.ramp(111.0, 115.0, 100, 78)
    bass.cc(109.95, 11, 100)
    bass.note(110.0, 'D1', 5.0, 66)
    cello.note(110.0, 'D2', 5.0, 58)
    cello.ramp(109.95, 110.3, 0, 76).ramp(113.0, 115.0, 76, 30)
    for i, p_ in enumerate(['A5', 'D6', 'E6', 'F#6', 'A6']):
        cel.note(110.0 + i * 0.06, p_, 2.6, 60, exact=True)
    glock.note(110.0, 'A6', 2.0, 44, exact=True)
    for t0, ch, root, d in [(115.0, ['D3', 'G3', 'B3', 'D4'], 'G1', 2.0), (117.0, ['D3', 'F#3', 'A3', 'E4'], 'D2', 5.0)]:
        pad.chord(t0, ch, d, 44)
        bass.note(t0, root, d, 44)
    pad.ramp(118.5, 121.9, 80, 0)
    bass.ramp(118.5, 121.9, 100, 0)
    for t, p_, d, v in [(115.0, 'B4', 1.0, 38), (116.0, 'A4', 1.0, 36), (117.0, 'F#4', 2.0, 34), (119.0, 'E4', 2.5, 30)]:
        piano.note(t, p_, d, v)
    piano.pedal(115.05, 122.5)
    return P


LEVELS = {
    'piano': (-21.5, 0.32), 'pad': (-25.0, 0.40), 'warm': (-27.0, 0.40), 'pizz': (-26.5, 0.30), 'mar': (-26.5, 0.38),
    'cel': (-28.0, 0.52), 'glock': (-31.0, 0.52), 'harp': (-26.5, 0.45), 'bass': (-27.0, 0.26), 'cello': (-29.0, 0.35),
}
RIDE = [(0, -1), (11.9, -1), (12.1, 0), (109.8, 0), (110.1, 0.5), (124, 0.5)]


def ride(x):
    t = np.arange(len(x)) / S.SR
    ts, gs = zip(*RIDE)
    return (x * S.db(np.interp(t, ts, gs))[:, None]).astype(np.float32)


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
    mix.add(norm_active(S.boom(4.0, 60, 34, seed=201, click=0.05), -31.0), 1.0, send=0.35)
    for i in range(4):  # icon strokes
        mix.add(norm_active(S.tick(0.25, 2400 + i * 300, seed=202 + i), -40.0), 3.0 + i * 0.5, send=0.3)
    # scene transitions
    for i, t in enumerate([11.3, 25.3, 37.3, 61.3, 79.3, 95.3, 105.3]):
        mix.add(norm_active(S.whoosh(1.0, 350, 3200, peak=0.55, seed=210 + i), -35.0), t, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(1.2, seed=220), -32.0), 10.8, send=0.4)
    mix.add(norm_active(S.reverse_cymbal(1.2, seed=221), -32.0), 36.8, send=0.4)
    mix.add(norm_active(S.boom(3.0, 70, 40, seed=222, click=0.05), -32.0), 38.0, send=0.3)
    mix.add(norm_active(S.reverse_cymbal(1.2, seed=223), -32.0), 78.8, send=0.4)
    # groove percussion: soft kick on 1 & 3, snap on 2 & 4, hats on the off-beats
    kick = S.thud(0.8, 58, seed=230)
    for b in range(int((96.0 - 26.0) / 0.5)):
        t = 26.0 + b * 0.5
        beat = b % 4
        full, med = within(t, FULL), within(t, MEDIUM)
        if (full or med) and beat in (0, 2):
            mix.add(norm_active(kick, -33.0 if full else -35.0), t, send=0.08)
        if full and beat in (1, 3):
            mix.add(norm_active(snap(seed=300 + b), -37.0), t, send=0.25)
        mix.add(norm_active(hat(seed=400 + b), -41.0 if not full else -39.5), t + 0.25, send=0.1)
        if 42.0 <= t < 60.0:
            mix.add(norm_active(hat(seed=500 + b), -45.0), t + 0.125, send=0.1)
            mix.add(norm_active(hat(seed=600 + b), -45.0), t + 0.375, send=0.1)
    # the logo
    mix.add(norm_active(S.riser(2.2, seed=240, f0=250, f1=7000), -32.0), 107.8, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(1.6, seed=241), -30.0), 108.4, send=0.45)
    mix.add(norm_active(S.boom(4.5, 62, 32, seed=242, click=0.1), -28.0), 110.0, send=0.4)


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
            x = S.filt(x, 'lowpass', 7000, 2)
        if name in ('bass', 'pizz', 'cello'):
            x = S.filt(x, 'highpass', 35, 2)
        x = ride(x)
        mix.add(x, 0.0, send=send)
        print(f'{name:6s} peak {20 * np.log10(np.abs(x).max() + 1e-9):6.1f} dBFS')
    sound_design(mix)
    irs = {'hall': S.make_ir(2.6, pre=0.025, seed=19)}
    y = mix.render(irs, {'hall': -3.5})
    y = S.master(y, target_lufs=-15.0, ceiling_db=-1.0, fade_out=(120.8, 122.0))
    S.write(out, y)
    print('LUFS', round(S.loudness(y), 2), 'peak', round(20 * np.log10(np.abs(y).max()), 2))


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'build/company-audio.wav')
