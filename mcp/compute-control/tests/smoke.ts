import assert from "node:assert/strict";
import {createExecutionReceipt} from "../src/receipt.js";
import {assertLifecycleAllowed,assertPhysicalActuationBlocked} from "../src/policy.js";
const resource={provider:"runpod",resourceId:"gpu-test-1",kind:"gpu" as const,region:"us-east"};
const receipt=createExecutionReceipt("execute_workload",resource,{name:"pop-e2e",gitCommit:"312b419658c3c171a8bfeb2dcd11b73dd308f675",command:"python -m pytest -q"},{exitCode:0,startedAt:"2026-10-25T00:00:00Z",endedAt:"2026-10-25T00:00:01Z",stdoutHash:"sha256:stdout",stderrHash:"sha256:stderr",artifactHashes:[]});
assert.equal(receipt.state,"VERIFIED_PROCESS"); assert.match(receipt.receiptHash,/^sha256:[0-9a-f]{64}$/); assert.doesNotThrow(()=>assertLifecycleAllowed("restart")); assert.throws(()=>assertLifecycleAllowed("terminate")); assert.throws(()=>assertPhysicalActuationBlocked()); console.log("Compute Control MCP contract smoke: PASS");
