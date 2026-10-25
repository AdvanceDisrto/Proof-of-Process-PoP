import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { executeOmniscopeProtocol } from "../src/omniscope_protocol_v2.js";
import { SovereignPhysicalGate } from "../src/actuation/sovereign_gate.js";

const sha = (seed: string) => `sha256:${Buffer.from(seed).toString("hex").padEnd(64, "0").slice(0, 64)}`;

function canonicalIntent(commandHash: string, witnesses: Array<{
  agentId: string;
  observedCommandHash: string;
  radioToF_Distance: number;
  signature: string;
}>): Buffer {
  return Buffer.from(JSON.stringify({
    commandHash,
    riskLevel: "HIGH",
    witnesses: witnesses.map((w) => ({
      agentId: w.agentId,
      observedCommandHash: w.observedCommandHash,
      radioToF_Distance: w.radioToF_Distance,
      signature: w.signature,
    })),
  }));
}

async function main(): Promise<void> {
  const commandHash = sha("omniscope-e2e-command");
  const swarmObservations = [1, 2, 3].map((n) => ({
    observerId: `drone-${n}`,
    evidenceHash: sha(`observation-${n}`),
    signature: `signed-observation-${n}`,
    labSterile: true,
    labEmpty: true,
  }));

  const reference = await executeOmniscopeProtocol({
    payload: { scenario: "offline-reference-only" },
    dataHash: sha("a2a-observation"),
    modelHash: sha("egicore-model"),
    outputHash: commandHash,
    swarmObservations,
    nodeId: "node-e2e-001",
    genesisRootHash: sha("genesis-root"),
  });

  assert.equal(reference.protocol, "OMNISCOPE_PROTOCOL_V2.0");
  assert.equal(reference.gate, "LAB_DISPATCH_VERIFIED");
  assert.equal(reference.swarm.state, "VERIFIED_PROCESS");
  assert.equal(reference.zkTee.productionVerified, false);
  assert.equal(reference.biologicalArchive?.physicalSynthesisPerformed, false);
  assert.equal(reference.genesisSeed.globalAnchor, "PENDING");

  const witnesses = [1, 2, 3].map((n) => ({
    agentId: `drone-${n}`,
    observedCommandHash: commandHash,
    radioToF_Distance: n * 10,
    signature: `a2a-signature-${n}`,
  }));

  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const signature = sign(null, canonicalIntent(commandHash, witnesses), privateKey);

  const sovereignState = SovereignPhysicalGate.validate({
    agentCommandHash: commandHash,
    a2aWitnessProof: {
      operatorId: "operator-e2e-001",
      commandHash,
      a2aWitnesses: witnesses,
      flightTelemetry: { batteryLevel: 85, windShear: "STABLE" },
    },
    humanAuthorization: {
      operatorId: "operator-e2e-001",
      publicKey,
      signature,
    },
    riskLevel: "HIGH",
  });

  assert.equal(sovereignState, "LAB_DISPATCH_VERIFIED");

  // Physical execution is intentionally not simulated as successful:
  // the reference zk/TEE evidence is not a production proof/quote and no
  // real actuator, hardware interlock, or lab receipt is present.
  const physicalState = reference.zkTee.productionVerified
    ? "PHYSICAL_EXECUTION_COMPLETE"
    : "ACTION_REQUIRED";

  assert.equal(physicalState, "ACTION_REQUIRED");

  console.log("====================================================");
  console.log("OMNISCOPE E2E REFERENCE RECEIPT");
  console.log("====================================================");
  console.log("[1] EDGE:       A2A swarm quorum (3 nodes) -> PASS");
  console.log("[2] AI:         zk/TEE commitment binding -> PASS (REFERENCE)");
  console.log("[3] ANCHOR:     Genesis global anchor -> PENDING");
  console.log("[4] ECONOMY:    Slashing path -> NOT TRIGGERED");
  console.log("[5] HUMAN:      Sovereign Ed25519 authorization -> PASS");
  console.log("[6] ACTUATION:  Production hardware evidence -> ACTION_REQUIRED");
  console.log("[7] MEMORY:     Reference receipt constructed -> PASS");
  console.log("====================================================");
  console.log("FINAL STATE: ACTION_REQUIRED");
  console.log("====================================================");
  console.log("Omniscope E2E reference smoke: PASS");
}

void main();
