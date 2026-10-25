import { generateKeyPairSync, sign } from "node:crypto";
import test from "node:test";
import assert from "node:assert/strict";
import {
  EvidenceAdapterVerifier,
  UniversalSignatureEngine,
  type UniversalSignature,
} from "../src/core/universal_signature.js";

const base: UniversalSignature = {
  author: "MACHINE",
  signatureFormat: "ED25519",
  imprintData: "receipt-001",
  ledger: "BLOCKCHAIN",
  evidenceHash: UniversalSignatureEngine.hashImprint("receipt-001"),
};

test("refuses to fabricate domain verification", () => {
  const result = new UniversalSignatureEngine().verifySignature({
    author: "PHYSICS",
    signatureFormat: "SPECTRAL_LINES",
    imprintData: "observed-spectrum",
    ledger: "SPACETIME",
  });
  assert.equal(result.verified, false);
  assert.equal(result.status, "PENDING");
});

test("rejects author/format mismatch", () => {
  const result = new UniversalSignatureEngine().verifySignature({
    author: "GEOLOGY",
    signatureFormat: "ED25519",
    imprintData: "receipt",
    ledger: "BLOCKCHAIN",
  });
  assert.equal(result.status, "QUARANTINED");
  assert.equal(result.verified, false);
});

test("verifies an actual Ed25519 machine signature", () => {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const signedPayload = JSON.stringify({ receiptId: "receipt-001", state: "EXECUTION_REPORTED" });
  const signature = sign(null, Buffer.from(signedPayload, "utf8"), privateKey).toString("base64");

  const result = new UniversalSignatureEngine().verifySignature({
    ...base,
    publicKey: publicKey.export({ type: "spki", format: "pem" }).toString(),
    signature,
    signedPayload,
  });
  assert.equal(result.status, "VERIFIED");
  assert.equal(result.verified, true);
});

test("tampering produces a failed verification rather than rewriting history", () => {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const signedPayload = "receipt-before-correction";
  const signature = sign(null, Buffer.from(signedPayload, "utf8"), privateKey).toString("base64");

  const result = new UniversalSignatureEngine().verifySignature({
    ...base,
    publicKey: publicKey.export({ type: "spki", format: "pem" }).toString(),
    signature,
    signedPayload: "receipt-after-tampering",
  });
  assert.equal(result.status, "QUARANTINED");
  assert.equal(result.verified, false);
});

test("external evidence can advance only by producing a new verification result", () => {
  const verifier = new EvidenceAdapterVerifier(() => ({
    status: "VERIFIED",
    verified: true,
    reason: "Independent evidence adapter verified the observed event.",
  }));

  const result = new UniversalSignatureEngine().verifyWith(
    {
      author: "CIVILIZATION",
      signatureFormat: "TECHNOSIGNATURE",
      imprintData: "observed-technosphere-event",
      ledger: "GALAXY",
    },
    verifier,
  );

  assert.equal(result.status, "VERIFIED");
  assert.equal(result.verified, true);
});
