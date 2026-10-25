import assert from "node:assert/strict";
import { createExecutionReceipt, merkleRoot } from "../src/receipt.js";
import { assertLifecycleAllowed, assertPhysicalActuationBlocked } from "../src/policy.js";

const resource = { provider: "runpod", resourceId: "gpu-test-1", kind: "gpu" as const, region: "us-east" };
const workload = { name: "pop-e2e", gitCommit: "312b419658c3c171a8bfeb2dcd11b73dd308f675", command: "python -m pytest -q" };
const execution = {
  exitCode: 0,
  startedAt: "2026-10-25T00:00:00Z",
  endedAt: "2026-10-25T00:00:01Z",
  stdoutHash: "sha256:stdout",
  stderrHash: "sha256:stderr",
  artifactHashes: [],
};

const submitted = createExecutionReceipt("execute_workload", resource, workload, execution, {
  status: "submitted", chain: "test", txHash: "tx-submitted",
});
assert.equal(submitted.state, "ACTION_REQUIRED");
assert.equal(submitted.anchor.status, "submitted");
assert.equal(submitted.prevReceiptHash, null);

const confirmed = createExecutionReceipt("execute_workload", resource, workload, execution, {
  status: "confirmed", chain: "test", txHash: "tx-confirmed", confirmations: 6,
}, submitted.receiptHash);
assert.equal(confirmed.state, "VERIFIED_PROCESS");
assert.equal(confirmed.anchor.status, "confirmed");
assert.equal(confirmed.prevReceiptHash, submitted.receiptHash);
assert.match(confirmed.receiptHash, /^sha256:[0-9a-f]{64}$/);

const reorged = createExecutionReceipt("execute_workload", resource, workload, execution, {
  status: "reorged", chain: "test", txHash: "tx-reorged",
}, confirmed.receiptHash);
assert.equal(reorged.state, "ACTION_REQUIRED");
assert.equal(reorged.anchor.status, "reorged");

const absent = createExecutionReceipt("execute_workload", resource, workload, execution);
assert.equal(absent.state, "ACTION_REQUIRED");
assert.equal(absent.anchor.status, "absent");

const root = merkleRoot([submitted.receiptHash, confirmed.receiptHash, reorged.receiptHash]);
assert.match(root, /^sha256:[0-9a-f]{64}$/);

assert.doesNotThrow(() => assertLifecycleAllowed("restart"));
assert.throws(() => assertLifecycleAllowed("terminate"));
assert.throws(() => assertPhysicalActuationBlocked());

console.log("Compute Control MCP fail-closed receipt smoke: PASS");
