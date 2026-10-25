import {createHash} from "node:crypto";
import type {ExecutionResult,PoPExecutionReceipt,ResourceRef,WorkloadRequest} from "./types.js";
function canonical(value:unknown):string { return JSON.stringify(value,Object.keys((value??{}) as object).sort()) ?? ""; }
function sha256(value:string):string { return "sha256:"+createHash("sha256").update(value).digest("hex"); }
export function createExecutionReceipt(operation:string,resource:ResourceRef,workload?:WorkloadRequest,execution?:ExecutionResult,externalAnchor?:string):PoPExecutionReceipt {
  const requestHash=sha256(canonical({operation,resource,workload}));
  const body={
    schema:"pop/compute-control-execution/v1" as const,operation,resource,workload,execution,
    evidence:{requestHash,telemetryHash:execution?sha256(canonical(execution)):undefined,provenanceHash:workload?.gitCommit?sha256(workload.gitCommit):undefined,externalAnchor},
    state:execution?.exitCode===0?"VERIFIED_PROCESS" as const:"ACTION_REQUIRED" as const
  };
  return {...body,receiptHash:sha256(canonical(body))};
}
