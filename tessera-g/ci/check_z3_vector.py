"""Connect actual Rust/Z3 formal verdict fixture to Tessera hardware reference model.

No cryptographic signature or physical sensor evidence is asserted by this adapter.
"""
import argparse
import hashlib
import json
from pathlib import Path
from model.tessera_g_model import TesseraModel

EXPECTED = [1,1,2,3,1,3,4,5]

def check(text: str) -> dict:
    rows=[]
    for line in text.splitlines():
        if line.startswith('TESSERA_VECTOR '):
            parts=line.split()
            if len(parts) != 5:
                raise ValueError('malformed vector')
            rows.append(tuple(map(int,parts[1:])))
    if len(rows) != len(EXPECTED):
        raise ValueError('expected eight Z3-sourced input rows')
    model=TesseraModel()
    statuses=[]
    for i, row in enumerate(rows):
        node_idx, verdict, pa, pb = row
        if node_idx != i or verdict not in (0,1,2,3):
            raise ValueError('non-canonical index or verdict')
        status=model.append(verdict, None if pa == -1 else pa, None if pb == -1 else pb)
        statuses.append(int(status))
    if statuses != EXPECTED:
        raise ValueError(f'integration mismatch {statuses} != {EXPECTED}')
    payload=dict(
        schema='innovulis/tessera-z3-software-bridge/v0.1',
        formal_source='real native Z3 via Rust on CI CPU host',
        statuses=statuses,
        nodes=model.export_visualizer(),
        hardware_execution='NOT_PERFORMED',
        signature_verification='NOT_PERFORMED',
        does_not_prove=['physical measurements','hardware root of trust','FPGA or GPU execution','input authenticity'],
    )
    data=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    return dict(payload,canonical_sha256=hashlib.sha256(data).hexdigest())

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('rust_log')
    p.add_argument('--out',default='evidence/z3_tessera_bridge.json')
    args=p.parse_args()
    result=check(Path(args.rust_log).read_text())
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('TESSERA_REAL_Z3_SOFTWARE_BRIDGE=PASS statuses='+str(result['statuses']))
