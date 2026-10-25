export interface SlashingExecutor {
  execute(nodeId: string, reason: string): Promise<string>;
}

export interface SlashingReceipt {
  nodeId: string;
  reason: string;
  state: "SIMULATION_ONLY" | "ACTION_REQUIRED" | "EXECUTED";
  executionReceipt?: string;
}

/**
 * Cryptoeconomic boundary. The default path never burns funds locally.
 * A live smart-contract adapter must be supplied explicitly.
 */
export class SlashingEngine {
  public static async penalizeNode(
    nodeId: string,
    reason: string,
    executor?: SlashingExecutor,
  ): Promise<SlashingReceipt> {
    if (!nodeId || !reason) {
      throw new Error("SLASHING_REJECTED: nodeId and reason are required");
    }
    console.error(`[SLASHING] Node ${nodeId} violated the evidence policy: ${reason}`);
    if (!executor) {
      return { nodeId, reason, state: "ACTION_REQUIRED" };
    }
    const executionReceipt = await executor.execute(nodeId, reason);
    return { nodeId, reason, state: "EXECUTED", executionReceipt };
  }
}
