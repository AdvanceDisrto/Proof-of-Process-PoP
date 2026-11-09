"""Loopback-only, token-gated read-only local evidence viewer.
No upload/filing endpoints. JS never executes untrusted documents.
"""
from __future__ import annotations
import os, hmac
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from .ledger import CaseBook,case_id_ok
from .cli import format_status

HTML='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>i™ Twinions Evidence Review</title><link rel="stylesheet" href="/style.css">
<main><header><h1>i™ <b>TWINIONS</b> <small>Evidence Review / v0.1</small></h1><p>LOCAL WORKFLOW · NOT A COURT FINDING · NOT A LEGAL ADVISER</p></header>
<form id="lookup"><label>Operator token <input id="token" type="password" required autocomplete="off"></label><label>Case reference <input id="case" maxlength="64" required></label><button>Read local DAG</button></form>
<section id="summary" role="status" aria-live="polite"></section><ol id="gates"></ol><footer>No physical signature, legal merit finding, or immutable ledger is asserted.</footer></main><script src="/app.js" defer></script></html>'''
CSS='''*{box-sizing:border-box}body{margin:0;min-height:100vh;font:14px ui-monospace,monospace;background:radial-gradient(circle at top,#12343b,#05080d 55%);color:#dceff1}main{max-width:1100px;margin:auto;padding:2rem}header{border-bottom:1px solid #37666c;margin-bottom:1.6rem}h1{font-size:2rem;letter-spacing:.08em}h1 b{color:#8fffd6}small{font-size:.7rem;color:#88a0a7}header p{color:#ffd48a}form{display:flex;gap:1rem;flex-wrap:wrap}label{display:grid;gap:.4rem;flex:1}input{border:1px solid #426c7a;background:#111e25;color:#fff;padding:.8rem;border-radius:6px}button{background:#8fffd6;color:#07110f;border:0;border-radius:6px;padding:.7rem 1.4rem;cursor:pointer}section{padding:1rem;margin:1rem 0;background:#102028;border-left:4px solid #8fffd6;white-space:pre-wrap}ol{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:.6rem}li{padding:1rem;border:1px solid #42626b;background:#0c151d;border-radius:5px}strong{color:#8fffd6}em{color:#d6c798;font-style:normal}footer{margin:2rem 0;color:#94a7b1}'''
JS='''const form=document.querySelector('#lookup');
form.addEventListener('submit',async e=>{
 e.preventDefault();const out=document.querySelector('#summary');const list=document.querySelector('#gates');list.replaceChildren();out.textContent='Checking local journal…';
 const id=document.querySelector('#case').value;const token=document.querySelector('#token').value;
 try { const r=await fetch('/api/cases/'+encodeURIComponent(id),{headers:{'X-Operator-Token':token},cache:'no-store'});
 if(!r.ok)throw Error('Request rejected ('+r.status+')');const s=await r.json();
 out.textContent='CASE '+s.case_id+'\\nOUTCOME '+s.outcome+'\\nLEGAL MERITS '+s.legal_merits_verdict+'\\nFILING '+s.filing_authorization+'\\nAUDIT '+(s.journal_check.valid?'LOCAL CHAIN CONSISTENT':'AUDIT INVALID')+'\\nMISSING '+s.missing_gates.join(', ')+'\\nUNDEFINED '+s.undefined_gates.join(', ');
 for(const g of s.gate_states){const li=document.createElement('li'); const a=document.createElement('strong');a.textContent='#'+g.gate+' '+g.name;const b=document.createElement('p');b.textContent='STATUS: '+g.status;const c=document.createElement('em');c.textContent='EVIDENCE HASH: '+(g.evidence_hash||'NONE');li.append(a,b,c);list.append(li);}
 }catch(err){out.textContent='UNVERIFIED / BLOCKED: '+err.message;}
});'''

def app_for(db_path,token:str):
    if not isinstance(token,str) or len(token)<24:raise ValueError('a nontrivial operator token is required')
    db_path=Path(db_path)
    app=FastAPI(title='Twinions read-only local evidence viewer',docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def headers(request:Request,call_next):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'none'; connect-src 'self'; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'"
        response.headers['Referrer-Policy']='no-referrer'
        return response
    @app.get('/')
    async def home():return HTMLResponse(HTML)
    @app.get('/app.js')
    async def script():
        from fastapi.responses import Response
        return Response(JS,media_type='application/javascript')
    @app.get('/style.css')
    async def css():
        from fastapi.responses import Response
        return Response(CSS,media_type='text/css')
    @app.get('/api/cases/{case_id}')
    async def status(case_id:str,request:Request):
        supplied=request.headers.get('X-Operator-Token','')
        if not hmac.compare_digest(supplied,token):raise HTTPException(status_code=403,detail='invalid operator token')
        if not case_id_ok(case_id):raise HTTPException(status_code=400,detail='invalid case ID')
        book=CaseBook(db_path)
        try:
            try:return format_status(book,case_id)
            except ValueError:raise HTTPException(status_code=404,detail='case not found')
        finally:book.close()
    return app

def run(db_path,port:int):
    if not 1024<=port<=65535:raise ValueError('invalid local port')
    token=os.getenv('TWINIONS_OPERATOR_TOKEN','')
    if len(token)<24:raise RuntimeError('set TWINIONS_OPERATOR_TOKEN (>=24 chars) before serving')
    import uvicorn
    uvicorn.run(app_for(db_path,token),host='127.0.0.1',port=port,access_log=False)
