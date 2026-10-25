import { createHash } from "node:crypto";

export interface GenesisSeedReceipt {
  payloadHash: string;
  meshId: string;
  connectivity: "OFFLINE";
  localOts: "SIMULATED";
  localTee: "REQUIRED";
  globalAnchor: "PENDING" | "VERIFIED_PROCESS";
  seedHash: string;
}

function hash(value: string): string {
  return `sha256:${createHash("sha256").update(value).digest("hex")}`;
}

/**
 * Offline receipt primitive. Local OTS/TEE are evidence requirements; this
 * reference implementation does not impersonate either physical service.
 */
export class GenesisSeedAgent {
  public static async generateOfflineReceipt(
    payload: unknown,
    meshId = "offline-mesh-0",
  ): Promise<GenesisSeedReceipt> {
    const payloadHash = hash(JSON.stringify(payload));
    const body = JSON.stringify({ payloadHash, meshId, connectivity: "OFFLINE" });
    return {
      payloadHash,
      meshId,
      connectivity: "OFFLINE",
      localOts: "SIMULATED",
      localTee: "REQUIRED",
      globalAnchor: "PENDING",
      seedHash: hash(body),
    };
  }

  public static attachGlobalAnchor(
    receipt: GenesisSeedReceipt,
    anchorReceiptHash: string,
  ): GenesisSeedReceipt {
    if (!/^sha256:[0-9a-f]{64}$/.test(anchorReceiptHash)) {
      throw new Error("GENESIS_SEED_REJECTED: invalid anchor receipt hash");
    }
    return {
      ...receipt,
      globalAnchor: "VERIFIED_PROCESS",
      seedHash: hash(JSON.stringify({ ...receipt, anchorReceiptHash })),
    };
  }
}
