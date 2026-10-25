import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export type OtsStatus = "PENDING_BLOCK" | "ANCHORED_IN_LEDGER";

export interface OtsReceipt {
  contentHash: string;
  calendarUri: string;
  otsFilePath: string;
  status: OtsStatus;
}

export class OpenTimestampsEngine {
  public static readonly defaultCalendarUri =
    process.env.OTS_CALENDAR_URL ?? "http://127.0.0.1:14788";

  public static validateHash(contentHash: string): void {
    if (!/^[a-fA-F0-9]{64}$/.test(contentHash)) {
      throw new Error("OTS ERROR: content hash must be exactly 64 hex characters");
    }
  }

  public static buildStampArgs(calendarUri: string, filePath: string): string[] {
    if (!calendarUri || !filePath) {
      throw new Error("OTS ERROR: calendar URI and file path are required");
    }
    return ["stamp", "-c", calendarUri, filePath];
  }

  public static async stampFile(
    contentHash: string,
    filePath: string,
    calendarUri = this.defaultCalendarUri,
  ): Promise<OtsReceipt> {
    this.validateHash(contentHash);
    await fs.access(filePath);

    try {
      await execFileAsync(
        "ots",
        this.buildStampArgs(calendarUri, filePath),
        { timeout: 30_000 },
      );
    } catch {
      return {
        contentHash,
        calendarUri,
        otsFilePath: "",
        status: "PENDING_BLOCK",
      };
    }

    return {
      contentHash,
      calendarUri,
      otsFilePath: filePath + ".ots",
      status: "PENDING_BLOCK",
    };
  }

  public static async upgrade(
    otsFilePath: string,
  ): Promise<{ status: OtsStatus; otsFilePath: string }> {
    await fs.access(otsFilePath);

    try {
      await execFileAsync("ots", ["upgrade", otsFilePath], { timeout: 60_000 });
    } catch {
      return { status: "PENDING_BLOCK", otsFilePath };
    }

    return { status: "ANCHORED_IN_LEDGER", otsFilePath };
  }

  public static async verify(
    otsFilePath: string,
    expectedHash: string,
  ): Promise<boolean> {
    this.validateHash(expectedHash);
    await fs.access(otsFilePath);

    try {
      await execFileAsync("ots", ["verify", otsFilePath], { timeout: 60_000 });
      return true;
    } catch {
      return false;
    }
  }
}
