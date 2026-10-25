import { strict as assert } from "node:assert";
import { RootCauseAgent } from "../src/agentic_core/root_cause_agent.js";
import { AttestationEvidence } from "../src/crypto/attestation_evidence.js";
import { OtsEvidence } from "../src/crypto/ots_evidence.js";
import { ActuatorEvidence } from "../src/physical/actuator_evidence.js";
import { bindPhysicalEvidence } from "../src/translation/physical_dispatch_bundle.js";
import { PhysicalEvidenceGate } from "../src/translation/physical_evidence_gate.js";
import { QuarantineLedger } from "../src/quarantine/quarantine_ledger.js";

const inference = new RootCauseAgent().analyze("verified-payload");
assert.throws(() => AttestationEvidence.acceptVerifiedQuote("AMD_SEV_SNP", new Uint8Array(), "0".repeat(64), false), /ACTION_REQUIRED/);
assert.throws(() => OtsEvidence.acceptVerifiedProof(inference.hypothesisHash, 1, false), /ACTION_REQUIRED/);
assert.throws(() => ActuatorEvidence.acceptObservation("robot-1", false, inference.hypothesisHash), /ACTION_REQUIRED/);

const tee = AttestationEvidence.acceptVerifiedQuote("AMD_SEV_SNP", new Uint8Array([1,2,3]), "a".repeat(64), true);
const ots = OtsEvidence.acceptVerifiedProof(inference.hypothesisHash, 900000, true);
const actuator = ActuatorEvidence.acceptObservation("robot-1", true, inference.hypothesisHash);
const evidence = bindPhysicalEvidence(inference, { tee, ots, actuator });
assert.equal(new PhysicalEvidenceGate().evaluate(inference, evidence), "LAB_DISPATCH_VERIFIED");

assert.throws(() => bindPhysicalEvidence(inference, {
  tee,
  ots: OtsEvidence.acceptVerifiedProof("b".repeat(64), 900000, true),
  actuator,
}), /QUARANTINED/);

const ledger = new QuarantineLedger();
const record = ledger.append("robot-1", "COMMAND_HASH_MISMATCH", { expected: inference.hypothesisHash }, "2026-10-25T00:00:00Z");
assert.equal(ledger.get(record.contentHash)?.reason, "COMMAND_HASH_MISMATCH");
assert.match(record.contentHash, /^[a-f0-9]{64}$/);

console.log("Physical integration boundary tests passed");
