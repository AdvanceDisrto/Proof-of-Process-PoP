use base64::{engine::general_purpose::STANDARD as B64, Engine};
use ed25519_dalek::{Signer, SigningKey};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{env, fs, path::{Path, PathBuf}, process::Command};
use walkdir::WalkDir;

const DOMAIN_LEAF: &[u8] = b"iComp-v1:leaf\0";
const DOMAIN_NODE: &[u8] = b"iComp-v1:node\0";
const DOMAIN_ROOT: &[u8] = b"iComp-v1:root\0";

#[derive(Debug)]
enum CompileState { Verified, Quarantined(String) }

#[derive(Debug, Serialize)]
struct Anchor { status: String, chain: Option<String>, reference: Option<String> }

#[derive(Debug, Serialize)]
struct ProvenanceReceipt {
    artifact_type: String,
    compiler_version: String,
    source_merkle_root: String,
    binary_sha256: String,
    sentinel_scan: String,
    signature: String,
    timestamp: String,
    anchor: Anchor,
    state: String,
}

#[derive(Debug, Serialize)]
struct ICompArtifact {
    artifact_type: String,
    target_architecture: String,
    source_merkle_root: String,
    binary_sha256: String,
    sentinel_scan: String,
    compiler_version: String,
    provenance_receipt: ProvenanceReceipt,
}

struct IComp { source: PathBuf, canonical_root: String, signing_key: SigningKey, target: String }

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(data);
    h.finalize().into()
}

fn hex32(v: [u8; 32]) -> String { hex::encode(v) }

fn merkle_root(source: &Path) -> Result<String, String> {
    let mut leaves = Vec::new();
    for entry in WalkDir::new(source).follow_links(false) {
        let entry = entry.map_err(|e| format!("walk error: {e}"))?;
        if !entry.file_type().is_file() { continue; }
        let rel = entry.path().strip_prefix(source).map_err(|e| e.to_string())?;
        let rel = rel.to_string_lossy().replace('\\', "/");
        let content = fs::read(entry.path()).map_err(|e| format!("read error {rel}: {e}"))?;
        let file_digest = sha256(&content);
        let mut leaf = Vec::new();
        leaf.extend_from_slice(DOMAIN_LEAF);
        leaf.extend_from_slice(rel.as_bytes());
        leaf.push(0);
        leaf.extend_from_slice(&file_digest);
        leaves.push(sha256(&leaf));
    }
    if leaves.is_empty() { return Err("QUARANTINED: source tree is empty".into()); }
    leaves.sort();
    while leaves.len() > 1 {
        let mut next = Vec::with_capacity((leaves.len() + 1) / 2);
        let mut i = 0;
        while i < leaves.len() {
            let right = if i + 1 < leaves.len() { leaves[i + 1] } else { leaves[i] };
            let mut node = Vec::new();
            node.extend_from_slice(DOMAIN_NODE);
            node.extend_from_slice(&leaves[i]);
            node.extend_from_slice(&right);
            next.push(sha256(&node));
            i += 2;
        }
        leaves = next;
    }
    let mut root = Vec::new();
    root.extend_from_slice(DOMAIN_ROOT);
    root.extend_from_slice(&leaves[0]);
    Ok(hex32(sha256(&root)))
}

fn sentinel_scan(source: &Path) -> Result<(), String> {
    let banned = ["MOCK-TEE", "unsafe_tee", "signatureVerified: true", "signature_verified: true"];
    let env_patterns = ["process.env.", "std::env::var(", "os.environ", "getenv("];
    for entry in WalkDir::new(source).follow_links(false) {
        let entry = entry.map_err(|e| format!("walk error: {e}"))?;
        if !entry.file_type().is_file() { continue; }
        let path = entry.path();
        let text = match fs::read_to_string(path) { Ok(v) => v, Err(_) => continue };
        let rel = path.strip_prefix(source).unwrap_or(path).display();
        for pattern in banned {
            if text.contains(pattern) {
                return Err(format!("QUARANTINED: Sentinel violation in {rel}: {pattern}"));
            }
        }
        for pattern in env_patterns {
            if text.contains(pattern) {
                return Err(format!("QUARANTINED: unsealed environment access in {rel}: {pattern}"));
            }
        }
        let lower = text.to_ascii_lowercase();
        if lower.contains("// mock") || lower.contains("# mock") {
            return Err(format!("QUARANTINED: hardcoded mock marker in {rel}"));
        }
    }
    Ok(())
}

fn run(program: &str, args: &[String]) -> Result<(), String> {
    let out = Command::new(program).args(args).output()
        .map_err(|e| format!("{program}: {e}"))?;
    if out.status.success() {
        Ok(())
    } else {
        Err(format!("{program} failed: {}", String::from_utf8_lossy(&out.stderr).trim()))
    }
}

fn compile_source(source: &Path, target: &str, out: &Path) -> Result<(), String> {
    let files: Vec<PathBuf> = WalkDir::new(source)
        .follow_links(false)
        .into_iter()
        .filter_map(Result::ok)
        .map(|e| e.into_path())
        .filter(|p| p.is_file())
        .collect();

    if let Some(rust) = files.iter().find(|p| p.extension().and_then(|x| x.to_str()) == Some("rs")) {
        let mut args = vec![rust.display().to_string(), "-O".into(), "-o".into(), out.display().to_string()];
        if target != "host" {
            args.push("--target".into());
            args.push(target.into());
        }
        return run("rustc", &args);
    }
    if let Some(cpp) = files.iter().find(|p| p.extension().and_then(|x| x.to_str()) == Some("cpp")) {
        return run("g++", &[
            cpp.display().to_string(), "-std=c++20".into(), "-O2".into(),
            "-o".into(), out.display().to_string()
        ]);
    }
    if files.iter().any(|p| p.extension().and_then(|x| x.to_str()) == Some("py")) {
        return Err("QUARANTINED: Python codegen adapter requires an explicit output packaging backend".into());
    }
    if files.iter().any(|p| p.extension().and_then(|x| x.to_str()) == Some("ts")) {
        return Err("QUARANTINED: TypeScript codegen adapter requires an explicit project output backend".into());
    }
    if files.iter().any(|p| p.extension().and_then(|x| x.to_str()) == Some("sol")) {
        return Err("QUARANTINED: Solidity codegen adapter requires solc output-path policy".into());
    }
    Err("QUARANTINED: no supported source language detected".into())
}

impl IComp {
    fn execute(&self, out: &Path) -> Result<ICompArtifact, CompileState> {
        let root = merkle_root(&self.source).map_err(CompileState::Quarantined)?;
        let expected = self.canonical_root.trim_start_matches("0x").to_ascii_lowercase();
        if expected.len() != 64 || !expected.chars().all(|c| c.is_ascii_hexdigit()) || root != expected {
            return Err(CompileState::Quarantined(format!(
                "1:1 Mismatch. Expected {}, Found {}", expected, root
            )));
        }
        sentinel_scan(&self.source).map_err(CompileState::Quarantined)?;
        if let Some(parent) = out.parent() {
            fs::create_dir_all(parent).map_err(|e| CompileState::Quarantined(e.to_string()))?;
        }
        compile_source(&self.source, &self.target, out).map_err(CompileState::Quarantined)?;
        let binary = fs::read(out)
            .map_err(|e| CompileState::Quarantined(format!("output read error: {e}")))?;
        let binary_hash = hex32(sha256(&binary));
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs().to_string())
            .unwrap_or_else(|_| "0".into());
        let payload = format!("iComp-v1|{}|{}|{}", root, binary_hash, self.target);
        let sig = self.signing_key.sign(payload.as_bytes());

        let receipt = ProvenanceReceipt {
            artifact_type: "iComp_CompilationProvenanceReceipt".into(),
            compiler_version: "iComp-v1.0.0".into(),
            source_merkle_root: root,
            binary_sha256: binary_hash,
            sentinel_scan: "PASSED_ZERO_VIOLATIONS".into(),
            signature: format!("ed25519:{}", B64.encode(sig.to_bytes())),
            timestamp,
            anchor: Anchor { status: "absent".into(), chain: None, reference: None },
            state: "ACTION_REQUIRED".into(),
        };

        Ok(ICompArtifact {
            artifact_type: "iComp_Binary_Bundle".into(),
            target_architecture: self.target.clone(),
            source_merkle_root: receipt.source_merkle_root.clone(),
            binary_sha256: receipt.binary_sha256.clone(),
            sentinel_scan: receipt.sentinel_scan.clone(),
            compiler_version: receipt.compiler_version.clone(),
            provenance_receipt: receipt,
        })
    }
}

fn usage() -> ! {
    eprintln!("usage: icomp build --source DIR --root SHA256 --out FILE --target TARGET --signing-key-hex HEX");
    std::process::exit(2)
}

fn main() {
    let a: Vec<String> = env::args().collect();
    if a.len() < 12 || a[1] != "build" { usage(); }
    let get = |name: &str| -> String {
        a.windows(2).find(|w| w[0] == name).map(|w| w[1].clone()).unwrap_or_else(|| usage())
    };
    let source = PathBuf::from(get("--source"));
    let root = get("--root");
    let out = PathBuf::from(get("--out"));
    let target = get("--target");
    let key_hex = get("--signing-key-hex");
    let key_bytes = match hex::decode(key_hex) {
        Ok(v) if v.len() == 32 => {
            let mut x = [0u8; 32];
            x.copy_from_slice(&v);
            x
        }
        _ => {
            eprintln!("QUARANTINED: signing key must be exactly 32 bytes of hex");
            std::process::exit(1)
        }
    };
    let compiler = IComp { source, canonical_root: root, signing_key: SigningKey::from_bytes(&key_bytes), target };
    match compiler.execute(&out) {
        Ok(artifact) => {
            let receipt_path = out.with_extension("icomp");
            fs::write(&receipt_path, serde_json::to_vec_pretty(&artifact).unwrap()).unwrap();
            println!("iComp: VERIFIED source + sentinel + codegen + signed receipt");
            println!("artifact: {}", receipt_path.display());
        }
        Err(CompileState::Quarantined(reason)) => {
            eprintln!("iComp: QUARANTINED — {reason}");
            std::process::exit(1);
        }
        Err(CompileState::Verified) => unreachable!(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, time::{SystemTime, UNIX_EPOCH}};

    fn temp_dir(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!("icomp-{name}-{}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()))
    }

    #[test]
    fn merkle_root_is_path_bound_and_deterministic() {
        let d = temp_dir("merkle");
        fs::create_dir_all(&d).unwrap();
        fs::write(d.join("a.txt"), b"A").unwrap();
        let r1 = merkle_root(&d).unwrap();
        let r2 = merkle_root(&d).unwrap();
        assert_eq!(r1, r2);
        fs::write(d.join("b.txt"), b"A").unwrap();
        assert_ne!(r1, merkle_root(&d).unwrap());
        fs::remove_dir_all(d).unwrap();
    }

    #[test]
    fn sentinel_fails_closed_on_mock_and_unsealed_env() {
        let d = temp_dir("sentinel");
        fs::create_dir_all(&d).unwrap();
        fs::write(d.join("bad.rs"), b"fn main(){ let x = std::env::var(\"SECRET\"); } // mock").unwrap();
        assert!(sentinel_scan(&d).is_err());
        fs::remove_dir_all(d).unwrap();
    }
}
