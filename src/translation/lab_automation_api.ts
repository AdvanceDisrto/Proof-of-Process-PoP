import type { InferenceReceipt } from "../agentic_core/root_cause_agent.js";

export type PhysicalGateState =
  | "LAB_DISPATCH_VERIFIED"
  | "ACTION_REQUIRED"
  | "QUARANTINED";

export class LabAutomationAPI {
  public dispatchSynthesis(
    inference: InferenceReceipt,
    labTeeAttestation: string | null,
  ): PhysicalGateState {
    if (inference.status !== "UNVERIFIED_INFERENCE") {
      return "QUARANTINED";
    }
    if (!labTeeAttestation) {
      return "ACTION_REQUIRED";
    }
    return "LAB_DISPATCH_VERIFIED";
  }
}
