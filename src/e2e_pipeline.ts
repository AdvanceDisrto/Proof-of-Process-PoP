import { RootCauseAgent } from "./agentic_core/root_cause_agent.js";
import { LabAutomationAPI } from "./translation/lab_automation_api.js";

export function runE2EPipeline() {
  const fabricPayload = "Patient_EHR_Data_Block_101";
  const inference = new RootCauseAgent().analyze(fabricPayload);
  const lab = new LabAutomationAPI();

  return {
    inference,
    noTee: lab.dispatchSynthesis(inference, null),
    validTee: lab.dispatchSynthesis(inference, "TEST-TEE-ATTESTATION"),
  };
}
