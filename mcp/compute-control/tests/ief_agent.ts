import assert from "node:assert/strict";
import test from "node:test";
import { iEfAgent, iEfCode, type FailureRemediator, type FailureAnchor } from "../src/agents/ief/ief_agent.js";

test("iEf classifies provenance failures as slashing", () => {
  assert.equal(iEfAgent.determineRemediation(iEfCode.ICOPM_HASH_MISMATCH), "SLASHED");
  assert.equal(iEfAgent.determineRemediation(iEfCode.STALE_MANIFEST), "SLASHED");
});

test("iEf classifies physical failures as quarantined", () => {
  assert.equal(iEfAgent.determineRemediation(iEfCode.TEE_QUOTE_MISSING), "QUARANTINED");
  assert.equal(iEfAgent.determineRemediation(iEfCode.COMMAND_HASH_MISMATCH), "QUARANTINED");
});

test("iEf records remediation and keeps submitted distinct from confirmed", async () => {
  const actions: string[] = [];
  const remediator: FailureRemediator = {
    async remediate(action) { actions.push(action); },
  };
  const anchor: FailureAnchor = {
    async submit() { return { status: "submitted", chain: "test", txHash: "tx-test" }; },
  };

  const receipt = await iEfAgent.handleFailure(
    iEfCode.PROVIDER_API_TIMEOUT,
    "node-test",
    "provider unavailable",
    remediator,
    anchor,
  );

  assert.equal(receipt.actionTaken, "RESTARTED");
  assert.deepEqual(actions, ["RESTARTED"]);
  assert.equal(receipt.anchor.status, "submitted");
  assert.equal(receipt.spec, "iEf-failure/v1");
  assert.equal(receipt.failureHash.length, 64);
});

test("iEf produces no anchor claim when anchor submission fails", async () => {
  const anchor: FailureAnchor = {
    async submit() { throw new Error("offline"); },
  };
  const receipt = await iEfAgent.handleFailure(
    iEfCode.OTS_ANCHOR_FAILED,
    "node-test",
    "anchor unavailable",
    undefined,
    anchor,
  );
  assert.deepEqual(receipt.anchor, { status: "absent" });
});
