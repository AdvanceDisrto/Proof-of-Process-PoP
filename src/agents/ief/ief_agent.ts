import { createHash } from "node:crypto";

export enum iEfCode {
  ICOPM_HASH_MISMATCH = "iEf-101",
  UNAUTHORIZED_OPERATOR = "iEf-102",
  STALE_MANIFEST = "iEf-103",
  KRAG_GPU_OVERHEAT = "iEf-201",
  CLUSTER_ORPHANED = "iEf-202",
  PROVIDER_API_TIMEOUT = "iEf-203",
  OTS_ANCHOR_FAILED = "iEf-301",
  QUORUM_NOT_MET = "iEf-302",
  TEE_QUOTE_MISSING = "iEf-401",
  ACTUATOR_JAMMED = "iEf-402",
  COMMAND_HASH_MISMATCH = "iEf-403",
}

export type iEfAction = "HALTED" | "SLASHED" | "QUARANTINED" | "RESTARTED";

export interface FailureProvenanceReceipt {
  spec: "iEf-failure/v1";
  errorCode: iEfCode;
  nodeId: string;
  reason: string;
  timestamp: number;
  actionTaken: iEfAction;
  failureHash: string;
  anchor: { status: "absent" | "submitted"; txHash?: string; chain?: string };
}

export interface FailureRemediator {
  remediate(action: iEfAction, nodeId: string, code: iEfCode, reason: string): Promise<void>;
}

export interface FailureAnchor {
  submit(failureHash: string): Promise<{ status: "submitted"; chain: string; txHash: string }>;
}

export class NoopFailureRemediator implements FailureRemediator {
  async remediate(): Promise<void> {}
}

export class iEfAgent {
  public static determineRemediation(code: iEfCode): iEfAction {
    if (code === iEfCode.ICOPM_HASH_MISMATCH || code === iEfCode.UNAUTHORIZED_OPERATOR || code === iEfCode.STALE_MANIFEST) {
      return "SLASHED";
    }
    if (code === iEfCode.KRAG_GPU_OVERHEAT || code === iEfCode.PROVIDER_API_TIMEOUT) return "RESTARTED";
    if (code === iEfCode.CLUSTER_ORPHANED) return "QUARANTINED";
    if (code === iEfCode.OTS_ANCHOR_FAILED || code === iEfCode.QUORUM_NOT_MET) return "HALTED";
    if (code === iEfCode.TEE_QUOTE_MISSING || code === iEfCode.ACTUATOR_JAMMED || code === iEfCode.COMMAND_HASH_MISMATCH) return "QUARANTINED";
    return "HALTED";
  }

  public static async handleFailure(
    code: iEfCode,
    nodeId: string,
    reason: string,
    remediator: FailureRemediator = new NoopFailureRemediator(),
    anchor?: FailureAnchor,
  ): Promise<FailureProvenanceReceipt> {
    const actionTaken = this.determineRemediation(code);
    await remediator.remediate(actionTaken, nodeId, code, reason);

    const timestamp = Date.now();
    const failureHash = createHash("sha256")
      .update("iEf-v1\0" + JSON.stringify({ code, nodeId, reason, timestamp }), "utf8")
      .digest("hex");

    let result: FailureProvenanceReceipt["anchor"] = { status: "absent" };
    if (anchor) {
      try {
        const submitted = await anchor.submit(failureHash);
        result = { status: "submitted", chain: submitted.chain, txHash: submitted.txHash };
      } catch {
        result = { status: "absent" };
      }
    }

    return {
      spec: "iEf-failure/v1",
      errorCode: code,
      nodeId,
      reason,
      timestamp,
      actionTaken,
      failureHash,
      anchor: result,
    };
  }
}
