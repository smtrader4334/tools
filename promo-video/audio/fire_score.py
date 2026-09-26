"""
Original score + sound design for the fire brand film (144 s, 60 BPM).

Harmonic arc: D minor (loss) -> F major (trust). Cue times match
fire/scenes.js; every musical hit lands on the 60 BPM beat/eighth grid.

    python3 audio/fire_score.py build/fire-audio.wav
"""
import sys
import numpy as np
import score_lib as S
from score_lib import Part, n

LEN = 146.0  # a little tail beyond the 144 s picture; trimmed at mux time


def compose():
    P = {}
    piano = P['piano'] = Part('piano', 0, pan=58, seed=1)
    pad = P['pad'] = Part('pad', 49, pan=64, seed=2, humanize=0.0)
    fast = P['fast'] = Part('fast', 48, pan=70, seed=3, humanize=0.004)
    mid = P['mid'] = Part('mid', 48, pan=48, seed=4, humanize=0.004)
    bass = P['bass'] = Part('bass', 43, pan=76, seed=5, humanize=0.0)
    cello = P['cello'] = Part('cello', 42, pan=80, seed=6)
    horn = P['horn'] = Part('horn', 60, pan=44, seed=7)
    harp = P['harp'] = Part('harp', 46, pan=40, seed=8, humanize=0.0)
    cel = P['cel'] = Part('cel', 8, pan=54, seed=9, humanize=0.0)
    glock = P['glock'] = Part('glock', 9, pan=74, seed=10, humanize=0.0)
    pizz = P['pizz'] = Part('pizz', 45, pan=60, seed=11, humanize=0.0)
    timp = P['timp'] = Part('timp', 47, pan=64, seed=12, humanize=0.0)
    trem = P['trem'] = Part('trem', 44, pan=64, seed=13, humanize=0.0)

    # ---------------- A  0–16  ashes (D minor)
    pad.cc(0, 11, 0)
    pad.chord(1.5, ['D3', 'A3', 'F4'], 6.55, 52)
    pad.ramp(1.5, 5.5, 0, 92).ramp(6.5, 8.0, 92, 76)
    pad.chord(8.0, ['Bb2', 'F3', 'D4', 'F4'], 4.05, 52)
    pad.ramp(8.0, 9.5, 76, 96)
    pad.chord(12.0, ['G2', 'D3', 'Bb3', 'D4'], 4.4, 50)
    pad.ramp(13.0, 16.2, 96, 0)
    bass.cc(0, 11, 0)
    bass.note(1.0, 'D2', 7.2, 48).note(8.0, 'Bb1', 4.2, 48).note(12.0, 'G1', 4.3, 46)
    bass.ramp(1.0, 5.0, 0, 90).ramp(13.0, 16.2, 90, 0)
    for t, p, v in [(1.9, 'D5', 44), (2.9, 'A4', 40), (3.9, 'F4', 38), (5.1, 'C5', 44), (6.1, 'A4', 40), (7.1, 'D4', 38),
                    (8.5, 'Bb4', 42), (9.5, 'F4', 38), (10.5, 'D4', 36)]:
        piano.note(t, p, 2.4, v)
    piano.note(1.9, 'D3', 5.0, 32).note(8.5, 'Bb2', 3.6, 30)
    piano.chord(12.3, ['G3', 'D4', 'A4'], 3.8, 32, strum=0.05)
    piano.pedal(1.8, 8.4).pedal(8.45, 12.2).pedal(12.25, 16.8)

    # ---------------- B  16–28  the notice (tension -> hit at 22.0)
    trem.cc(16.0, 11, 0)
    trem.chord(16.4, ['D5', 'A5'], 5.55, 40)
    trem.ramp(16.4, 21.9, 0, 88, curve=1.6)
    for p_ in ['D2', 'D1']:
        piano.note(22.0, p_, 3.2, 78, exact=True)
    piano.pedal(21.98, 26.5)
    timp.note(22.0, 'D2', 2.0, 96, exact=True)
    fast.note(22.0, 'D2', 0.55, 86, exact=True).note(22.0, 'D3', 0.55, 78, exact=True)
    bass.cc(21.9, 11, 100).note(22.0, 'D2', 0.9, 84, exact=True)
    pad.cc(22.2, 11, 0)
    pad.note(22.3, 'D6', 5.3, 34)
    pad.ramp(22.3, 24.5, 0, 58).ramp(25.5, 27.8, 58, 0)
    piano.note(24.0, 'A5', 3.0, 28, exact=True)

    # ---------------- C  28–44  what is loss adjustment (Dm Bb F C)
    arps = {28: ['D4', 'A4', 'F4', 'A4', 'D5', 'A4', 'F4', 'A4'],
            32: ['Bb3', 'F4', 'D4', 'F4', 'Bb4', 'F4', 'D4', 'F4'],
            36: ['A3', 'F4', 'C4', 'F4', 'A4', 'F4', 'C4', 'F4'],
            40: ['G3', 'E4', 'C4', 'E4', 'G4', 'E4', 'C4', 'E4']}
    for t0, pat in arps.items():
        piano.seq(t0, pat, 0.5, 0.48, 40, accents=[6, 0, 2, 0, 4, 0, 2, 0])
        piano.pedal(t0 + 0.02, t0 + 3.95)
    for t0, p_ in [(28, 'D3'), (32, 'Bb2'), (36, 'F2'), (40, 'C3')]:
        piano.note(t0, p_, 3.8, 42)
    for t, p_, d, v in [(38.0, 'A5', 1.0, 50), (39.0, 'G5', 0.5, 46), (39.5, 'F5', 0.5, 46), (40.0, 'E5', 2.0, 50), (42.0, 'G5', 1.8, 46)]:
        piano.note(t, p_, d, v)
    pad.cc(28.0, 11, 100)
    for t0, ch, d in [(28.2, ['D3', 'F3', 'A3'], 3.8), (32.0, ['Bb2', 'D3', 'F3'], 4.0), (36.0, ['A2', 'C3', 'F3'], 4.0), (40.0, ['G2', 'C3', 'E3'], 4.2)]:
        pad.chord(t0, ch, d, 48)
    cello.cc(36, 11, 80)
    cello.note(36.0, 'F2', 4.0, 46).note(40.0, 'C3', 4.2, 44)
    for t, p_ in [(32.5, 'A5'), (33.5, 'C6'), (34.5, 'D6')]:
        cel.note(t, p_, 1.5, 64, exact=True)
    glock.note(39.0, 'F6', 1.5, 52, exact=True)

    # ---------------- D  44–60  who adjusts? (tension -> balance at 55.5)
    fast.cc(44.0, 11, 70)
    osti = [(44.0, 48.0, 'D2', 'D3'), (48.0, 52.0, 'Bb1', 'Bb2'), (52.0, 54.0, 'G1', 'G2'), (54.0, 55.5, 'C2', 'C3')]
    for a, b, lo, hi in osti:
        t = a
        k = 0
        while t < b - 0.01:
            fast.note(t, lo if k % 2 == 0 else hi, 0.4, 58 + (10 if k % 2 == 0 else 0))
            t += 0.5
            k += 1
    fast.ramp(44.0, 55.4, 70, 112)
    pad.cc(44.0, 11, 70)
    pad.chord(44.0, ['D3', 'F3', 'A3'], 4.1, 44).chord(48.0, ['Bb2', 'D3', 'F3'], 4.1, 46)
    pad.chord(52.0, ['Bb2', 'D3', 'F3'], 2.1, 50).chord(54.0, ['Bb2', 'C3', 'F3'], 1.0, 54).chord(55.0, ['Bb2', 'C3', 'E3'], 0.55, 58)
    pad.ramp(44.0, 55.4, 70, 110)
    bass.cc(43.9, 11, 80)
    bass.note(44.0, 'D2', 4.1, 50).note(48.0, 'Bb1', 4.1, 52).note(52.0, 'G1', 2.1, 54).note(54.0, 'C2', 1.55, 58)
    timp.note(48.5, 'D2', 1.5, 84, exact=True)
    for i, p_ in enumerate(['F3', 'A3', 'C4', 'F4', 'A4', 'C5', 'F5']):
        harp.note(55.5 + i * 0.07, p_, 2.5, 62 + i * 3, exact=True)
    # resolution: F major
    pad.cc(55.45, 11, 90)
    pad.chord(55.5, ['F2', 'C3', 'F3', 'A3', 'C4'], 2.6, 70)
    pad.ramp(55.5, 57.0, 90, 118)
    pad.chord(58.0, ['E3', 'G3', 'C4'], 2.1, 56)
    bass.cc(55.45, 11, 100)
    bass.note(55.5, 'F1', 2.6, 70).note(58.0, 'E1', 2.1, 58)
    piano.chord(55.5, ['F2', 'C3'], 2.4, 58, exact=True)
    for i, p_ in enumerate(['F4', 'A4', 'C5', 'F5']):
        piano.note(55.5 + i * 0.5, p_, 1.6, 54 + i * 2)
    piano.note(58.0, 'E4', 1.8, 44).note(59.0, 'C5', 1.0, 42)
    piano.pedal(55.48, 57.95).pedal(58.0, 59.98)
    timp.note(55.5, 'F2', 2.0, 70, exact=True)

    # ---------------- E  60–80  why fire is different (drive, D minor)
    bars = [(60, 64, 'Dm'), (64, 68, 'Bb'), (68, 72, 'F'), (72, 76, 'C'), (76, 78, 'Gm'), (78, 80, 'C7')]
    lows = {'Dm': ('D2', 'D3'), 'Bb': ('Bb1', 'Bb2'), 'F': ('F2', 'F3'), 'C': ('C2', 'C3'), 'Gm': ('G2', 'G3'), 'C7': ('C2', 'C3')}
    figs = {'Dm': ['A4', 'F4', 'D4', 'F4'], 'Bb': ['F4', 'D4', 'Bb3', 'D4'], 'F': ['C5', 'A4', 'F4', 'A4'],
            'C': ['G4', 'E4', 'C4', 'E4'], 'Gm': ['D5', 'Bb4', 'G4', 'Bb4'], 'C7': ['Bb4', 'G4', 'E4', 'G4']}
    pads = {'Dm': ['D3', 'F3', 'A3', 'D4'], 'Bb': ['D3', 'F3', 'Bb3', 'D4'], 'F': ['C3', 'F3', 'A3', 'C4'],
            'C': ['C3', 'E3', 'G3', 'C4'], 'Gm': ['D3', 'G3', 'Bb3', 'D4'], 'C7': ['C3', 'E3', 'G3', 'Bb3']}
    roots = {'Dm': 'D2', 'Bb': 'Bb1', 'F': 'F1', 'C': 'C2', 'Gm': 'G1', 'C7': 'C2'}
    hi_arp = {'F': ['F5', 'A5', 'C6', 'A5'], 'C': ['E5', 'G5', 'C6', 'G5'], 'Gm': ['D5', 'G5', 'Bb5', 'G5'], 'C7': ['E5', 'G5', 'Bb5', 'G5']}
    fast.cc(59.9, 11, 84)
    mid.cc(63.9, 11, 70)
    pad.cc(59.9, 11, 72)
    bass.cc(59.9, 11, 84)
    for a, b, c in bars:
        lo, hi = lows[c]
        t, k = float(a), 0
        while t < b - 0.01:
            fast.note(t, lo if k % 2 == 0 else hi, 0.42, 54 + (12 if k % 2 == 0 else 0))
            t += 0.5
            k += 1
        if a >= 64:
            t, k = float(a), 0
            while t < b - 0.01:
                mid.note(t, figs[c][k % 4], 0.2, 40 + (10 if k % 4 == 0 else 0))
                t += 0.25
                k += 1
        if a >= 68:
            t, k = float(a), 0
            while t < b - 0.01:
                piano.note(t, hi_arp[c][k % 4], 0.22, 30 + (6 if k % 4 == 0 else 0))
                t += 0.25
                k += 1
        pad.chord(a, pads[c], b - a + 0.05, 50)
        bass.note(a, roots[c], b - a + 0.05, 56)
    fast.ramp(60, 79.9, 84, 120)
    mid.ramp(64, 79.9, 70, 112)
    pad.ramp(60, 79.9, 72, 116)
    cello.cc(59.9, 11, 60)
    for t, p_, d in [(60, 'D3', 4), (64, 'F3', 4), (68, 'A3', 4), (72, 'G3', 4), (76, 'Bb3', 4)]:
        cello.note(t, p_, d + 0.05, 64)
        cello.ramp(t, t + 1.5, 60, 100).ramp(t + 2.5, t + 3.95, 100, 78)
    for i, p_ in enumerate(['F5', 'D5', 'Bb5', 'F5', 'A5', 'C6', 'F5', 'A5']):
        pizz.note(66.0 + i * 0.5, p_, 0.4, 76, exact=True)
    timp.note(71.0, 'F2', 2.0, 104, exact=True)
    piano.chord(71.0, ['F1', 'F2'], 2.0, 84, exact=True)
    timp.note(75.0, 'C2', 1.8, 90, exact=True)
    piano.chord(75.0, ['C2', 'C3'], 1.8, 74, exact=True)
    for i in range(16):
        timp.note(78.0 + i * 0.125, 'C2', 0.12, 44 + i * 3, exact=True)

    # ---------------- F  80–96  the expert (F major, noble)
    fchords = [(80, 84, ['C3', 'F3', 'A3', 'C4'], 'F1'), (84, 88, ['E3', 'G3', 'C4', 'E4'], 'E1'), (88, 90, ['D3', 'F3', 'A3', 'D4'], 'D2'),
               (90, 92, ['D3', 'F3', 'Bb3', 'D4'], 'Bb1'), (92, 94, ['C3', 'F3', 'A3', 'C4'], 'C2'), (94, 95, ['C3', 'F3', 'G3', 'C4'], 'C2'),
               (95, 96, ['C3', 'E3', 'G3', 'Bb3'], 'C2')]
    pad.cc(79.95, 11, 96)
    bass.cc(79.95, 11, 96)
    for a, b, ch, r in fchords:
        pad.chord(a, ch, b - a + 0.05, 56)
        bass.note(a, r, b - a + 0.05, 60)
    pad.ramp(80, 81.5, 96, 110).ramp(93.5, 95.9, 104, 84)
    parp = {80: ['F3', 'C4', 'A4', 'C4'], 84: ['E3', 'C4', 'G4', 'C4'], 88: ['D3', 'A3', 'F4', 'A3'], 90: ['Bb2', 'F3', 'D4', 'F3'],
            92: ['C3', 'A3', 'F4', 'A3'], 94: ['C3', 'G3', 'F4', 'G3'], 95: ['C3', 'G3', 'E4', 'G3']}
    for t0, pat in parp.items():
        end = min([k for k in list(parp) + [96] if k > t0])
        t, k = float(t0), 0
        while t < end - 0.01:
            piano.note(t, pat[k % 4], 0.48, 38 + (6 if k % 4 == 0 else 0))
            t += 0.5
            k += 1
        piano.pedal(t0 + 0.02, end - 0.04)
    horn.cc(80, 11, 88)
    for t, p_, d in [(80.5, 'C4', 1.0), (81.5, 'F4', 1.0), (82.5, 'A4', 1.5), (84.0, 'G4', 2.0), (86.0, 'E4', 1.0), (87.0, 'C4', 1.0),
                     (88.0, 'D4', 1.0), (89.0, 'F4', 1.0), (90.0, 'F4', 1.0), (91.0, 'D4', 1.0), (92.0, 'C4', 1.5), (93.5, 'F4', 0.5), (94.0, 'G4', 2.0)]:
        horn.note(t, p_, d * 0.98, 64)
    horn.ramp(80.5, 82.5, 80, 104).ramp(93.8, 95.9, 104, 86)
    for t, p_ in [(85.0, 'G5'), (86.5, 'C6'), (88.0, 'A5'), (89.5, 'D6')]:
        cel.note(t, p_, 1.6, 62, exact=True)
    for i, p_ in enumerate(['C3', 'F3', 'A3', 'C4', 'F4', 'A4']):
        harp.note(92.0 + i * 0.09, p_, 2.2, 58 + i * 2, exact=True)

    # ---------------- G  96–112  process (F C Dm Bb)
    garps = [(96, ['F3', 'C4', 'F4', 'A4', 'C5', 'A4', 'F4', 'C4'], ['A3', 'C4', 'F4'], 'F2', 'A4'),
             (100, ['C3', 'G3', 'C4', 'E4', 'G4', 'E4', 'C4', 'G3'], ['G3', 'C4', 'E4'], 'C2', 'G4'),
             (104, ['D3', 'A3', 'D4', 'F4', 'A4', 'F4', 'D4', 'A3'], ['A3', 'D4', 'F4'], 'D2', 'F4'),
             (108, ['Bb2', 'F3', 'Bb3', 'D4', 'F4', 'D4', 'Bb3', 'F3'], ['Bb3', 'D4', 'F4'], 'Bb1', 'D4')]
    pad.cc(95.95, 11, 88)
    bass.cc(95.95, 11, 88)
    for t0, pat, ch, root, line in garps:
        piano.seq(t0, pat, 0.5, 0.46, 46, accents=[8, 0, 3, 0, 5, 0, 3, 0])
        piano.pedal(t0 + 0.02, t0 + 3.96)
        pad.chord(t0, ch, 4.05, 50)
        bass.note(t0, root, 4.05, 56)
        for q in range(4):
            pizz.note(t0 + q, root.replace('1', '2') if q % 2 == 0 else root.replace('1', '2'), 0.45, 60 + (8 if q == 0 else 0))
        cello.note(t0, n(line) - 12, 4.02, 56)
    cello.cc(95.95, 11, 86)
    pad.ramp(109, 111.9, 88, 60)
    for t, p_ in [(98, 'F4'), (100, 'A4'), (102, 'C5'), (104, 'F5')]:
        harp.note(t, p_, 2.0, 80, exact=True)
        harp.note(t, n(p_) - 12, 2.0, 66, exact=True)

    # ---------------- H  112–120  timing (breath)
    hch = [(112, 116, ['D3', 'F3', 'Bb3'], 'Bb1'), (116, 118, ['C3', 'F3', 'G3'], 'C2'), (118, 120, ['C3', 'E3', 'G3'], 'C2')]
    pad.cc(111.95, 11, 70)
    bass.cc(111.95, 11, 70)
    for a, b, ch, r in hch:
        pad.chord(a, ch, b - a + 0.05, 42)
        bass.note(a, r, b - a + 0.05, 48)
    pad.ramp(117, 119.9, 70, 96)
    for t, p_, d, v in [(112.5, 'F5', 2.0, 40), (114.5, 'D5', 1.5, 38), (116.0, 'C5', 2.0, 38), (118.0, 'E5', 2.0, 40)]:
        piano.note(t, p_, d, v)
    piano.pedal(112.4, 115.9).pedal(116.0, 119.95)

    # ---------------- I  120–132  brand line -> logo (sonic logo at 127.5)
    ich = [(120, 122, ['D3', 'F3', 'A3', 'D4'], 'D2'), (122, 124, ['D3', 'F3', 'Bb3', 'D4'], 'Bb1'),
           (124, 126, ['C3', 'E3', 'G3', 'C4'], 'C2'), (126, 127.5, ['C3', 'E3', 'G3', 'Bb3'], 'C2')]
    pad.cc(119.95, 11, 84)
    bass.cc(119.95, 11, 84)
    for a, b, ch, r in ich:
        pad.chord(a, ch, b - a + 0.03, 58)
        bass.note(a, r, b - a + 0.03, 58)
    pad.ramp(120, 127.4, 84, 120)
    bass.ramp(120, 127.4, 84, 112)
    for t, p_, d, v in [(120.5, 'D5', 1.0, 48), (121.5, 'A4', 0.5, 44), (122.0, 'F5', 2.0, 50), (124.0, 'E5', 1.0, 48), (125.0, 'G5', 1.0, 50), (126.0, 'E5', 1.4, 48)]:
        piano.note(t, p_, d, v)
    piano.pedal(120.4, 121.95).pedal(122.0, 123.95).pedal(124.0, 127.45)
    # the sonic logo
    piano.chord(127.5, ['F1', 'F2'], 4.5, 70, exact=True)
    piano.chord(127.5, ['C3', 'F3', 'A3', 'C4', 'G4', 'A4'], 4.5, 60, strum=0.012, exact=True)
    piano.pedal(127.48, 132.0)
    pad.cc(127.45, 11, 108)
    pad.chord(127.5, ['F2', 'C3', 'F3', 'A3', 'C4', 'F4', 'A4'], 4.6, 64)
    pad.ramp(128.5, 132.0, 108, 84)
    bass.cc(127.45, 11, 104)
    bass.note(127.5, 'F1', 4.6, 66)
    for i, p_ in enumerate(['C6', 'F6', 'G6', 'A6', 'C7']):
        cel.note(127.5 + i * 0.06, p_, 2.5, 62, exact=True)
    glock.note(127.5, 'C7', 2.0, 46, exact=True)
    timp.note(127.5, 'F2', 3.0, 76, exact=True)
    for i in range(10):
        cel.note(128.9 + i * 0.1, 'A6' if i % 2 == 0 else 'C7', 0.25, 40 - i * 2, exact=True)

    # ---------------- J  132–144  end card (gentle outro)
    jch = [(132, 136, ['A3', 'C4', 'F4'], 'F2'), (136, 140, ['Bb3', 'D4', 'F4'], 'Bb1'), (140, 144, ['A3', 'C4', 'F4'], 'F1')]
    pad.cc(131.95, 11, 88)
    bass.cc(131.95, 11, 84)
    for a, b, ch, r in jch:
        pad.chord(a, ch, b - a + 0.05, 46)
        bass.note(a, r, b - a + 0.05, 48)
    pad.ramp(140.5, 143.8, 88, 0)
    bass.ramp(140.5, 143.8, 84, 0)
    for t, p_, d, v in [(132.5, 'C5', 1.0, 42), (133.5, 'A4', 1.0, 40), (134.5, 'F4', 1.5, 38), (136.5, 'D5', 1.0, 42), (137.5, 'Bb4', 1.0, 40),
                        (138.5, 'F4', 1.5, 38), (140.5, 'C5', 1.0, 34), (141.5, 'F5', 2.4, 30)]:
        piano.note(t, p_, d, v)
    piano.chord(140.0, ['F3', 'C4', 'A4'], 4.0, 36, strum=0.03)
    piano.pedal(132.4, 135.95).pedal(136.0, 139.95).pedal(140.0, 145.0)
    return P


# active-region loudness targets (LUFS) and reverb sends per stem
LEVELS = {
    'piano': (-21.0, 0.34), 'pad': (-23.5, 0.42), 'fast': (-25.5, 0.30), 'mid': (-28.0, 0.34), 'bass': (-26.0, 0.26),
    'cello': (-24.5, 0.36), 'horn': (-24.0, 0.42), 'harp': (-26.0, 0.46), 'cel': (-28.5, 0.55), 'glock': (-31.0, 0.55),
    'pizz': (-27.0, 0.36), 'timp': (-23.0, 0.38), 'trem': (-26.5, 0.48),
}


norm_active = S.norm_active


def sound_design(mix):
    # fire bed for the cold open (0–16.5), boosted while the title burns
    def inten(t):
        base = np.clip(t / 3.5, 0, 1) ** 1.5
        burn = 0.35 * np.exp(-((t - 11.5) / 1.6) ** 2)
        out = np.clip((16.3 - t) / 3.0, 0, 1)
        return (base + burn) * out
    fire = S.filt(S.fire_bed(16.8, inten, seed=21), 'highpass', 70, 2)
    mix.add(norm_active(fire, -32.5), 0.0, send=0.18)
    mix.add(norm_active(S.drone(['D1', 'A1'], 13.5, level=0.3, attack=4.0, release=3.0), -33.0), 0.0, send=0.1)
    mix.add(norm_active(S.whoosh(2.6, 260, 2400, peak=0.45, seed=22), -31.0), 9.9, send=0.4)
    # the notice
    mix.add(norm_active(S.drone(['D2', 'A2'], 5.6, level=0.3, attack=1.5, release=0.3, lfo=0.3), -31.0), 16.3, send=0.2)
    mix.add(norm_active(S.paper(0.4, 0.8, seed=23), -30.0), 15.95, send=0.25)
    for i in range(6):
        mix.add(norm_active(S.tick(0.3, 2600 if i % 2 == 0 else 2150, seed=24 + i), -36.0), 16.0 + i, send=0.3)
    mix.add(norm_active(S.thud(0.6, 95, seed=31), -27.0), 19.0, send=0.25)
    mix.add(norm_active(S.riser(1.9, seed=32, f0=250, f1=7000), -30.0), 20.1, send=0.3)
    mix.add(norm_active(S.boom(5.0, 64, 30, seed=33), -23.5), 22.0, send=0.35)
    mix.add(norm_active(S.whoosh(1.3, 500, 5000, peak=0.46, seed=34), -32.0), 27.4, send=0.35)
    # definition -> scale
    mix.add(norm_active(S.whoosh(1.2, 300, 2000, peak=0.5, seed=35), -34.0), 43.4, send=0.35)
    mix.add(norm_active(S.thud(0.6, 70, seed=36), -26.0), 48.5, send=0.3)
    mix.add(norm_active(S.reverse_cymbal(1.8, seed=37), -30.0), 53.7, send=0.4)
    mix.add(norm_active(S.boom(3.5, 58, 34, seed=38, click=0.1), -27.0), 55.5, send=0.4)
    # fire loss items
    for i in range(8):
        mix.add(norm_active(S.tick(0.3, 3200, seed=40 + i), -37.0), 66.0 + i * 0.5, send=0.2)
    mix.add(norm_active(S.reverse_cymbal(1.4, seed=50), -30.0), 69.6, send=0.4)
    mix.add(norm_active(S.boom(4.0, 60, 32, seed=51), -24.0), 71.0, send=0.35)
    mix.add(norm_active(S.boom(3.0, 55, 34, seed=52, click=0.15), -29.0), 75.0, send=0.35)
    mix.add(norm_active(S.riser(2.0, seed=53), -31.0), 78.0, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(2.0, seed=54), -29.0), 78.0, send=0.45)
    # process wipe
    mix.add(norm_active(S.whoosh(1.2, 500, 5000, peak=0.5, seed=55), -33.0), 95.4, send=0.35)
    kick = S.thud(0.8, 55, seed=56)
    shaker = S.filt(S.noise(int(0.09 * S.SR), 'white', 57), 'bandpass', [5000, 11000]) * np.exp(-np.arange(int(0.09 * S.SR)) / S.SR * 45)[:, None]
    for b in range(15):
        t = 96.5 + b * 1.0
        if t < 110.8:
            if b % 2 == 1:
                mix.add(norm_active(kick, -36.0), t - 0.5, send=0.1)
            mix.add(norm_active(shaker.astype(np.float32), -43.0), t, send=0.15)
    for t in [98, 100, 102, 104]:
        mix.add(norm_active(S.whoosh(0.7, 800, 4000, peak=0.6, seed=60 + t), -40.0), t - 0.45, send=0.3)
    # timing ring ticks
    for i in range(8):
        mix.add(norm_active(S.tick(0.3, 2400 if i % 2 == 0 else 2000, seed=70 + i), -36.0), 112.0 + i, send=0.3)
    mix.add(norm_active(S.riser(1.7, seed=80, f0=300, f1=6000), -32.0), 118.3, send=0.3)
    # brand + sonic logo
    mix.add(norm_active(S.riser(2.2, seed=81, f0=200, f1=8000), -30.0), 125.3, send=0.35)
    mix.add(norm_active(S.reverse_cymbal(2.0, seed=82), -28.0), 125.5, send=0.45)
    mix.add(norm_active(S.boom(5.0, 60, 30, seed=83, click=0.12), -27.0), 127.5, send=0.4)


# fader rides for the music bus (dB), linear between points
RIDE = [(0, -2), (15.9, -2), (16.3, 5), (21.8, 5), (21.95, 0), (22.25, 0), (22.6, 6), (27.6, 6), (28.0, -1.5), (43.8, -1.5),
        (44.2, 0), (79.9, 0), (80.2, -1), (95.8, -1), (96.2, -1), (111.8, -1), (112.2, 2), (119.8, 2), (120.2, 0),
        (146, 0)]


def ride(x):
    t = np.arange(len(x)) / S.SR
    ts, gs = zip(*RIDE)
    return (x * S.db(np.interp(t, ts, gs))[:, None]).astype(np.float32)


def build(out):
    parts = compose()
    mix = S.Mix(LEN)
    stems = {}
    for name, part in parts.items():
        x = part.render(LEN)
        if np.abs(x).max() < 1e-5:
            print('WARNING silent stem', name)
            continue
        tgt, send = LEVELS[name]
        x = norm_active(x, tgt)
        if name in ('bass', 'fast'):
            x = S.filt(x, 'highpass', 32, 2)
        if name == 'pad':
            x = S.peak_eq(x, 320, -2.0, 0.9)
        x = ride(x)
        stems[name] = x
        mix.add(x, 0.0, send=send)
        print(f'{name:6s} peak {20 * np.log10(np.abs(x).max() + 1e-9):6.1f} dBFS')
    sound_design(mix)
    irs = {'hall': S.make_ir(3.4, pre=0.03, seed=7)}
    y = mix.render(irs, {'hall': -3.0})
    y = S.master(y, target_lufs=-15.0, ceiling_db=-1.0, fade_out=(142.6, 144.0))
    S.write(out, y)
    print('LUFS', round(S.loudness(y), 2), 'peak', round(20 * np.log10(np.abs(y).max()), 2))
    return stems


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'build/fire-audio.wav')
