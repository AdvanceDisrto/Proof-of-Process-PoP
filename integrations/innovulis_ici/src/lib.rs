use blake3::Hasher;
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};

pub const IRAW_MAGIC: &[u8; 8] = b"iRAW_v01";
pub const ISC_MAGIC: &[u8; 8] = b"iSC_CNT1";
pub const IGXP_MAGIC: &[u8; 8] = b"iGXP4096";
pub const PENDING: &str = "PENDING PROOF OF PROCESS — CIH VERIFICATION";
pub const IRAW_HEADER_LEN: usize = 208;
pub const ISC_SIZE: usize = 4160;
pub const IGXP_SIZE: usize = 4096;
const MAX_IRAW_TRACK: usize = 512 * 1024 * 1024;
const GENESIS: &[u8] = b"iNNOVULIS/iCi/genesis/v1";

fn h(bytes: &[u8]) -> [u8; 32] { *blake3::hash(bytes).as_bytes() }
pub fn genesis() -> [u8; 32] { h(GENESIS) }
fn arr32(src: &[u8]) -> Result<[u8;32],String> {
    src.try_into().map_err(|_| "expected exactly 32 bytes".to_string())
}
fn decoded32(s: &str) -> Result<[u8;32],String> {
    arr32(&hex::decode(s).map_err(|_| "invalid hex".to_string())?)
}
pub fn public_key_from_hex(s: &str) -> Result<VerifyingKey,String> {
    VerifyingKey::from_bytes(&decoded32(s)?).map_err(|_| "invalid trusted public key".to_string())
}
fn transition(prev: &[u8;32], seq: u64, tick: u64, kind: &str, digest: &[u8;32]) -> [u8;32] {
    let mut b = Hasher::new();
    b.update(b"iCi/chain/v1\0");
    b.update(prev);
    b.update(&seq.to_le_bytes());
    b.update(&tick.to_le_bytes());
    b.update(&(kind.len() as u32).to_le_bytes());
    b.update(kind.as_bytes());
    b.update(digest);
    *b.finalize().as_bytes()
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct IciReceipt {
    pub artifact_type: String,
    pub sequence_id: u64,
    pub chronos_tick: u64,
    pub artifact_digest_hex: String,
    pub prev_ici_chain_root_hex: String,
    pub new_ici_chain_root_hex: String,
    pub signer_pubkey_hex: String,
    pub signature_hex: String,
    pub cih_verification: String,
}
fn receipt_bytes(r: &IciReceipt) -> Vec<u8> {
    let mut b = Vec::new();
    b.extend_from_slice(b"iCi/receipt/v1\0");
    b.extend_from_slice(&(r.artifact_type.len() as u32).to_le_bytes());
    b.extend_from_slice(r.artifact_type.as_bytes());
    b.extend_from_slice(&r.sequence_id.to_le_bytes());
    b.extend_from_slice(&r.chronos_tick.to_le_bytes());
    for x in [&r.artifact_digest_hex,&r.prev_ici_chain_root_hex,
              &r.new_ici_chain_root_hex,&r.signer_pubkey_hex] {
        // Strings are canonical lowercase hex, checked before acceptance.
        b.extend_from_slice(x.as_bytes());
    }
    b.extend_from_slice(r.cih_verification.as_bytes());
    b
}
pub struct IciEngine {
    signing_key: SigningKey,
    pub verifying_key: VerifyingKey,
    pub sequence_counter: u64,
    pub chain_root: [u8;32],
}
impl IciEngine {
    pub fn new(signing_key: SigningKey) -> Self {
        let verifying_key = signing_key.verifying_key();
        Self { signing_key, verifying_key, sequence_counter: 0, chain_root: genesis() }
    }
    pub fn attest_artifact(&mut self, kind: &str, tick: u64, artifact: &[u8]) -> Result<IciReceipt,String> {
        if kind.is_empty() || kind.len()>128 || !kind.is_ascii() { return Err("invalid artifact type".into()); }
        let seq = self.sequence_counter.checked_add(1).ok_or("sequence overflow")?;
        let digest = h(artifact);
        let prev = self.chain_root;
        let next = transition(&prev,seq,tick,kind,&digest);
        let mut r = IciReceipt {
            artifact_type:kind.into(), sequence_id:seq, chronos_tick:tick,
            artifact_digest_hex:hex::encode(digest),
            prev_ici_chain_root_hex:hex::encode(prev),
            new_ici_chain_root_hex:hex::encode(next),
            signer_pubkey_hex:hex::encode(self.verifying_key.to_bytes()),
            signature_hex:String::new(), cih_verification:PENDING.into()
        };
        r.signature_hex=hex::encode(self.signing_key.sign(&receipt_bytes(&r)).to_bytes());
        self.sequence_counter=seq;
        self.chain_root=next;
        Ok(r)
    }
    pub fn seal_iraw_frame(&mut self, model: &str, tick: u64, raw: &[u8], npu: &[u8])
        -> Result<(Vec<u8>, IciReceipt),String> {
        if model.len()>16 || !model.is_ascii() || raw.len()>MAX_IRAW_TRACK || npu.len()>MAX_IRAW_TRACK {
            return Err("iRAW model or track size invalid".into());
        }
        let mut header=Vec::with_capacity(IRAW_HEADER_LEN);
        header.extend_from_slice(IRAW_MAGIC);
        let mut fixed=[0u8;16]; fixed[..model.len()].copy_from_slice(model.as_bytes());
        header.extend_from_slice(&fixed);
        header.extend_from_slice(&tick.to_le_bytes());
        header.extend_from_slice(&(raw.len() as u64).to_le_bytes());
        header.extend_from_slice(&(npu.len() as u64).to_le_bytes());
        header.extend_from_slice(&h(raw));
        header.extend_from_slice(&h(npu));
        header.extend_from_slice(&self.verifying_key.to_bytes());
        let header_digest=h(&[b"iCi/iRAW/header/v1\0".as_slice(),&header].concat());
        header.extend_from_slice(&self.signing_key.sign(&header_digest).to_bytes());
        debug_assert_eq!(header.len(),IRAW_HEADER_LEN);
        let mut out=header;
        out.extend_from_slice(raw); out.extend_from_slice(npu);
        let r=self.attest_artifact("iGFX_iRAW_FRAME",tick,&out)?;
        Ok((out,r))
    }
    pub fn verify_and_attest_igxp(&mut self, envelope: &[u8]) -> Result<IciReceipt,String> {
        let tick=verify_igxp(envelope)?;
        self.attest_artifact("iGXP_4096_ENVELOPE",tick,envelope)
    }
    pub fn verify_and_attest_isc(&mut self, container: &[u8]) -> Result<IciReceipt,String> {
        let tick=verify_isc(container)?;
        self.attest_artifact("iSC_CONTAINER_4160B",tick,container)
    }
}
pub fn verify_iraw_frame(blob: &[u8], trusted: &VerifyingKey) -> Result<(),String> {
    if blob.len()<IRAW_HEADER_LEN || &blob[..8]!=IRAW_MAGIC { return Err("invalid iRAW header".into()); }
    let raw_len=u64::from_le_bytes(blob[32..40].try_into().unwrap());
    let npu_len=u64::from_le_bytes(blob[40..48].try_into().unwrap());
    if raw_len>MAX_IRAW_TRACK as u64 || npu_len>MAX_IRAW_TRACK as u64 { return Err("iRAW track limit".into()); }
    let raw_len=usize::try_from(raw_len).map_err(|_| "length overflow")?;
    let npu_len=usize::try_from(npu_len).map_err(|_| "length overflow")?;
    let end=IRAW_HEADER_LEN.checked_add(raw_len).and_then(|n| n.checked_add(npu_len)).ok_or("length overflow")?;
    if blob.len()!=end {return Err("iRAW length mismatch".into());}
    if blob[112..144]!=trusted.to_bytes() {return Err("untrusted iRAW signing key".into());}
    let sensor_end=IRAW_HEADER_LEN+raw_len;
    if h(&blob[IRAW_HEADER_LEN..sensor_end])!=blob[48..80] {return Err("iRAW sensor digest mismatch".into());}
    if h(&blob[sensor_end..end])!=blob[80..112] {return Err("iRAW NPU digest mismatch".into());}
    let sig=Signature::from_slice(&blob[144..208]).map_err(|_| "invalid iRAW signature")?;
    let digest=h(&[b"iCi/iRAW/header/v1\0".as_slice(),&blob[..144]].concat());
    trusted.verify(&digest,&sig).map_err(|_| "iRAW signature invalid".into())
}
pub fn build_igxp(tick: u64, payload: &[u8]) -> Result<Vec<u8>,String> {
    if payload.len()>IGXP_SIZE-56 {return Err("iGXP payload too large".into());}
    let mut b=vec![0u8;IGXP_SIZE];
    b[..8].copy_from_slice(IGXP_MAGIC);
    b[8..16].copy_from_slice(&tick.to_le_bytes());
    b[16..20].copy_from_slice(&(payload.len() as u32).to_le_bytes());
    b[20..24].copy_from_slice(&1u32.to_le_bytes());
    b[24..56].copy_from_slice(&h(payload));
    b[56..56+payload.len()].copy_from_slice(payload);
    Ok(b)
}
pub fn verify_igxp(b: &[u8]) -> Result<u64,String> {
    if b.len()!=IGXP_SIZE || &b[..8]!=IGXP_MAGIC {return Err("invalid iGXP envelope".into());}
    if u32::from_le_bytes(b[20..24].try_into().unwrap())!=1 {return Err("unsupported iGXP version".into());}
    let n=u32::from_le_bytes(b[16..20].try_into().unwrap()) as usize;
    if n>IGXP_SIZE-56 {return Err("iGXP length invalid".into());}
    if h(&b[56..56+n])!=b[24..56] || b[56+n..].iter().any(|v|*v!=0) {
        return Err("iGXP digest or padding invalid".into());
    }
    Ok(u64::from_le_bytes(b[8..16].try_into().unwrap()))
}
pub fn build_isc(seq: u64, tick: u64, payload: &[u8]) -> Result<Vec<u8>,String> {
    if payload.len()>4096 {return Err("iSC payload too large".into());}
    let mut b=vec![0u8;ISC_SIZE];
    b[..8].copy_from_slice(ISC_MAGIC);
    b[8..16].copy_from_slice(&seq.to_le_bytes());
    b[16..24].copy_from_slice(&tick.to_le_bytes());
    b[24..28].copy_from_slice(&(payload.len() as u32).to_le_bytes());
    b[28..32].copy_from_slice(&1u32.to_le_bytes());
    b[32..64].copy_from_slice(&h(payload));
    b[64..64+payload.len()].copy_from_slice(payload);
    Ok(b)
}
pub fn verify_isc(b: &[u8]) -> Result<u64,String> {
    if b.len()!=ISC_SIZE || &b[..8]!=ISC_MAGIC {return Err("invalid iSC container".into());}
    if u32::from_le_bytes(b[28..32].try_into().unwrap())!=1 {return Err("unsupported iSC version".into());}
    let n=u32::from_le_bytes(b[24..28].try_into().unwrap()) as usize;
    if n>4096 {return Err("iSC length invalid".into());}
    if h(&b[64..64+n])!=b[32..64] || b[64+n..].iter().any(|v|*v!=0) {
        return Err("iSC digest or padding invalid".into());
    }
    Ok(u64::from_le_bytes(b[16..24].try_into().unwrap()))
}
pub fn verify_attached_artifact(r: &IciReceipt, bytes: &[u8]) -> bool {
    decoded32(&r.artifact_digest_hex).map(|d|d==h(bytes)).unwrap_or(false)
}
pub fn verify_chain(receipts: &[IciReceipt], trusted: &VerifyingKey) -> Result<[u8;32],String> {
    let mut prev=genesis();
    for (i,r) in receipts.iter().enumerate() {
        let seq=u64::try_from(i+1).map_err(|_|"sequence overflow")?;
        if r.sequence_id!=seq || r.artifact_type.is_empty() || r.artifact_type.len()>128
            || !r.artifact_type.is_ascii() || r.cih_verification!=PENDING {
            return Err("chain sequence/type/status invalid".into());
        }
        let digest=decoded32(&r.artifact_digest_hex)?;
        let old=decoded32(&r.prev_ici_chain_root_hex)?;
        let root=decoded32(&r.new_ici_chain_root_hex)?;
        let pk=decoded32(&r.signer_pubkey_hex)?;
        if old!=prev || pk!=trusted.to_bytes() {return Err("chain anchor or signer mismatch".into());}
        if transition(&prev,seq,r.chronos_tick,&r.artifact_type,&digest)!=root {
            return Err("chain transition invalid".into());
        }
        // Refuse non-canonical encodings; otherwise different text can represent identical bytes.
        if r.artifact_digest_hex!=hex::encode(digest) ||
            r.prev_ici_chain_root_hex!=hex::encode(old) ||
            r.new_ici_chain_root_hex!=hex::encode(root) ||
            r.signer_pubkey_hex!=hex::encode(pk) {return Err("noncanonical hex".into());}
        let sig=Signature::from_slice(&hex::decode(&r.signature_hex).map_err(|_|"invalid signature hex")?)
            .map_err(|_|"invalid signature bytes")?;
        trusted.verify(&receipt_bytes(r),&sig).map_err(|_|"receipt signature invalid")?;
        prev=root;
    }
    if receipts.is_empty() {return Err("empty ledger".into());}
    Ok(prev)
}
