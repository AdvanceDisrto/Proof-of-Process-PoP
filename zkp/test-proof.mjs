import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync, writeFileSync, rmSync, readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {buildPoseidon} from 'circomlibjs';
const poseidon=await buildPoseidon();
const output=join(process.cwd(),'build');
const tmp=mkdtempSync(join(tmpdir(),'innovulis-zk-'));
function witness(input, shouldPass, expectedFlag){
 const name=join(tmp,'input.json');const result=join(tmp,'witness.wtns');
 const exportPath=join(tmp,'witness.json');
 writeFileSync(name,JSON.stringify(input));
 let built=false;
 try{
  execFileSync(process.execPath,[join(output,'PretextualShield_js','generate_witness.js'),
      join(output,'PretextualShield_js','PretextualShield.wasm'),name,result],{stdio:'pipe'});
  execFileSync(join(process.cwd(),'node_modules','.bin','snarkjs'),
    ['wtns','check',join(output,'PretextualShield.r1cs'),result],{stdio:'pipe'});
  execFileSync(join(process.cwd(),'node_modules','.bin','snarkjs'),
    ['wtns','export','json',result,exportPath],{stdio:'pipe'});
  built=true;
 }catch(e){
  if(shouldPass)throw e;
  console.log('INVALID_WITNESS_REJECTED');
 }
 if(!shouldPass && built)throw new Error('bad witness incorrectly accepted');
 if(shouldPass){
  const values=JSON.parse(readFileSync(exportPath,'utf8'));
  assert.equal(String(values[1]), String(expectedFlag),'wrong disclosed heuristic bit');
  console.log('VALID_WITNESS_FLAG',values[1]);
 }
}

function sample(penalty, entropy, count, salt, threshold){
 const hash=poseidon([BigInt(penalty),BigInt(entropy),BigInt(count),BigInt(salt)]);
 return {penaltyBps:String(penalty),entropyBps:String(entropy),chargeStackCount:String(count),witnessSalt:String(salt),
  publicCommitment:poseidon.F.toString(hash),thresholdProduct:String(threshold)};
}
try{
 const positive=sample(7500,8000,2,1525133573,70_000_000);
 witness(positive,true,'1');
 const negative=sample(1000,1000,1,1525133573,70_000_000);
 witness(negative,true,'0');
 witness({...positive,penaltyBps:'10001'},false);
 witness({...positive,publicCommitment:'42'},false);
 witness({...positive,thresholdProduct:String(2**36)},false);
}finally{rmSync(tmp,{recursive:true,force:true});}

