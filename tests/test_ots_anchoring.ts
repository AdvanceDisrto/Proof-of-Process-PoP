import { strict as assert } from "node:assert";
import { OpenTimestampsEngine } from "../src/crypto/ots_anchoring.js";

const hash = "a".repeat(64);

assert.doesNotThrow(() => OpenTimestampsEngine.validateHash(hash));
assert.throws(
  () => OpenTimestampsEngine.validateHash("broken"),
  /OTS ERROR/,
);

assert.deepEqual(
  OpenTimestampsEngine.buildStampArgs(
    "http://127.0.0.1:14788",
    "/tmp/evidence.bin",
  ),
  ["stamp", "-c", "http://127.0.0.1:14788", "/tmp/evidence.bin"],
);

console.log("OTS integration boundary tests passed");
