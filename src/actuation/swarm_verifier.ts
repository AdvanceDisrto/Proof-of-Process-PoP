export interface SwarmObservation {
  observerId: string;
  evidenceHash: string;
  signature: string;
  labSterile: boolean;
  labEmpty: boolean;
}

export interface SwarmVerification {
  independentObservers: string[];
  quorumRequired: number;
  quorumMet: boolean;
  state: "VERIFIED_PROCESS" | "ACTION_REQUIRED" | "QUARANTINED";
}

export class SwarmVerifier {
  public static verifyPhysicalLabState(
    observations: SwarmObservation[],
    requiredIndependent = 2,
  ): SwarmVerification {
    const seen = new Set<string>();
    const valid: string[] = [];
    let unsafe = false;

    for (const observation of observations) {
      if (
        !observation.observerId ||
        !observation.evidenceHash ||
        !observation.signature
      ) continue;
      if (!observation.labSterile || !observation.labEmpty) {
        unsafe = true;
        continue;
      }
      if (seen.has(observation.observerId)) continue;
      seen.add(observation.observerId);
      valid.push(observation.observerId);
    }

    if (unsafe) {
      return {
        independentObservers: valid,
        quorumRequired: requiredIndependent,
        quorumMet: false,
        state: "QUARANTINED",
      };
    }

    return {
      independentObservers: valid,
      quorumRequired: requiredIndependent,
      quorumMet: valid.length >= requiredIndependent,
      state: valid.length >= requiredIndependent ? "VERIFIED_PROCESS" : "ACTION_REQUIRED",
    };
  }
}
