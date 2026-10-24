#!/usr/bin/env python3
import hashlib, ipaddress, json, time
from pathlib import Path

PHYSICAL_TRANSPORTS={"LoRa","LoRa_868MHz","LoRa_915MHz","PacketRadio","WiFi","Bluetooth","Serial","Ethernet","Fiber"}

def _sha(obj):
    b=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(b).hexdigest()

def validate_address(address, public_key_hex):
    try:
        ipaddress.IPv6Address(address)
    except ValueError:
        return False
    if not address.lower().startswith("200:"):
        return False
    expected=hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:8]
    return expected in address.replace(":","").lower()

def build_receipt(node_id, public_key_hex, yggdrasil_ipv6, physical_transport, hop_count, payload):
    payload_hash="sha256:"+hashlib.sha256(payload).hexdigest()
    address_ok=validate_address(yggdrasil_ipv6,public_key_hex)
    transport_ok=physical_transport in PHYSICAL_TRANSPORTS and hop_count >= 1
    route_gate="MEASURED_PASS" if address_ok and transport_ok else "ACTION_REQUIRED"
    receipt={
      "spec":"innovulis-inetty-routing/1.0",
      "timestamp_utc":time.time(),
      "node_identity":node_id,
      "sovereign_address":yggdrasil_ipv6,
      "routing_path":{"transport":physical_transport,"hops":hop_count,"payload_hash":payload_hash},
      "verification":{"address_structurally_cryptographic":address_ok,"transport_is_local_capable":transport_ok,
                       "route_gate":route_gate},
      "proves":["The supplied receipt is internally consistent with its declared inputs."],
      "does_not_prove":["That a physical radio transmitted the packet.","That firmware was untampered.","That energy sovereignty exists.","That the global physical_gate is unlocked."],
      "physical_gate":"ACTION_REQUIRED",
      "the_central_rule":"The receipt can record reality; it cannot manufacture reality."
    }
    receipt["receipt_sha256"]="sha256:"+_sha(receipt)
    return receipt

def emit(out_path, **kwargs):
    receipt=build_receipt(**kwargs)
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(receipt,indent=2))
    return receipt

if __name__=="__main__":
    pub="8f4a2b1c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1"
    h=hashlib.sha256(bytes.fromhex(pub)).hexdigest()[:8]
    address=f"200:{h[:4]}:{h[4:]}::1"
    emit("evidence/inetty_sovereign_node.json",
         node_id="did:iska:node:alpha-01",public_key_hex=pub,yggdrasil_ipv6=address,
         physical_transport="LoRa_868MHz",hop_count=3,payload=b"iNetty test packet")
