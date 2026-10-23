import crypto from "node:crypto";

export const SSN_SPEC = "innovulis-ssn-privacy-boundary/1.0";
const SSN_PATTERN = /(?<!\d)(?:\d{3}-\d{2}-\d{4}|\d{9})(?!\d)/g;

export interface SSNTokenPayload {
  spec: string;
  executionId: string;
  nonceB64: string;
  ciphertextB64: string;
  valueCommitment: string;
}

export interface SanitizedSSN {
  text: string;
  tokenMap: Record<string, SSNTokenPayload>;
  receipt: Record<string, unknown>;
}

function canonical(value: unknown): Buffer {
  return Buffer.from(JSON.stringify(value, Object.keys(value as object).sort()));
}

function deriveKey(masterKey: Buffer, executionId: string, purpose: string): Buffer {
  if (masterKey.length !== 32) throw new Error("SSN master key must be 32 bytes");
  return Buffer.from(
    crypto.hkdfSync(
      "sha256",
      masterKey,
      Buffer.alloc(0),
      Buffer.from("innovulis-ssn/v1:" + purpose + ":" + executionId),
      32,
    ),
  );
}

export class SSNBoundary {
  constructor(private readonly masterKey: Buffer) {
    if (masterKey.length !== 32) throw new Error("SSN master key must be 32 bytes");
  }

  sanitize(text: string, executionId: string): SanitizedSSN {
    const tokenMap: Record<string, SSNTokenPayload> = {};
    const output: string[] = [];
    let cursor = 0;
    SSN_PATTERN.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = SSN_PATTERN.exec(text)) !== null) {
      output.push(text.slice(cursor, match.index));
      const token = "[SSN_TOKEN_" + crypto.randomBytes(16).toString("hex") + "]";
      const nonce = crypto.randomBytes(12);
      const aad = canonical({ executionId, spec: SSN_SPEC, token });
      const cipher = crypto.createCipheriv(
        "aes-256-gcm",
        deriveKey(this.masterKey, executionId, "encryption"),
        nonce,
      );
      cipher.setAAD(aad);
      const ciphertext = Buffer.concat([cipher.update(match[0], "utf8"), cipher.final()]);
      const tag = cipher.getAuthTag();
      const commitment = crypto
        .createHmac("sha256", deriveKey(this.masterKey, executionId, "commitment"))
        .update(match[0], "utf8")
        .digest("hex");
      tokenMap[token] = {
        spec: SSN_SPEC,
        executionId,
        nonceB64: nonce.toString("base64"),
        ciphertextB64: Buffer.concat([ciphertext, tag]).toString("base64"),
        valueCommitment: "hmac-sha256:" + commitment,
      };
      output.push(token);
      cursor = match.index + match[0].length;
    }
    output.push(text.slice(cursor));
    const sanitized = output.join("");
    return {
      text: sanitized,
      tokenMap,
      receipt: {
        spec: "innovulis-ssn-receipt/1.0",
        executionId,
        tokenCount: Object.keys(tokenMap).length,
        sanitizedTextHash: "sha256:" + crypto.createHash("sha256").update(sanitized).digest("hex"),
        physicalGate: "ACTION_REQUIRED",
        doesNotProve: [
          "a formal zero-knowledge proof",
          "provider isolation outside this local boundary",
          "physical TPM-backed key custody",
          "SSN ownership or SSA validation",
        ],
      },
    };
  }

  static revealIntentHash(executionId: string, token: string): string {
    const body = JSON.stringify({ action: "reveal_ssn", executionId, spec: SSN_SPEC, token });
    return "sha256:" + crypto.createHash("sha256").update(body).digest("hex");
  }
}
