import type { KernelRequest, KernelDispatch } from "./iKerNeL.js";

export interface EvidenceRecord {
  artifactId: string;
  artifactSha256: string;
  runtimeVersion: string;
  outputSha256: string;
  completedAt: string;
  compute: { device: string; driver: string; memoryBytes: number };
  networkMode: string;
  artifactBytes: number;
  status: string;
  environmentHash: string;
  reproductionCommand: string;
}

export interface IProofReceipt {
  protocol: "IPROOF-v1";
  evidenceId: string;
  requestId: string;
  execution: {
    artifact_sha256: string;
    output_sha256: string;
    runtime_version: string;
    completed_at: string;
    compute: EvidenceRecord["compute"];
    network_mode: string;
    artifact_bytes: number;
    status: string;
    environment_hash: string;
  };
  reproduction: {
    required: true;
    command: string;
  };
}

const SHA256_RE = /^sha256:[a-f0-9]{64}$/;

function assertSha256(field: string, value: string): void {
  if (!SHA256_RE.test(value)) {
    throw new Error(
      `incomplete SHA-256: ${field} must be sha256:<64 hex chars>, got ${value}`,
    );
  }
}

export function buildEvidence(
  request: KernelRequest,
  _dispatch: KernelDispatch,
  evidence: EvidenceRecord,
  evidenceId: string,
): IProofReceipt {
  assertSha256("artifactSha256", evidence.artifactSha256);
  assertSha256("outputSha256", evidence.outputSha256);
  assertSha256("environmentHash", evidence.environmentHash);

  return {
    protocol: "IPROOF-v1",
    evidenceId,
    requestId: request.requestId,
    execution: {
      artifact_sha256: evidence.artifactSha256,
      output_sha256: evidence.outputSha256,
      runtime_version: evidence.runtimeVersion,
      completed_at: evidence.completedAt,
      compute: evidence.compute,
      network_mode: evidence.networkMode,
      artifact_bytes: evidence.artifactBytes,
      status: evidence.status,
      environment_hash: evidence.environmentHash,
    },
    reproduction: {
      required: true,
      command: evidence.reproductionCommand,
    },
  };
}
