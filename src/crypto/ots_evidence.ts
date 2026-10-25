export interface VerifiedOtsEvidence {
  payloadHash: string;
  bitcoinBlockHeight: number;
  verified: true;
}

export class OtsEvidence {
  public static acceptVerifiedProof(payloadHash: string, bitcoinBlockHeight: number, verifierAccepted: boolean): VerifiedOtsEvidence {
    if (!/^[a-f0-9]{64}$/i.test(payloadHash) || !Number.isSafeInteger(bitcoinBlockHeight) || bitcoinBlockHeight <= 0 || !verifierAccepted) {
      throw new Error("ACTION_REQUIRED: OTS proof is not independently Bitcoin-verified");
    }
    return { payloadHash: payloadHash.toLowerCase(), bitcoinBlockHeight, verified: true };
  }
}
