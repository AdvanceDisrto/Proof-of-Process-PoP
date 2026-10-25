import { MultiChainAnchorEngine, type ChainAttestation, type QuorumPolicy, type QuorumResult } from "../anchor/multi_chain_attestation.js";

export type OracleProvider = "ALCHEMY" | "MORALIS" | "BLOCKCHAIR" | "BLOCKCHAIN_COM" | "KALEIDO";
export type OracleState = "VERIFIED_PROCESS" | "PENDING" | "QUARANTINED" | "ACTION_REQUIRED";

export interface AnchorRouteObservation {
  chain: string;
  available: boolean;
  confirmed: boolean;
  latencyMs: number;
  feeMetric: number;
}

export interface ProvenanceReport {
  isSafe: boolean;
  riskScore: number;
  flaggedWallets: string[];
}

export interface TimeCausalityEvidence {
  anchorTimestamp: number;
  executionTimestamp: number;
}

export interface RegulatoryReceipt {
  provider: "KALEIDO";
  event: "ASSP_GENESIS_SYNTHESIS_DISPATCH";
  proofHash: string;
  transactionId: string;
  verificationChain: string;
  timestamp: number;
  regulatoryStandard: "FDA-21-CFR-PART-11-DIGITAL-PROOFS";
}

export interface ChainOracleEvidence {
  subjectHash: string;
  provenance: ProvenanceReport;
  attestations: ChainAttestation[];
  time: TimeCausalityEvidence;
}

export interface ChainOracleResult {
  state: OracleState;
  selectedChain?: string;
  quorum: QuorumResult;
  regulatoryReceipt?: RegulatoryReceipt;
}

export class ChainOracle {
  public static routeAndAnchor(
    hypothesisHash: string,
    observations: AnchorRouteObservation[],
  ): { state: OracleState; selectedChain?: string } {
    MultiChainAnchorEngine.validateHash(hypothesisHash);
    const viable = observations
      .filter((x) => x.available && x.confirmed && Number.isFinite(x.latencyMs) && Number.isFinite(x.feeMetric))
      .sort((a, b) => (a.latencyMs + a.feeMetric) - (b.latencyMs + b.feeMetric));

    if (viable.length === 0) return { state: "PENDING" };
    return { state: "VERIFIED_PROCESS", selectedChain: viable[0].chain };
  }

  public static traceProvenance(report: ProvenanceReport): OracleState {
    if (!Number.isFinite(report.riskScore) || report.riskScore < 0 || report.riskScore > 100) {
      return "QUARANTINED";
    }
    if (!report.isSafe || report.flaggedWallets.length > 0) return "QUARANTINED";
    return "VERIFIED_PROCESS";
  }

  public static verifyQuorum(
    hypothesisHash: string,
    attestations: ChainAttestation[],
    policy: QuorumPolicy = { requiredDistinctChains: 2 },
  ): QuorumResult {
    return new MultiChainAnchorEngine().evaluate(hypothesisHash, attestations, policy);
  }

  public static auditTimeCausality(evidence: TimeCausalityEvidence): OracleState {
    if (!Number.isSafeInteger(evidence.anchorTimestamp) || !Number.isSafeInteger(evidence.executionTimestamp)) {
      return "QUARANTINED";
    }
    return evidence.anchorTimestamp <= evidence.executionTimestamp
      ? "VERIFIED_PROCESS"
      : "QUARANTINED";
  }

  public static buildRegulatoryReceipt(
    proofHash: string,
    transactionId: string,
    verificationChain: string,
    timestamp: number,
  ): RegulatoryReceipt {
    MultiChainAnchorEngine.validateHash(proofHash);
    if (!transactionId || !verificationChain || !Number.isSafeInteger(timestamp)) {
      throw new Error("ACTION_REQUIRED: incomplete regulatory anchor evidence");
    }
    return {
      provider: "KALEIDO",
      event: "ASSP_GENESIS_SYNTHESIS_DISPATCH",
      proofHash,
      transactionId,
      verificationChain,
      timestamp,
      regulatoryStandard: "FDA-21-CFR-PART-11-DIGITAL-PROOFS",
    };
  }

  public static evaluate(
    evidence: ChainOracleEvidence,
    policy: QuorumPolicy = { requiredDistinctChains: 2 },
  ): ChainOracleResult {
    MultiChainAnchorEngine.validateHash(evidence.subjectHash);

    const provenanceState = ChainOracle.traceProvenance(evidence.provenance);
    if (provenanceState !== "VERIFIED_PROCESS") {
      return {
        state: provenanceState,
        quorum: {
          state: "QUARANTINED",
          subjectHash: evidence.subjectHash,
          confirmedChains: [],
          missingChains: [],
        },
      };
    }

    const quorum = ChainOracle.verifyQuorum(evidence.subjectHash, evidence.attestations, policy);
    if (quorum.state === "QUARANTINED") return { state: "QUARANTINED", quorum };
    if (quorum.state !== "VERIFIED") return { state: "PENDING", quorum };

    const timeState = ChainOracle.auditTimeCausality(evidence.time);
    if (timeState !== "VERIFIED_PROCESS") return { state: timeState, quorum };

    return { state: "VERIFIED_PROCESS", quorum };
  }
}
