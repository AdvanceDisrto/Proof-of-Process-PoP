import { createHash } from "node:crypto";
import { executeOmniscopeProtocol } from "../src/omniscope_protocol_v2.js";
import { ZkTeeEngine } from "../src/crypto/zk_tee_engine.js";
import { GenesisSeedAgent } from "../src/edge/genesis_seed.js";

const sha = (seed: string) => `sha256:${createHash("sha256").update(seed).digest("hex")}`;

async function main(): Promise<void> {
  const observations = [
    { observerId: "drone-a", evidenceHash: sha("a"), signature: "sig-a", labSterile: true, labEmpty: true },
    { observerId: "drone-b", evidenceHash: sha("b"), signature: "sig-b", labSterile: true, labEmpty: true },
  ];
  const result = await executeOmniscopeProtocol({
    payload: { observation: "offline-demo" },
    dataHash: sha("data"),
    modelHash: sha("model"),
    swarmObservations: observations,
    nodeId: "node-001",
    genesisRootHash: sha("genesis"),
  });
  if (result.gate !== "LAB_DISPATCH_VERIFIED") throw new Error("expected lab gate");
  if (!result.biologicalArchive || result.biologicalArchive.physicalSynthesisPerformed) {
    throw new Error("expected encoding-only biological archive");
  }
  if (result.genesisSeed.globalAnchor !== "PENDING") throw new Error("expected offline seed to remain pending");
  if (!ZkTeeEngine.verify(result.zkTee)) throw new Error("expected commitment verification");
  const anchored = GenesisSeedAgent.attachGlobalAnchor(result.genesisSeed, sha("anchor"));
  if (anchored.globalAnchor !== "VERIFIED_PROCESS") throw new Error("expected explicit global anchor");
  console.log("Omniscope Protocol v2.0 reference test: PASS");
}

void main();
