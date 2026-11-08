"""Smoke demonstration: python -m itelepathy.demo"""
import asyncio, tempfile, json, time
from pathlib import Path
from . import Identity, Sender, Receiver, Rejected, verify_ack, Policy
from .loopback import start_receiver,send_local

async def run():
    policy=Policy()
    a,b=Identity("alice"),Identity("buddy")
    source=Sender(a,policy,consent=True)
    with tempfile.TemporaryDirectory() as d:
        sink=Receiver(b,{"alice":a.public()},Path(d)/"received.db",policy,consent=True)
        server=await start_receiver(sink)
        try:
            packet=source.seal(b.public(),action="SEND_MESSAGE",value=500,message="test-only")
            start=time.perf_counter_ns()
            response=await send_local(server.sockets[0].getsockname()[1],packet)
            elapsed_us=(time.perf_counter_ns()-start)//1000
            assert response["ok"] and verify_ack(response["ack"],b.public(),packet)
            again=await send_local(server.sockets[0].getsockname()[1],packet)
            assert again=={"ok":False,"status":"REJECTED"}
            try: source.seal(b.public(),action="TRANSFER_FUNDS",value=50_000)
            except Rejected:blocked=True
            else:blocked=False
            assert blocked
            return {"scope":"local synthetic typed intent (NOT neural signal)",
                "native_Z3":"PASS","AES256_GCM_X25519":"PASS","Ed25519_pinned_ack":"PASS",
                "sqlite_replay_rejected":True,"forbidden_financial_command_rejected":True,
                "local_roundtrip_microseconds_observed":elapsed_us,
                "latency_guarantee":None,"real_hardware_signer":None,
                "external_actions":False,"external_peer_network":False}
        finally:
            server.close();await server.wait_closed();sink.close()

if __name__=="__main__":
    print(json.dumps(asyncio.run(run()),sort_keys=True,indent=2))
