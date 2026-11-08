"""Real localhost process smoke: no PHI or remote/physical services."""
import json, os, secrets, socket, subprocess, sys, tempfile, time
from pathlib import Path
import httpx

def run():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    token=secrets.token_urlsafe(40)
    with tempfile.TemporaryDirectory() as td:
        env=dict(os.environ,HUB_OPERATOR_TOKEN=token)
        args=[sys.executable,"-m","human_hub","serve","--db",str(Path(td)/"hub.db"),"--port",str(port)]
        proc=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
        try:
            url=f"http://127.0.0.1:{port}"
            with httpx.Client(timeout=10) as c:
                for _ in range(40):
                    try:
                        r=c.get(url+"/health")
                        if r.status_code==200:break
                    except httpx.TransportError:pass
                    if proc.poll() is not None:raise RuntimeError("Hub exited before HTTP health")
                    time.sleep(.15)
                else:raise RuntimeError("Hub startup timeout")
                h={"X-I-Hub-Token":token}
                assert c.get(url+"/api/feeds").status_code==403
                response=c.post(url+"/api/demo",headers=h,
                   json={"explicit_demo_consent":True,"observed":65000,"limit":50000})
                assert response.status_code==200,response.text
                demo=response.json();rid=demo["event_id"]
                assert demo["issuer_claim"]=="REFUTED_FALSE"
                qr=c.get(url+"/api/qr/"+rid,headers=h)
                assert qr.status_code==200 and qr.content.startswith(b"\x89PNG")
                preview=c.get(url+"/api/print-preview/"+rid,headers=h)
                assert preview.status_code==200
                assert b"SYNTHETIC DEMO ONLY" in preview.content
                assert c.post(url+"/api/review/"+rid,headers=h,json={"confirm_scope":False}).status_code==422
                ack=c.post(url+"/api/review/"+rid,headers=h,json={"confirm_scope":True})
                assert ack.status_code==200 and not ack.json()["is_professional_medical_approval"]
                feed=c.get(url+"/api/feeds",headers=h).json()
                assert feed["journal"]["chain_ok"] and len(feed["events"])==2
                return {"live_loopback_http":"PASS","real_signed_crypto_under_synthetic_anchor":True,
                        "issuer_refuted_status_preserved":True,
                        "scan_carrier_png_bytes":len(qr.content),
                        "escpos_preview_bytes":len(preview.content),
                        "real_sensor":"NOT_CONNECTED","physical_printer":"NOT_CONNECTED",
                        "clinical_readiness":False,"patient_data":"NOT_ACCEPTED"}
        finally:
            proc.terminate()
            try:proc.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill();proc.communicate()
if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
