// CI-ONLY demonstration witness. Not a real claim and not independently bound to evidence.
import {createRequire} from 'node:module';
import {randomBytes} from 'node:crypto';
import {writeFileSync} from 'node:fs';
const require=createRequire(import.meta.url);
const {buildPoseidon}=require('circomlibjs');
const poseidon=await buildPoseidon();
const inputs=[7500n,8000n,2n,BigInt('0x'+randomBytes(20).toString('hex'))];
const commitment=poseidon.F.toString(poseidon(inputs));
const data={penaltyBps:'7500',entropyBps:'8000',chargeStackCount:'2',
 witnessSalt:inputs[3].toString(),publicCommitment:commitment,
 thresholdProduct:'70000000'};
writeFileSync('build/dev-private-input-DO-NOT-UPLOAD.json',JSON.stringify(data));

