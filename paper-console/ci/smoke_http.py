"""Actual localhost HTTP subprocess smoke. Does not bind to public network."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib import request, error


def send(url,data,token=None):
    headers={'Content-Type':'application/json'}
    if token is not None: headers['X-i-Operator-Token']=token
    req=request.Request(url,data=json.dumps(data).encode('utf-8'),headers=headers,method='POST')
    try:
        with request.urlopen(req,timeout=3) as r:return r.status, json.loads(r.read())
    except error.HTTPError as exc:return exc.code,{}


def smoke():
    with tempfile.TemporaryDirectory() as dir:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=os.environ.copy();env['PYTHONPATH']=os.path.abspath('.')+os.pathsep+os.path.abspath('integrations')
        cmd=[sys.executable,'-m','paper_console','serve','--db',str(Path(dir)/'console.db'),'--port',str(port)]
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        try:
            line=proc.stdout.readline().strip()
            if not line.startswith('Operator ingestion token (do not log/share): '):
                raise RuntimeError('service did not generate a strong operator credential')
            token=line.split(': ',1)[1]
            url=f'http://127.0.0.1:{port}'
            for attempt in range(60):
                if proc.poll() is not None:raise RuntimeError('server exited during HTTP startup')
                try:
                    with request.urlopen(url+'/health',timeout=1) as r:
                        if r.status==200:break
                except (OSError,TimeoutError):time.sleep(.1)
            else:raise RuntimeError('server HTTP health probe failed')
            event={'event_id':'smoke-20261108','occurred_at':int(time.time()),'track':'claim',
                   'subject':'synthetic:http-smoke','claim_verdict':'UNRESOLVED',
                   'verification':'NOT_CHECKED','details':{'source':'test_only'},
                   'source_tier':'DEMO','source_ref':'smoke:localhost'}
            assert send(url+'/api/ingest',event)[0]==403
            assert send(url+'/api/ingest',event,token=token)[0]==200
            assert send(url+'/api/ingest',event,token=token)[1]['duplicate'] is True
            with request.urlopen(url+'/api/timeline') as r:
                rows=json.load(r)['events']
            assert len(rows)==1 and rows[0]['verification']=='NOT_CHECKED'
            with request.urlopen(url+'/api/integrity') as r:
                audit=json.load(r)
            assert audit['chain_ok'] and audit['checked']==1
            print('PAPER_CONSOLE_LOCAL_HTTP=PASS operator_gate=PASS unsigned_only=PASS sqlite_chain=PASS printer=OFF')
            return True
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)

if __name__=='__main__':smoke()
