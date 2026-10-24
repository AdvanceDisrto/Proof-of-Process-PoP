import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";

globalThis.crypto ??= webcrypto;

const { default: worker } = await import("../index.js");

function envWith(keyHex = "") {
  return { ORIGIN_HOST: "example.invalid", IPOP_PUBLIC_KEY: keyHex };
}

test("unsigned lifecycle request fails closed before origin fetch", async () => {
  const request = new Request("https://www.proofofprocess.online/api/lifecycle/challenge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  const response = await worker.fetch(request, envWith(), { waitUntil() {} });
  assert.equal(response.status, 401);
  const body = await response.json();
  assert.equal(body.status, "ACTION_REQUIRED");
  assert.match(body.error, /EDGE_REJECTION/);
});

test("stale signed timestamp fails closed before cryptographic acceptance", async () => {
  const request = new Request("https://www.proofofprocess.online/api/lifecycle/verify", {
    method: "POST",
    headers: {
      "X-iPop-Timestamp": "1",
      "X-iPop-Signature": "00".repeat(64),
      "Content-Type": "application/json",
    },
    body: "{}",
  });
  const response = await worker.fetch(request, envWith("11".repeat(32)), { waitUntil() {} });
  assert.equal(response.status, 403);
  assert.match((await response.json()).error, /Timestamp/);
});
