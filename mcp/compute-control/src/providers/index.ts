import type { ProviderAdapter } from "../orchestra.js";
import { HyperstackAdapter } from "./hyperstack.js";
import { HttpCatalogProviderAdapter, type HttpCatalogProviderConfig } from "./http_catalog.js";

export interface ProviderRegistryEntry {
  name: string;
  mode: "native" | "http-catalog" | "framework";
  credentialEnv?: string;
  openSource: boolean;
  status: "implemented" | "configured" | "action-required";
  note: string;
}

export const providerRegistry: ProviderRegistryEntry[] = [
  { name: "hyperstack", mode: "native", credentialEnv: "HYPERSTACK_API_KEY", openSource: false, status: "implemented", note: "Native flavors + pricebook adapter." },
  { name: "runpod", mode: "http-catalog", credentialEnv: "RUNPOD_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "nebius", mode: "http-catalog", credentialEnv: "NEBIUS_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "vast.ai", mode: "http-catalog", credentialEnv: "VAST_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "io.net", mode: "http-catalog", credentialEnv: "IO_NET_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "thunder-compute", mode: "http-catalog", credentialEnv: "THUNDER_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "tensordock", mode: "http-catalog", credentialEnv: "TENSORDOCK_API_KEY", openSource: false, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "akash", mode: "http-catalog", openSource: true, status: "implemented", note: "Public provider GPU availability discovery; live lease/bid execution remains ACTION_REQUIRED." },
  { name: "nosana", mode: "http-catalog", credentialEnv: "NOSANA_API_KEY", openSource: true, status: "configured", note: "Endpoint must be supplied and contract-verified before live routing." },
  { name: "skypilot", mode: "framework", openSource: true, status: "action-required", note: "Local framework integration requires installed SkyPilot plus underlying cloud credentials." },
  { name: "ray-kuberay", mode: "framework", openSource: true, status: "action-required", note: "Distributed runtime, not a GPU marketplace; requires a configured Ray/KubeRay cluster." },
];

function envCatalog(
  name: string,
  urlEnv: string,
  apiKeyEnv: string | undefined,
  openSource = false,
): HttpCatalogProviderConfig | null {
  const catalogUrl = process.env[urlEnv];
  if (!catalogUrl) return null;
  return {
    name,
    catalogUrl,
    apiKeyEnv,
    authHeader: "Authorization",
    authScheme: "Bearer",
    isOpenSource: openSource,
    defaultPricingTier: "marketplace",
    defaultReliability: 0,
  };
}

export function buildUniversalProviderAdapters(): ProviderAdapter[] {
  const adapters: ProviderAdapter[] = [new HyperstackAdapter()];

  const configured = [
    envCatalog("runpod", "RUNPOD_CATALOG_URL", "RUNPOD_API_KEY"),
    envCatalog("nebius", "NEBIUS_CATALOG_URL", "NEBIUS_API_KEY"),
    envCatalog("vast.ai", "VAST_CATALOG_URL", "VAST_API_KEY"),
    envCatalog("io.net", "IO_NET_CATALOG_URL", "IO_NET_API_KEY"),
    envCatalog("thunder-compute", "THUNDER_CATALOG_URL", "THUNDER_API_KEY"),
    envCatalog("tensordock", "TENSORDOCK_CATALOG_URL", "TENSORDOCK_API_KEY"),
    envCatalog("nosana", "NOSANA_CATALOG_URL", "NOSANA_API_KEY", true),
  ].filter((v): v is HttpCatalogProviderConfig => v !== null);

  adapters.push(...configured.map(config => new HttpCatalogProviderAdapter(config)));

  adapters.push(new HttpCatalogProviderAdapter({
    name: "akash",
    catalogUrl: "https://console-api.akash.network/v1/providers",
    isOpenSource: true,
    defaultPricingTier: "reverse-auction",
    defaultReliability: 0,
  }));

  return adapters;
}
