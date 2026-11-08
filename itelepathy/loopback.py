"""Length-prefixed bounded localhost-only asyncio transport; no public routing."""
import asyncio, json
from .core import MAX_PACKET, Rejected, canonical

async def _serve(reader,writer,receiver):
    try:
        size=int.from_bytes(await asyncio.wait_for(reader.readexactly(4),2),'big')
        if not 0<size<=MAX_PACKET:raise Rejected("invalid request frame")
        request=json.loads(await asyncio.wait_for(reader.readexactly(size),2))
        ack=receiver.receive(request)
        payload={"ok":True,"ack":ack}
    except (Rejected,KeyError,ValueError,TypeError,UnicodeError,asyncio.TimeoutError,asyncio.IncompleteReadError):
        payload={"ok":False,"status":"REJECTED"}
    out=canonical(payload)
    writer.write(len(out).to_bytes(4,"big")+out)
    try:await asyncio.wait_for(writer.drain(),2)
    finally:
        writer.close();await writer.wait_closed()

async def start_receiver(receiver):
    return await asyncio.start_server(lambda r,w:_serve(r,w,receiver),"127.0.0.1",0)

async def send_local(port,packet):
    rd,wr=await asyncio.open_connection("127.0.0.1",port)
    try:
        raw=canonical(packet)
        if len(raw)>MAX_PACKET:raise Rejected("outbound packet too large")
        wr.write(len(raw).to_bytes(4,"big")+raw)
        await asyncio.wait_for(wr.drain(),2)
        size=int.from_bytes(await asyncio.wait_for(rd.readexactly(4),2),"big")
        if not 0<size<=MAX_PACKET:raise Rejected("response too large")
        return json.loads(await asyncio.wait_for(rd.readexactly(size),2))
    finally:
        wr.close();await wr.wait_closed()
