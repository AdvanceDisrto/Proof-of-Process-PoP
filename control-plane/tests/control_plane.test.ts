import test from "node:test";
import assert from "node:assert/strict";
import { route } from "../src/core/iKerNeL.js";
import { buildEvidence } from "../src/core/innovalus_engine.js";

const good = "sha256:" + "a".repeat(64);

test("high-risk deployment requires human review", () => {
  const d = route({requestId:"req-1",prompt:"Deploy the model to production",identity:"operator",permissions:["deployment.production"]});
  assert.equal(d.executionClass, "HUMAN_REVIEW");
});

test("missing permission blocks deterministic action", () => {
  const d = route({requestId:"req-2",prompt:"execute code",identity:"operator",permissions:[]});
  assert.equal(d.executionClass, "BLOCKED");
});

test("iProof rejects incomplete evidence digests", () => {
  const d = route({requestId:"req-3",prompt:"verify artifact",identity:"operator",permissions:["artifact.verify"]});
  assert.throws(() => buildEvidence({
    requestId:"req-3",prompt:"verify artifact",identity:"operator",permissions:["artifact.verify"]
  }, d, {
    artifactId:"artifact",artifactSha256:"sha256:mock",runtimeVersion:"test",outputSha256:good,
    completedAt:"2026-10-25T12:00:00.000Z",compute:{device:"local",driver:"n/a",memoryBytes:0},
    networkMode:"UNSPECIFIED",artifactBytes:0,status:"PASS",environmentHash:good,reproductionCommand:"reproduce req-3"
  }, "ev-1"), /incomplete SHA-256/);
});

test("iProof binds complete evidence without inventing a signature", () => {
  const d = route({requestId:"req-4",prompt:"verify artifact",identity:"operator",permissions:["artifact.verify"]});
  const r = buildEvidence({
    requestId:"req-4",prompt:"verify artifact",identity:"operator",permissions:["artifact.verify"]
  }, d, {
    artifactId:"artifact",artifactSha256:good,runtimeVersion:"test",outputSha256:good,
    completedAt:"2026-10-25T12:00:00.000Z",compute:{device:"local",driver:"n/a",memoryBytes:0},
    networkMode:"UNSPECIFIED",artifactBytes:0,status:"PASS",environmentHash:good,reproductionCommand:"reproduce req-4"
  }, "ev-2");
  assert.equal(r.protocol,"IPROOF-v1");
  assert.equal(r.reproduction.required,true);
  assert.match(r.execution.artifact_sha256,/^sha256:[a-f0-9]{64}$/);
});
