import type {LifecycleAction} from "./types.js";
export interface MutationPolicy { allowLifecycle:LifecycleAction[]; allowSsh:boolean; allowPhysicalActuation:boolean; }
export const DEFAULT_POLICY:MutationPolicy={allowLifecycle:["create","start","stop","restart"],allowSsh:true,allowPhysicalActuation:false};
export function assertLifecycleAllowed(action:LifecycleAction,policy=DEFAULT_POLICY):void { if(!policy.allowLifecycle.includes(action)) throw new Error(`ACTION_REQUIRED: lifecycle action ${action} is not authorized`); }
export function assertPhysicalActuationBlocked(policy=DEFAULT_POLICY):void { if(!policy.allowPhysicalActuation) throw new Error("ACTION_REQUIRED: physical actuation remains outside Compute Control MCP"); }
