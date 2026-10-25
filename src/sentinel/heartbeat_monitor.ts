export type HeartbeatState = "HEARTBEAT_VERIFIED" | "ACTION_REQUIRED";
export interface HeartbeatProbes {
  internalApi: () => Promise<boolean>;
  chainOracle: () => Promise<boolean>;
  hardware: () => Promise<boolean>;
}
export class HeartbeatMonitor {
  public static async checkSystemPulse(probes: HeartbeatProbes): Promise<HeartbeatState> {
    try {
      const [internal, oracle, hardware] = await Promise.all([probes.internalApi(), probes.chainOracle(), probes.hardware()]);
      return internal && oracle && hardware ? "HEARTBEAT_VERIFIED" : "ACTION_REQUIRED";
    } catch {
      return "ACTION_REQUIRED";
    }
  }
}