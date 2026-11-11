import assert from "node:assert/strict";
const endpoint="https://innovulis-buddy-constitutional-preview-20261111.innovulis-i-edge.workers.dev/api/buddy";
async function ask(message) {
  const result=await fetch(endpoint,{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({message,history:[]}),
    signal:AbortSignal.timeout(28000)
  });
  let data;
  try {data=await result.json();}catch{throw Error("Non-JSON Buddy response HTTP "+result.status)}
  return {status:result.status,...data};
}

const previewPage=await fetch(endpoint.replace("/api/buddy","/voice-test"),{
  method:"GET",signal:AbortSignal.timeout(10000)
});
assert.equal(previewPage.status,200);
const html=await previewPage.text();
assert.match(html,/Buddy™/);
assert.match(html,/START MICROPHONE/);
assert.match(html,/SPOKEN REPLIES ON/);
console.log("LIVE_BUDDY_VOICE_DIAGNOSTIC_PAGE_PASS");

const identity=await ask("Who are you?");
assert.equal(identity.status,200,JSON.stringify(identity));
assert.equal(identity.source,"DETERMINISTIC_BUDDY_IDENTITY");
assert.equal(identity.llm_called,false);
assert.equal(identity.receipt_issued,false);
assert.match(identity.reply,/Buddy™/);
assert.doesNotMatch(identity.reply,/Apple/);
console.log("LIVE_BUDDY_IDENTITY_DETERMINISTIC_PASS");

const voice=await ask("Can you hear me?");
assert.equal(voice.status,200,JSON.stringify(voice));
assert.equal(voice.source,"DETERMINISTIC_VOICE_CAPABILITY");
assert.match(voice.reply,/permission/);
console.log("LIVE_BUDDY_VOICE_CAPABILITY_DISCLOSURE_PASS");

const model=await ask("Briefly explain how photovoltaic cells generate electricity.");
if(model.status===200){
  assert.equal(model.source,"CLOUDFLARE_WORKERS_AI");
  assert.equal(model.llm_called,true);
  assert.equal(model.receipt_issued,false);
  console.log("LIVE_WORKERS_AI_MODEL_RESPONSE_PASS");
  console.log("MODEL_ID="+model.model);
  console.log("MODEL_TEXT_UNVERIFIED="+JSON.stringify(model.reply.slice(0,250)));
} else {
  assert.equal(model.status,503,JSON.stringify(model));
  assert.equal(model.reply,undefined);
  assert.equal(model.error,"BUDDY_INFERENCE_UNAVAILABLE");
  console.log("LIVE_WORKERS_AI_HOLD_INFERENCE_UNAVAILABLE_NO_FABRICATION");
}
