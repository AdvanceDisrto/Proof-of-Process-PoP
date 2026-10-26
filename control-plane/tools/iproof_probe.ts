import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { buildEvidence } from "../src/core/innovalus_engine.js";
import { route } from "../src/core/iKerNeL.js";

function sha256(value: string): string {
  return "sha256:" + createHash("sha256").update(value, "utf8").digest("hex");
}

const request = {
  requestId: "islr-iproof-schema-probe",
  prompt: "verify artifact",
  identity: "local-operator",
  permissions: ["artifact.verify"],
};

const decision = route(request);
const digest = sha256("iSLR-IPROOF-SCHEMA-PROBE-v1");

const receipt = buildEvidence(
  request,
  decision,
  {
    artifactId: "islr-probe-artifact",
    artifactSha256: digest,
    runtimeVersion: "iSLR-control-plane-v1",
    outputSha256: digest,
    completedAt: "2026-10-26T00:00:00.000Z",
    compute: { device: "local", driver: "n/a", memoryBytes: 0 },
    networkMode: "LOCAL_ONLY_DECLARED",
    artifactBytes: 0,
    status: "PASS",
    environmentHash: digest,
    reproductionCommand: "python iSLR.py",
  },
  "islr-iproof-schema-probe",
);

mkdirSync("../evidence/islr", { recursive: true });
writeFileSync(
  "../evidence/islr/iproof-probe.json",
  JSON.stringify(receipt, null, 2) + "\n",
  "utf8",
);

console.log("iProof schema probe emitted: evidence/islr/iproof-probe.json");
