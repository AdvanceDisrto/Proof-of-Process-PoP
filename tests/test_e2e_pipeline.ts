import { strict as assert } from "node:assert";
import { runE2EPipeline } from "../src/e2e_pipeline.js";

const result = runE2EPipeline();

assert.equal(result.inference.status, "UNVERIFIED_INFERENCE");
assert.equal(result.noTee, "ACTION_REQUIRED");
assert.equal(result.validTee, "LAB_DISPATCH_VERIFIED");
assert.match(result.inference.boundInputHash, /^[a-f0-9]{64}$/);
assert.match(result.inference.hypothesisHash, /^[a-f0-9]{64}$/);

console.log("E2E pipeline tests passed");
