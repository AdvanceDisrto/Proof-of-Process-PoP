export interface ProductionConfig {
  NODE_ENV: "production";
  API_GATEWAY: string;
  CHAIN_ORACLE_RPC: string;
  TEE_ENABLED: true;
  MOCK_SERVICES: false;
  HEARTBEAT_INTERVAL_MS: number;
}

function isUrl(value: unknown): value is string {
  if (typeof value !== "string" || !value) return false;
  try {
    const u = new URL(value);
    return u.protocol === "https:" || u.protocol === "http:";
  } catch {
    return false;
  }
}

export function enforceProductionConfig(config: Record<string, unknown>): ProductionConfig {
  if (config.NODE_ENV !== "production") throw new Error("QUARANTINED: NODE_ENV must be production");
  if (!isUrl(config.API_GATEWAY) || !isUrl(config.CHAIN_ORACLE_RPC)) throw new Error("QUARANTINED: production URLs invalid");
  if (config.TEE_ENABLED !== true) throw new Error("ACTION_REQUIRED: TEE_ENABLED must be true");
  if (config.MOCK_SERVICES !== false) throw new Error("QUARANTINED: mocks forbidden in production");
  if (typeof config.HEARTBEAT_INTERVAL_MS !== "number" || !Number.isInteger(config.HEARTBEAT_INTERVAL_MS) || config.HEARTBEAT_INTERVAL_MS < 1000) {
    throw new Error("QUARANTINED: heartbeat interval must be an integer >= 1000ms");
  }
  return config as ProductionConfig;
}