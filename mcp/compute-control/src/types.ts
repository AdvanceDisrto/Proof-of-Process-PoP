export type ProviderKind = "cloud"|"gpu"|"vm"|"container"|"bare_metal"|"cellular"|"telecom"|"internet"|"wifi"|"bluetooth"|"wireless"|"blockchain"|"crypto"|"chat"|"ai";
export type LifecycleAction = "create"|"start"|"stop"|"restart"|"terminate";
export interface ResourceRef { provider:string; resourceId:string; kind:ProviderKind; region?:string; }
export interface ProviderCapabilities { kinds:ProviderKind[]; lifecycle:LifecycleAction[]; gpuVendors?:("amd"|"nvidia"|"other")[]; runtimes?:("rocm"|"cuda"|"cpu"|"other")[]; connectivity?:("ssh"|"cellular"|"telecom"|"internet"|"wifi"|"bluetooth"|"wireless")[]; }
export interface WorkloadRequest { name:string; gitCommit?:string; command:string; environmentHash?:string; inputHash?:string; }
export interface ExecutionResult { exitCode:number; startedAt:string; endedAt:string; stdoutHash:string; stderrHash:string; artifactHashes:string[]; providerReceipt?:string; }
export interface PoPExecutionReceipt {
  schema:"pop/compute-control-execution/v2";
  operation:string;
  prevReceiptHash:string|null;
  resource:ResourceRef;
  workload:WorkloadRequest|null;
  execution:ExecutionResult|null;
  evidence:{requestHash:string;telemetryHash:string|null;provenanceHash:string|null};
  anchor:{status:"absent"|"submitted"|"confirmed"|"reorged";chain?:string;txHash?:string;confirmations?:number};
  state:"VERIFIED_PROCESS"|"ACTION_REQUIRED"|"QUARANTINED";
  receiptHash:string;
}
