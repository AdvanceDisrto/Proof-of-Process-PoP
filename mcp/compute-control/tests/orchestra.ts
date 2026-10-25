import assert from "node:assert/strict";
import { Orchestra, type ProviderAdapter, type WorkloadSpec } from "../src/orchestra.js";

const spec: WorkloadSpec = {
  workloadId: "epoch-42-inference",
  gpuModel: "H100",
  minVramGb: 80,
  durationHours: 2,
  maxCostUsd: 10,
  minReliability: 0.9,
  allowSpot: true,
};

const mk = (name: string, price: number, reliability: number, tier: "spot"|"on-demand"): ProviderAdapter => ({
  name,
  async discover() {
    return [{ provider:name, offerId:name+"-h100", gpuModel:"H100", vramGb:80, priceUsdPerHour:price, pricingTier:tier, available:true, region:"test", reliability, source:"fixture" }];
  },
  async health() {
    return { provider:name, status:"healthy", observedAt:"2026-10-25T00:00:00Z", source:"fixture" };
  },
});

const orchestra = new Orchestra([mk("cheap-unreliable", 1, 0.5, "spot"), mk("hyperstack", 2.5, 0.99, "on-demand")]);
const plan = await orchestra.routeWorkload(spec);
assert.equal(plan.provider, "hyperstack");
assert.equal(plan.estimatedCostUsd, 5);
assert.match(plan.routingReceipt, /^sha256:[0-9a-f]{64}$/);

const impossible = new Orchestra([mk("bad", 1, 0.2, "spot")]);
await assert.rejects(() => impossible.routeWorkload(spec), /ACTION_REQUIRED/);

console.log("iFloo Orchestra routing smoke: PASS");
