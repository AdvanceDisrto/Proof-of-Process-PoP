"""Real localhost socket smoke via uvicorn and httpx. No external network calls."""
from __future__ import annotations
import json, multiprocessing, secrets, socket, time, sys
import httpx


def serve(port,token):
    from unified_i.service import create_app
    import uvicorn
    uvicorn.run(create_app(operator_token=token),host="127.0.0.1",port=port,log_level="error",access_log=False)


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    token=secrets.token_urlsafe(32)
    child=multiprocessing.Process(target=serve,args=(port,token),daemon=True)
    child.start()
    base=f"http://127.0.0.1:{port}"
    try:
        for k in range(45):
            try:
                response=httpx.get(base+"/health",timeout=2)
                if response.status_code==200:break
            except (httpx.TransportError,httpx.TimeoutException):time.sleep(0.1)
        else:raise AssertionError("localhost server failed to start")
        assert response.json()["physical"]=="PENDING"
        assert httpx.get(base+"/").status_code==200
        assert "iNNOVULIS" in httpx.get(base+"/").text
        assert httpx.get(base+"/v1/gates").status_code==401
        assert httpx.get(base+"/v1/gates",headers={"x-operator-token":"bad"}).status_code==401
        g=httpx.get(base+"/v1/gates",headers={"x-operator-token":token}).json()
        assert not g["physical_acceptance"]
        assert len(g["gates"])>=15
        assert httpx.post(base+"/v1/demo/claim",headers={"x-operator-token":token},json={"observed":1,"limit":2}).status_code==403
        claim=httpx.post(base+"/v1/demo/claim",headers={"x-operator-token":token},json={"observed":3,"limit":2,"explicit_demo_ack":True}).json()
        assert claim["status"]=="REFUTED_BOUNDED_CLAIM" and claim["factual_truth"]=="NOT_ESTABLISHED"
        bad=httpx.post(base+"/v1/audit/free-text",headers={"x-operator-token":token},json={"text":"A patient is healthy"}).json()
        assert bad["status"]=="UNRESOLVED"
        result={"status":"PASS", "server":"REAL_LOOPBACK_SOCKET", "http_checks":9,
                "unauthorized_rejected":True,"physical_gates":len(g["gates"]),
                "clinical_ruling":"NOT_GRANTED"}
        print(json.dumps(result,indent=2))
    finally:
        child.terminate();child.join(timeout=8)
        if child.is_alive():child.kill();child.join()
if __name__=="__main__":main()
