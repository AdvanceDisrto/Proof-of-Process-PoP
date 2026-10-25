export type AerialGateState =
  | "AERIAL_DISPATCH_VERIFIED"
  | "ACTION_REQUIRED"
  | "QUARANTINED";

export interface A2AObservation {
  agentId: string;
  observedCommandHash: string;
  radioToF_Distance: number;
  signature: string;
}

export interface AerialActuationBundle {
  operatorId: string;
  commandHash: string;
  a2aWitnesses: A2AObservation[];
  flightTelemetry: {
    batteryLevel: number;
    windShear: "STABLE" | "CRITICAL";
  };
}

export class A2A_AerialGate {
  public static validateA2ACommand(
    bundle: AerialActuationBundle,
    requiredWitnesses = 3,
  ): AerialGateState {
    if (!bundle.operatorId || !bundle.commandHash) return "ACTION_REQUIRED";
    if (!Number.isInteger(requiredWitnesses) || requiredWitnesses < 3) {
      throw new Error("A2A_POLICY_REJECTED: witness quorum must be at least 3");
    }

    const witnesses = bundle.a2aWitnesses ?? [];
    if (witnesses.length < requiredWitnesses) return "ACTION_REQUIRED";

    const unique = new Set<string>();
    for (const witness of witnesses) {
      if (!witness.agentId || !witness.signature) return "ACTION_REQUIRED";
      if (!Number.isFinite(witness.radioToF_Distance) || witness.radioToF_Distance < 0) {
        return "QUARANTINED";
      }
      if (unique.has(witness.agentId)) continue;
      unique.add(witness.agentId);
      if (witness.observedCommandHash !== bundle.commandHash) return "QUARANTINED";
    }

    if (bundle.flightTelemetry.windShear === "CRITICAL") return "QUARANTINED";
    if (!Number.isFinite(bundle.flightTelemetry.batteryLevel) ||
        bundle.flightTelemetry.batteryLevel < 20) return "QUARANTINED";
    if (unique.size < requiredWitnesses) return "ACTION_REQUIRED";

    return "AERIAL_DISPATCH_VERIFIED";
  }
}
