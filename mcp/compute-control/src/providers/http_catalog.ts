import type { ProviderAdapter, ProviderHealth, ProviderOffer, PricingTier, WorkloadSpec } from "../orchestra.js";

export interface HttpCatalogProviderConfig {
  name: string;
  catalogUrl: string;
  healthUrl?: string;
  apiKeyEnv?: string;
  authHeader?: string;
  authScheme?: string;
  isOpenSource?: boolean;
  defaultPricingTier?: PricingTier;
  defaultReliability?: number;
}

type FetchLike = typeof fetch;

function finiteNumber(value: unknown): number | undefined {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function pickString(row: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = row[key];
    if (typeof value === "string" && value.length) return value;
  }
  return undefined;
}

function pickNumber(row: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = finiteNumber(row[key]);
    if (value !== undefined) return value;
  }
  return undefined;
}

function rowsFrom(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) return payload.filter(v => v && typeof v === "object") as Record<string, unknown>[];
  if (!payload || typeof payload !== "object") return [];
  const obj = payload as Record<string, unknown>;
  for (const key of ["offers", "instances", "flavors", "data", "results", "items", "nodes", "machines"]) {
    const value = obj[key];
    if (Array.isArray(value)) return value.filter(v => v && typeof v === "object") as Record<string, unknown>[];
  }
  return [];
}

/**
 * Strict generic HTTP catalog adapter.
 *
 * It intentionally refuses to fabricate offers when a provider response cannot
 * be normalized. Provider-specific adapters can replace this class as their API
 * contracts are pinned and tested.
 */
export class HttpCatalogProviderAdapter implements ProviderAdapter {
  readonly name: string;

  constructor(
    private readonly config: HttpCatalogProviderConfig,
    private readonly fetcher: FetchLike = fetch,
  ) {
    this.name = config.name;
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (!this.config.apiKeyEnv) return headers;
    const secret = process.env[this.config.apiKeyEnv];
    if (!secret) throw new Error(`ACTION_REQUIRED: ${this.config.apiKeyEnv} is absent`);
    const header = this.config.authHeader ?? "Authorization";
    headers[header] = this.config.authScheme ? `${this.config.authScheme} ${secret}` : secret;
    return headers;
  }

  private async get(url: string): Promise<unknown> {
    const response = await this.fetcher(url, { headers: this.headers() });
    if (!response.ok) throw new Error(`${this.name} API ${response.status}`);
    return response.json();
  }

  async discover(spec: WorkloadSpec): Promise<ProviderOffer[]> {
    const payload = await this.get(this.config.catalogUrl);
    const offers: ProviderOffer[] = [];
    for (const row of rowsFrom(payload)) {
      const gpuModel = pickString(row, ["gpuModel", "gpu_model", "gpu_name", "gpuName", "model", "gpu"]);
      const price = pickNumber(row, ["priceUsdPerHour", "price_per_hour", "price_per_hr", "hourly_price", "dph_total", "price"]);
      if (!gpuModel || price === undefined || price < 0) continue;
      if (!gpuModel.toLowerCase().includes(spec.gpuModel.toLowerCase())) continue;
      const vramGb = pickNumber(row, ["vramGb", "vram_gb", "gpu_ram_gb", "gpu_memory_gb", "gpu_memory", "vram"]) ?? 0;
      const spot = row.isSpot === true || row.is_spot === true || row.interruptible === true;
      offers.push({
        provider: this.name,
        offerId: pickString(row, ["offerId", "offer_id", "id", "name", "machine_id"]) ?? `${this.name}:${gpuModel}:${offers.length}`,
        gpuModel,
        vramGb,
        priceUsdPerHour: price,
        pricingTier: spot ? "spot" : (this.config.defaultPricingTier ?? "marketplace"),
        available: row.available !== false && row.is_available !== false,
        region: pickString(row, ["region", "region_name", "location", "datacenter"]) ?? spec.region ?? "unknown",
        reliability: this.config.defaultReliability ?? 0,
        source: this.config.catalogUrl,
        isOpenSource: this.config.isOpenSource === true,
      });
    }
    return offers;
  }

  async health(): Promise<ProviderHealth> {
    const started = Date.now();
    try {
      await this.get(this.config.healthUrl ?? this.config.catalogUrl);
      return {
        provider: this.name,
        status: "healthy",
        observedAt: new Date().toISOString(),
        apiLatencyMs: Date.now() - started,
        source: this.config.healthUrl ?? this.config.catalogUrl,
      };
    } catch {
      return {
        provider: this.name,
        status: "unavailable",
        observedAt: new Date().toISOString(),
        apiLatencyMs: Date.now() - started,
        source: this.config.healthUrl ?? this.config.catalogUrl,
      };
    }
  }
}
