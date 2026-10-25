import assert from "node:assert/strict";
import { MultiChainAnchorEngine } from "../src/anchor/multi_chain_attestation.js";
import { VONAGE_POT_INVENTIONS, evaluateVonageEvidence } from "../src/edge/vonage_pot_registry.js";
import { IMobileCellularOrchestra } from "../src/edge/imobile_cellular_orchestra.js";

const HASH = "a".repeat(64);

assert.equal(VONAGE_POT_INVENTIONS.length, 30);
assert.equal(new Set(VONAGE_POT_INVENTIONS.map((x) => x.id)).size, 30);
assert.equal(new Set(VONAGE_POT_INVENTIONS.map((x) => x.surface)).size, 6);

const invention = VONAGE_POT_INVENTIONS[0];
assert.equal(evaluateVonageEvidence(invention, false, false), "ACTION_REQUIRED");
assert.equal(evaluateVonageEvidence(invention, true, false), "QUARANTINED");
assert.equal(evaluateVonageEvidence(invention, true, true), "VERIFIED_PROCESS");

const anchors = new MultiChainAnchorEngine();
assert.equal(
  anchors.evaluate(HASH, [
    { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
    { chain: "ETHEREUM_EAS", subjectHash: HASH, confirmed: true, evidenceRef: "eas-proof" },
  ]).state,
  "VERIFIED",
);
assert.equal(
  anchors.evaluate(HASH, [
    { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
  ]).state,
  "PENDING",
);
assert.equal(
  anchors.evaluate(HASH, [
    { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
    { chain: "ETHEREUM_EAS", subjectHash: "b".repeat(64), confirmed: true, evidenceRef: "spoof" },
  ]).state,
  "QUARANTINED",
);

const devices = [1,2,3].map((n) => ({
  deviceId: `device-${n}`,
  payloadHash: HASH,
  teeQuoteVerified: true,
  cellId: "cell-1",
  signature: `sig-${n}`,
}));
const expectedReceipt = IMobileCellularOrchestra.receiptHash("cell-1", HASH, devices.map((d) => d.deviceId));
assert.equal(
  new IMobileCellularOrchestra().aggregate(devices, {
    cellId: "cell-1",
    gNodeBId: "gnb-1",
    authorized: true,
    teeVerified: true,
    receiptHash: expectedReceipt,
  }, 3).state,
  "VERIFIED_PROCESS",
);
assert.equal(
  new IMobileCellularOrchestra().aggregate(
    devices.map((d) => ({ ...d, payloadHash: d.deviceId === "device-2" ? "b".repeat(64) : HASH })),
    { cellId: "cell-1", gNodeBId: "gnb-1", authorized: true, teeVerified: true, receiptHash: "" },
    3,
  ).state,
  "ACTION_REQUIRED",
);

console.log("PoT Vonage + multi-chain + iMobile integration tests PASS");
