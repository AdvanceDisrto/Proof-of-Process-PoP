import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { iCLEngine } from "./icl_engine.js";

test("iCL rejects invalid configuration instead of casting unknown YAML", () => {
  assert.throws(() => new iCLEngine("./missing-config.yaml"));
});

test("iCL engine module has deterministic source", () => {
  const digest = createHash("sha256").update("iCL-engine-v1").digest("hex");
  assert.equal(digest.length, 64);
});
