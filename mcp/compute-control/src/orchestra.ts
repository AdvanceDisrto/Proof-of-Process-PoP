import { createHash } from "node:crypto";

export type PricingTier = "on-demand" | "spot";
export type ProviderHealthState = "healthy" | "degraded" | "unavailable" | "unknown";

export interface WorkloadSpec {
  workloadId: string;
  gpuModel: string;
  minVramGb?: number;
  durationHours: number;
  urgency?: "batch" | "standard" | "realtime";
  maxCostUsd?: number;
  minReliability?: number;
  allowSpot?: boolean;
  region?: string;
}

export interface ProviderOffer {
  provider: string;
  offerId: string;
  gpuModel: string;
  vramGb: number;
  priceUsdPerHour: number;
  pricingTier: PricingTier;
  available: boolean;
  region: string;
  reliability: number;
  source: string;
}

export interface ProviderHealth {
  provider: string;
  status: ProviderHealthState;
  observedAt: string;
  apiLatencyMs?: number;
  interruptionRate24h?: number;
  source: string;
}

export interface ExecutionPlan {
  schema: "ifloo/execution-plan/v1";
  workloadId: string;
  provider: string;
  offerId: string;
  gpuModel: string;
  region: string;
  pricingTier: PricingTier;
  estimatedCostUsd: number;
  reliability: number;
  routingReason: string;
  providerHealth: ProviderHealth;
  routingReceipt: string;
}

export interface ProviderAdapter {
  name: string;
  discover(spec: WorkloadSpec): Promise<ProviderOffer[]>;
  health(): Promise<ProviderHealth>;
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return "[" + value.map(stableStringify).join(",") + "]";
  const obj = value as Record<string, unknown>;
  return "{" + Object.keys(obj).sort().map(k => JSON.stringify(k) + ":" + stableStringify(obj[k])).join(",") + "}";
}

function sha256(value: unknown): string {
  return "sha256:" + createHash("sha256").update("iFloo-routing-v1\x00" + stableStringify(value)).digest("hex");
}

export class Orchestra {
  constructor(private readonly adapters: ProviderAdapter[]) {}

  async discoverProviders(spec: WorkloadSpec): Promise<ProviderOffer[]> {
    const settled = await Promise.allSettled(this.adapters.map(adapter => adapter.discover(spec)));
    return settled.flatMap(result => result.status === "fulfilled" ? result.value : []);
  }

  async getProviderHealth(): Promise<ProviderHealth[]> {
    const settled = await Promise.allSettled(this.adapters.map(adapter => adapter.health()));
    return settled.map((result, i) => result.status === "fulfilled" ? result.value : {
      provider: this.adapters[i].name,
      status: "unavailable",
      observedAt: new Date().toISOString(),
      source: "adapter-error",
    });
  }

  async routeWorkload(spec: WorkloadSpec): Promise<ExecutionPlan> {
    const [offers, health] = await Promise.all([this.discoverProviders(spec), this.getProviderHealth()]);
    const healthByProvider = new Map(health.map(item => [item.provider, item]));
    const candidates = offers.filter(offer => {
      const providerHealth = healthByProvider.get(offer.provider);
      const cost = offer.priceUsdPerHour * spec.durationHours;
      return offer.available
        && offer.vramGb >= (spec.minVramGb ?? 0)
        && (spec.allowSpot !== false || offer.pricingTier !== "spot")
        && offer.reliability >= (spec.minReliability ?? 0)
        && (spec.maxCostUsd === undefined || cost <= spec.maxCostUsd)
        && providerHealth?.status !== "unavailable";
    });
    if (!candidates.length) throw new Error("ACTION_REQUIRED: no provider satisfies workload policy");

    candidates.sort((a, b) => {
      const aScore = a.priceUsdPerHour / Math.max(a.reliability, 0.01);
      const bScore = b.priceUsdPerHour / Math.max(b.reliability, 0.01);
      return aScore - bScore || b.reliability - a.reliability;
    });
    const selected = candidates[0];
    const providerHealth = healthByProvider.get(selected.provider)!;
    const unsigned = {
      schema: "ifloo/execution-plan/v1" as const,
      workloadId: spec.workloadId,
      provider: selected.provider,
      offerId: selected.offerId,
      gpuModel: selected.gpuModel,
      region: selected.region,
      pricingTier: selected.pricingTier,
      estimatedCostUsd: Number((selected.priceUsdPerHour * spec.durationHours).toFixed(6)),
      reliability: selected.reliability,
      routingReason: "lowest reliability-weighted cost among policy-compliant offers",
      providerHealth,
    };
    return { ...unsigned, routingReceipt: sha256(unsigned) };
  }
}
