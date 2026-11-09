"""Real loopback TCP HTTP + concurrent WebSocket smoke; no physical sensor/printer."""
from __future__ import annotations
import asyncio, json, os, pathlib, socket, subprocess, sys, tempfile, time
import httpx
from websockets.asyncio.client import connect
from rgpu_terminal.crypto import verify_envelope,ZERO_HASH

ROOT=pathlib.Path(__file__).resolve().parents[1]

async def run():
    with tempfile.TemporaryDirectory(prefix='innovulis-rgpu-smoke-') as tmp:
        s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
        token='local-test-'+'N'*56
        env={**os.environ,'PYTHONPATH':str(ROOT),'INNOVULIS_OPERATOR_TOKEN':token,
             'INNOVULIS_SYNTHETIC_DEMO':'1'}
        args=[sys.executable,'-m','rgpu_terminal','serve','--data-dir',tmp,'--port',str(port)]
        process=subprocess.Popen(args,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        async def wait_up():
            async with httpx.AsyncClient(timeout=1.0) as client:
                for _ in range(80):
                    if process.poll() is not None:raise RuntimeError('server died before startup')
                    try:
                        r=await client.get(f'http://127.0.0.1:{port}/api/health')
                        if r.status_code==200:return
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.10)
                raise RuntimeError('HTTP startup timeout')
        try:
            await wait_up()
            base=f'http://127.0.0.1:{port}'
            async with httpx.AsyncClient() as cli:
                trust=(await cli.get(base+'/api/identity')).json()
                pub=trust['ed25519_public_key_hex']
                genesis=(await cli.get(base+'/api/receipt/1')).json()
                payload=verify_envelope(genesis,pub,previous=ZERO_HASH,expected_sequence=1)
                assert payload['declared_verdict']=='PROCESS_OBSERVED'
                url=f'ws://127.0.0.1:{port}/ws'
                async with connect(url,origin=base) as a, connect(url,origin=base) as b:
                    assert json.loads(await asyncio.wait_for(a.recv(),3))['type']=='hello'
                    assert json.loads(await asyncio.wait_for(b.recv(),3))['type']=='hello'
                    issue=await cli.post(base+'/api/demo/tick',headers={'x-innovulis-operator-token':token},json={'outcome':'REFUTED'})
                    assert issue.status_code==200,issue.text
                    frames=await asyncio.gather(a.recv(),b.recv())
                    packets=[json.loads(s) for s in frames]
                    assert all(p['type']=='receipt' for p in packets)
                    assert packets[0]['envelope']==packets[1]['envelope']
                    child=verify_envelope(packets[0]['envelope'],pub,previous=genesis['payload_sha256'],expected_sequence=2)
                    assert child['source_tier']=='SYNTHETIC_DEMO' and child['declared_verdict']=='REFUTED_FALSE'
                svg=await cli.get(base+'/api/receipt/1/qr.svg')
                assert svg.status_code==200 and svg.headers.get('content-type','').startswith('image/svg+xml')
                assert len(svg.content)>500
            process.terminate();await asyncio.to_thread(process.wait,5)
            process=subprocess.Popen(args,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            await wait_up()
            async with httpx.AsyncClient() as cli:
                trust2=(await cli.get(base+'/api/identity')).json()
                last=(await cli.get(base+'/api/history?after=0')).json()['envelopes']
                assert trust['key_fingerprint_sha256']==trust2['key_fingerprint_sha256']
                assert len(last)==2
            result={'real_loopback_http':'PASS','two_concurrent_websocket_clients':'PASS',
                    'signed_refuted_alert':'PASS','restart_persistent_identity':'PASS',
                    'hash_chain_through_restart':'PASS','qr_svg_generated':'PASS',
                    'hardware_status':'NOT_CONNECTED','physical_print':'NOT_PERFORMED',
                    'trusted_pub_fingerprint_for_synthetic_test':trust['key_fingerprint_sha256']}
            print(json.dumps(result,sort_keys=True,indent=2))
        finally:
            if process.poll() is None:
                process.terminate()
                try:await asyncio.to_thread(process.wait,5)
                except subprocess.TimeoutExpired:process.kill()

if __name__=='__main__':asyncio.run(run())
