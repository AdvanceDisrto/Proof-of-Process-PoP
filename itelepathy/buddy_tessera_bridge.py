"""Read-only iTP→Buddy/Tessera-G intent-delivery bridge.

This prepares a typed DAG input; FPGA does NOT authenticate the ACK itself.
"""
from .core import Rejected, verify_ack

def buddy_tessera_demo(ack, pinned_recipient, packet, *, parent_a=None, parent_b=None):
    if not verify_ack(ack,pinned_recipient,packet):
        raise Rejected("pinned, signed receiver acknowledgement required")
    if parent_a is not None and (type(parent_a) is not int or parent_a < 0):
        raise Rejected("invalid parent a")
    if parent_b is not None and (type(parent_b) is not int or parent_b < 0):
        raise Rejected("invalid parent b")
    if parent_a is not None and parent_a == parent_b:
        raise Rejected("duplicate parent pointers")
    body=ack["body"]
    return {
        "schema":"itp/buddy-tessera-software-bridge/v1",
        "buddy":{
            "message":"Typed demo intent delivered to consenting receiver",
            "action":body["action"],
            "status":body["status"],
            "truth_scope":"digital receipt authenticated; NOT human thought or physical reality",
        },
        "tessera_g":{
            "cmd_verdict":1,  # ACK passed digital Ed25519 verification
            "cmd_parent_a":255 if parent_a is None else parent_a,
            "cmd_parent_b":255 if parent_b is None else parent_b,
            "ack_packet_sha256":body["packet_sha256"],
            "hardware_has_verified_signature":False,
            "state_meaning":"received acknowledgement, NOT truth of original intent",
        },
        "external_effects":False,
    }
