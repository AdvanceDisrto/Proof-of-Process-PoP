use ed25519_dalek::SigningKey;
use innovulis_ici::*;
fn engine() -> IciEngine {IciEngine::new(SigningKey::from_bytes(&[0x42;32]))}
#[test] fn iraw_roundtrip(){let mut e=engine();let (b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();verify_iraw_frame(&b,&e.verifying_key).unwrap();}
#[test] fn iraw_sensor_tamper(){let mut e=engine();let (mut b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();b[208]^=1;assert!(verify_iraw_frame(&b,&e.verifying_key).is_err());}
#[test] fn iraw_npu_tamper(){let mut e=engine();let (mut b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();b[211]^=1;assert!(verify_iraw_frame(&b,&e.verifying_key).is_err());}
#[test] fn iraw_header_tamper(){let mut e=engine();let (mut b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();b[25]^=1;assert!(verify_iraw_frame(&b,&e.verifying_key).is_err());}
#[test] fn iraw_wrong_key(){let mut e=engine();let (b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();let other=IciEngine::new(SigningKey::from_bytes(&[0x43;32]));assert!(verify_iraw_frame(&b,&other.verifying_key).is_err());}
#[test] fn iraw_truncated_and_oversized(){let mut e=engine();let (mut b,_)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();assert!(verify_iraw_frame(&b[..150],&e.verifying_key).is_err());b[32..40].copy_from_slice(&u64::MAX.to_le_bytes());assert!(verify_iraw_frame(&b,&e.verifying_key).is_err());}
#[test] fn isc_roundtrip_and_tamper(){let mut b=build_isc(1,3,b"abc").unwrap();assert_eq!(verify_isc(&b).unwrap(),3);b[64]^=1;assert!(verify_isc(&b).is_err());}
#[test] fn isc_padding_and_size(){let mut b=build_isc(1,3,b"abc").unwrap();b[4000]=1;assert!(verify_isc(&b).is_err());b.truncate(4096);assert!(verify_isc(&b).is_err());}
#[test] fn igxp_roundtrip_and_tamper(){let mut b=build_igxp(3,b"abc").unwrap();assert_eq!(verify_igxp(&b).unwrap(),3);b[56]^=1;assert!(verify_igxp(&b).is_err());}
#[test] fn igxp_padding_and_size(){let mut b=build_igxp(3,b"abc").unwrap();b[4000]=1;assert!(verify_igxp(&b).is_err());b.truncate(4095);assert!(verify_igxp(&b).is_err());}
#[test] fn oversize_rejected(){assert!(build_isc(1,1,&vec![0;4097]).is_err());assert!(build_igxp(1,&vec![0;4041]).is_err());}
#[test] fn chain_all_three_and_artifact_binding(){
 let mut e=engine();let (raw,r1)=e.seal_iraw_frame("TEST",1,b"raw",b"depth").unwrap();
 let ig=build_igxp(2,b"run").unwrap();let r2=e.verify_and_attest_igxp(&ig).unwrap();
 let sc=build_isc(3,3,b"store").unwrap();let r3=e.verify_and_attest_isc(&sc).unwrap();
 let rs=vec![r1,r2,r3];verify_chain(&rs,&e.verifying_key).unwrap();
 assert!(verify_attached_artifact(&rs[0],&raw));assert!(verify_attached_artifact(&rs[1],&ig));assert!(verify_attached_artifact(&rs[2],&sc));
 assert!(!verify_attached_artifact(&rs[0],b"changed"));
}
#[test] fn chain_previous_root_tamper(){let mut e=engine();let r1=e.attest_artifact("TEST",1,b"a").unwrap();let mut r2=e.attest_artifact("TEST",2,b"b").unwrap();r2.prev_ici_chain_root_hex="00".repeat(32);assert!(verify_chain(&[r1,r2],&e.verifying_key).is_err());}
#[test] fn chain_signature_tamper(){let mut e=engine();let mut r=e.attest_artifact("TEST",1,b"a").unwrap();r.signature_hex="00".repeat(64);assert!(verify_chain(&[r],&e.verifying_key).is_err());}
#[test] fn chain_sequence_and_order(){let mut e=engine();let r1=e.attest_artifact("TEST",1,b"a").unwrap();let r2=e.attest_artifact("TEST",2,b"b").unwrap();assert!(verify_chain(&[r2,r1],&e.verifying_key).is_err());}
#[test] fn chain_wrong_signer(){let mut e=engine();let r=e.attest_artifact("TEST",1,b"a").unwrap();let other=engine().verifying_key;assert!(verify_chain(&[r.clone()],&other).is_ok());let wrong=IciEngine::new(SigningKey::from_bytes(&[0x77;32]));assert!(verify_chain(&[r],&wrong.verifying_key).is_err());}
#[test] fn pending_only(){let mut e=engine();let r=e.attest_artifact("TEST",1,b"a").unwrap();assert_eq!(r.cih_verification,PENDING);}
