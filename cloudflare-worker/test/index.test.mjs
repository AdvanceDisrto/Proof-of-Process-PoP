import test from "node:test";
import assert from "node:assert/strict";
import worker from "../index.js";

function env(overrides={}){return {ORIGIN_HOST:"example.invalid",IPOP_PUBLIC_KEY:"00".repeat(32),...overrides};}

test("developer console is public and receipt-first", async () => {
  const response=await worker.fetch(new Request("https://edge.example/developer"),env());
  assert.equal(response.status,200);
  const html=await response.text();
  assert.match(html,/DEVELOPER RECEIPT CONSOLE/);
  assert.match(html,/SOURCE .* BUILD .* VERIFY .* ANCHOR .* DEPLOY/s);
  assert.match(html,/ACTION_REQUIRED/);
});

test("unsupported method fails closed", async () => {
  const response=await worker.fetch(new Request("https://edge.example/private",{method:"DELETE"}),env());
  assert.equal(response.status,405);
  assert.equal((await response.json()).status,"ACTION_REQUIRED");
});

test("private route without signature fails closed", async () => {
  const response=await worker.fetch(new Request("https://edge.example/private"),env());
  assert.equal(response.status,401);
  const body=await response.json();
  assert.equal(body.status,"ACTION_REQUIRED");
  assert.match(body.error,/EDGE_REJECTION/);
});
