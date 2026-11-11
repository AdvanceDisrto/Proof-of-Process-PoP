#!/usr/bin/env node
// Buddy™ v2: verify three independently signed demo receipts and two links.
// This reads the trust key from the preinstalled reviewed viewer, NOT the QR.
"use strict";
const fs=require("node:fs");
const path=require("node:path");
const assert=require("node:assert/strict");
const cryptoModule=require("node:crypto");
if(!globalThis.crypto)Object.defineProperty(globalThis,"crypto",{value:cryptoModule.webcrypto});
require("./verifier-core.js");
const V=globalThis.BuddyReceiptVerifier;
const here=__dirname;
const viewer=fs.readFileSync(path.join(here,"verifier.html"),"utf8");
const matches=[...viewer.matchAll(/const DEMO_PINNED_PUBLIC_KEY_B64=([^;]+);/g)];
if(matches.length!==1)throw Error("EXACTLY_ONE_PINNED_VIEWER_KEY_REQUIRED");
const pinned=JSON.parse(matches[0][1]);
const anchor=JSON.parse(fs.readFileSync(path.join(here,"demo-public-trust-anchor.json"),"utf8"));
if(anchor.public_key_b64!==pinned)throw Error("VIEWER_TRUST_ANCHOR_MISMATCH");
const actualFingerprint=cryptoModule.createHash("sha256").update(Buffer.from(pinned,"base64")).digest("hex");
if(actualFingerprint!==anchor.public_key_sha256)throw Error("TRUST_FINGERPRINT_MISMATCH");
const file=path.resolve(process.argv[2]||path.join(here,"signed-receipt-chain-v2.json"));
const input=JSON.parse(fs.readFileSync(file,"utf8"));
const receipts=Array.isArray(input)?input:input?.receipts;
(async()=>{
 const result=await V.verifyChain(receipts,pinned,3);
 if(!result.valid)throw Error("SIGNED_CHAIN_REFUTED: "+result.error);
 for(const [i,receipt]of receipts.entries()){
   const filename="receipt-"+(i+1)+"-"+receipt.brain+".json";
   const single=JSON.parse(fs.readFileSync(path.join(here,filename),"utf8"));
   assert.deepEqual(single,receipt,"INDIVIDUAL_RECEIPT_FILE_MISMATCH: "+filename);
   console.log("PASS "+(i+1)+": "+receipt.brain+" / "+receipt.gate_verdict);
   console.log("  SHA256 "+receipt.receipt_hash);
   console.log("  parent "+receipt.prev_hash);
 }
 console.log("THREE_SIGNED_RECEIPT_INTERNAL_CHAIN_PASS");
 console.log("TIP "+result.tip);
 console.log("EXTERNAL_GENESIS_ANCHOR NOT_VERIFIED");
 console.log("SIGNER_IDENTITY PHYSICAL_TRUTH HARDWARE_EXECUTION NOT_PROVEN");
})().catch(e=>{console.error("FAIL_CLOSED: "+e.message);process.exitCode=1;});
