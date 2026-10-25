import assert from "node:assert/strict";
import test from "node:test";
import { ConfirmedAnchorSourceUpdater, type SourceUpdate } from "../src/anchor/confirmed_source_update.js";

test("does not update source when anchor is not confirmed", async () => {
  let writes = 0;
  const result = await ConfirmedAnchorSourceUpdater.run(
    "a".repeat(64),
    { async verify() { return null; } },
    { async update() { writes++; } },
  );
  assert.equal(result, null);
  assert.equal(writes, 0);
});

test("updates source and notifies only after independent confirmation", async () => {
  const updates: SourceUpdate[] = [];
  const notifications: SourceUpdate[] = [];
  const subjectHash = "a".repeat(64);

  const result = await ConfirmedAnchorSourceUpdater.run(
    subjectHash,
    {
      async verify(hash) {
        return { subjectHash: hash, chain: "bitcoin", txHash: "tx-123", confirmedAt: 1770000000000, confirmations: 6 };
      },
    },
    { async update(update) { updates.push(update); } },
    { async notify(update) { notifications.push(update); } },
  );

  assert.equal(result?.state, "CONFIRMED");
  assert.equal(updates.length, 1);
  assert.equal(notifications.length, 1);
  assert.equal(ConfirmedAnchorSourceUpdater.contentHash(result!), ConfirmedAnchorSourceUpdater.contentHash(updates[0]));
});

test("rejects a confirmation for a different hash", async () => {
  await assert.rejects(
    () => ConfirmedAnchorSourceUpdater.run(
      "a".repeat(64),
      { async verify() { return { subjectHash: "b".repeat(64), chain: "bitcoin", txHash: "tx", confirmedAt: 1770000000000, confirmations: 6 }; } },
      { async update() {} },
    ),
    /subject hash does not match/,
  );
});
