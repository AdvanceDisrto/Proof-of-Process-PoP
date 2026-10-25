import { strict as assert } from "node:assert";
import { runE2EPipeline } from "../src/e2e_pipeline.js";

const result = runE2EPipeline();

assert.equal(result.inference.status, "UNVERIFIED_INFERENCE");
assert.equal(result.noEvidence, "ACTION_REQUIRED");
assert.equal(result.incompleteEvidence, "ACTION_REQUIRED");
assert.equal(result.mismatchedCommand, "QUARANTINED");
assert.equal(result.completeSyntheticEvidence, "LAB_DISPATCH_VERIFIED");
assert.match(result.inference.boundInputHash, /^[a-f0-9]{64}$/);
assert.match(result.inference.hypothesisHash, /^[a-f0-9]{64}$/);

console.log("E2E physical evidence gate tests passed");
