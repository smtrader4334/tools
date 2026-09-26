"""Print a per-section loudness table for every stem + the sound-design bus."""
import sys, importlib
import numpy as np
import score_lib as S

mod = importlib.import_module(sys.argv[1])
wins = [tuple(map(float, w.split('-'))) for w in sys.argv[2].split(',')]
parts = mod.compose()
rows = {}
for name, part in parts.items():
    x = part.render(mod.LEN)
    tgt, _ = mod.LEVELS[name]
    x = mod.norm_active(x, tgt)
    if hasattr(mod, 'ride'):
        x = mod.ride(x)
    rows[name] = x
sfx = S.Mix(mod.LEN)
mod.sound_design(sfx)
rows['SFX'] = sfx.dry
def lu(x):
    e = np.mean(x.astype(np.float64) ** 2)
    return 10 * np.log10(e + 1e-12) - 0.691 + 3.0
print('stem    ' + ''.join(f'{a:>5.0f}-{b:<4.0f}' for a, b in wins))
for name, x in rows.items():
    cells = []
    for a, b in wins:
        seg = x[int(a * S.SR):int(b * S.SR)]
        v = lu(seg)
        cells.append(f'{v:9.1f} ' if v > -70 else '        . ')
    print(f'{name:7s} ' + ''.join(cells))
