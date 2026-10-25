import assert from "node:assert/strict";
import { createHash, generateKeyPairSync, sign, verify } from "node:crypto";
import test from "node:test";

function canonicalJson(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("NON_CANONICAL_NUMBER");
    return Object.is(value, -0) ? "0" : JSON.stringify(value);
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    return "{" + Object.keys(record).sort().map((key) => JSON.stringify(key) + ":" + canonicalJson(record[key])).join(",") + "}";
  }
  throw new Error("NON_CANONICAL_VALUE");
}

test("canonicalization is key-order independent", () => {
  assert.equal(canonicalJson({ b: 2, a: 1 }), canonicalJson({ a: 1, b: 2 }));
});

test("nested arrays and objects are canonicalized", () => {
  assert.equal(canonicalJson({ z: [2, { b: true, a: null }] }), '{"z":[2,{"a":null,"b":true}]}');
});

test("canonical hash is reproducible", () => {
  const a = canonicalJson({ provider: "hyperstack", gitCommit: "a".repeat(40), exitCode: 0 });
  const b = canonicalJson({ exitCode: 0, gitCommit: "a".repeat(40), provider: "hyperstack" });
  assert.equal(createHash("sha256").update(a).digest("hex"), createHash("sha256").update(b).digest("hex"));
});

test("Ed25519 signature verifies", () => {
  const { privateKey, publicKey } = generateKeyPairSync("ed25519");
  const message = Buffer.from("receipt-test");
  const signature = sign(null, message, privateKey);
  assert.equal(verify(null, message, publicKey, signature), true);
});
