"""Generate deterministic OpenAPI spec without real runtime state or secrets."""
import argparse
import json
from pathlib import Path
from .api import Settings, make_app

def generate():
    sample = Settings(Path('/not-a-real-runtime'), '0' * 64, 'DOCUMENTATION_ONLY_NOT_A_REAL_SECRET')
    return json.dumps(make_app(sample).openapi(), indent=2, sort_keys=True) + '\n'

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    p.add_argument('--out', type=Path, default=Path('openapi.json'))
    args = p.parse_args()
    value = generate()
    if args.check:
        if not args.out.exists() or args.out.read_text() != value:
            raise SystemExit('OPENAPI_DRIFT: Regenerate with python -m innovulis.openapi')
        print('OpenAPI contract up to date')
    else:
        args.out.write_text(value)
        print('OpenAPI:', args.out)
