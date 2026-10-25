import type {ProviderCapabilities,ResourceRef,WorkloadRequest,ExecutionResult,LifecycleAction} from "./types.js";
export interface ComputeProviderAdapter {
  readonly id:string;
  capabilities():Promise<ProviderCapabilities>;
  listResources(filter?:Partial<ResourceRef>):Promise<ResourceRef[]>;
  getResource(resource:ResourceRef):Promise<unknown>;
  lifecycle(action:LifecycleAction,resource:ResourceRef):Promise<unknown>;
  inspectGpu?(resource:ResourceRef):Promise<unknown>;
  inspectConnectivity?(resource:ResourceRef):Promise<unknown>;
  execute?(resource:ResourceRef,workload:WorkloadRequest):Promise<ExecutionResult>;
}
