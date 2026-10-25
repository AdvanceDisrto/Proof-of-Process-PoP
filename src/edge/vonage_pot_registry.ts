export type VonageSurface =
  | "IDENTITY_SECURITY"
  | "MESSAGING"
  | "VOICE"
  | "VIDEO"
  | "NETWORK"
  | "PLATFORM_AI";

export type IntegrationState = "VERIFIED_PROCESS" | "ACTION_REQUIRED" | "QUARANTINED";

export interface VonageInvention {
  id: string;
  name: string;
  surface: VonageSurface;
  requiredCapabilities: string[];
  evidence: string[];
  failClosedState: IntegrationState;
}

type InventionSpec = readonly [string, VonageSurface, string[]];

const INVENTION_SPECS: readonly InventionSpec[] = [
  ["Autonomous KYC/AML Corridor","IDENTITY_SECURITY",["Subscriber Match","Age Verification"]],
  ["Sovereign Device Reissuance","IDENTITY_SECURITY",["SIM Swap Insight","Silent Authentication"]],
  ["Ephemeral Location-Bound Identities","IDENTITY_SECURITY",["Location Verification"]],
  ["Proof-of-Humanity Handshake","IDENTITY_SECURITY",["Subscriber Tenure","Scam Signal"]],
  ["Zero-Knowledge Age Gate","IDENTITY_SECURITY",["Age Verification"]],
  ["Bi-Directional Clinical Trial Telemetry","MESSAGING",["RCS","Messages API"]],
  ["Epistemic Alert Cascade","MESSAGING",["Scam Signal","Reachability","SMS","WhatsApp"]],
  ["Micro-Ledger Payments","MESSAGING",["RCS","WhatsApp"]],
  ["Chain-of-Custody Cold Chain Alerts","MESSAGING",["Messages API"]],
  ["Universal Proof-of-Receipt","MESSAGING",["Messages API","read receipts"]],
  ["Autonomous Triage Voice Agent","VOICE",["ASR","Programmable Voice","TTS"]],
  ["Voice-Biometric Hash Verification","VOICE",["Real-time audio streaming","Speech"]],
  ["Synthetic Voice Emergency Fallback","VOICE",["TTS","Programmable Voice"]],
  ["Real-Time FDA Call Audit","VOICE",["SIP Trunking","ASR"]],
  ["Voice-Keyed Hardware Unlock","VOICE",["Voice recognition","Programmable Voice"]],
  ["Automated Telehealth Receipts","VIDEO",["Video API","Experience Composer"]],
  ["Remote Surgeon-in-the-Loop","VIDEO",["Video API","real-time feed"]],
  ["Interactive Epidemic Briefing Room","VIDEO",["Experience Composer","HLS/RTMP"]],
  ["Multi-Party Consent Anchor","VIDEO",["Video API","digital consent"]],
  ["Evidence-Based Patient Intake","VIDEO",["Video API","media evidence"]],
  ["Critical Command 5G Slicing","NETWORK",["Quality on Demand"]],
  ["Spoof-Proof Drone Dispatch","NETWORK",["Device Location Retrieval"]],
  ["Population Density-Based Lab Routing","NETWORK",["Network Insights"]],
  ["Latency-Sensitive Surgical Control","NETWORK",["Quality on Demand","Video"]],
  ["Geofenced Lab Actuation","NETWORK",["Device Location Retrieval"]],
  ["AI Studio for Regulatory Onboarding","PLATFORM_AI",["AI Studio"]],
  ["MCP-Connected Lab Orchestrator","PLATFORM_AI",["MCP Server"]],
  ["Redact API for Privacy-Preserving Anchors","PLATFORM_AI",["Redact API"]],
  ["Fraud Defender for Outbreak Scenarios","PLATFORM_AI",["Fraud Defender"]],
  ["Audit API for Automated Compliance","PLATFORM_AI",["Audit API"]],
];

export const VONAGE_POT_INVENTIONS: readonly VonageInvention[] =
  INVENTION_SPECS.map(([name, surface, requiredCapabilities], i) => ({
    id: `VONAGE-POT-${String(i + 1).padStart(2, "0")}`,
    name,
    surface,
    requiredCapabilities,
    evidence: ["provider response", "cryptographic binding", "receipt"],
    failClosedState: "ACTION_REQUIRED",
  }));

export function evaluateVonageEvidence(
  invention: VonageInvention,
  providerAvailable: boolean,
  cryptographicallyBound: boolean,
): IntegrationState {
  if (!providerAvailable) return "ACTION_REQUIRED";
  if (!cryptographicallyBound) return "QUARANTINED";
  return invention.failClosedState === "ACTION_REQUIRED"
    ? "VERIFIED_PROCESS"
    : invention.failClosedState;
}
