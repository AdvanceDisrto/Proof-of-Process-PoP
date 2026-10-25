import type { InferenceReceipt } from "../agentic_core/root_cause_agent.js";

export type PhysicalGateState =
  | "LAB_DISPATCH_VERIFIED"
  | "ACTION_REQUIRED"
  | "QUARANTINED";

export interface PhysicalDispatchEvidence {
  teeQuoteVerified: boolean;
  otsAnchorVerified: boolean;
  physicalActuatorInterlockHealthy: boolean;
  commandHash: string;
}

/**
 * Production-shaped boundary for physical dispatch.
 *
 * This module deliberately accepts already-verified evidence. It does not
 * manufacture a TEE quote, OTS proof, or physical actuator observation.
 * A real deployment must replace the evidence producers with independently
 * verified hardware/anchor integrations.
 */
export class PhysicalEvidenceGate {
  public evaluate(
    inference: InferenceReceipt,
    evidence: PhysicalDispatchEvidence | null,
  ): PhysicalGateState {
    if (inference.status !== "UNVERIFIED_INFERENCE") {
      return "QUARANTINED";
    }

    if (!evidence) {
      return "ACTION_REQUIRED";
    }

    if (evidence.commandHash !== inference.hypothesisHash) {
      return "QUARANTINED";
    }

    if (
      !evidence.teeQuoteVerified ||
      !evidence.otsAnchorVerified ||
      !evidence.physicalActuatorInterlockHealthy
    ) {
      return "ACTION_REQUIRED";
    }

    return "LAB_DISPATCH_VERIFIED";
  }
}
