from pathlib import Path
from twinions_legal import CaseBook
from twinions_legal.report import printable_report

def test_printable_report_blocks_legal_merits_and_escapes_labels(tmp_path):
    b=CaseBook(tmp_path/'demo.db');b.create('SAFE-001')
    file=tmp_path/'file.txt';file.write_text('synthetic')
    h=b.add_evidence('SAFE-001',file,'<script>alert(1)</script>')
    b.set_gate('SAFE-001',1,'EVIDENCE_ATTACHED',h)
    path=printable_report(b,'SAFE-001',tmp_path/'out.html')
    html=path.read_text()
    assert 'NOT CERTIFIED FOR FILING' in html
    assert 'NOT_DETERMINED' in html
    assert 'PHYSICAL SENSOR: NOT CONNECTED' in html
    assert 'script>alert' not in html
    assert html.count('<tr>')==19
    b.close()
