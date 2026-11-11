import test from "node:test";
import assert from "node:assert/strict";
import {
  buddyHandler, MODEL_ID, BUDDY_SYSTEM_PROMPT,
} from "./fixtures/buddy-constitutional.mjs";

function post(message, history = [], origin = "https://innovulis.com") {
  return new Request("https://staged.worker/api/buddy", {
    method: "POST", headers: { "content-type": "application/json", origin },
    body: JSON.stringify({message,history}),
  });
}
test("Buddy identity is deterministic and not a vendor impersonation",async()=>{
  let ran = false;
  const response=await buddyHandler(post("Who are you?"),{AI:{run:async()=>{ran=true;throw Error("must not run")}}});
  assert.equal(response.status,200);
  const data=await response.json();
  assert.equal(data.source,"DETERMINISTIC_BUDDY_IDENTITY");
  assert.equal(data.llm_called,false);
  assert.equal(data.receipt_issued,false);
  assert.match(data.reply,/iNNOVULIS/);
  assert.doesNotMatch(data.reply,/Apple/);
  assert.equal(ran,false);
});
test("Buddy reports browser-conditional ears",async()=>{
  const r=await buddyHandler(post("Can you hear me?"),{});
  assert.equal(r.status,200);
  const data=await r.json();
  assert.equal(data.source,"DETERMINISTIC_VOICE_CAPABILITY");
  assert.match(data.reply,/permission/);
  assert.match(data.reply,/receives text/);
});
test("Generic messages cannot masquerade as constitutional identity",async()=>{
  const r=await buddyHandler(post("I have a question about apples."),{});
  assert.equal(r.status,503);
  assert.equal((await r.json()).error,"BUDDY_AI_BINDING_UNAVAILABLE");
});
test("Engine unavailable returns no fabricated answer",async()=>{
  const r=await buddyHandler(post("Explain fusion reactions"),{AI:{run:async()=>{throw Error("Cloudflare outage")}}});
  assert.equal(r.status,503);
  const data=await r.json();
  assert.equal(data.error,"BUDDY_INFERENCE_UNAVAILABLE");
  assert.equal(data.reply,undefined);
  assert.equal(data.receipt_issued,false);
});
test("Configured model output remains attributed and not CIH receipt",async()=>{
  let called=false;
  const r=await buddyHandler(post("Explain how solar cells work."),{
    AI:{run:async(model,opts)=>{
      called=true;
      assert.equal(model,MODEL_ID);
      assert.equal(opts.messages[0].content,BUDDY_SYSTEM_PROMPT);
      return {response:"Light produces current in a photovoltaic junction."};
    }}
  });
  assert.equal(r.status,200);
  const data=await r.json();
  assert.equal(data.source,"CLOUDFLARE_WORKERS_AI");
  assert.equal(data.assurance,"MODEL_OUTPUT_UNVERIFIED");
  assert.equal(data.llm_called,true);
  assert.equal(data.receipt_issued,false);
  assert.equal(called,true);
});
test("Edge clock is explicit about unverified synchronization",async()=>{
  const r=await buddyHandler(post("What is the date today?"),{});
  assert.equal(r.status,200);
  const data=await r.json();
  assert.equal(data.source,"EDGE_SYSTEM_CLOCK");
  assert.equal(data.clock_synchronization_attested,false);
});
test("Unknown or untrusted origin is rejected",async()=>{
  const r=await buddyHandler(post("Who are you?",[],"https://untrusted.invalid"),{});
  assert.equal(r.status,403);
});
test("Malformed JSON is refused with 400",async()=>{
  const r=await buddyHandler(new Request("https://staged.worker/api/buddy",{
    method:"POST",headers:{"content-type":"application/json"},body:"{invalid"
  }),{});
  assert.equal(r.status,400);
});

test("isolated browser voice diagnostic never starts the microphone automatically",async()=>{
  const r=await buddyHandler(new Request("https://staged.worker/voice-test",{method:"GET"}),{});
  assert.equal(r.status,200);
  assert.match(r.headers.get("content-type")||"",/text\/html/);
  const html=await r.text();
  assert.match(html,/START MICROPHONE/);
  assert.match(html,/SpeechRecognition/);
  assert.match(html,/speechSynthesis/);
  assert.match(html,/fetch\("\/api\/buddy"/);
  assert.match(html,/Microphone remains off until you click/);
  assert.match(html,/No model answer was produced/);
});
