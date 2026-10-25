/**
 * i™ Compute Control MCP — strict provenance foundation.
 *
 * This file proves exactly what it can prove:
 * - the accepted workload request,
 * - the reported execution result,
 * - the canonical payload hash,
 * - and the Ed25519 signature made by the configured signing key.
 *
 * It does NOT claim that a signature alone proves physical GPU execution.
 * A real provider executor/attestation must supply that evidence before the
 * receipt may be promoted to VERIFIED_PROCESS.
 */
import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import {
  createHash,
  createPrivateKey,
  createPublicKey,
  sign,
  type KeyObject,
} from "node:crypto";

const WorkloadSchema = z.object({
  provider: z.enum(["hyperstack", "runpod", "akash", "vast.ai"]),
  gitCommit: z.string().regex(/^[0-9a-f]{40}$/i),
  command: z.string().min(1).max(16_384),
  priority: z.enum(["cost", "reliability"]).default("reliability"),
}).strict();

type Workload = z.infer<typeof WorkloadSchema>;

interface ExecutionEvidence {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionId: string;
  physicalAttestation?: string;
}

interface ComputeExecutor {
  execute(workload: Workload): Promise<ExecutionEvidence>;
}

interface ReceiptPayload {
  provider: Workload["provider"];
  gitCommit: string;
  command: string;
  priority: Workload["priority"];
  stdoutHash: string;
  stderrHash: string;
  exitCode: number;
  executionId: string;
  timestampMs: number;
  state: "EXECUTION_REPORTED" | "VERIFIED_PROCESS";
  physicalAttestationHash?: string;
}

interface Receipt {
  receipt_version: "iP-v1.1.0";
  canonical_hash: string;
  signature: string;
  public_key: string;
  payload: ReceiptPayload;
}

function canonicalJson(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("NON_CANONICAL_NUMBER");
    return Object.is(value, -0) ? "0" : JSON.stringify(value);
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record).sort();
    return "{" + keys.map((key) => JSON.stringify(key) + ":" + canonicalJson(record[key])).join(",") + "}";
  }
  throw new Error("NON_CANONICAL_VALUE");
}

function sha256Utf8(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function loadSigningKey(): { privateKey: KeyObject; publicKeyPem: string } {
  const encoded = process.env.ITENSOR_ED25519_PRIVATE_KEY_PEM;
  if (!encoded) throw new Error("ACTION_REQUIRED: ITENSOR_ED25519_PRIVATE_KEY_PEM is not configured");
  const privateKey = createPrivateKey(encoded);
  if (privateKey.asymmetricKeyType !== "ed25519") {
    throw new Error("QUARANTINED: signing key is not Ed25519");
  }
  const publicKeyPem = createPublicKey(privateKey).export({ type: "spki", format: "pem" }).toString();
  return { privateKey, publicKeyPem };
}

class ProvenanceEngine {
  public constructor(
    private readonly privateKey: KeyObject,
    private readonly publicKeyPem: string,
  ) {}

  public receipt(workload: Workload, evidence: ExecutionEvidence): Receipt {
    const payload: ReceiptPayload = {
      provider: workload.provider,
      gitCommit: workload.gitCommit,
      command: workload.command,
      priority: workload.priority,
      stdoutHash: sha256Utf8(evidence.stdout),
      stderrHash: sha256Utf8(evidence.stderr),
      exitCode: evidence.exitCode,
      executionId: evidence.executionId,
      timestampMs: Date.now(),
      state: evidence.physicalAttestation ? "VERIFIED_PROCESS" : "EXECUTION_REPORTED",
      ...(evidence.physicalAttestation
        ? { physicalAttestationHash: sha256Utf8(evidence.physicalAttestation) }
        : {}),
    };

    const canonical = canonicalJson(payload);
    const canonicalHash = sha256Utf8(canonical);
    const signature = sign(null, Buffer.from(canonicalHash, "utf8"), this.privateKey).toString("base64");

    return {
      receipt_version: "iP-v1.1.0",
      canonical_hash: canonicalHash,
      signature,
      public_key: this.publicKeyPem,
      payload,
    };
  }
}

class UnconfiguredExecutor implements ComputeExecutor {
  public async execute(_workload: Workload): Promise<ExecutionEvidence> {
    throw new Error("ACTION_REQUIRED: no real provider executor is configured; refusing simulated execution");
  }
}

function createServer(executor: ComputeExecutor, engine: ProvenanceEngine): McpServer {
  const server = new McpServer({
    name: "compute-control-mcp",
    version: "1.1.0-singularity-foundation",
  });

  server.registerTool(
    "execute_workload",
    {
      description: "Execute a real provider workload and return a signed provenance receipt. Simulation is forbidden.",
      inputSchema: WorkloadSchema,
    },
    async (workload) => {
      try {
        const evidence = await executor.execute(workload);
        if (!evidence.executionId) {
          throw new Error("QUARANTINED: executor returned no executionId");
        }
        const receipt = engine.receipt(workload, evidence);
        return { content: [{ type: "text", text: JSON.stringify(receipt, null, 2) }] };
      } catch (error: unknown) {
        const reason = error instanceof Error ? error.message : "UNKNOWN_EXECUTION_FAILURE";
        console.error("[iEf] compute-control failure:", reason);
        return {
          isError: true,
          content: [{ type: "text", text: reason.startsWith("ACTION_REQUIRED:") || reason.startsWith("QUARANTINED:")
            ? reason
            : "ACTION_REQUIRED: Compute dispatch failed." }],
        };
      }
    },
  );

  return server;
}

const { privateKey, publicKeyPem } = loadSigningKey();
const engine = new ProvenanceEngine(privateKey, publicKeyPem);
const executor: ComputeExecutor = new UnconfiguredExecutor();

const server = createServer(executor, engine);
const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[iTensor] compute-control-mcp listening on stdio");
