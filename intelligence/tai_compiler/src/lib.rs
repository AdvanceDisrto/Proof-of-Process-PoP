use sha2::{Digest,Sha256};
use serde::Serialize;
#[derive(Debug,Serialize,Clone)]
pub struct TokenPrimitive { pub layer:String,pub action:String,pub parameters:Vec<String>,pub conditional:Option<String> }
pub fn compile_manifest(tokens:&[TokenPrimitive])->Result<String,String>{
 let bytes=serde_json::to_vec(tokens).map_err(|e|e.to_string())?;
 let mut h=Sha256::new(); h.update(b"innovulis-tailwind-ast-v1:"); h.update(bytes);
 Ok(format!("sha256:{:x}",h.finalize()))
}
#[cfg(test)]
mod tests{use super::*;#[test]fn deterministic_hash(){let t=vec![TokenPrimitive{layer:"human-approve".into(),action:"disburse".into(),parameters:vec![],conditional:None}];assert_eq!(compile_manifest(&t).unwrap(),compile_manifest(&t).unwrap());}}
