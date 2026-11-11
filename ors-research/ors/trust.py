"""iNNOVULIS trust-fabric software prototype.

Ed25519 signatures authenticate issuer bytes, not physical measurements, billing or
regulatory compliance. Python canonical JSON is NOT RFC 8785 JCS. No secrets in HTTP
responses. All policies and meters must be externally audited before production use.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import math
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

SHA = re.compile(r'^sha256:[0-9a-f]{64}$')
SPECS = {'ipqr/utility-receipt/v1','ipqr/providence-receipt/v1','ipqr/energy-receipt/v1','ipqr/energy-match-attestation/v1'}
SCOPE = ['that a signature proves underlying telemetry is true', 'that timestamp accuracy is independently established', 'that authorization or legal compliance is established', 'that the material represents a tradable carbon credit']


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(obj):
    return 'sha256:'+hashlib.sha256(canonical(obj)).hexdigest()


def public_hex(key):
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def issue(spec, fields, sk):
    if spec not in SPECS: raise ValueError('unrecognized spec')
    if not isinstance(fields,dict):raise ValueError('fields must be object')
    body = {'spec':spec, **fields}
    if body['spec']!=spec:raise ValueError('spec mismatch')
    body.setdefault('issued_at_utc_untrusted', datetime.now(timezone.utc).isoformat())
    dnp=body.get('does_not_prove')
    if not isinstance(dnp,list) or not dnp or not all(isinstance(x,str) and x for x in dnp):raise ValueError('does_not_prove required')
    serialized=canonical(body)
    return {'payload':body,'payload_hash':digest(body),'signature':{'algorithm':'Ed25519','value':sk.sign(serialized).hex(),'public_key_hex':public_hex(sk)}}


def verify(receipt,pinned_public_key_hex):
    issues=[]
    try:
        if not isinstance(receipt,dict):raise ValueError('not object')
        body=receipt['payload']; sig=receipt['signature']
        if not isinstance(body,dict) or body.get('spec') not in SPECS:issues.append('invalid_spec')
        if not isinstance(body.get('does_not_prove'),list) or not body['does_not_prove']:issues.append('scope_missing')
        if sig.get('algorithm')!='Ed25519':issues.append('algorithm_invalid')
        if sig.get('public_key_hex')!=pinned_public_key_hex:issues.append('pin_mismatch')
        if receipt['payload_hash']!=digest(body):issues.append('hash_mismatch')
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key_hex)).verify(bytes.fromhex(sig['value']),canonical(body))
    except (ValueError,KeyError,TypeError,InvalidSignature,OverflowError):issues.append('signature_or_format_invalid')
    return {'ok':not issues,'errors':issues}


def _positive_quantity(value):
    if isinstance(value,bool):raise ValueError('quantity cannot be boolean')
    try: q=Decimal(str(value))
    except (InvalidOperation,TypeError):raise ValueError('invalid quantity')
    if not q.is_finite() or q<=0:raise ValueError('quantity must be positive finite')
    return q


def meter_utility(sk, consumer, resource_type, quantity, unit, evidence_hash, event_id):
    """Meters *reported* usage; real meter is external. Event ID is source dedup key."""
    if not all(isinstance(v,str) and v.strip() for v in (consumer,resource_type,unit,event_id)):raise ValueError('required field blank')
    if not isinstance(evidence_hash,str) or not SHA.fullmatch(evidence_hash):raise ValueError('invalid evidence hash')
    q=_positive_quantity(quantity)
    fields={'utility_id': 'urn:iur:'+hashlib.sha256((public_hex(sk)+'|'+event_id).encode()).hexdigest(),
            'issuer':{'role':'METER_SIMULATOR','public_key_hex':public_hex(sk)},'consumer':consumer,
            'resource':{'type':resource_type,'quantity':str(q),'unit':unit},
            'metering_evidence':{'evidence_hash':evidence_hash,'event_id':event_id},
            'trust_basis':'software_reported_metering_NOT_HARDWARE_ATTESTED','does_not_prove':SCOPE[:]}
    return issue('ipqr/utility-receipt/v1',fields,sk)


def _utc(dt):
    if not isinstance(dt,str):raise ValueError('time must be ISO string')
    d=datetime.fromisoformat(dt.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('timezone required')
    return d.astimezone(timezone.utc)


def mint_energy(sk,meter_id,source_type,kwh,start_utc,end_utc,event_id):
    if source_type not in {'SOLAR','WIND','HYDRO','NUCLEAR','OTHER'}:raise ValueError('invalid source')
    if not meter_id or not event_id:raise ValueError('meter/event required')
    q=_positive_quantity(kwh)
    start,end=_utc(start_utc),_utc(end_utc)
    if not start<end:raise ValueError('invalid window')
    fields={'energy_id':'urn:ienergy:'+hashlib.sha256((public_hex(sk)+'|'+event_id).encode()).hexdigest(),
            'meter_id':meter_id,'source_type':source_type,'output_kwh':str(q),
            'timestamp_window':{'start_utc':start.isoformat(),'end_utc':end.isoformat()},
            'event_id':event_id,'trust_basis':'software_meter_not_physically_calibrated',
            'does_not_prove':SCOPE+['that the grid delivered this generation to the consumer']}
    return issue('ipqr/energy-receipt/v1',fields,sk)


def match_energy(sk, generation, consumption, generation_public_key, consumption_public_key, used_allocation_ids=None):
    """Accounting match; explicitly NOT offset/carbon credit issuance. Caller owns dedup state."""
    if not verify(generation,generation_public_key)['ok'] or not verify(consumption,consumption_public_key)['ok']:
        raise ValueError('source signature not verified')
    ep= generation['payload']; cp=consumption['payload']
    if ep.get('spec')!='ipqr/energy-receipt/v1' or cp.get('spec')!='ipqr/utility-receipt/v1':raise ValueError('incorrect source types')
    resource=cp['resource']
    if resource['type']!='ENERGY' or resource['unit']!='kWh':raise ValueError('consumer energy units required')
    q=_positive_quantity(resource['quantity']); produced=_positive_quantity(ep['output_kwh'])
    if q>produced:raise ValueError('consumption exceeds supplied generation evidence')
    stamp=_utc(cp['issued_at_utc_untrusted']); a=_utc(ep['timestamp_window']['start_utc']); b=_utc(ep['timestamp_window']['end_utc'])
    if not (a<=stamp<b):raise ValueError('consumption outside generation window')
    allocation_id=digest({'gen':generation['payload_hash'],'consumer':consumption['payload_hash']})
    if used_allocation_ids is not None:
        if allocation_id in used_allocation_ids:raise ValueError('duplicate allocation')
        used_allocation_ids.add(allocation_id)
    return issue('ipqr/energy-match-attestation/v1',{
        'claim_type':'SIMULATED_TIME_WINDOW_MATCH_NOT_CARBON_CREDIT',
        'energy_source_hash':generation['payload_hash'],'consumer_hash':consumption['payload_hash'],
        'matched_kwh':str(q),'allocation_id':allocation_id,'offset_kg_co2':'NOT_ASSERTED',
        'trust_basis':'software_signed_accounting_inputs_only',
        'does_not_prove':SCOPE+['generation attributes were exclusively allocated','the meters were calibrated or independently audited','that this receipt is a REC or carbon offset']},sk)


def guardian_evaluate(sk, proposal, policy_id, policy_text, approved, guardian_id, reason):
    """Demo-only deterministic policy guardian. Production requires separate trusted human signing service."""
    if not isinstance(proposal,str) or not isinstance(policy_text,str) or not guardian_id or not reason:raise ValueError('invalid guardian request')
    if not isinstance(approved,bool):raise ValueError('approved must be boolean')
    # Never assert autonomous safety: external approved is an explicitly reported decision.
    return issue('ipqr/providence-receipt/v1',{'providence_id':'urn:popp:'+secrets.token_hex(32),
        'ai_proposal_hash':digest({'proposal':proposal}),
        'safety_policy':{'policy_id':policy_id,'policy_hash':digest({'policy_text':policy_text})},
        'guardian':{'identity':guardian_id,'type':'DEMO_SOFTWARE_GUARDIAN','verdict':'APPROVED' if approved else 'REJECTED','reason':reason},
        'trust_basis':'software_reported_policy_decision_NOT_INDEPENDENT_HUMAN_APPROVAL',
        'does_not_prove':SCOPE+['the proposal was actually safe','that a trusted human reviewed the proposal']},sk)


def decision_authorized(receipt,pinned_key,proposal,policy_text,trusted_guardian_keys):
    if not verify(receipt,pinned_key)['ok'] or pinned_key not in trusted_guardian_keys:return False
    body=receipt['payload']
    return (body.get('spec')=='ipqr/providence-receipt/v1'
            and body.get('trust_basis')=='independent_human_approval'
            and body.get('guardian',{}).get('type')=='HUMAN_OVERSEER'
            and body.get('guardian',{}).get('verdict')=='APPROVED'
            and body.get('ai_proposal_hash')==digest({'proposal':proposal})
            and body.get('safety_policy',{}).get('policy_hash')==digest({'policy_text':policy_text}))
