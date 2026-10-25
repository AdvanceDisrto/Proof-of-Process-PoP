import { SlashingEngine, type SlashingExecutor } from "./economy/slashing_engine.js";
import { ZkTeeEngine, type ZkTeeEvidence } from "./crypto/zk_tee_engine.js";
import { SwarmVerifier, type SwarmObservation, type SwarmVerification } from "./actuation/swarm_verifier.js";
import { BiologicalArchiver, type BiologicalArchiveReceipt } from "./archive/bio_archiver.js";
import { GenesisSeedAgent, type GenesisSeedReceipt } from "./edge/genesis_seed.js";

export interface OmniscopeV2Input {
  payload: unknown;
  dataHash: string;
  modelHash: string;
  outputHash?: string;
  swarmObservations: SwarmObservation[];
  nodeId: string;
  genesisRootHash: string;
}

export interface OmniscopeV2Receipt {
  protocol: "OMNISCOPE_PROTOCOL_V2.0";
  genesisSeed: GenesisSeedReceipt;
  zkTee: ZkTeeEvidence;
  swarm: SwarmVerification;
  gate: "LAB_DISPATCH_VERIFIED" | "ACTION_REQUIRED" | "QUARANTINED";
  biologicalArchive?: BiologicalArchiveReceipt;
  slashing: "NOT_TRIGGERED" | "ACTION_REQUIRED" | "EXECUTED";
}

export async function executeOmniscopeProtocol(
  input: OmniscopeV2Input,
  slashingExecutor?: SlashingExecutor,
): Promise<OmniscopeV2Receipt> {
  const genesisSeed = await GenesisSeedAgent.generateOfflineReceipt(input.payload);
  const zkTee = await ZkTeeEngine.generateProofAndQuote(
    input.dataHash,
    input.modelHash,
    input.outputHash,
  );
  const swarm = SwarmVerifier.verifyPhysicalLabState(input.swarmObservations);

  const cryptographicReady = ZkTeeEngine.verify(zkTee);
  const gate =
    swarm.state === "QUARANTINED"
      ? "QUARANTINED"
      : cryptographicReady && swarm.state === "VERIFIED_PROCESS"
        ? "LAB_DISPATCH_VERIFIED"
        : "ACTION_REQUIRED";

  if (gate !== "LAB_DISPATCH_VERIFIED") {
    const slash = await SlashingEngine.penalizeNode(
      input.nodeId,
      `Omniscope gate state: ${gate}`,
      slashingExecutor,
    );
    return {
      protocol: "OMNISCOPE_PROTOCOL_V2.0",
      genesisSeed,
      zkTee,
      swarm,
      gate,
      slashing:
        slash.state === "EXECUTED" ? "EXECUTED" : "ACTION_REQUIRED",
    };
  }

  const biologicalArchive = await BiologicalArchiver.encodeToDNA(input.genesisRootHash);
  return {
    protocol: "OMNISCOPE_PROTOCOL_V2.0",
    genesisSeed,
    zkTee,
    swarm,
    gate,
    biologicalArchive,
    slashing: "NOT_TRIGGERED",
  };
}
