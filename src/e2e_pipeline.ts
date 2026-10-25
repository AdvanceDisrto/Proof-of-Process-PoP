import { RootCauseAgent } from "./agentic_core/root_cause_agent.js";
import { LabAutomationAPI } from "./translation/lab_automation_api.js";

export function runE2EPipeline() {
  const fabricPayload = "Patient_EHR_Data_Block_101";
  const inference = new RootCauseAgent().analyze(fabricPayload);
  const lab = new LabAutomationAPI();

  const completeSyntheticEvidence = {
    teeQuoteVerified: true,
    otsAnchorVerified: true,
    physicalActuatorInterlockHealthy: true,
    commandHash: inference.hypothesisHash,
  };

  return {
    inference,
    noEvidence: lab.dispatchSynthesis(inference, null),
    incompleteEvidence: lab.dispatchSynthesis(inference, {
      ...completeSyntheticEvidence,
      otsAnchorVerified: false,
    }),
    mismatchedCommand: lab.dispatchSynthesis(inference, {
      ...completeSyntheticEvidence,
      commandHash: "0".repeat(64),
    }),
    completeSyntheticEvidence: lab.dispatchSynthesis(
      inference,
      completeSyntheticEvidence,
    ),
  };
}
