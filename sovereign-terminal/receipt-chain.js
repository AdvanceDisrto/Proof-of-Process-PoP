"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

function canonicalize(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalize).join(",") + "]";
  return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + canonicalize(value[key])).join(",") + "}";
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

class ReceiptChain {
  constructor(dataDir) {
    this.dataDir = dataDir;
    this.keysDir = path.join(dataDir, "keys");
    this.chainFile = path.join(dataDir, "chain.jsonl");
    fs.mkdirSync(this.keysDir, { recursive: true, mode: 0o700 });
    this.privateKey = this.loadOrCreateKey();
    this.publicKey = crypto.createPublicKey(this.privateKey);
    const recovered = this.verify();
    if (!recovered.valid) throw new Error("existing receipt chain failed verification");
    this.head = recovered.head;
    this.sequence = recovered.count;
  }

  loadOrCreateKey() {
    const keyPath = path.join(this.keysDir, "identity.pem");
    if (fs.existsSync(keyPath)) return crypto.createPrivateKey(fs.readFileSync(keyPath));
    const { privateKey } = crypto.generateKeyPairSync("ed25519");
    fs.writeFileSync(keyPath, privateKey.export({ type: "pkcs8", format: "pem" }), { mode: 0o600 });
    return privateKey;
  }

  append(payload) {
    const body = {
      protocol: "IPROOF-EXEC-v1",
      sequence: ++this.sequence,
      ...payload,
      prev: this.head,
      timestamp: new Date().toISOString(),
    };
    const digest = sha256(Buffer.from(canonicalize(body), "utf8"));
    const receipt = {
      ...body,
      hash: "sha256:" + digest,
      signature: "ed25519:" + crypto.sign(null, Buffer.from(digest, "hex"), this.privateKey).toString("hex"),
    };
    fs.appendFileSync(this.chainFile, JSON.stringify(receipt) + "\n", { encoding: "utf8", mode: 0o600 });
    this.head = receipt.hash;
    return receipt;
  }

  verifyReceipt(receipt, expectedPrev) {
    const { hash, signature, ...body } = receipt;
    const digest = sha256(Buffer.from(canonicalize(body), "utf8"));
    if (hash !== "sha256:" + digest || body.prev !== expectedPrev) return false;
    const sig = String(signature || "").replace(/^ed25519:/, "");
    if (!/^[a-f0-9]{128}$/.test(sig)) return false;
    return crypto.verify(null, Buffer.from(digest, "hex"), this.publicKey, Buffer.from(sig, "hex"));
  }

  verify() {
    if (!fs.existsSync(this.chainFile)) return { valid: true, count: 0, head: null };
    let prev = null;
    let count = 0;
    try {
      for (const line of fs.readFileSync(this.chainFile, "utf8").split("\n").filter(Boolean)) {
        const receipt = JSON.parse(line);
        if (!this.verifyReceipt(receipt, prev)) return { valid: false, count, head: prev };
        prev = receipt.hash;
        count += 1;
      }
    } catch {
      return { valid: false, count, head: prev };
    }
    return { valid: true, count, head: prev };
  }
}

module.exports = { ReceiptChain, canonicalize, sha256 };
