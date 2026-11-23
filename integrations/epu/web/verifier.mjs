import { blake3 } from '@noble/hashes/blake3';
import { sha256 } from '@noble/hashes/sha256';
import { ed25519 } from '@noble/curves/ed25519';
import canonicalize from 'canonicalize';
const te=new TextEncoder();
const pfx=te.encode('iNNOVULIS/EPU/v1\0');
export class Rejection extends Error { constructor(code){super(code);this.code=code;} }
const assert=(truth,code)=>{if(!truth)throw new Rejection(code);};
const hex=(bytes)=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
function unhex(s){assert(typeof s==='string'&&s.length%2===0&&/^[0-9a-f]*$/.test(s),'INVALID_HEX');return Uint8Array.from(s.match(/../g)||[],x=>parseInt(x,16));}
function digest(kind, bytes) {return kind==='sha256'?'sha256:'+hex(sha256(bytes)):'blake3:'+hex(blake3(bytes));}
function canonicalBytes(v){const value=canonicalize(v);assert(typeof value==='string','BAD_JCS');return te.encode(value);}
function sigVerify(obj,expectedPk){
  assert(obj&&typeof obj==='object','RECEIPT_NOT_OBJECT');
  assert(obj.signer_pubkey===expectedPk,'UNTRUSTED_SIGNER');
  assert(typeof obj.signature==='string'&&/^[0-9a-f]{128}$/.test(obj.signature),'SIGNATURE_MALFORMED');
  const {signature,...unsigned}=obj;
  const data=new Uint8Array(32+pfx.length);data.set(pfx);data.set(blake3(canonicalBytes(unsigned)),pfx.length);
  assert(ed25519.verify(unhex(signature),data,unhex(expectedPk)),'SIGNATURE_INVALID');
}
function d9(num){return (num/1000000000n).toString()+'.'+(num%1000000000n).toString().padStart(9,'0');}
function energy(samples){
 assert(samples&&samples.unit==='mW'&&Array.isArray(samples.samples)&&samples.samples.length>=2&&samples.samples.length<=1000000,'BAD_SAMPLE_COUNT');
 let sum=0n, prior=null;
 for(const item of samples.samples){
  assert(Array.isArray(item)&&item.length===2,'BAD_SAMPLE_RECORD');
  const [ms,power]=item;
  assert(Number.isSafeInteger(ms)&&ms>=0,'BAD_SAMPLE_TIMESTAMP');
  assert(typeof power==='string'&&/^\d+$/.test(power),'POWER_MW_MUST_BE_INTEGER_STRING');
  const p=BigInt(power);
  if(prior){assert(ms>prior[0],'NON_MONOTONIC_SAMPLES');sum+=(p+prior[1])*BigInt(ms-prior[0]);}
  prior=[ms,p];
 }
 // mW*ms -> J; 1e9 scaled J = sum*500 because 1J=1e6 mW*ms, trapezoid factor 2.
 return sum*500n;
}
function shaJcs(v){return digest('sha256',canonicalBytes(v));}
function blakeJcs(v){return digest('blake3',canonicalBytes(v));}
function isoMs(s){assert(typeof s==='string'&&s.endsWith('Z')&&!Number.isNaN(Date.parse(s)),'INVALID_UTC_TIME');return Date.parse(s);}
export function verify(bundle, trust){
  assert(trust&&typeof trust==='object'&&trust.job_id&&trust.job_start_ts&&trust.meter_pubkey&&trust.lab_pubkey&&trust.allocation_policy,'CONFIG_MISSING');
  const {registration:r,calibration:c,execution:e,allocation:a,artifacts}=bundle||{};
  sigVerify(r,trust.meter_pubkey);sigVerify(e,trust.meter_pubkey);
  assert(r.protocol==='ITM-EPU-REGISTRATION-v1','BAD_REGISTRATION_PROTOCOL');
  assert(e.protocol==='ITM-EPU-EXECUTION-v1','BAD_EXECUTION_PROTOCOL');
  assert(r.epu_id===trust.expected_meter_id&&e.epu_id===trust.expected_meter_id,'METER_BINDING_MISMATCH');
  assert(['WALL_PDU','SMART_PDU','RAPL_PER_CORE','RAPL_PKG','ON_DIE_SENSOR','SBC_PMIC'].includes(r.meter_class),'BAD_METER_CLASS');
  assert(e.job_id===trust.job_id,'T5_JOB_REPLAY');
  const win=e.window||{};
  assert(win.start_ts===trust.job_start_ts,'JOB_START_BINDING_MISMATCH');
  const start=isoMs(trust.job_start_ts),end=isoMs(win.end_ts);
  assert(end>start,'INVALID_JOB_WINDOW');
  assert(win.duration_ms===end-start,'DURATION_MISMATCH');
  const policy=trust.allocation_policy;
  assert(a&&JSON.stringify(a.bounded_domain_kw)===JSON.stringify(policy.bounded_domain_kw),'POLICY_BOUND_MISMATCH');
  assert(a.available_kw===policy.available_kw,'POLICY_CAPACITY_MISMATCH');
  assert(['VERIFIED','UNVERIFIED'].includes(a.status),'BAD_ALLOCATION_STATUS');
  const [lo,hi]=policy.bounded_domain_kw;
  assert(Number.isSafeInteger(lo)&&Number.isSafeInteger(hi)&&lo>=0&&lo<=hi&&policy.available_kw<=hi,'BAD_TRUSTED_POLICY');
  assert(Array.isArray(a.requests_kw)&&Array.isArray(a.allocated_kw)&&a.requests_kw.length===policy.num_jobs&&a.allocated_kw.length===policy.num_jobs,'BAD_ALLOC_LENGTH');
  assert([...a.requests_kw,...a.allocated_kw].every(v=>Number.isSafeInteger(v)&&v>=0&&v<=hi),'BAD_ALLOC_VALUE');
  let cap=policy.available_kw;const expected=a.requests_kw.map(x=>{const take=Math.min(x,cap);cap-=take;return take;});
  assert(JSON.stringify(a.allocated_kw)===JSON.stringify(expected),'PRIORITY_ALLOCATION_MISMATCH');
  const proof={method:'Z3_FIXED_ASSIGNMENT_COUNTEREXAMPLE_UNSAT_V1',policy,requests_kw:a.requests_kw,allocated_kw:a.allocated_kw};
  assert(a.constraints_hash===shaJcs(policy)&&a.proof_hash===shaJcs(proof),'ALLOCATION_EVIDENCE_HASH_MISMATCH');
  // Python additionally runs actual Z3 fixed-assignment proof. JS independently checks same deterministic allocation, not Z3.
  const method=e.attribution_method, cons=e.consumption||{};
  assert(['DEDICATED_CIRCUIT','DIFFERENTIAL','RAPL_PER_JOB','ESTIMATED_FROM_UTIL','NONE'].includes(method),'BAD_ATTRIBUTION_METHOD');
  assert(['METERED','METERED_STALE','NOT_MEASURED'].includes(cons.status),'CLAIMED_STATUS_FORBIDDEN');
  assert(e.derivation&&e.derivation.status==='NONE','DERIVATION_FORBIDDEN');
  if(['ESTIMATED_FROM_UTIL','NONE'].includes(method)||(c&&c.lab_accreditation==='SELF_REPORTED')){
   assert(cons.status==='NOT_MEASURED'&&cons.joules===null,'T1_T3_NOT_MEASURED_REQUIRED');
   return {effective_consumption_status:'NOT_MEASURED',billing_eligible:false,cih_status:'PENDING PROOF OF PROCESS — CIH VERIFICATION'};
  }
  assert(['DEDICATED_CIRCUIT','DIFFERENTIAL','RAPL_PER_JOB'].includes(method),'METHOD_NOT_METERED');
  assert(!!c,'CALIBRATION_REQUIRED');sigVerify(c,trust.lab_pubkey);
  assert(c.protocol==='ITM-EPU-CALIBRATION-v1','BAD_CALIBRATION_PROTOCOL');
  assert(c.epu_id===trust.expected_meter_id,'CAL_METER_MISMATCH');
  assert(['ISO17025','NIST_TRACEABLE'].includes(c.lab_accreditation),'UNACCREDITED_CALIBRATION');
  const {signature,...unsignedCert}=c;
  assert(r.calibration&&r.calibration.certificate_hash===shaJcs(unsignedCert),'CAL_CERT_BINDING_MISMATCH');
  const calAt=isoMs(c.calibrated_at);
  assert(Number.isSafeInteger(c.interval_days)&&c.interval_days>0&&c.interval_days<=3650,'BAD_CALIBRATION_INTERVAL');
  assert(calAt<=start,'CALIBRATED_AFTER_JOB');
  const expired=calAt+c.interval_days*86400000<start;
  const rh=e.measurement?.raw_samples_hash;
  assert(typeof rh==='string'&&/^blake3:[0-9a-f]{64}$/.test(rh),'T6_RAW_HASH_MISSING');
  assert(artifacts&&Object.hasOwn(artifacts,rh),'T6_RAW_SAMPLES_UNRECOVERABLE');
  const raw=artifacts[rh];assert(blakeJcs(raw)===rh,'T6_RAW_SAMPLES_TAMPERED');
  assert(e.measurement.sample_count===raw.samples.length,'SAMPLE_COUNT_MISMATCH');
  assert(raw.samples[0][0]===0&&raw.samples.at(-1)[0]===end-start,'SAMPLE_WINDOW_MISMATCH');
  let nJ=energy(raw);
  if(method==='DIFFERENTIAL'){
   const b=e.baseline;assert(b&&typeof b==='object','T4_DIFFERENTIAL_BASELINE_REQUIRED');
   const bh=b.baseline_samples_hash;
   assert(typeof bh==='string'&&Object.hasOwn(artifacts,bh),'T4_BASELINE_SAMPLES_UNAVAILABLE');
   assert(blakeJcs(artifacts[bh])===bh,'T4_BASELINE_TAMPERED');
   const idle=artifacts[bh];assert(idle.samples[0][0]===0&&idle.samples.at(-1)[0]===end-start,'BASELINE_WINDOW_MISMATCH');
   const idleJ=energy(idle);assert(nJ>=idleJ,'BASELINE_EXCEEDS_LOAD');nJ-=idleJ;
   assert(typeof e.uncertainty?.combined_joules_1sigma==='string'&&Number(e.uncertainty.combined_joules_1sigma)>0,'DIFFERENTIAL_UNCERTAINTY_REQUIRED');
  }
  if(method==='RAPL_PER_JOB')assert(!!trust.expected_scope_hash&&e.job_scope_hash===trust.expected_scope_hash,'RAPL_SCOPE_NOT_VERIFIED');
  if(method==='DEDICATED_CIRCUIT')assert(r.dedicated_job_circuit===true,'CIRCUIT_NOT_DEDICATED');
  assert(e.measurement.joules_integrated===d9(nJ),'MEASURED_JOULES_RECOMPUTE_FAILED');
  assert(cons.joules===d9(nJ),'CONSUMPTION_JOULES_MISMATCH');
  const status=expired?'METERED_STALE':'METERED';
  assert(cons.status===status,'T2_CALIBRATION_STATE_MISMATCH');
  return {effective_consumption_status:status,joules_integrated:d9(nJ),billing_eligible:false,
   physical_ground_truth_verified:false,cih_status:'PENDING PROOF OF PROCESS — CIH VERIFICATION',
   note:'Software-only: physical meter, accreditation authority and ground truth NOT independently validated'};
}
