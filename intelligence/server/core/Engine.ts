import crypto from "node:crypto"; import {TailwindAIPluginRegistry} from "./PluginRegistry.js"; import {IDRSentinel} from "./IDRSentinel.js";
export interface PipelineContext{executionId:string;workflowKey:string;variables:Record<string,unknown>;history:Array<{layer:string;output:unknown;latencyMs:number}>}
export interface TokenPrimitive{layer:string;action:string;parameters:string[];conditional?:string}
export class TailwindAIEngine{
 private context:PipelineContext; private idr:IDRSentinel;
 constructor(workflowKey:string,initialVariables:Record<string,unknown>,idr=new IDRSentinel()){this.idr=idr;this.idr.verifyGenesis();this.context={executionId:crypto.randomUUID(),workflowKey,variables:initialVariables,history:[]}}
 async executePipeline(pipeline:TokenPrimitive[]){
  for(const token of pipeline){
   if(!this.idr.checkAiAuthorization(token.action))throw new Error("iDr Boundary Violation: "+token.action);
   if(token.layer==="human-approve"||token.layer==="human-edit"){const intent=JSON.stringify({execution_id:this.context.executionId,workflow_key:this.context.workflowKey,variables:this.context.variables,next_token:token});const intent_hash="sha256:"+crypto.createHash("sha256").update(intent).digest("hex");return{status:"SUSPENDED" as const,activeId:this.context.executionId,activeBreakpoint:`${token.layer}:${token.action}`,snapshot:this.context.variables,intent_hash}}
   const start=Date.now(),plugin=TailwindAIPluginRegistry.get(token.layer);if(!plugin)throw new Error("No verified plugin registered for layer "+token.layer);const result=await plugin.execute(token.action,token.parameters,this.context);this.context.variables[token.action]=result.data;this.context.history.push({layer:token.layer,output:result.data,latencyMs:Date.now()-start});
  } return{status:"COMPLETED" as const,activeId:this.context.executionId}
 }
}
