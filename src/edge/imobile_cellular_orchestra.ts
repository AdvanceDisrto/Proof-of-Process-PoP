import { createHash } from "node:crypto";

export type OrchestraState = "VERIFIED_PROCESS" | "ACTION_REQUIRED" | "QUARANTINED";

export interface DeviceObservation {
  deviceId: string;
  payloadHash: string;
  teeQuoteVerified: boolean;
  cellId: string;
  signature: string;
}

export interface EdgeAttestation {
  cellId: string;
  gNodeBId: string;
  authorized: boolean;
  teeVerified: boolean;
  receiptHash: string;
}

export interface OrchestraReceipt {
  cellId: string;
  payloadHash: string;
  memberDeviceIds: string[];
  quorum: number;
  receiptHash: string;
  state: OrchestraState;
}

export class IMobileCellularOrchestra {
  public static receiptHash(cellId: string, payloadHash: string, deviceIds: string[]): string {
    return createHash("sha256")
      .update(JSON.stringify({ cellId, payloadHash, deviceIds: [...deviceIds].sort() }) ?? "")
      .digest("hex");
  }

  public aggregate(
    observations: DeviceObservation[],
    edge: EdgeAttestation,
    quorum: number,
  ): OrchestraReceipt {
    if (quorum < 1) throw new Error("ORCHESTRA ERROR: quorum must be positive");
    if (!edge.authorized || !edge.teeVerified) {
      return { cellId: edge.cellId, payloadHash: "", memberDeviceIds: [], quorum, receiptHash: "", state: "QUARANTINED" };
    }

    const eligible = observations.filter(
      (o) => o.cellId === edge.cellId && o.teeQuoteVerified && o.signature.length > 0,
    );
    const hashes = [...new Set(eligible.map((o) => o.payloadHash))];

    if (hashes.length !== 1) {
      return { cellId: edge.cellId, payloadHash: "", memberDeviceIds: [], quorum, receiptHash: "", state: "ACTION_REQUIRED" };
    }

    const memberDeviceIds = [...new Set(eligible.map((o) => o.deviceId))];
    if (memberDeviceIds.length < quorum) {
      return { cellId: edge.cellId, payloadHash: hashes[0], memberDeviceIds, quorum, receiptHash: "", state: "ACTION_REQUIRED" };
    }

    const receiptHash = IMobileCellularOrchestra.receiptHash(edge.cellId, hashes[0], memberDeviceIds);
    if (edge.receiptHash && edge.receiptHash !== receiptHash) {
      return { cellId: edge.cellId, payloadHash: hashes[0], memberDeviceIds, quorum, receiptHash, state: "QUARANTINED" };
    }

    return { cellId: edge.cellId, payloadHash: hashes[0], memberDeviceIds, quorum, receiptHash, state: "VERIFIED_PROCESS" };
  }
}
