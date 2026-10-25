import {
  createHash,
  createPublicKey,
  createVerify,
  type KeyObject,
} from "node:crypto";

export type AuthorType =
  | "PHYSICS" | "GEOLOGY" | "BIOLOGY" | "HUMAN" | "MACHINE" | "CIVILIZATION";

export type LedgerType =
  | "SPACETIME" | "CRUST" | "GENOME" | "PAPER" | "BLOCKCHAIN" | "GALAXY";

export type SignatureFormat =
  | "CMB_RADIATION" | "GRAVITATIONAL_WAVE" | "SPECTRAL_LINES"
  | "STRATIGRAPHY" | "FOSSIL" | "DNA_BASE_PAIR" | "BIOMETRIC"
  | "HANDWRITTEN_MARK" | "SEAL" | "ELECTRONIC_SIGNATURE"
  | "ED25519" | "MACHINE_RECEIPT" | "C2PA" | "TECHNOSIGNATURE";

export interface UniversalSignature {
  author: AuthorType;
  signatureFormat: SignatureFormat;
  imprintData: string;
  ledger: LedgerType;
  observedAt?: string;
  sourceId?: string;
  evidenceHash?: string;
  publicKey?: string;
  signature?: string;
  signedPayload?: string;
}

export type VerificationStatus =
  | "VERIFIED" | "UNVERIFIED_INFERENCE" | "PENDING" | "ACTION_REQUIRED" | "QUARANTINED";

export interface VerificationResult {
  status: VerificationStatus;
  verified: boolean;
  reason: string;
  evidenceHash?: string;
}

export interface SignatureVerifier {
  verify(signature: UniversalSignature): VerificationResult;
}

const FORMAT_LEDGER: Record<SignatureFormat, LedgerType[]> = {
  CMB_RADIATION: ["SPACETIME"],
  GRAVITATIONAL_WAVE: ["SPACETIME"],
  SPECTRAL_LINES: ["SPACETIME"],
  STRATIGRAPHY: ["CRUST"],
  FOSSIL: ["CRUST"],
  DNA_BASE_PAIR: ["GENOME"],
  BIOMETRIC: ["GENOME"],
  HANDWRITTEN_MARK: ["PAPER"],
  SEAL: ["PAPER"],
  ELECTRONIC_SIGNATURE: ["PAPER", "BLOCKCHAIN"],
  ED25519: ["BLOCKCHAIN", "PAPER"],
  MACHINE_RECEIPT: ["BLOCKCHAIN", "PAPER"],
  C2PA: ["BLOCKCHAIN", "PAPER"],
  TECHNOSIGNATURE: ["GALAXY"],
};

const AUTHOR_FORMATS: Record<AuthorType, SignatureFormat[]> = {
  PHYSICS: ["CMB_RADIATION", "GRAVITATIONAL_WAVE", "SPECTRAL_LINES"],
  GEOLOGY: ["STRATIGRAPHY", "FOSSIL"],
  BIOLOGY: ["DNA_BASE_PAIR", "BIOMETRIC"],
  HUMAN: ["HANDWRITTEN_MARK", "SEAL", "ELECTRONIC_SIGNATURE", "ED25519", "BIOMETRIC"],
  MACHINE: ["ED25519", "MACHINE_RECEIPT", "C2PA"],
  CIVILIZATION: ["TECHNOSIGNATURE"],
};

function sha256(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function structuralValidation(sig: UniversalSignature): VerificationResult | null {
  if (!sig.imprintData || sig.imprintData.trim().length === 0) {
    return { status: "ACTION_REQUIRED", verified: false, reason: "Signature imprint is empty." };
  }

  if (!AUTHOR_FORMATS[sig.author]?.includes(sig.signatureFormat)) {
    return {
      status: "QUARANTINED",
      verified: false,
      reason: \`Signature format \${sig.signatureFormat} is not valid for author \${sig.author}.\`,
    };
  }

  if (!FORMAT_LEDGER[sig.signatureFormat]?.includes(sig.ledger)) {
    return {
      status: "QUARANTINED",
      verified: false,
      reason: \`Ledger \${sig.ledger} is not valid for signature format \${sig.signatureFormat}.\`,
    };
  }

  const evidenceHash = sha256(sig.imprintData);
  if (sig.evidenceHash && sig.evidenceHash !== evidenceHash) {
    return {
      status: "QUARANTINED",
      verified: false,
      reason: "Evidence hash does not match the observed imprint.",
      evidenceHash,
    };
  }

  return { status: "PENDING", verified: false, reason: "Awaiting domain evidence.", evidenceHash };
}

export class Ed25519SignatureVerifier implements SignatureVerifier {
  verify(signature: UniversalSignature): VerificationResult {
    const structural = structuralValidation(signature);
    if (structural?.status === "QUARANTINED" || structural?.status === "ACTION_REQUIRED") return structural;

    if (!signature.publicKey || !signature.signature || signature.signedPayload === undefined) {
      return {
        status: "ACTION_REQUIRED",
        verified: false,
        reason: "Cryptographic signature requires publicKey, signature, and signedPayload.",
        evidenceHash: structural?.evidenceHash,
      };
    }

    try {
      const publicKey: KeyObject = createPublicKey(signature.publicKey);
      const verifier = createVerify("SHA256");
      verifier.update(signature.signedPayload, "utf8");
      verifier.end();
      const valid = verifier.verify(publicKey, Buffer.from(signature.signature, "base64"));

      return {
        status: valid ? "VERIFIED" : "QUARANTINED",
        verified: valid,
        reason: valid
          ? "Ed25519 signature verified against the supplied payload."
          : "Ed25519 signature verification failed.",
        evidenceHash: structural?.evidenceHash,
      };
    } catch (error) {
      return {
        status: "QUARANTINED",
        verified: false,
        reason: \`Cryptographic verification failed: \${error instanceof Error ? error.message : String(error)}\`,
        evidenceHash: structural?.evidenceHash,
      };
    }
  }
}

export class EvidenceAdapterVerifier implements SignatureVerifier {
  public constructor(
    private readonly adapter: (signature: UniversalSignature) => VerificationResult,
  ) {}

  verify(signature: UniversalSignature): VerificationResult {
    const structural = structuralValidation(signature);
    if (structural?.status === "QUARANTINED" || structural?.status === "ACTION_REQUIRED") return structural;
    const result = this.adapter(signature);
    return { ...result, evidenceHash: result.evidenceHash ?? structural?.evidenceHash };
  }
}

export class UniversalSignatureEngine {
  private readonly cryptographicVerifier = new Ed25519SignatureVerifier();

  public verifySignature(signature: UniversalSignature): VerificationResult {
    const structural = structuralValidation(signature);
    if (structural?.status === "QUARANTINED" || structural?.status === "ACTION_REQUIRED") return structural;

    switch (signature.signatureFormat) {
      case "ED25519":
      case "MACHINE_RECEIPT":
      case "C2PA":
        return this.cryptographicVerifier.verify(signature);
      default:
        return {
          status: "PENDING",
          verified: false,
          reason: \`Domain evidence adapter required for \${signature.signatureFormat}; the engine will not fabricate verification.\`,
          evidenceHash: structural?.evidenceHash,
        };
    }
  }

  public verifyWith(signature: UniversalSignature, verifier: SignatureVerifier): VerificationResult {
    return verifier.verify(signature);
  }

  public static hashImprint(imprintData: string): string {
    return sha256(imprintData);
  }
}
