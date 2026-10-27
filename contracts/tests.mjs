import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as ethers from 'ethers';
import ganache from 'ganache';
import solc from 'solc';
const src=fs.readFileSync(new URL('./EpistemicReceiptQuorum.sol',import.meta.url),'utf8');
const input={language:'Solidity',sources:{'EpistemicReceiptQuorum.sol':{content:src}},settings:{optimizer:{enabled:true,runs:200},outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}};
const output=JSON.parse(solc.compile(JSON.stringify(input)));
if(output.errors?.some(e=>e.severity==='error'))throw new Error(output.errors.map(e=>e.formattedMessage).join('\n'));
const target=output.contracts['EpistemicReceiptQuorum.sol'].EpistemicReceiptQuorum;
const addr=(s)=>BigInt(s.address.toLowerCase());
const types={Confirm:[{name:'receiptRoot',type:'bytes32'},{name:'nodeEpoch',type:'uint256'},{name:'deadline',type:'uint256'}],
 RotateNode:[{name:'oldNode',type:'address'},{name:'newNode',type:'address'},{name:'nodeEpoch',type:'uint256'},{name:'governanceEpoch',type:'uint256'},{name:'nonce',type:'uint256'},{name:'deadline',type:'uint256'}],
 RotateGovernor:[{name:'oldGovernor',type:'address'},{name:'newGovernor',type:'address'},{name:'governanceEpoch',type:'uint256'},{name:'nonce',type:'uint256'},{name:'deadline',type:'uint256'}],
 SetPaused:[{name:'paused',type:'bool'},{name:'governanceEpoch',type:'uint256'},{name:'nonce',type:'uint256'},{name:'deadline',type:'uint256'}]};
let env;
async function setup(){
 const gp=ganache.provider({logging:{quiet:true}});
 const provider=new ethers.BrowserProvider(gp);const payer=await provider.getSigner(0);
 const nodes=Array.from({length:5},()=>ethers.Wallet.createRandom());
 const governors=Array.from({length:5},()=>ethers.Wallet.createRandom());
 const factory=new ethers.ContractFactory(target.abi,'0x'+target.evm.bytecode.object,payer);
 const contract=await factory.deploy(nodes.map(x=>x.address),governors.map(x=>x.address));await contract.waitForDeployment();
 const net=await provider.getNetwork();
 const domain={name:'iNNOVULISReceiptQuorum',version:'1',chainId:net.chainId,verifyingContract:await contract.getAddress()};
 const block=await provider.getBlock('latest');
 return {gp,provider,payer,contract,nodes,governors,domain,deadline:BigInt(block.timestamp+180)};
}
async function signatures(wallets,domain,key,value){
 const selected=wallets.slice().sort((a,b)=>addr(a)<addr(b)?-1:1);
 return Promise.all(selected.map(w=>w.signTypedData(domain,{[key]:types[key]},value)));
}
function root(byte){return '0x'+byte.repeat(64)}
async function confirmData(e,r=root('a')){return {receiptRoot:r,nodeEpoch:await e.contract.nodeEpoch(),deadline:e.deadline}}
async function expectRevert(p){
 try{const tx=await p;await tx.wait();assert.fail('unexpected successful execution');}
 catch(e){if(e.code==='ERR_ASSERTION')throw e;assert.ok(/CALL_EXCEPTION|revert|VM Exception|missing revert data|transaction execution reverted/.test(String(e)||String(e.code)),String(e));}
}
function close(e){e.gp.disconnect()}

test('3-of-5 signatures confirm; duplicate root is rejected',async()=>{
 const e=await setup();try{const args=await confirmData(e);const sig=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',args);
 assert.equal(await e.contract.confirmedRoot(args.receiptRoot),false);
 await(await e.contract.confirmReceipt(args.receiptRoot,args.deadline,sig)).wait();
 assert.equal(await e.contract.confirmedRoot(args.receiptRoot),true);
 await expectRevert(e.contract.confirmReceipt(args.receiptRoot,args.deadline,sig));}finally{close(e)}
});
test('2-of-5 cannot confirm even with valid EIP712 signatures',async()=>{
 const e=await setup();try{const d=await confirmData(e);const sig=await signatures(e.nodes.slice(0,2),e.domain,'Confirm',d);
 await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,sig));assert.equal(await e.contract.confirmedRoot(d.receiptRoot),false);}finally{close(e)}
});
test('identical signatures cannot vote twice and order is enforced',async()=>{
 const e=await setup();try{const d=await confirmData(e);const sig=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',d);
 await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,[sig[0],sig[0],sig[1]]));
 await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,sig.slice().reverse()));}finally{close(e)}
});
test('wrong EIP712 verifying contract and wrong chain reject relay',async()=>{
 const e=await setup();try{const d=await confirmData(e);const sig=await signatures(e.nodes.slice(0,3),{...e.domain,chainId:99999},'Confirm',d);
 await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,sig));
 const sig2=await signatures(e.nodes.slice(0,3),{...e.domain,verifyingContract:ethers.ZeroAddress},'Confirm',d);
 await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,sig2));}finally{close(e)}
});
test('expired and far-future deadline reject',async()=>{
 const e=await setup();try{const d=await confirmData(e);d.deadline=1n;
 const sig=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',d);await expectRevert(e.contract.confirmReceipt(d.receiptRoot,d.deadline,sig));
 const d2={...d,deadline:e.deadline+9999n};const s2=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',d2);
 await expectRevert(e.contract.confirmReceipt(d2.receiptRoot,d2.deadline,s2));}finally{close(e)}
});
test('governance rotation requires 3 of 5 and invalidates old node key',async()=>{
 const e=await setup();try{const spare=ethers.Wallet.createRandom();let d={oldNode:e.nodes[0].address,newNode:spare.address,nodeEpoch:await e.contract.nodeEpoch(),governanceEpoch:await e.contract.governanceEpoch(),nonce:await e.contract.governanceNonce(),deadline:e.deadline};
 const bad=await signatures(e.governors.slice(0,2),e.domain,'RotateNode',d);
 await expectRevert(e.contract.rotateNode(d.oldNode,d.newNode,d.deadline,bad));
 const good=await signatures(e.governors.slice(0,3),e.domain,'RotateNode',d);
 await(await e.contract.rotateNode(d.oldNode,d.newNode,d.deadline,good)).wait();
 assert.equal(await e.contract.isNode(e.nodes[0].address),false);
 assert.equal(await e.contract.isNode(spare.address),true);
 assert.equal(await e.contract.nodeEpoch(),2n);
 await expectRevert(e.contract.rotateNode(d.oldNode,d.newNode,d.deadline,good));
 const c=await confirmData(e,root('b'));
 const oldVotes=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',c);
 await expectRevert(e.contract.confirmReceipt(c.receiptRoot,c.deadline,oldVotes));
 const newVotes=await signatures([spare,...e.nodes.slice(1,3)],e.domain,'Confirm',c);
 await(await e.contract.confirmReceipt(c.receiptRoot,c.deadline,newVotes)).wait();
 assert.equal(await e.contract.confirmedRoot(c.receiptRoot),true);
 }finally{close(e)}
});
test('old attestations from prior node epoch are invalid even if signers not removed',async()=>{
 const e=await setup();try{const args=await confirmData(e,root('e'));
 const pre=await signatures(e.nodes.slice(1,4),e.domain,'Confirm',args);
 const spare=ethers.Wallet.createRandom();const d={oldNode:e.nodes[0].address,newNode:spare.address,nodeEpoch:1n,governanceEpoch:1n,nonce:0n,deadline:e.deadline};
 const sigs=await signatures(e.governors.slice(0,3),e.domain,'RotateNode',d);
 await(await e.contract.rotateNode(d.oldNode,d.newNode,d.deadline,sigs)).wait();
 await expectRevert(e.contract.confirmReceipt(args.receiptRoot,args.deadline,pre));
 }finally{close(e)}
});
test('governance pause blocks mint and unpause needs fresh signatures/nonce',async()=>{
 const e=await setup();try{let d={paused:true,governanceEpoch:await e.contract.governanceEpoch(),nonce:await e.contract.governanceNonce(),deadline:e.deadline};
 const sig=await signatures(e.governors.slice(0,3),e.domain,'SetPaused',d);
 await(await e.contract.setPaused(true,d.deadline,sig)).wait();assert.equal(await e.contract.paused(),true);
 await expectRevert(e.contract.setPaused(true,d.deadline,sig));
 const c=await confirmData(e);const votes=await signatures(e.nodes.slice(0,3),e.domain,'Confirm',c);
 await expectRevert(e.contract.confirmReceipt(c.receiptRoot,c.deadline,votes));
 d={paused:false,governanceEpoch:await e.contract.governanceEpoch(),nonce:await e.contract.governanceNonce(),deadline:e.deadline};
 const resume=await signatures(e.governors.slice(0,3),e.domain,'SetPaused',d);
 await(await e.contract.setPaused(false,d.deadline,resume)).wait();
 assert.equal(await e.contract.paused(),false);
 assert.equal(await e.contract.confirmedRoot(c.receiptRoot),false);
 // Execute a previously rejected attestation after unpausing; bypass Ganache's cached gas estimate.
 await(await e.contract.confirmReceipt(c.receiptRoot,c.deadline,votes,{gasLimit:350000})).wait();
 assert.equal(await e.contract.confirmedRoot(c.receiptRoot),true);
 }finally{close(e)}
});
test('rotate governor revokes its prior voting power and invalidates old nonce',async()=>{
 const e=await setup();try{const spare=ethers.Wallet.createRandom();const d={oldGovernor:e.governors[0].address,newGovernor:spare.address,governanceEpoch:1n,nonce:0n,deadline:e.deadline};
 const govsig=await signatures(e.governors.slice(0,3),e.domain,'RotateGovernor',d);
 await(await e.contract.rotateGovernor(d.oldGovernor,d.newGovernor,d.deadline,govsig)).wait();
 assert.equal(await e.contract.isGovernor(e.governors[0].address),false);
 assert.equal(await e.contract.isGovernor(spare.address),true);
 const p={paused:true,governanceEpoch:2n,nonce:1n,deadline:e.deadline};
 const invalid=await signatures(e.governors.slice(0,3),e.domain,'SetPaused',p);
 await expectRevert(e.contract.setPaused(true,p.deadline,invalid));
 const valid=await signatures([spare,...e.governors.slice(1,3)],e.domain,'SetPaused',p);
 await(await e.contract.setPaused(true,p.deadline,valid)).wait();
 }finally{close(e)}
});
test('no fund withdrawal or external asset transfer ABI',()=>{
 const names=target.abi.filter(x=>x.type==='function').map(x=>x.name);
 assert.equal(names.includes('withdraw'),false);
 assert.equal(names.includes('freezeAssets'),false);
 assert.equal(names.includes('transferFunds'),false);
});


test('validator and governance signing keys must be disjoint at genesis',async()=>{
 const e=await setup();try{
 const factory=new ethers.ContractFactory(target.abi,'0x'+target.evm.bytecode.object,e.payer);
 const badGovs=[e.nodes[4].address,...e.governors.slice(1).map(x=>x.address)];
 await expectRevert(factory.deploy(e.nodes.map(x=>x.address),badGovs));
 }finally{close(e)}
});

test('governance cannot rotate a validator into a governance key',async()=>{
 const e=await setup();try{const d={oldNode:e.nodes[0].address,newNode:e.governors[4].address,
 nodeEpoch:1n,governanceEpoch:1n,nonce:0n,deadline:e.deadline};
 const signs=await signatures(e.governors.slice(0,3),e.domain,'RotateNode',d);
 await expectRevert(e.contract.rotateNode(d.oldNode,d.newNode,d.deadline,signs));
 }finally{close(e)}
});

test('governance cannot rotate a governor into a validator key',async()=>{
 const e=await setup();try{const d={oldGovernor:e.governors[0].address,newGovernor:e.nodes[4].address,
 governanceEpoch:1n,nonce:0n,deadline:e.deadline};
 const signs=await signatures(e.governors.slice(0,3),e.domain,'RotateGovernor',d);
 await expectRevert(e.contract.rotateGovernor(d.oldGovernor,d.newGovernor,d.deadline,signs));
 }finally{close(e)}
});
