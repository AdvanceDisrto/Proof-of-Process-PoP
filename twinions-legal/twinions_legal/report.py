"""Printable untrusted physical carrier for a local signed evidence REVIEW receipt.

A static HTML report is a human-readable summary, not a filing, court judgment,
cryptographic proof on paper, or validation of the claimed evidence source.
"""
from __future__ import annotations
import html
from pathlib import Path
from .cli import format_status
from .ledger import CaseBook


def printable_report(book:CaseBook,case_id:str,path:Path):
    r=format_status(book,case_id)
    def esc(x):return html.escape(str(x),quote=True)
    rows=[]
    for g in r['gate_states']:
        is_unknown=g['definition_source']=='not_provided'
        rows.append(f'<tr><td>{g["gate"]:02d}</td><td>{esc(g["name"])}</td><td>{esc(g["status"])}</td>'
                    f'<td>{esc((g["evidence_hash"] or "NONE")[:16])}</td><td>{"UNDEFINED" if is_unknown else "USER-SUPPLIED"}</td></tr>')
    body=f'''<!doctype html><html lang="en"><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>iNNOVULIS™ Twinions — Evidence Review</title>
<style>*{{box-sizing:border-box}}body{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#080d10;color:#d7e7e7;margin:0;padding:2rem}}main{{max-width:900px;margin:auto}}header{{border-bottom:2px solid #64d5c5}}h1{{letter-spacing:.03em}}.tag{{padding:.7rem;margin:1rem 0;background:#321318;color:#ffc7c7;font-weight:700}}.box{{padding:1rem;border:1px solid #3d666b;background:#102027;overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%;font-size:.8rem;margin-top:1rem}}th,td{{border:1px solid #42646b;text-align:left;padding:.65rem}}th{{color:#7de0cd}}footer{{font-size:.8rem;opacity:.8}}@media print{{body{{background:white;color:black;padding:0.3in}}.tag{{color:#8b0000;background:#fff0f0}}.box{{background:white}}table{{font-size:9pt}}th{{color:black}}tr{{page-break-inside:avoid}}}}</style>
<main><header><h1>i™ TWINIONS / EVIDENCE INTAKE</h1><p>REVIEW RECEIPT · NOT A COURT RULING</p></header>
<p class="tag">{esc(r['outcome'])} — NOT CERTIFIED FOR FILING</p>
<div class="box"><p>CASE REFERENCE: {esc(case_id)}</p><p>LEGAL MERITS: {esc(r['legal_merits_verdict'])}</p><p>FILING AUTHORITY: {esc(r['filing_authorization'])}</p><p>JOURNAL INTEGRITY: {esc(r['journal_check']['valid'])}</p><p>LOCAL SHA-256 TIP: <code>{esc(r['journal_check'].get('tip_sha256','INVALID'))}</code></p><p>UNDEFINED WORKFLOW SLOTS: {esc(', '.join(map(str,r['undefined_gates'])) or 'none')}</p><p>NEED REVIEW: {esc(', '.join(map(str,r['missing_gates'])) or 'none')}</p></div>
<table><thead><tr><th>Gate</th><th>Review item</th><th>Status</th><th>Evidence hash prefix</th><th>Definition provenance</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<footer><p>Evidence hashes alone do not prove source authenticity or the asserted facts. A SHA-256-linked local journal can be rewritten by a privileged actor. Keep externally authenticated originals and consult independent qualified counsel before any filing.</p><p>PHYSICAL SENSOR: NOT CONNECTED · SECURE ELEMENT: NOT CONNECTED · PRIVILEGED COURT VERDICT: NONE</p></footer></main></html>'''
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(body,encoding='utf-8')
    return path
