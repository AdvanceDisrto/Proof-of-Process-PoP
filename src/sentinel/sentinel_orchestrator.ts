import { enforceProductionConfig, type ProductionConfig } from "./config_validator.js";
import { HeartbeatMonitor, type HeartbeatProbes } from "./heartbeat_monitor.js";
export type SentinelState = "PRODUCTION_DEPLOYMENT_AUTHORIZED" | "QUARANTINED" | "ACTION_REQUIRED" | "PENDING";
export interface SentinelInputs {
  config: Record<string, unknown>;
  sourceFiles: Record<string, string>;
  integrationAudit: () => Promise<boolean>;
  hardwareAudit: () => Promise<boolean>;
  heartbeat: HeartbeatProbes;
  immutableLawAudit: () => Promise<boolean>;
}
export interface SentinelReceipt {
  state: SentinelState;
  config: ProductionConfig | null;
  checks: { configuration: boolean; scissors: boolean; mastermind: boolean; machineMechanic: boolean; heartbeat: boolean; auditors: boolean };
  refusedClaims: string[];
}
export class SentinelSwarmOrchestrator {
  public static async executeProductionGate(input: SentinelInputs): Promise<SentinelReceipt> {
    const checks = { configuration:false, scissors:false, mastermind:false, machineMechanic:false, heartbeat:false, auditors:false };
    let config: ProductionConfig | null = null;
    try { config = enforceProductionConfig(input.config); checks.configuration = true; }
    catch (error) { return { state:"QUARANTINED", config:null, checks, refusedClaims:["configuration refused: " + String(error)] }; }
    const allSource = Object.values(input.sourceFiles).join("\n").toLowerCase();
    checks.scissors = ["todo","mock_services","localhost","127.0.0.1"].every((token) => !allSource.includes(token));
    if (!checks.scissors) return { state:"QUARANTINED", config, checks, refusedClaims:["prototype/mock/local endpoint marker found"] };
    try { checks.mastermind = await input.integrationAudit(); } catch { checks.mastermind = false; }
    if (!checks.mastermind) return { state:"ACTION_REQUIRED", config, checks, refusedClaims:["polyglot integration audit failed"] };
    try { checks.machineMechanic = await input.hardwareAudit(); } catch { checks.machineMechanic = false; }
    if (!checks.machineMechanic) return { state:"ACTION_REQUIRED", config, checks, refusedClaims:["live hardware evidence missing or unhealthy"] };
    checks.heartbeat = (await HeartbeatMonitor.checkSystemPulse(input.heartbeat)) === "HEARTBEAT_VERIFIED";
    if (!checks.heartbeat) return { state:"PENDING", config, checks, refusedClaims:["system heartbeat degraded or unavailable"] };
    try { checks.auditors = await input.immutableLawAudit(); } catch { checks.auditors = false; }
    if (!checks.auditors) return { state:"QUARANTINED", config, checks, refusedClaims:["immutable-law receipt/deployment evidence not verified"] };
    return { state:"PRODUCTION_DEPLOYMENT_AUTHORIZED", config, checks, refusedClaims:["this gate does not prove physical-world correspondence","this gate does not manufacture TEE, blockchain, hardware, or laboratory evidence"] };
  }
}