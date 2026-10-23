import assert from "node:assert/strict";
import test from "node:test";
import { SSNBoundary } from "../core/SSNBoundary.js";

test("SSN boundary removes matched values before model-facing text", () => {
  const boundary = new SSNBoundary(Buffer.alloc(32, 7));
  const result = boundary.sanitize("synthetic SSN 000-00-0000", "ts-exec-1");
  assert.equal(result.text.includes("000-00-0000"), false);
  assert.equal(Object.keys(result.tokenMap).length, 1);
  assert.equal(result.receipt.physicalGate, "ACTION_REQUIRED");
});

test("SSN token does not derive from the raw value", () => {
  const boundary = new SSNBoundary(Buffer.alloc(32, 8));
  const a = boundary.sanitize("000-00-0000", "ts-exec-2");
  const b = boundary.sanitize("000-00-0000", "ts-exec-2");
  assert.notDeepEqual(Object.keys(a.tokenMap), Object.keys(b.tokenMap));
});

test("reveal intent is deterministic for the same token and execution", () => {
  const token = "[SSN_TOKEN_test]";
  assert.equal(
    SSNBoundary.revealIntentHash("e", token),
    SSNBoundary.revealIntentHash("e", token),
  );
  assert.notEqual(
    SSNBoundary.revealIntentHash("e", token),
    SSNBoundary.revealIntentHash("e2", token),
  );
});
