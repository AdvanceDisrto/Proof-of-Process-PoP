import type { InferenceReceipt } from "../agentic_core/root_cause_agent.js";
import type { VerifiedTeeEvidence } from "../crypto/attestation_evidence.js";
import type { VerifiedOtsEvidence } from "../crypto/ots_evidence.js";
import type { VerifiedActuatorEvidence } from "../physical/actuator_evidence.js";
import type { PhysicalDispatchEvidence } from "./physical_evidence_gate.js";

export interface PhysicalDispatchBundle {
  tee: VerifiedTeeEvidence;
  ots: VerifiedOtsEvidence;
  actuator: VerifiedActuatorEvidence;
}

export function bindPhysicalEvidence(inference: InferenceReceipt, bundle: PhysicalDispatchBundle): PhysicalDispatchEvidence {
  const commandHash = inference.hypothesisHash.toLowerCase();
  if (bundle.ots.payloadHash !== commandHash || bundle.actuator.observedCommandHash !== commandHash) {
    throw new Error("QUARANTINED: physical evidence is not bound to hypothesisHash");
  }
  return {
    teeQuoteVerified: bundle.tee.verified,
    otsAnchorVerified: bundle.ots.verified,
    physicalActuatorInterlockHealthy: bundle.actuator.interlockHealthy,
    commandHash,
  };
}
