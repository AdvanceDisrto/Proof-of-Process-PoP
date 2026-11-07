"""Non-invasive AMD hardware / eight external gates readiness receipt. No remote actions."""
import json
from pathlib import Path
import shutil
import sys

GATES = ('tsa','witnesses','raft','zk','finance','physical','github_release','cloud')


def probe(device_root=Path('/')):
    return {
        'schema': 'ipqr/amd-preflight/v1',
        'amd': {
            'kfd_exists': (device_root/'dev/kfd').exists(),
            'dri_exists': (device_root/'dev/dri').exists(),
            'amd_smi_present': shutil.which('amd-smi') is not None,
            'actual_amd_gpu_execution': 'NOT_PERFORMED',
        },
        'tool_presence': {name: shutil.which(name) is not None
                          for name in ('cargo','rustc','naga','openssl','docker','i2cdetect')},
        'gates': {name: 'PENDING_OPERATOR_VERIFIED_EVIDENCE' for name in GATES},
        'external_activated': False,
        'verdict': 'LOCAL_PREFLIGHT_ONLY',
        'does_not_prove': [
            'that separate witnesses actually exist or control independent signing keys',
            'that an RFC3161 token has been independently verified',
            'that AMD ROCm ran on a genuine supported AMD GPU',
            'that any payment, cloud deployment, physical signing or formal ZK proof occurred',
        ],
    }


if __name__ == '__main__':
    value = probe()
    output = json.dumps(value, indent=2, sort_keys=True)
    if len(sys.argv) == 3 and sys.argv[1] == '--out':
        Path(sys.argv[2]).write_text(output + '\n', encoding='utf-8')
    elif len(sys.argv) != 1:
        raise SystemExit('usage: python tools/amd_external_gate_probe.py [--out report.json]')
    print(output)
