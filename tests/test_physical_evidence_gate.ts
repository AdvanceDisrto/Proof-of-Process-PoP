import { strict as assert } from "node:assert";
import { RootCauseAgent } from "../src/agentic_core/root_cause_agent.js";
import { PhysicalEvidenceGate } from "../src/translation/physical_evidence_gate.js";

const inference = new RootCauseAgent().analyze("fabric-payload");
const gate = new PhysicalEvidenceGate();

const complete = {
  teeQuoteVerified: true,
  otsAnchorVerified: true,
  physicalActuatorInterlockHealthy: true,
  commandHash: inference.hypothesisHash,
};

assert.equal(gate.evaluate(inference, null), "ACTION_REQUIRED");
assert.equal(
  gate.evaluate(inference, { ...complete, teeQuoteVerified: false }),
  "ACTION_REQUIRED",
);
assert.equal(
  gate.evaluate(inference, { ...complete, otsAnchorVerified: false }),
  "ACTION_REQUIRED",
);
assert.equal(
  gate.evaluate(inference, {
    ...complete,
    physicalActuatorInterlockHealthy: false,
  }),
  "ACTION_REQUIRED",
);
assert.equal(
  gate.evaluate(inference, { ...complete, commandHash: "f".repeat(64) }),
  "QUARANTINED",
);
assert.equal(gate.evaluate(inference, complete), "LAB_DISPATCH_VERIFIED");

console.log("Physical evidence gate tests passed");
