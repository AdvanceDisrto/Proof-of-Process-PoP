export type ExecutionClass = "INTELLIGENCE" | "DETERMINISTIC" | "HUMAN_REVIEW" | "BLOCKED";
export type Risk = "LOW" | "MEDIUM" | "HIGH";

export interface RouteRequest {
  requestId: string;
  prompt: string;
  identity: string;
  permissions: string[];
}

export interface RouteDecision {
  actionId: string;
  risk: Risk;
  executionClass: ExecutionClass;
  reason: string;
  modules: string[];
}

const ACTIONS: Record<string, { risk: Risk; permission: string; modules: string[] }> = {
  "artifact.create": { risk: "LOW", permission: "artifact.create", modules: ["buddy", "iproof"] },
  "code.execute": { risk: "HIGH", permission: "code.execute", modules: ["ikernel", "islr", "iproof"] },
  "deployment.production": { risk: "HIGH", permission: "deployment.production", modules: ["ikernel", "sovereign-gate", "iproof"] },
  "artifact.verify": { risk: "MEDIUM", permission: "artifact.verify", modules: ["icl", "iproof"] }
};

export function classifyIntent(prompt: string): string {
  const p = prompt.toLowerCase();
  if (/deploy|production|release/.test(p)) return "deployment.production";
  if (/execute|run|invoke/.test(p) && /code|command|program|test/.test(p)) return "code.execute";
  if (/verify|validate|prove|check/.test(p)) return "artifact.verify";
  return "artifact.create";
}

export function route(request: RouteRequest): RouteDecision {
  if (!request.requestId || !request.identity || !request.prompt) {
    return { actionId: "unknown", risk: "HIGH", executionClass: "BLOCKED", reason: "invalid_request", modules: ["ikernel"] };
  }
  const actionId = classifyIntent(request.prompt);
  const action = ACTIONS[actionId];
  if (!action) return { actionId, risk: "HIGH", executionClass: "BLOCKED", reason: "unknown_action", modules: ["ikernel"] };
  if (!request.permissions.includes(action.permission)) {
    return { actionId, risk: action.risk, executionClass: "BLOCKED", reason: "permission_required", modules: action.modules };
  }
  if (action.risk === "HIGH") {
    return { actionId, risk: action.risk, executionClass: "HUMAN_REVIEW", reason: "high_risk_requires_sovereign_approval", modules: action.modules };
  }
  if (actionId === "artifact.create") {
    return { actionId, risk: action.risk, executionClass: "INTELLIGENCE", reason: "low_risk_generation_allowed", modules: action.modules };
  }
  return { actionId, risk: action.risk, executionClass: "DETERMINISTIC", reason: "verified_route_allowed", modules: action.modules };
}
