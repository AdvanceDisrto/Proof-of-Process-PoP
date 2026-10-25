import type { InferenceReceipt } from "../agentic_core/root_cause_agent.js";
import { ChainOracle, type ChainOracleEvidence } from "../oracle/chain_oracle.js";

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
 * manufacture a TEE quote, OTS proof, chain attestation, or physical
 * actuator observation.
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

  public evaluateWithChainOracle(
    inference: InferenceReceipt,
    evidence: PhysicalDispatchEvidence | null,
    oracleEvidence: ChainOracleEvidence | null,
  ): PhysicalGateState {
    const physicalState = this.evaluate(inference, evidence);
    if (physicalState !== "LAB_DISPATCH_VERIFIED") return physicalState;
    if (!oracleEvidence) return "ACTION_REQUIRED";
    if (oracleEvidence.subjectHash !== inference.hypothesisHash) return "QUARANTINED";

    const oracleState = ChainOracle.evaluate(oracleEvidence).state;
    if (oracleState === "VERIFIED_PROCESS") return "LAB_DISPATCH_VERIFIED";
    if (oracleState === "QUARANTINED") return "QUARANTINED";
    return "ACTION_REQUIRED";
  }
}
