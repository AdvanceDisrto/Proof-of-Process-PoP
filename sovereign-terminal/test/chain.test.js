"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { ReceiptChain, canonicalize } = require("../receipt-chain");

test("canonical JSON is recursively stable", () => {
  assert.equal(
    canonicalize({ z: { b: 2, a: 1 }, a: [3, { y: 2, x: 1 }] }),
    canonicalize({ a: [3, { x: 1, y: 2 }], z: { a: 1, b: 2 } }),
  );
});

test("signed receipts survive restart and preserve the previous hash", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sovereign-terminal-"));
  const first = new ReceiptChain(dir);
  const a = first.append({ event: "A" });
  assert.equal(first.verify().valid, true);

  const second = new ReceiptChain(dir);
  assert.equal(second.head, a.hash);
  const b = second.append({ event: "B" });
  assert.equal(b.prev, a.hash);
  assert.deepEqual(second.verify(), { valid: true, count: 2, head: b.hash });
});

test("tampering is rejected", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sovereign-terminal-tamper-"));
  const chain = new ReceiptChain(dir);
  chain.append({ event: "ORIGINAL" });
  const lines = fs.readFileSync(chain.chainFile, "utf8").trim().split("\n");
  const receipt = JSON.parse(lines[0]);
  receipt.event = "ALTERED";
  fs.writeFileSync(chain.chainFile, JSON.stringify(receipt) + "\n");
  assert.equal(chain.verify().valid, false);
});
