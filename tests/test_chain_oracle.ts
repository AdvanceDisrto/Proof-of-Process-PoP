import assert from "node:assert/strict";
import { RootCauseAgent } from "../src/agentic_core/root_cause_agent.js";
import { ChainOracle } from "../src/oracle/chain_oracle.js";
import { PhysicalEvidenceGate } from "../src/translation/physical_evidence_gate.js";

const HASH = "a".repeat(64);

assert.deepEqual(
  ChainOracle.routeAndAnchor(HASH, [
    { chain: "ethereum", available: true, confirmed: true, latencyMs: 80, feeMetric: 20 },
    { chain: "polygon", available: true, confirmed: true, latencyMs: 30, feeMetric: 10 },
  ]),
  { state: "VERIFIED_PROCESS", selectedChain: "polygon" },
);

assert.deepEqual(
  ChainOracle.routeAndAnchor(HASH, [
    { chain: "ethereum", available: false, confirmed: false, latencyMs: 1, feeMetric: 1 },
  ]),
  { state: "PENDING" },
);

assert.equal(
  ChainOracle.traceProvenance({ isSafe: false, riskScore: 95, flaggedWallets: ["wallet-1"] }),
  "QUARANTINED",
);

const verified = ChainOracle.evaluate({
  subjectHash: HASH,
  provenance: { isSafe: true, riskScore: 0, flaggedWallets: [] },
  attestations: [
    { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
    { chain: "ETHEREUM_EAS", subjectHash: HASH, confirmed: true, evidenceRef: "eas-proof" },
  ],
  time: { anchorTimestamp: 1000, executionTimestamp: 1001 },
});
assert.equal(verified.state, "VERIFIED_PROCESS");
assert.deepEqual(verified.quorum.confirmedChains.sort(), ["BITCOIN_OTS", "ETHEREUM_EAS"]);

assert.equal(
  ChainOracle.evaluate({
    subjectHash: HASH,
    provenance: { isSafe: true, riskScore: 0, flaggedWallets: [] },
    attestations: [
      { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
    ],
    time: { anchorTimestamp: 1000, executionTimestamp: 1001 },
  }).state,
  "PENDING",
);

assert.equal(
  ChainOracle.evaluate({
    subjectHash: HASH,
    provenance: { isSafe: true, riskScore: 0, flaggedWallets: [] },
    attestations: [
      { chain: "BITCOIN_OTS", subjectHash: HASH, confirmed: true, evidenceRef: "btc-proof" },
      { chain: "ETHEREUM_EAS", subjectHash: "b".repeat(64), confirmed: true, evidenceRef: "spoof" },
    ],
    time: { anchorTimestamp: 1000, executionTimestamp: 1001 },
  }).state,
  "QUARANTINED",
);

assert.throws(
  () => ChainOracle.buildRegulatoryReceipt("bad", "tx", "ethereum", 1000),
  /subject hash/,
);

const receipt = ChainOracle.buildRegulatoryReceipt(HASH, "0xtx", "ethereum", 1000);
assert.equal(receipt.provider, "KALEIDO");
assert.equal(receipt.regulatoryStandard, "FDA-21-CFR-PART-11-DIGITAL-PROOFS");

const inference = new RootCauseAgent().analyze("chain-bound-payload");
const physicalEvidence = {
  teeQuoteVerified: true,
  otsAnchorVerified: true,
  physicalActuatorInterlockHealthy: true,
  commandHash: inference.hypothesisHash,
};
assert.equal(
  new PhysicalEvidenceGate().evaluateWithChainOracle(inference, physicalEvidence, {
    subjectHash: inference.hypothesisHash,
    provenance: { isSafe: true, riskScore: 0, flaggedWallets: [] },
    attestations: [
      { chain: "BITCOIN_OTS", subjectHash: inference.hypothesisHash, confirmed: true, evidenceRef: "btc-proof" },
      { chain: "ETHEREUM_EAS", subjectHash: inference.hypothesisHash, confirmed: true, evidenceRef: "eas-proof" },
    ],
    time: { anchorTimestamp: 1000, executionTimestamp: 1001 },
  }),
  "LAB_DISPATCH_VERIFIED",
);

assert.equal(
  new PhysicalEvidenceGate().evaluateWithChainOracle(inference, physicalEvidence, {
    subjectHash: inference.hypothesisHash,
    provenance: { isSafe: true, riskScore: 0, flaggedWallets: [] },
    attestations: [
      { chain: "BITCOIN_OTS", subjectHash: inference.hypothesisHash, confirmed: true, evidenceRef: "btc-proof" },
    ],
    time: { anchorTimestamp: 1000, executionTimestamp: 1001 },
  }),
  "ACTION_REQUIRED",
);

console.log("Chain Infrastructure Oracle + PhysicalEvidenceGate integration tests PASS");
