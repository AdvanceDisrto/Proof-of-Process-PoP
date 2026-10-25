export type ChainId = "BITCOIN_OTS" | "ETHEREUM_EAS" | "POLYGON_EAS" | "SOLANA" | "L2";

export type AnchorState = "VERIFIED" | "PENDING" | "QUARANTINED";

export interface ChainAttestation {
  chain: ChainId;
  subjectHash: string;
  confirmed: boolean;
  evidenceRef: string;
}

export interface QuorumPolicy {
  requiredDistinctChains: number;
}

export interface QuorumResult {
  state: AnchorState;
  subjectHash: string;
  confirmedChains: ChainId[];
  missingChains: ChainId[];
}

export class MultiChainAnchorEngine {
  public static validateHash(subjectHash: string): void {
    if (!/^[a-fA-F0-9]{64}$/.test(subjectHash)) {
      throw new Error("ANCHOR ERROR: subject hash must be exactly 64 hex characters");
    }
  }

  public evaluate(
    subjectHash: string,
    attestations: ChainAttestation[],
    policy: QuorumPolicy = { requiredDistinctChains: 2 },
  ): QuorumResult {
    MultiChainAnchorEngine.validateHash(subjectHash);
    if (!Number.isInteger(policy.requiredDistinctChains) || policy.requiredDistinctChains < 1) {
      throw new Error("ANCHOR ERROR: quorum must be a positive integer");
    }

    const relevant = attestations.filter((a) => a.subjectHash === subjectHash);
    const mismatches = attestations.some((a) => a.subjectHash !== subjectHash);
    if (mismatches) {
      return { state: "QUARANTINED", subjectHash, confirmedChains: [], missingChains: [] };
    }

    const confirmedChains = [...new Set(
      relevant.filter((a) => a.confirmed && a.evidenceRef.length > 0).map((a) => a.chain),
    )];

    if (confirmedChains.length >= policy.requiredDistinctChains) {
      return { state: "VERIFIED", subjectHash, confirmedChains, missingChains: [] };
    }

    const allChains = [...new Set(relevant.map((a) => a.chain))];
    return {
      state: "PENDING",
      subjectHash,
      confirmedChains,
      missingChains: allChains.filter((c) => !confirmedChains.includes(c)),
    };
  }
}
