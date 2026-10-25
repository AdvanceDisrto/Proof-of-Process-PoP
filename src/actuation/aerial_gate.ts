import {
  A2A_AerialGate,
  type AerialActuationBundle,
  type AerialGateState,
} from "./a2a_aerial_gate.js";

export interface AerialSafetyReceipt {
  batteryLevel: number;
  windShearStatus: "STABLE" | "CRITICAL";
  altitude: number;
  velocity?: number;
  tiltDegrees?: number;
}

export interface AerialEvidenceBundle {
  operatorId: string;
  commandHash: string;
  droneTeeQuote: string | null;
  aerialSafetyReceipt: AerialSafetyReceipt;
  locationQuorumProof?: string;
  a2aWitnesses?: AerialActuationBundle["a2aWitnesses"];
}

export class AerialActuationGate {
  public static validateAerialCommand(bundle: AerialEvidenceBundle): AerialGateState {
    if (!bundle.operatorId || !bundle.commandHash) return "ACTION_REQUIRED";

    const witnesses = bundle.a2aWitnesses ?? [];
    const result = A2A_AerialGate.validateA2ACommand({
      operatorId: bundle.operatorId,
      commandHash: bundle.commandHash,
      a2aWitnesses: witnesses,
      flightTelemetry: {
        batteryLevel: bundle.aerialSafetyReceipt.batteryLevel,
        windShear: bundle.aerialSafetyReceipt.windShearStatus,
      },
    });

    if (result === "QUARANTINED") return result;
    if (result === "ACTION_REQUIRED") return result;

    if (!Number.isFinite(bundle.aerialSafetyReceipt.altitude) ||
        bundle.aerialSafetyReceipt.altitude < 0) return "ACTION_REQUIRED";

    return "AERIAL_DISPATCH_VERIFIED";
  }
}
