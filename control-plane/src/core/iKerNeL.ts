export interface KernelRequest {
  requestId: string;
  prompt: string;
  identity: string;
  permissions: string[];
}

export type ExecutionClass = "HUMAN_REVIEW" | "BLOCKED" | "DETERMINISTIC";

export interface KernelDispatch {
  requestId: string;
  executionClass: ExecutionClass;
  prompt: string;
  identity: string;
  permissions: string[];
}

const HIGH_RISK_PATTERNS: RegExp[] = [/\bproduction\b/i];

function isHighRisk(prompt: string): boolean {
  return HIGH_RISK_PATTERNS.some((p) => p.test(prompt));
}

export function route(request: KernelRequest): KernelDispatch {
  if (request.permissions.length === 0) {
    return { ...request, executionClass: "BLOCKED" };
  }
  if (isHighRisk(request.prompt)) {
    return { ...request, executionClass: "HUMAN_REVIEW" };
  }
  return { ...request, executionClass: "DETERMINISTIC" };
}
