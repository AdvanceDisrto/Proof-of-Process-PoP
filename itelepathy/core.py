"""i™ iTP v0.12: typed/manual opt-in intent, authenticated encryption, signed ACK.
No EEG, physical secure element, hardware attestation, actions, or <1ms guarantee.
"""
from __future__ import annotations
import hashlib, json, secrets, sqlite3, time
from pathlib import Path
from dataclasses import dataclass
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from .policy import Policy

SCHEMA="itp/typed-manual-intent/v1"
MAX_PACKET=16384
SAFE_ACTIONS=frozenset(("PING","SEND_MESSAGE"))

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def public_hex(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,
                                         serialization.PublicFormat.Raw).hex()

class Rejected(ValueError):
    pass

@dataclass(frozen=True)
class PublicIdentity:
    node_id: str
    signer_hex: str
    decrypt_hex: str

class Identity:
    def __init__(self,node_id):
        if (not isinstance(node_id,str) or not 1 <= len(node_id) <= 40 or
            any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in node_id)):
            raise ValueError("invalid node ID")
        self.node_id=node_id
        self.signer=ed25519.Ed25519PrivateKey.generate()
        self.decrypt=x25519.X25519PrivateKey.generate()
    def public(self):
        return PublicIdentity(self.node_id,public_hex(self.signer),public_hex(self.decrypt))

def key_from_shared(secret,salt):
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,
        info=b"iNNOVULIS/iTP/v1/aes-256-gcm").derive(secret)

class Sender:
    def __init__(self,identity,policy=None,*,consent=False,clock=None):
        self.identity=identity
        self.policy=policy or Policy()
        self.consent=consent
        self.clock=clock or (lambda:int(time.time()))
        self.sequence=0

    def seal(self,to,*,action,value,message="",limit=1000,ttl=30):
        if self.consent is not True:raise Rejected("sender opt-in required")
        if action not in SAFE_ACTIONS:raise Rejected("unsafe or unapproved action")
        if not isinstance(message,str) or len(message.encode())>2048 or (action=="PING" and message):
            raise Rejected("invalid message")
        if type(ttl) is not int or not 1<=ttl<=60:raise Rejected("invalid ttl")
        if not self.policy.allowed(value,limit):raise Rejected("fixed-policy Z3 gate failed")
        if not isinstance(to,PublicIdentity):raise Rejected("recipient public key is required")
        stamp=self.clock()
        if type(stamp) is not int:raise Rejected("invalid clock")
        ephemeral=x25519.X25519PrivateKey.generate()
        salt=secrets.token_bytes(16);nonce=secrets.token_bytes(12)
        header={"schema":SCHEMA,"sender":self.identity.node_id,"recipient":to.node_id,
                "sequence":self.sequence+1,"issued_at":stamp,"expires_at":stamp+ttl,
                "ephemeral_pub_hex":public_hex(ephemeral),
                "salt_hex":salt.hex(),"nonce_hex":nonce.hex()}
        plain={"action":action,"value":value,"limit":limit,"message":message,
               "source":"MANUAL_DEMO_ONLY","consent":True}
        secret=ephemeral.exchange(x25519.X25519PublicKey.from_public_bytes(bytes.fromhex(to.decrypt_hex)))
        ciphertext=AESGCM(key_from_shared(secret,salt)).encrypt(nonce,canonical(plain),canonical(header))
        envelope={**header,"ciphertext_hex":ciphertext.hex()}
        signature=self.identity.signer.sign(canonical(envelope)).hex()
        self.sequence+=1
        return {"envelope":envelope,"signature_hex":signature}

class Receiver:
    def __init__(self,identity,trusted_senders,dbpath,policy=None,*,consent=False,
                 clock=None,limit=1000,allowed_actions=SAFE_ACTIONS):
        self.identity=identity
        self.trusted_senders=dict(trusted_senders)
        self.db=sqlite3.connect(str(dbpath))
        self.db.execute("PRAGMA busy_timeout=3000")
        self.db.execute("CREATE TABLE IF NOT EXISTS received (sender TEXT, sequence INTEGER, packet_hash TEXT, PRIMARY KEY(sender,sequence))")
        self.db.commit()
        self.policy=policy or Policy()
        self.consent=consent
        self.clock=clock or (lambda:int(time.time()))
        self.limit=limit
        self.allowed_actions=frozenset(allowed_actions)&SAFE_ACTIONS

    def receive(self,packet):
        if self.consent is not True:raise Rejected("receiver opt-in required")
        try:
            if len(canonical(packet))>MAX_PACKET or set(packet)!={"envelope","signature_hex"}:
                raise Rejected("malformed or oversized packet")
            env=packet["envelope"]
            names={"schema","sender","recipient","sequence","issued_at","expires_at",
                   "ephemeral_pub_hex","salt_hex","nonce_hex","ciphertext_hex"}
            if type(env) is not dict or set(env)!=names or env["schema"]!=SCHEMA:
                raise Rejected("unsupported packet schema")
            if env["recipient"]!=self.identity.node_id:raise Rejected("wrong recipient")
            pinned=self.trusted_senders.get(env["sender"])
            if not isinstance(pinned,PublicIdentity) or pinned.node_id!=env["sender"]:
                raise Rejected("sender not pinned")
            if type(env["sequence"]) is not int or env["sequence"]<=0:
                raise Rejected("invalid sequence")
            issued,expires,now=env["issued_at"],env["expires_at"],self.clock()
            if any(type(x) is not int for x in (issued,expires,now)) or not 1<=expires-issued<=60 or now>expires or issued>now+5:
                raise Rejected("invalid local time window")
            wire=canonical(env)
            ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned.signer_hex)).verify(
                bytes.fromhex(packet["signature_hex"]),wire)
            metadata=dict(env)
            ciphertext=bytes.fromhex(metadata.pop("ciphertext_hex"))
            salt=bytes.fromhex(env["salt_hex"]);nonce=bytes.fromhex(env["nonce_hex"])
            if len(salt)!=16 or len(nonce)!=12:raise Rejected("invalid nonce")
            ephemeral=x25519.X25519PublicKey.from_public_bytes(bytes.fromhex(env["ephemeral_pub_hex"]))
            shared=self.identity.decrypt.exchange(ephemeral)
            decrypted=AESGCM(key_from_shared(shared,salt)).decrypt(nonce,ciphertext,canonical(metadata))
            if len(decrypted)>8192:raise Rejected("oversized decrypted intent")
            body=json.loads(decrypted)
            if type(body) is not dict or set(body)!={"action","value","limit","message","source","consent"}:
                raise Rejected("invalid plaintext schema")
            if body["source"]!="MANUAL_DEMO_ONLY" or body["consent"] is not True:
                raise Rejected("no disclosed opt-in source")
            if (body["action"] not in self.allowed_actions or
                not isinstance(body["message"],str) or len(body["message"].encode())>2048 or
                (body["action"]=="PING" and body["message"])):
                raise Rejected("receiver action policy denied")
            if type(body["limit"]) is not int or body["limit"]!=self.limit:
                raise Rejected("sender cannot weaken recipient policy")
            if not self.policy.allowed(body["value"],self.limit):
                raise Rejected("independent receiver Z3 recheck failed")
            packet_hash=hashlib.sha256(wire).hexdigest()
            with self.db:
                max_seq=self.db.execute("SELECT MAX(sequence) FROM received WHERE sender=?",(env["sender"],)).fetchone()[0]
                if max_seq is not None and env["sequence"]<=max_seq:
                    raise Rejected("replay or out-of-order packet")
                self.db.execute("INSERT INTO received VALUES(?,?,?)",(env["sender"],env["sequence"],packet_hash))
            ack={"schema":"itp/signed-ack/v1","status":"ACKNOWLEDGED_NO_EXTERNAL_ACTION",
                 "sender":env["sender"],"recipient":self.identity.node_id,
                 "sequence":env["sequence"],"packet_sha256":packet_hash,
                 "action":body["action"],"message_sha256":hashlib.sha256(body["message"].encode()).hexdigest(),
                 "external_side_effects":False,"proof_scope":"Z3 declared integer policy only",
                 "does_not_prove":["human thought decoding","hardware or silicon root of trust",
                                   "sub-millisecond latency","real-world authorization"]}
            return {"body":ack,"signature_hex":self.identity.signer.sign(canonical(ack)).hex()}
        except Rejected:raise
        except (ValueError,KeyError,TypeError,UnicodeError,OverflowError,AttributeError,InvalidSignature,InvalidTag) as exc:
            raise Rejected("invalid signed/encrypted intent") from exc

    def close(self):
        self.db.close()

def verify_ack(ack,public_receiver,packet):
    try:
        body=ack["body"];e=packet["envelope"]
        if (body["schema"]!="itp/signed-ack/v1" or body["status"]!="ACKNOWLEDGED_NO_EXTERNAL_ACTION" or
            body["recipient"]!=public_receiver.node_id or body["sender"]!=e["sender"] or
            body["sequence"]!=e["sequence"] or
            body["packet_sha256"]!=hashlib.sha256(canonical(e)).hexdigest() or
            body["external_side_effects"] is not False):
            return False
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_receiver.signer_hex)).verify(
            bytes.fromhex(ack["signature_hex"]),canonical(body))
        return True
    except (InvalidSignature,ValueError,KeyError,TypeError,AttributeError):
        return False
