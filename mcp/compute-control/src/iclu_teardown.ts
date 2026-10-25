import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
const execFileAsync = promisify(execFile);
export type TeardownStatus = "DESTROYED" | "FAILED_TO_DESTROY";
export interface TeardownReceipt { clusterId: string; status: TeardownStatus; reason: string; timestamp: number; proofHash: string; }
export interface Destroyer { destroy(clusterId: string): Promise<void>; }
export class KubectlDestroyer implements Destroyer {
  async destroy(clusterId: string): Promise<void> {
    await execFileAsync("kubectl", ["delete","raycluster",clusterId,"-n","ray-system","--ignore-not-found=true","--wait=true"]);
  }
}
export class iCluTeardown {
  private tornDown = false;
  constructor(private readonly clusterId: string, private readonly destroyer: Destroyer) {}
  async executeTeardown(reason: string): Promise<TeardownReceipt> {
    if (this.tornDown) return this.receipt("DESTROYED", "already torn down");
    try { await this.destroyer.destroy(this.clusterId); this.tornDown = true; return this.receipt("DESTROYED", reason); }
    catch (error) { const detail = error instanceof Error ? error.message : String(error); return this.receipt("FAILED_TO_DESTROY", reason + ": " + detail); }
  }
  private receipt(status: TeardownStatus, reason: string): TeardownReceipt {
    const timestamp = Date.now();
    const payload = "iClu-Teardown-v1|" + this.clusterId + "|" + status + "|" + reason + "|" + timestamp;
    return { clusterId: this.clusterId, status, reason, timestamp, proofHash: createHash("sha256").update(payload).digest("hex") };
  }
}