import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";

export interface IP_1to1_Receipt {
  sandboxId: string;
  codebaseRootHash: string;
  canonicalRootHash: string;
  isMatch: boolean;
  timestamp: number;
  ipAssetId: string;
  filesHashed: number;
}

export interface CanonicalResolver {
  (): Promise<string>;
}

export class IP_OneToOne_Engine {
  public static async searchAndFind(
    rootDir: string,
    sandboxId: string,
    canonicalRootHashOrResolver: string | CanonicalResolver,
  ): Promise<IP_1to1_Receipt> {
    if (!fs.statSync(rootDir).isDirectory()) throw new Error("QUARANTINED: sandbox root is not a directory");
    const files = this.getAllFiles(rootDir);
    const entries = files.map((file) => {
      const relative = path.relative(rootDir, file).split(path.sep).join("/");
      const digest = createHash("sha256").update(fs.readFileSync(file)).digest("hex");
      return relative + ":" + digest;
    }).sort();

    const codebaseRootHash = createHash("sha256").update(entries.join("\n")).digest("hex");
    const canonicalRootHash = typeof canonicalRootHashOrResolver === "function"
      ? await canonicalRootHashOrResolver()
      : canonicalRootHashOrResolver;
    if (!/^([0-9a-f]{64}|0x[0-9a-f]{64})$/i.test(canonicalRootHash)) {
      throw new Error("QUARANTINED: canonical root is not a valid SHA-256 commitment");
    }
    const normalized = canonicalRootHash.replace(/^0x/i, "").toLowerCase();
    const isMatch = codebaseRootHash === normalized;
    return {
      sandboxId,
      codebaseRootHash,
      canonicalRootHash: normalized,
      isMatch,
      timestamp: Date.now(),
      ipAssetId: "iP-" + codebaseRootHash.slice(0, 16),
      filesHashed: files.length,
    };
  }

  private static getAllFiles(dirPath: string, output: string[] = []): string[] {
    for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
      const fullPath = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
        if ([".git", "node_modules", "coverage", "dist", ".circleci"].includes(entry.name)) continue;
        this.getAllFiles(fullPath, output);
      } else if (entry.isFile()) {
        if ([".env", ".env.local", ".env.production"].includes(entry.name)) continue;
        output.push(fullPath);
      }
    }
    return output;
  }
}
