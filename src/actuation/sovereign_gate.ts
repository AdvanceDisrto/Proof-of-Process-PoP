import { createHash, verify } from "node:crypto";
import type { AerialActuationBundle } from "./a2a_aerial_gate.js";
import { A2A_AerialGate } from "./a2a_aerial_gate.js";

export type SovereignGateState =
  | "LAB_DISPATCH_VERIFIED"
  | "ACTION_REQUIRED"
  | "QUARANTINED";

export interface SovereignActuationBundle {
  agentCommandHash: string;
  a2aWitnessProof: AerialActuationBundle;
  humanAuthorization?: {
    operatorId: string;
    publicKey: object;
    signature: Buffer;
  };
  riskLevel: "LOW" | "HIGH";
}

function canonicalAgentIntent(bundle: SovereignActuationBundle): Buffer {
  return Buffer.from(JSON.stringify({
    commandHash: bundle.agentCommandHash,
    riskLevel: bundle.riskLevel,
    witnesses: bundle.a2aWitnessProof.a2aWitnesses.map((w) => ({
      agentId: w.agentId,
      observedCommandHash: w.observedCommandHash,
      radioToF_Distance: w.radioToF_Distance,
      signature: w.signature,
    })),
  }));
}

export class SovereignPhysicalGate {
  public static validate(bundle: SovereignActuationBundle): SovereignGateState {
    if (!bundle.agentCommandHash || !bundle.a2aWitnessProof) return "ACTION_REQUIRED";

    if (bundle.a2aWitnessProof.commandHash !== bundle.agentCommandHash) {
      return "QUARANTINED";
    }

    const agentState = A2A_AerialGate.validateA2ACommand(bundle.a2aWitnessProof);
    if (agentState !== "AERIAL_DISPATCH_VERIFIED") return "ACTION_REQUIRED";

    if (bundle.riskLevel === "HIGH") {
      const human = bundle.humanAuthorization;
      if (!human || !human.operatorId || !human.publicKey || !human.signature) {
        return "ACTION_REQUIRED";
      }

      const message = canonicalAgentIntent(bundle);
      const valid = verify(
        null,
        message,
        human.publicKey,
        human.signature,
      );
      if (!valid) return "QUARANTINED";
    }

    return "LAB_DISPATCH_VERIFIED";
  }

  public static intentDigest(bundle: SovereignActuationBundle): string {
    return createHash("sha256").update(canonicalAgentIntent(bundle)).digest("hex");
  }
}
