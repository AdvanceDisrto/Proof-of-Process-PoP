import { createHash } from "node:crypto";

export type TeeTier = "MOBILE_TRUSTZONE" | "AMD_SEV_SNP" | "INTEL_TDX" | "ACCELERATED_GPU";

export interface VerifiedTeeEvidence {
  tier: TeeTier;
  measurement: string;
  quoteDigest: string;
  verified: true;
}

export class AttestationEvidence {
  public static acceptVerifiedQuote(tier: TeeTier, rawQuote: Uint8Array, measurement: string, verifierAccepted: boolean): VerifiedTeeEvidence {
    if (!verifierAccepted || rawQuote.byteLength === 0 || !/^[a-f0-9]{64}$/i.test(measurement)) {
      throw new Error("ACTION_REQUIRED: TEE quote has not been independently verified");
    }
    return {
      tier,
      measurement: measurement.toLowerCase(),
      quoteDigest: createHash("sha256").update(rawQuote).digest("hex"),
      verified: true,
    };
  }
}
