import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { A2A_AerialGate, type AerialActuationBundle } from "../src/actuation/a2a_aerial_gate.js";
import { AerialActuationGate } from "../src/actuation/aerial_gate.js";
import { SovereignPhysicalGate } from "../src/actuation/sovereign_gate.js";

const commandHash = "c".repeat(64);
const witnesses = [1, 2, 3].map((n) => ({
  agentId: `drone-${n}`,
  observedCommandHash: commandHash,
  radioToF_Distance: n * 10,
  signature: `sig-${n}`,
}));

const base: AerialActuationBundle = {
  operatorId: "operator-1",
  commandHash,
  a2aWitnesses: witnesses,
  flightTelemetry: { batteryLevel: 80, windShear: "STABLE" },
};

assert.equal(A2A_AerialGate.validateA2ACommand(base), "AERIAL_DISPATCH_VERIFIED");
assert.equal(
  A2A_AerialGate.validateA2ACommand({ ...base, a2aWitnesses: witnesses.slice(0, 2) }),
  "ACTION_REQUIRED",
);
assert.equal(
  A2A_AerialGate.validateA2ACommand({
    ...base,
    a2aWitnesses: witnesses.map((w, i) => i === 2 ? { ...w, observedCommandHash: "d".repeat(64) } : w),
  }),
  "QUARANTINED",
);
assert.equal(
  A2A_AerialGate.validateA2ACommand({
    ...base,
    flightTelemetry: { batteryLevel: 80, windShear: "CRITICAL" },
  }),
  "QUARANTINED",
);
assert.equal(
  AerialActuationGate.validateAerialCommand({
    operatorId: "operator-1",
    commandHash,
    droneTeeQuote: null,
    aerialSafetyReceipt: { batteryLevel: 80, windShearStatus: "STABLE", altitude: 120 },
    a2aWitnesses: witnesses,
  }),
  "AERIAL_DISPATCH_VERIFIED",
);

const { publicKey, privateKey } = generateKeyPairSync("ed25519");
const sovereignBase = {
  agentCommandHash: commandHash,
  a2aWitnessProof: base,
  riskLevel: "HIGH" as const,
};
const signature = sign(null, Buffer.from(JSON.stringify({
  commandHash,
  riskLevel: "HIGH",
  witnesses: witnesses.map((w) => ({
    agentId: w.agentId,
    observedCommandHash: w.observedCommandHash,
    radioToF_Distance: w.radioToF_Distance,
    signature: w.signature,
  })),
})), privateKey);

assert.equal(
  SovereignPhysicalGate.validate({
    ...sovereignBase,
    humanAuthorization: { operatorId: "human-1", publicKey, signature },
  }),
  "LAB_DISPATCH_VERIFIED",
);
assert.equal(
  SovereignPhysicalGate.validate(sovereignBase),
  "ACTION_REQUIRED",
);
assert.equal(
  SovereignPhysicalGate.validate({
    ...sovereignBase,
    humanAuthorization: { operatorId: "human-1", publicKey, signature: Buffer.from("bad") },
  }),
  "QUARANTINED",
);

console.log("Aerial A2A + Sovereign Loop smoke: PASS");
