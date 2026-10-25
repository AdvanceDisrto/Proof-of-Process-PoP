/**
 * PoP Federated i Brain.
 *
 * This is an integration boundary, not a claim that every upstream model is
 * locally loaded. Runtime promotion remains evidence-gated.
 */

export type BrainCapabilityState =
  | "SOURCE_DECLARED"
  | "AVAILABLE"
  | "EXECUTED"
  | "VERIFIED_PROCESS"
  | "ACTION_REQUIRED"
  | "QUARANTINED";

export type BrainPhase =
  | "PERCEIVE"
  | "REASON"
  | "BIND"
  | "VERIFY"
  | "AUTHORIZE"
  | "ACT"
  | "OBSERVE"
  | "RECEIPT"
  | "FEEDBACK";

export interface BrainSource {
  name: string;
  repository: string;
  commit: string;
  role: string;
  capabilities: readonly string[];
}

export interface BrainRequest {
  intent: string;
  capability?: string;
  requiresPhysicalNode?: boolean;
  operatorApproved?: boolean;
}

export interface BrainDecision {
  phase: BrainPhase;
  state: BrainCapabilityState;
  capability: string | null;
  source: string | null;
  reason: string;
}

const SOURCES: readonly BrainSource[] = [
  {
    name: "STRMKRD-AI",
    repository: "AdvanceDisrto/STRMKRD-AI",
    commit: "b18e5dbd6409340da7b93d535edf007bd6a2a68c",
    role: "foundation-intelligence",
    capabilities: [
      "native_foundation_models",
      "specialist_models",
      "deterministic_kernels",
      "persistent_memory",
      "tools_execution",
      "routing_orchestration",
      "evidence_provenance_receipts",
      "heterogeneous_compute",
    ],
  },
  {
    name: "STRMKRD",
    repository: "STRMKRD/STRMKRD",
    commit: "17f12a354c38e88c5ef0eb8ec9347d17b0c407b7",
    role: "ecosystem-governance",
    capabilities: [
      "ecosystem_registry",
      "identity",
      "trust",
      "build_deploy_monitor_recover",
      "governed_intelligence",
    ],
  },
  {
    name: "Intelligent-Assistant-Nexus",
    repository: "AdvanceDisrto/Intelligent-Assistant-Nexus",
    commit: "776dc187b07e6400d730c89135548a10c55aa1d7",
    role: "assistant-brain",
    capabilities: [
      "buddy_brain",
      "multi_agent_orbit",
      "memory",
      "tools",
      "observer",
      "learner",
      "verifier",
      "builder",
      "communicator",
      "human_gate",
      "mission_system",
      "knowledge_base",
      "model_routing",
      "voice_first_action_flow",
    ],
  },
  {
    name: "AIA-AC",
    repository: "AdvanceDisrto/Artificial-Intelligence-Artifact-Architecture-Chain-AIA-AC-",
    commit: "10d341f94e22e8d82bf134084b30d675ce592b8c",
    role: "artifact-provenance",
    capabilities: [
      "content_addressed_model_registration",
      "inference_receipts",
      "controlled_evolution_proposals",
      "evidence_aware_compute_placement",
      "artifact_lineage",
    ],
  },
  {
    name: "iBare-Metal",
    repository: "AdvanceDisrto/iBare-Metal",
    commit: "d99def0feeb242e8be50dedcfa6e3fe445c3c54e",
    role: "physical-node-boundary",
    capabilities: [
      "read_only_preflight",
      "operator_approval",
      "node_commissioning",
      "hardware_identity",
      "firmware_record",
      "accelerator_identity",
      "network_topology",
      "physical_measurement_binding",
      "hrtf_physical_context",
    ],
  },
];

export class FederatedIBrain {
  readonly sources = SOURCES;

  listCapabilities(): Array<{
    id: string;
    source: string;
    state: BrainCapabilityState;
    requiresPhysicalEvidence: boolean;
  }> {
    return SOURCES.flatMap((source) =>
      source.capabilities.map((capability) => ({
        id: capability,
        source: source.name,
        state: "SOURCE_DECLARED" as const,
        requiresPhysicalEvidence:
          source.name === "iBare-Metal" ||
          capability === "physical_measurement_binding" ||
          capability === "hrtf_physical_context",
      })),
    );
  }

  decide(request: BrainRequest): BrainDecision {
    const capability = request.capability ?? null;

    if (!capability) {
      return {
        phase: "PERCEIVE",
        state: "ACTION_REQUIRED",
        capability: null,
        source: null,
        reason: "No capability was bound to the request.",
      };
    }

    const source = SOURCES.find((candidate) =>
      candidate.capabilities.includes(capability),
    );

    if (!source) {
      return {
        phase: "BIND",
        state: "ACTION_REQUIRED",
        capability,
        source: null,
        reason: "Capability is not present in the federated brain registry.",
      };
    }

    const physical =
      source.name === "iBare-Metal" ||
      capability === "physical_measurement_binding" ||
      capability === "hrtf_physical_context";

    if (physical && !request.operatorApproved) {
      return {
        phase: "AUTHORIZE",
        state: "ACTION_REQUIRED",
        capability,
        source: source.name,
        reason:
          "Physical-node capability requires read-only preflight and explicit operator approval before commissioning.",
      };
    }

    return {
      phase: physical ? "ACT" : "REASON",
      state: "SOURCE_DECLARED",
      capability,
      source: source.name,
      reason:
        "Capability is bound to a pinned source. Fresh execution evidence is still required before VERIFIED_PROCESS.",
    };
  }

  promoteAfterExecution(
    capability: string,
    executionPassed: boolean,
    physicalEvidencePresent = false,
  ): BrainCapabilityState {
    const source = SOURCES.find((candidate) =>
      candidate.capabilities.includes(capability),
    );

    if (!source) return "QUARANTINED";
    const requiresPhysical =
      source.name === "iBare-Metal" ||
      capability === "physical_measurement_binding" ||
      capability === "hrtf_physical_context";

    if (!executionPassed) return "ACTION_REQUIRED";
    if (requiresPhysical && !physicalEvidencePresent) return "ACTION_REQUIRED";

    return "VERIFIED_PROCESS";
  }
}
