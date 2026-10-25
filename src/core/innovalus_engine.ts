import { createHash } from "node:crypto";
import { route, type RouteRequest, type RouteDecision } from "./iKerNeL.js";

export interface ExecutionEvidence {
  artifactId: string;
  artifactSha256: string;
  runtimeVersion: string;
  outputSha256: string;
  completedAt: string;
  compute: { device: string; driver: string; memoryBytes: number };
  networkMode: string;
  artifactBytes: number;
  status: "PASS" | "FAIL" | "ACTION_REQUIRED" | "QUARANTINED";
  metrics?: Record<string, number | string | boolean | null>;
  environmentHash: string;
  reproductionCommand: string;
}

function sha256(value: string): string {
  return `sha256:${createHash("sha256").update(value, "utf8").digest("hex")}`;
}

function rejectPlaceholderHash(value: string, field: string): void {
  if (!/^sha256:[a-f0-9]{64}$/.test(value)) {
    throw new Error(`QUARANTINED: ${field} is not a complete SHA-256 evidence digest`);
  }
}

export interface IProofReceipt {
  protocol: "IPROOF-v1";
  evidence_id: string;
  intent: { request_sha256: string; intent_class: string };
  routing: {
    router_version: string;
    action_id: string;
    execution_class: RouteDecision["executionClass"];
    reason: string;
    module_ids: string[];
  };
  execution: {
    artifact_id: string;
    artifact_sha256: string;
    runtime_version: string;
    output_sha256: string;
    completed_at: string;
  };
  resources: {
    compute: { device: string; driver: string; memory_bytes: number };
    network: { mode: string };
    storage: { artifact_bytes: number };
  };
  result: { status: ExecutionEvidence["status"]; metrics?: ExecutionEvidence["metrics"] };
  reproduction: {
    required: true;
    command: string;
    environment_hash: string;
    expected_output_sha256: string;
  };
}

export function buildEvidence(request: RouteRequest, decision: RouteDecision, evidence: ExecutionEvidence, evidenceId: string): IProofReceipt {
  rejectPlaceholderHash(evidence.artifactSha256, "artifact_sha256");
  rejectPlaceholderHash(evidence.outputSha256, "output_sha256");
  rejectPlaceholderHash(evidence.environmentHash, "environment_hash");

  const intentHash = sha256(request.prompt);
  const receipt: IProofReceipt = {
    protocol: "IPROOF-v1",
    evidence_id: evidenceId,
    intent: { request_sha256: intentHash, intent_class: decision.actionId },
    routing: {
      router_version: "iKerNeL-v1.0",
      action_id: decision.actionId,
      execution_class: decision.executionClass,
      reason: decision.reason,
      module_ids: decision.modules
    },
    execution: {
      artifact_id: evidence.artifactId,
      artifact_sha256: evidence.artifactSha256,
      runtime_version: evidence.runtimeVersion,
      output_sha256: evidence.outputSha256,
      completed_at: evidence.completedAt
    },
    resources: {
      compute: { device: evidence.compute.device, driver: evidence.compute.driver, memory_bytes: evidence.compute.memoryBytes },
      network: { mode: evidence.networkMode },
      storage: { artifact_bytes: evidence.artifactBytes }
    },
    result: { status: evidence.status, metrics: evidence.metrics },
    reproduction: {
      required: true,
      command: evidence.reproductionCommand,
      environment_hash: evidence.environmentHash,
      expected_output_sha256: evidence.outputSha256
    }
  };
  return receipt;
}

export function decide(request: RouteRequest): RouteDecision {
  return route(request);
}
