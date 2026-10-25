import { createHash } from "node:crypto";
import type { ExecutionResult, PoPExecutionReceipt, ResourceRef, WorkloadRequest } from "./types.js";

export type AnchorStatus = "absent" | "submitted" | "confirmed" | "reorged";

export interface ChainReceipt {
  status: AnchorStatus;
  chain?: string;
  txHash?: string;
  confirmations?: number;
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return "[" + value.map(stableStringify).join(",") + "]";
  const obj = value as Record<string, unknown>;
  return "{" + Object.keys(obj).sort().map(k => JSON.stringify(k) + ":" + stableStringify(obj[k])).join(",") + "}";
}

function sha256(value: string): string {
  return "sha256:" + createHash("sha256").update(value).digest("hex");
}

const DOMAIN_RECEIPT = "iP-v2\x00";
const DOMAIN_MERKLE_LEAF = Buffer.from("iP-v2:merkle-leaf\x00");
const DOMAIN_MERKLE_NODE = Buffer.from("iP-v2:merkle-node\x00");

export function createExecutionReceipt(
  operation: string,
  resource: ResourceRef,
  workload?: WorkloadRequest,
  execution?: ExecutionResult,
  anchor?: ChainReceipt,
  prevReceiptHash: string | null = null,
): PoPExecutionReceipt & { anchor: ChainReceipt } {
  const body = {
    schema: "pop/compute-control-execution/v2" as const,
    operation,
    prevReceiptHash,
    resource,
    workload: workload ?? null,
    execution: execution ?? null,
    evidence: {
      requestHash: sha256(stableStringify({ operation, resource, workload: workload ?? null })),
      telemetryHash: execution ? sha256(stableStringify(execution)) : null,
      provenanceHash: workload?.gitCommit ? sha256(workload.gitCommit) : null,
    },
    anchor: anchor ?? { status: "absent" as const },
    state: execution?.exitCode === 0 && (anchor?.status ?? "absent") === "confirmed"
      ? "VERIFIED_PROCESS" as const
      : execution?.exitCode === 0
        ? "ACTION_REQUIRED" as const
        : "QUARANTINED" as const,
  };
  return { ...body, receiptHash: sha256(DOMAIN_RECEIPT + stableStringify(body)) };
}

export function merkleRoot(leaves: string[]): string {
  if (!leaves.length) throw new Error("empty receipt set");
  let level = leaves.map(h => createHash("sha256").update(Buffer.concat([
    DOMAIN_MERKLE_LEAF,
    Buffer.from(h.replace(/^sha256:/, ""), "hex"),
  ])).digest());
  while (level.length > 1) {
    const next: Buffer[] = [];
    for (let i = 0; i < level.length; i += 2) {
      const a = level[i], b = level[i + 1] ?? a;
      next.push(createHash("sha256").update(Buffer.concat([DOMAIN_MERKLE_NODE, a, b])).digest());
    }
    level = next;
  }
  return "sha256:" + Buffer.from(level[0]).toString("hex");
}
