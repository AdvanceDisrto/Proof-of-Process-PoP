import assert from "node:assert/strict";
import { Orchestra, type ProviderAdapter, type WorkloadSpec } from "../src/orchestra.js";
import { providerRegistry } from "../src/providers/index.js";

const mk = (name: string, price: number, reliability: number, isOpenSource: boolean): ProviderAdapter => ({
  name,
  async discover() {
    return [{
      provider: name,
      offerId: name + "-h100",
      gpuModel: "H100",
      vramGb: 80,
      priceUsdPerHour: price,
      pricingTier: "on-demand",
      available: true,
      region: "test",
      reliability,
      source: "fixture",
      isOpenSource,
    }];
  },
  async health() {
    return { provider: name, status: "healthy", observedAt: "2026-10-25T00:00:00Z", source: "fixture" };
  },
});

const base: WorkloadSpec = {
  workloadId: "universal-route",
  gpuModel: "H100",
  minVramGb: 80,
  durationHours: 1,
  allowSpot: true,
};

const adapters = [
  mk("cheap-proprietary", 1.0, 0.8, false),
  mk("reliable-proprietary", 2.0, 0.99, false),
  mk("open-source", 1.5, 0.9, true),
];

assert.equal((await new Orchestra(adapters).routeWorkload({ ...base, priority: "cost" })).provider, "cheap-proprietary");
assert.equal((await new Orchestra(adapters).routeWorkload({ ...base, priority: "reliability" })).provider, "reliable-proprietary");
const open = await new Orchestra(adapters).routeWorkload({ ...base, priority: "open_source_first" });
assert.equal(open.provider, "open-source");
assert.equal(open.isOpenSource, true);
assert.match(open.routingReceipt, /^sha256:[0-9a-f]{64}$/);

const names = new Set(providerRegistry.map(p => p.name));
for (const required of ["hyperstack", "runpod", "nebius", "vast.ai", "io.net", "thunder-compute", "tensordock", "akash", "nosana", "skypilot", "ray-kuberay"]) {
  assert(names.has(required), `missing provider/framework registry entry: ${required}`);
}

console.log("iFloo universal provider matrix smoke: PASS");
