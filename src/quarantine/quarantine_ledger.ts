import { createHash } from "node:crypto";

export type QuarantineReason =
  | "MISSING_TEE_ATTESTATION"
  | "MISSING_OTS_ANCHOR"
  | "ACTUATOR_INTERLOCK_UNHEALTHY"
  | "COMMAND_HASH_MISMATCH";

export interface QuarantineRecord {
  contentHash: string;
  originNodeId: string;
  reason: QuarantineReason;
  payload: unknown;
  observedAt: string;
}

export class QuarantineLedger {
  private readonly records = new Map<string, QuarantineRecord>();

  public append(originNodeId: string, reason: QuarantineReason, payload: unknown, observedAt: string): QuarantineRecord {
    const canonical = JSON.stringify({ originNodeId, reason, payload, observedAt });
    const contentHash = createHash("sha256").update(canonical).digest("hex");
    const record = { contentHash, originNodeId, reason, payload, observedAt };
    this.records.set(contentHash, record);
    return record;
  }

  public get(contentHash: string): QuarantineRecord | undefined {
    return this.records.get(contentHash);
  }
}
