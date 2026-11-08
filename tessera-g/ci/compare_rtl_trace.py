"""Independently compare simulator trace with reference model's 16 committed nodes."""
import argparse
from pathlib import Path
from model.tessera_g_model import TesseraModel

CASES = [
    (1, None, None), (1, 0, None), (2, 0, None), (1, 2, None),
    (1, 0, 1), (1, 4, 2), (1, 7, None), (1, 6, None),
    (3, None, None), (1, 8, None), (1, 0, 0), (1, 0, 12),
    (0, None, None), (2, None, None), (1, None, None), (1, 14, None),
]

def check(text: str) -> list[int]:
    entries=[]
    for line in text.splitlines():
        if line.startswith('TRACE '):
            _, index, status = line.split()
            entries.append((int(index), int(status)))
    if len(entries) != len(CASES)+1:
        raise ValueError(f'expected 17 trace entries (16 + reset), got {len(entries)}')
    model = TesseraModel()
    for idx, (verdict, pa, pb) in enumerate(CASES):
        actual=entries[idx]
        expected=(idx, int(model.append(verdict, pa, pb)))
        if actual != expected:
            raise ValueError(f'index {idx}: RTL {actual} != model {expected}')
    if entries[-1] != (0, 1):
        raise ValueError('post-reset status mismatch')
    if 'TESSERA_G_RTL=PASS' not in text:
        raise ValueError('RTL success marker absent')
    return [status for _, status in entries]

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('trace')
    args=parser.parse_args()
    states=check(Path(args.trace).read_text())
    print(f'TESSERA_G_RTL_MODEL_COMPARISON=PASS commits={len(states)}')
