import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { IP_OneToOne_Engine } from "../src/ip_one_to_one_engine.js";

const root = mkdtempSync(join(tmpdir(), "ip-1to1-"));
writeFileSync(join(root, "a.txt"), "canonical");
const first = await IP_OneToOne_Engine.searchAndFind(root, "sandbox-test", async () => {
  return "0".repeat(64);
});
assert.equal(first.isMatch, false);
const matching = await IP_OneToOne_Engine.searchAndFind(root, "sandbox-test", first.codebaseRootHash);
assert.equal(matching.isMatch, true);
assert.match(matching.ipAssetId, /^iP-[0-9a-f]{16}$/);
writeFileSync(join(root, "a.txt"), "tampered");
const tampered = await IP_OneToOne_Engine.searchAndFind(root, "sandbox-test", first.codebaseRootHash);
assert.equal(tampered.isMatch, false);
console.log("iP 1&1 exact-match smoke: PASS");
