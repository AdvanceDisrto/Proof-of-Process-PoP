"""iNNOVULIS EPU v1 software reference: signed provenance, policy, raw sample reconstruction.

No proof that a physical meter or lab exists follows from syntactically valid test receipts.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, timedelta
from typing import Any, Mapping

import blake3
import rfc8785
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
from z3 import Int, Solver, Or, unsat

PENDING = "PENDING PROOF OF PROCESS — CIH VERIFICATION"
METERS = {"WALL_PDU", "SMART_PDU", "RAPL_PER_CORE", "RAPL_PKG", "ON_DIE_SENSOR", "SBC_PMIC"}
ATTR = {"DEDICATED_CIRCUIT", "DIFFERENTIAL", "RAPL_PER_JOB", "ESTIMATED_FROM_UTIL", "NONE"}
STATES = {"METERED", "METERED_STALE", "NOT_MEASURED"}
HEX64 = '0123456789abcdef'

class Reject(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def demand(ok: bool, code: str) -> None:
    if not ok:
        raise Reject(code)


def jcs(obj: Any) -> bytes:
    return rfc8785.dumps(obj)


def sha(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def blake(data: bytes) -> str:
    return 'blake3:' + blake3.blake3(data).hexdigest()


def valid_hash(value: Any, kind: str = 'blake3') -> bool:
    return isinstance(value,str) and value.startswith(kind + ':') and len(value) == len(kind) + 65 and all(c in HEX64 for c in value.split(':')[1])


def sign(obj: dict, sk: SigningKey) -> dict:
    """Domain-separated signature over JCS excluding only `signature` field."""
    v = copy.deepcopy(obj)
    v.pop('signature', None)
    v['signer_pubkey'] = bytes(sk.verify_key).hex()
    msg = b'iNNOVULIS/EPU/v1\0' + blake3.blake3(jcs(v)).digest()
    v['signature'] = sk.sign(msg).signature.hex()
    return v


def verify_signature(obj: dict, expected_pubkey: str) -> None:
    demand(isinstance(obj,dict), 'RECEIPT_NOT_OBJECT')
    demand(obj.get('signer_pubkey') == expected_pubkey, 'UNTRUSTED_SIGNER')
    sig = obj.get('signature')
    demand(isinstance(sig,str) and len(sig)==128 and all(c in HEX64 for c in sig), 'SIGNATURE_MALFORMED')
    v = dict(obj); del v['signature']
    msg = b'iNNOVULIS/EPU/v1\0' + blake3.blake3(jcs(v)).digest()
    try:
        VerifyKey(bytes.fromhex(expected_pubkey)).verify(msg, bytes.fromhex(sig))
    except (BadSignatureError, ValueError) as exc:
        raise Reject('SIGNATURE_INVALID') from exc


def exact_decimal(v: Any, name: str) -> Decimal:
    demand(isinstance(v,str) and bool(v) and all(x not in v.lower() for x in ['nan','inf']), 'BAD_DECIMAL_' + name)
    try:
        d = Decimal(v)
        demand(d.is_finite() and d >= 0, 'NEGATIVE_OR_NONFINITE_' + name)
        return d
    except (InvalidOperation, ValueError) as exc:
        raise Reject('BAD_DECIMAL_' + name) from exc


def fmt(d: Decimal) -> str:
    return format(d.quantize(Decimal('0.000000001')), 'f')


def samples_energy(sample_object: dict) -> Decimal:
    """Riemann trapezoid integration of timestamp_ms and instantaneous mW into J."""
    demand(isinstance(sample_object,dict) and sample_object.get('unit') == 'mW', 'BAD_SAMPLE_UNITS')
    samples=sample_object.get('samples')
    demand(isinstance(samples,list) and 2 <= len(samples) <= 1_000_000, 'BAD_SAMPLE_COUNT')
    total = Decimal('0')
    last = None
    for item in samples:
        demand(isinstance(item,list) and len(item)==2, 'BAD_SAMPLE_RECORD')
        t, power = item
        demand(type(t) is int and t >= 0, 'BAD_SAMPLE_TIMESTAMP')
        demand(isinstance(power,str) and power.isdigit(), 'POWER_MW_MUST_BE_INTEGER_STRING')
        p = exact_decimal(power,'POWER')
        if last is not None:
            lt,lp=last
            demand(t > lt, 'NON_MONOTONIC_SAMPLES')
            total += ((p + lp)/2) * Decimal(t-lt) / Decimal(1_000_000)
        last=(t,p)
    return total


def sample_store_hash(samples: dict) -> str:
    return blake(jcs(samples))


def parse_time(ts: str) -> datetime:
    demand(isinstance(ts,str) and ts.endswith('Z'), 'INVALID_UTC_TIME')
    try:
        out=datetime.fromisoformat(ts.replace('Z','+00:00'))
    except ValueError as exc:
        raise Reject('INVALID_UTC_TIME') from exc
    demand(out.utcoffset()==timedelta(0), 'NON_UTC_TIME')
    return out


def verify_allocation(alloc: dict, trusted_policy: dict) -> dict:
    """Rebuild constraints and expected priority allocation from independently configured policy.

    Z3 checks the provided concrete allocation and proves no violating assignment
    exists *with these fixed concrete values*. This is not a universal optimization proof.
    """
    demand(isinstance(alloc,dict), 'MISSING_ALLOCATION')
    demand(alloc.get('bounded_domain_kw') == trusted_policy.get('bounded_domain_kw'), 'POLICY_BOUND_MISMATCH')
    demand(alloc.get('available_kw') == trusted_policy.get('available_kw'), 'POLICY_CAPACITY_MISMATCH')
    demand(alloc.get('status') in ('VERIFIED','UNVERIFIED'), 'BAD_ALLOCATION_STATUS')
    lo,hi=trusted_policy['bounded_domain_kw']
    cap=trusted_policy['available_kw']
    requests=alloc.get('requests_kw'); actual=alloc.get('allocated_kw')
    demand(type(lo) is int and type(hi) is int and 0<=lo<=hi and type(cap) is int and lo<=cap<=hi, 'BAD_TRUSTED_POLICY')
    demand(isinstance(requests,list) and isinstance(actual,list) and len(requests)==len(actual)==trusted_policy['num_jobs'], 'BAD_ALLOC_LENGTH')
    demand(all(type(x) is int and 0<=x<=hi for x in requests+actual), 'BAD_ALLOC_VALUE')
    rem=cap; expected=[]
    for requested in requests:
        given=min(requested,rem)
        expected.append(given);rem-=given
    demand(actual == expected, 'PRIORITY_ALLOCATION_MISMATCH')
    variables=[Int('allocation_'+str(i)) for i in range(len(actual))]
    s=Solver()
    for idx,x in enumerate(variables):
        s.add(x==actual[idx])
    s.add(Or(*([x<lo for x in variables]+[x>hi for x in variables]+
        [x>requests[i] for i,x in enumerate(variables)]+[sum(variables)>cap]+
        [variables[i]!=expected[i] for i in range(len(actual))])))
    demand(s.check()==unsat, 'Z3_ALLOCATION_COUNTEREXAMPLE')
    proof={"method":"Z3_FIXED_ASSIGNMENT_COUNTEREXAMPLE_UNSAT_V1","policy":trusted_policy,"requests_kw":requests,"allocated_kw":actual}
    expected_constraints=sha(jcs(trusted_policy))
    expected_proof=sha(jcs(proof))
    demand(alloc.get('constraints_hash') == expected_constraints and alloc.get('proof_hash') == expected_proof, 'ALLOCATION_EVIDENCE_HASH_MISMATCH')
    return {"status":"VERIFIED_FIXED_ASSIGNMENT" if alloc['status']=='VERIFIED' else 'UNVERIFIED', "scope":"concrete bounded allocation, not universal policy proof"}


@dataclass(frozen=True)
class VerifierTrust:
    job_id: str
    job_start_ts: str
    meter_pubkey: str
    lab_pubkey: str
    expected_meter_id: str
    allocation_policy: dict
    expected_scope_hash: str | None = None
    # Physical provenance is independently investigated, not inferred from a receipt.
    physically_inspected: bool = False


def verify_epu(
    registration: dict,
    calibration: dict | None,
    execution: dict,
    allocation: dict,
    artifacts: Mapping[str,dict],
    trust: VerifierTrust,
) -> dict:
    """Reconstruct from independently provided job/meter/lab/policy/artifacts.

    An METERED *protocol classification* in test vectors never implies a real meter
    was attached. physical_verified is always an independent requirement.
    """
    verify_signature(registration, trust.meter_pubkey)
    verify_signature(execution, trust.meter_pubkey)
    demand(registration.get('protocol') == 'ITM-EPU-REGISTRATION-v1', 'BAD_REGISTRATION_PROTOCOL')
    demand(execution.get('protocol') == 'ITM-EPU-EXECUTION-v1', 'BAD_EXECUTION_PROTOCOL')
    demand(registration.get('epu_id') == trust.expected_meter_id == execution.get('epu_id'), 'METER_BINDING_MISMATCH')
    demand(registration.get('meter_class') in METERS, 'BAD_METER_CLASS')
    demand(execution.get('job_id') == trust.job_id, 'T5_JOB_REPLAY')
    win=execution.get('window') or {}
    demand(win.get('start_ts') == trust.job_start_ts, 'JOB_START_BINDING_MISMATCH')
    start=parse_time(trust.job_start_ts)
    end=parse_time(win.get('end_ts'))
    demand(end>start, 'INVALID_JOB_WINDOW')
    duration_ms=int((end-start).total_seconds()*1000)
    demand(win.get('duration_ms') == duration_ms, 'DURATION_MISMATCH')
    alloc_result=verify_allocation(allocation,trust.allocation_policy)
    method=execution.get('attribution_method');cons=execution.get('consumption') or {}
    demand(method in ATTR, 'BAD_ATTRIBUTION_METHOD')
    demand(cons.get('status') in STATES, 'CLAIMED_STATUS_FORBIDDEN')
    demand((execution.get('derivation') or {}).get('status') == 'NONE', 'DERIVATION_FORBIDDEN')
    # Self-report and util-based estimates may ONLY be NOT_MEASURED, even if a number is present.
    if method in ('ESTIMATED_FROM_UTIL','NONE') or (calibration and calibration.get('lab_accreditation') == 'SELF_REPORTED'):
        demand(cons['status']=='NOT_MEASURED' and cons.get('joules') is None, 'T1_T3_NOT_MEASURED_REQUIRED')
        return {"effective_consumption_status":"NOT_MEASURED","billing_eligible":False,"allocation":alloc_result,"cih_status":PENDING}
    demand(method in {'DEDICATED_CIRCUIT','DIFFERENTIAL','RAPL_PER_JOB'}, 'METHOD_NOT_METERED')
    demand(calibration is not None, 'CALIBRATION_REQUIRED')
    verify_signature(calibration,trust.lab_pubkey)
    demand(calibration.get('protocol')=='ITM-EPU-CALIBRATION-v1', 'BAD_CALIBRATION_PROTOCOL')
    demand(calibration.get('epu_id')==trust.expected_meter_id, 'CAL_METER_MISMATCH')
    demand(calibration.get('lab_accreditation') in ('ISO17025','NIST_TRACEABLE'), 'UNACCREDITED_CALIBRATION')
    cert_hash=sha(jcs({k:v for k,v in calibration.items() if k!='signature'}))
    demand(registration.get('calibration',{}).get('certificate_hash')==cert_hash, 'CAL_CERT_BINDING_MISMATCH')
    cal_at=parse_time(calibration.get('calibrated_at'))
    interval=calibration.get('interval_days')
    demand(type(interval) is int and 0<interval<=3650, 'BAD_CALIBRATION_INTERVAL')
    demand(cal_at<=start, 'CALIBRATED_AFTER_JOB')
    expired = cal_at+timedelta(days=interval) < start
    rh=execution.get('measurement',{}).get('raw_samples_hash')
    demand(valid_hash(rh), 'T6_RAW_HASH_MISSING')
    raw=artifacts.get(rh)
    demand(raw is not None, 'T6_RAW_SAMPLES_UNRECOVERABLE')
    demand(sample_store_hash(raw)==rh, 'T6_RAW_SAMPLES_TAMPERED')
    sample_count=len(raw['samples'])
    demand(execution.get('measurement',{}).get('sample_count')==sample_count, 'SAMPLE_COUNT_MISMATCH')
    # Require samples bound to exactly the job window; nothing outside this boundary.
    demand(raw['samples'][0][0]==0 and raw['samples'][-1][0]==duration_ms, 'SAMPLE_WINDOW_MISMATCH')
    energy=samples_energy(raw)
    if method=='DIFFERENTIAL':
        baseline=execution.get('baseline')
        demand(isinstance(baseline,dict),'T4_DIFFERENTIAL_BASELINE_REQUIRED')
        bh=baseline.get('baseline_samples_hash')
        demand(valid_hash(bh) and bh in artifacts,'T4_BASELINE_SAMPLES_UNAVAILABLE')
        baseline_samples=artifacts[bh]
        demand(sample_store_hash(baseline_samples)==bh, 'T4_BASELINE_TAMPERED')
        demand(baseline_samples['samples'][0][0]==0 and baseline_samples['samples'][-1][0]==duration_ms,'BASELINE_WINDOW_MISMATCH')
        idle=samples_energy(baseline_samples)
        demand(energy>=idle, 'BASELINE_EXCEEDS_LOAD')
        energy-=idle
        demand(exact_decimal(execution.get('uncertainty',{}).get('combined_joules_1sigma'), 'UNCERTAINTY')>0, 'DIFFERENTIAL_UNCERTAINTY_REQUIRED')
    if method=='RAPL_PER_JOB':
        demand(trust.expected_scope_hash is not None and execution.get('job_scope_hash')==trust.expected_scope_hash,'RAPL_SCOPE_NOT_VERIFIED')
    if method=='DEDICATED_CIRCUIT':
        demand(registration.get('dedicated_job_circuit') is True,'CIRCUIT_NOT_DEDICATED')
    demand(exact_decimal(execution.get('measurement',{}).get('joules_integrated'), 'JOULES')==energy,'MEASURED_JOULES_RECOMPUTE_FAILED')
    demand(cons.get('joules')==fmt(energy), 'CONSUMPTION_JOULES_MISMATCH')
    expected_state='METERED_STALE' if expired else 'METERED'
    demand(cons.get('status')==expected_state,'T2_CALIBRATION_STATE_MISMATCH')
    return {
       'effective_consumption_status':expected_state,
       'joules_integrated':fmt(energy),
       'billing_eligible':bool(trust.physically_inspected and not expired and method in ('DEDICATED_CIRCUIT','RAPL_PER_JOB')),
       'physical_ground_truth_verified':False,
       'calibration_chain_signature_valid':True,
       'calibration_authority_external_verification_required':True,
       'allocation':alloc_result,
       'cih_status':PENDING,
    }


@dataclass(frozen=True)
class ExpectedPiTau:
    """Trusted provisioning, completely outside the prover's signed payload."""
    pi: str
    next_tick: int
    verifier_nonce: str


def verify_pi_tau(receipt: dict, expected: ExpectedPiTau | None, pubkey: str, used: set[tuple[str,int]]) -> str:
    if expected is None:
        raise Reject('CONFIG_MISSING_PI_TAU')
    if receipt.get('pi')!=expected.pi:
        raise Reject('PI_CONTRACT_MISMATCH')
    if receipt.get('tau')!=expected.next_tick:
        raise Reject('TAU_CHALLENGE_MISMATCH')
    if receipt.get('nonce')!=expected.verifier_nonce:
        raise Reject('VERIFIER_CHALLENGE_MISMATCH')
    if (expected.verifier_nonce,expected.next_tick) in used:
        raise Reject('REPLAYED_CHALLENGE')
    verify_signature(receipt,pubkey)
    expected_delta=[]
    for a,b in zip(expected.pi,receipt.get('output_pi','')):
        expected_delta.append(int(a!=b))
    demand(len(expected_delta)==len(expected.pi) and receipt.get('delta')==expected_delta, 'BIT_DELTA_MISMATCH')
    used.add((expected.verifier_nonce,expected.next_tick))
    return 'VERIFIED_CONTRACT_AND_DELTA'
