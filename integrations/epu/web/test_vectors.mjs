import fs from 'node:fs';
import {verify,Rejection} from './verifier.mjs';
const vectors=JSON.parse(fs.readFileSync('build/test_vectors.json','utf8'));
const trust=vectors.trusted_demo_config;
for(const [name,v] of Object.entries(vectors.positive)){
 const out=verify(v,trust);
 const expected={METERED_SOFTWARE_FIXTURE:'METERED',EXPIRED_SOFTWARE_FIXTURE:'METERED_STALE',NOT_MEASURED:'NOT_MEASURED'}[name];
 if(out.effective_consumption_status!==expected||out.billing_eligible)throw Error('Wrong positive result '+name);
 console.log('JS PASS',name,expected);
}
for(const [name,v] of Object.entries(vectors.negative)){
 try{verify(v,trust);throw Error('BAD negative accepted '+name);}
 catch(error){
  if(!(error instanceof Rejection)||error.code!==vectors.expected_negative_codes[name])throw error;
  console.log('JS PASS rejected',name,error.code);
 }
}
console.log('EPU_PYTHON_JAVASCRIPT_CROSS_LANGUAGE_VECTOR_PASS');
