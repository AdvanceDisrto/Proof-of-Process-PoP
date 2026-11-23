use ed25519_dalek::SigningKey;
use innovulis_ici::*;
use rand::rngs::OsRng;
use std::{env,fs,path::Path};

fn self_test() -> Result<(),Box<dyn std::error::Error>> {
    let mut engine=IciEngine::new(SigningKey::generate(&mut OsRng));
    let trusted=engine.verifying_key;
    let (iraw,r1)=engine.seal_iraw_frame("iGFX_DEMO",1_000_042,&vec![0xa5;8192],&vec![0x3c;2048])?;
    verify_iraw_frame(&iraw,&trusted)?;
    assert!(verify_attached_artifact(&r1,&iraw));
    let mut corrupted=iraw.clone(); corrupted[IRAW_HEADER_LEN]^=0xff;
    assert!(verify_iraw_frame(&corrupted,&trusted).is_err());
    let igxp=build_igxp(1_000_070,b"iGXP test execution envelope")?;
    let r2=engine.verify_and_attest_igxp(&igxp)?;
    let isc=build_isc(1,1_000_099,b"iSC verified storage page")?;
    let r3=engine.verify_and_attest_isc(&isc)?;
    let receipts=vec![r1,r2,r3];
    verify_chain(&receipts,&trusted)?;
    fs::create_dir_all("build_ici")?;
    fs::write("build_ici/DSC_0001.iraw",&iraw)?;
    fs::write("build_ici/igxp_0001.bin",&igxp)?;
    fs::write("build_ici/isc_0001.bin",&isc)?;
    fs::write("build_ici/ici_attestation_chain.json",serde_json::to_vec_pretty(&receipts)?)?;
    fs::write("build_ici/trusted_pubkey.hex",hex::encode(trusted.to_bytes()))?;
    println!("PASS iRAW verified; modified sensor pixel rejected");
    println!("PASS iGXP 4096 execution envelope");
    println!("PASS iSC 4160-byte storage container");
    println!("PASS 3-artifact signed sequential chain");
    println!("RECEIPT STATUS: {}",PENDING);
    Ok(())
}
fn run() -> Result<(),Box<dyn std::error::Error>> {
    let a:Vec<String>=env::args().collect();
    match a.get(1).map(|s|s.as_str()) {
        Some("verify-iraw") if a.len()==4 => {
            verify_iraw_frame(&fs::read(&a[2])?,&public_key_from_hex(&a[3])?)?;
            println!("PASS iRAW cryptographic integrity (not physical-origin proof)");
        }
        Some("verify-igxp") if a.len()==3 => {
            verify_igxp(&fs::read(&a[2])?)?;
            println!("PASS iGXP structural integrity (not hardware attestation)");
        }
        Some("verify-isc") if a.len()==3 => {
            verify_isc(&fs::read(&a[2])?)?;
            println!("PASS iSC structural integrity (not hardware attestation)");
        }
        Some("verify-chain") if a.len()==4 => {
            let receipts:Vec<IciReceipt>=serde_json::from_slice(&fs::read(&a[2])?)?;
            verify_chain(&receipts,&public_key_from_hex(&a[3])?)?;
            println!("PASS externally-keyed receipt chain; artifact bytes require separate matching");
        }
        None | Some("self-test") if a.len()<=2 => self_test()?,
        _ => return Err("usage: innovulis_ici [self-test | verify-iraw FILE TRUSTED_PUBKEY_HEX | verify-igxp FILE | verify-isc FILE | verify-chain RECEIPTS_JSON TRUSTED_PUBKEY_HEX]".into())
    }
    Ok(())
}
fn main() {
    if let Err(e)=run(){eprintln!("iCi ERROR: {e}");std::process::exit(1);}
}
