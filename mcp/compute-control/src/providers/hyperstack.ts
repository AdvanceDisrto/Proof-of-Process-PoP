import type { ProviderAdapter, ProviderHealth, ProviderOffer, WorkloadSpec } from "../orchestra.js";

const DEFAULT_BASE_URL = "https://infrahub-api.nexgencloud.com/v1";

type FetchLike = (input: string | URL | Request, init?: RequestInit) => Promise<Response>;

export class HyperstackAdapter implements ProviderAdapter {
  readonly name = "hyperstack";
  constructor(
    private readonly apiKey = process.env.HYPERSTACK_API_KEY ?? "",
    private readonly baseUrl = DEFAULT_BASE_URL,
    private readonly fetcher: FetchLike = fetch,
  ) {}

  private async get(path: string): Promise<unknown> {
    if (!this.apiKey) throw new Error("ACTION_REQUIRED: HYPERSTACK_API_KEY is absent");
    const response = await this.fetcher(this.baseUrl + path, {
      headers: { Accept: "application/json", api_key: this.apiKey },
    });
    if (!response.ok) throw new Error(`Hyperstack API ${response.status} for ${path}`);
    return response.json();
  }

  async discover(spec: WorkloadSpec): Promise<ProviderOffer[]> {
    const [flavorsRaw, pricebookRaw] = await Promise.all([
      this.get("/core/flavors"),
      this.get("/pricebook"),
    ]);
    const pricebook = Array.isArray(pricebookRaw) ? pricebookRaw as Array<Record<string, unknown>> : [];
    const prices = new Map(pricebook.map(item => [String(item.name ?? ""), Number(item.value ?? item.original_value ?? NaN)]));
    const groups = Array.isArray((flavorsRaw as { data?: unknown[] }).data) ? (flavorsRaw as { data: unknown[] }).data : [];
    const offers: ProviderOffer[] = [];
    for (const group of groups as Array<Record<string, unknown>>) {
      const flavors = Array.isArray(group.flavors) ? group.flavors as Array<Record<string, unknown>> : [];
      for (const flavor of flavors) {
        const gpu = String(flavor.gpu ?? group.gpu ?? "");
        if (!gpu || !gpu.toLowerCase().includes(spec.gpuModel.toLowerCase())) continue;
        const gpuCount = Number(flavor.gpu_count ?? 1);
        const price = prices.get(gpu);
        if (!Number.isFinite(price)) continue;
        offers.push({
          provider: this.name,
          offerId: String(flavor.name ?? flavor.id ?? gpu),
          gpuModel: gpu,
          vramGb: Number(flavor.gpu_memory ?? flavor.vram ?? 0),
          priceUsdPerHour: Number(price) * gpuCount,
          pricingTier: gpu.endsWith("-spot") ? "spot" : "on-demand",
          available: true,
          region: String(flavor.region_name ?? group.region_name ?? spec.region ?? "unknown"),
          reliability: gpu.endsWith("-spot") ? 0.9 : 0.99,
          source: "hyperstack:/core/flavors+/pricebook",
        });
      }
    }
    return offers;
  }

  async health(): Promise<ProviderHealth> {
    const started = Date.now();
    try {
      await this.get("/core/flavors");
      return {
        provider: this.name,
        status: "healthy",
        observedAt: new Date().toISOString(),
        apiLatencyMs: Date.now() - started,
        source: "hyperstack:/core/flavors",
      };
    } catch {
      return {
        provider: this.name,
        status: "unavailable",
        observedAt: new Date().toISOString(),
        apiLatencyMs: Date.now() - started,
        source: "hyperstack:/core/flavors",
      };
    }
  }
}
