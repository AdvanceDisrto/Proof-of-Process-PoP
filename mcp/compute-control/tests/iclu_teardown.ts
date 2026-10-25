import assert from "node:assert/strict";
import { iCluTeardown, type Destroyer } from "../src/iclu_teardown.js";
class FakeDestroyer implements Destroyer {
  public calls = 0;
  constructor(private readonly fail = false) {}
  async destroy(_clusterId: string): Promise<void> { this.calls++; if (this.fail) throw new Error("provider teardown failed"); }
}
{ const d = new FakeDestroyer(); const t = new iCluTeardown("test-cluster", d); const r = await t.executeTeardown("CI_FAILURE"); assert.equal(r.status,"DESTROYED"); assert.equal(d.calls,1); assert.match(r.proofHash,/^[a-f0-9]{64}$/); const again=await t.executeTeardown("DUPLICATE"); assert.equal(again.status,"DESTROYED"); assert.equal(d.calls,1); }
{ const d = new FakeDestroyer(true); const t = new iCluTeardown("orphan-risk", d); const r = await t.executeTeardown("TIMEOUT"); assert.equal(r.status,"FAILED_TO_DESTROY"); assert.match(r.proofHash,/^[a-f0-9]{64}$/); }
console.log("iClu teardown smoke: PASS");