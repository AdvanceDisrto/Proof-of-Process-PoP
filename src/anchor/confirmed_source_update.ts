import { createHash } from "node:crypto";

export interface ConfirmedAnchor {
  subjectHash: string;
  chain: string;
  txHash: string;
  confirmedAt: number;
  confirmations: number;
}

export interface SourceUpdate {
  path: string;
  previousHash: string | null;
  confirmedHash: string;
  chain: string;
  txHash: string;
  confirmedAt: number;
  state: "CONFIRMED";
}

export interface ConfirmationVerifier {
  verify(subjectHash: string): Promise<ConfirmedAnchor | null>;
}

export interface SourceWriter {
  update(update: SourceUpdate): Promise<void>;
}

export interface ConfirmationNotifier {
  notify(update: SourceUpdate): Promise<void>;
}

function validateHash(value: string, name: string): void {
  if (!/^[0-9a-f]{64}$/i.test(value)) throw new Error(name + " must be a SHA-256 hex digest");
}

export class ConfirmedAnchorSourceUpdater {
  public static async run(
    subjectHash: string,
    verifier: ConfirmationVerifier,
    writer: SourceWriter,
    notifier?: ConfirmationNotifier,
    path = "docs/ANCHOR_STATUS.json",
  ): Promise<SourceUpdate | null> {
    validateHash(subjectHash, "subjectHash");
    const confirmation = await verifier.verify(subjectHash);
    if (!confirmation) return null;

    validateHash(confirmation.subjectHash, "confirmed subjectHash");
    if (confirmation.subjectHash.toLowerCase() !== subjectHash.toLowerCase()) {
      throw new Error("QUARANTINED: confirmed subject hash does not match requested source update");
    }
    if (!confirmation.txHash || !confirmation.chain || !Number.isSafeInteger(confirmation.confirmedAt)) {
      throw new Error("ACTION_REQUIRED: incomplete chain confirmation evidence");
    }
    if (!Number.isSafeInteger(confirmation.confirmations) || confirmation.confirmations < 1) {
      throw new Error("ACTION_REQUIRED: confirmation count is not independently established");
    }

    const update: SourceUpdate = {
      path,
      previousHash: null,
      confirmedHash: confirmation.subjectHash.toLowerCase(),
      chain: confirmation.chain,
      txHash: confirmation.txHash,
      confirmedAt: confirmation.confirmedAt,
      state: "CONFIRMED",
    };

    await writer.update(update);
    if (notifier) await notifier.notify(update);
    return update;
  }

  public static contentHash(update: SourceUpdate): string {
    return createHash("sha256")
      .update("iEf-confirmed-source-v1\0" + JSON.stringify(update), "utf8")
      .digest("hex");
  }
}
