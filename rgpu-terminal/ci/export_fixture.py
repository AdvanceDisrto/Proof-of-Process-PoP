"""Export independently checkable signed Python fixture for Node WebCrypto tests."""
import json,sys,tempfile
from pathlib import Path
from rgpu_terminal.journal import ReceiptJournal
from rgpu_terminal.archival import carrier_text

out=Path(sys.argv[1])
with tempfile.TemporaryDirectory() as d:
    j=ReceiptJournal(d)
    e=j.ensure_genesis()
    e2=j.append(claim='SYNTHETIC_TELEMETRY',source_tier='SYNTHETIC_DEMO',
                verdict='REFUTED_FALSE',telemetry={'physical_joules':None,'simulated_joules':4.2})
    out.write_text(json.dumps({'public_key':j.public_key, 'fingerprint':j.fingerprint,
                               'genesis':e,'refuted':e2, 'carrier_compressed':carrier_text(e)},sort_keys=True))
    j.close()
print('CROSS_LANGUAGE_TEST_FIXTURE=GENERATED_SYNTHETIC')
