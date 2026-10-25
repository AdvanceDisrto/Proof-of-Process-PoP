import type { InferenceReceipt } from "../agentic_core/root_cause_agent.js";
import {
  PhysicalEvidenceGate,
  type PhysicalDispatchEvidence,
  type PhysicalGateState,
} from "./physical_evidence_gate.js";

export { PhysicalEvidenceGate };
export type { PhysicalDispatchEvidence, PhysicalGateState };

export class LabAutomationAPI {
  private readonly gate = new PhysicalEvidenceGate();

  public dispatchSynthesis(
    inference: InferenceReceipt,
    evidence: PhysicalDispatchEvidence | null,
  ): PhysicalGateState {
    return this.gate.evaluate(inference, evidence);
  }
}
