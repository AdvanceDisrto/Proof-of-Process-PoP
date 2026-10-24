#!/usr/bin/env python3
import json,time
from pathlib import Path
EDGE_NODE_HARVEST_UW=50.;EDGE_NODE_IDLE_UW=5.;EDGE_NODE_WORK_UW=20.
def classify(layers):
 t_h=t_r=0.; vs=[]
 for L in layers:
  n=L["node_count"]; h=L["harvested_w_per_node"]*n; r=(L["idle_w_per_node"]+L["workload_w_per_node"])*n
  if min(n,L["harvested_w_per_node"],L["idle_w_per_node"],L["workload_w_per_node"])<0: raise ValueError("negative budget")
  t_h+=h;t_r+=r
  v="LAYER_SELF_SUSTAINED" if h>=r else "GRID_REQUIRED"
  vs.append({"layer":L["layer"],"harvested_w":h,"required_w":r,"coverage_ratio":h/r if r else 0.,"verdict":v})
 overall="GRID_REQUIRED" if any(x["verdict"]=="GRID_REQUIRED" for x in vs) else ("SELF_RUNNING_CLAIMED" if t_r and t_h>=t_r else "EDGE_LAYER_REAL")
 return {"overall":overall,"total_harvested_w":t_h,"total_required_w":t_r,"coverage_ratio":t_h/t_r if t_r else 0.,"layer_verdicts":vs}
HONEST_DEPLOYMENT={"name":"honest-tiered-deployment","layers":[{"layer":"EDGE","node_count":1e9,"harvested_w_per_node":50e-6,"idle_w_per_node":5e-6,"workload_w_per_node":20e-6},{"layer":"ORBITAL","node_count":1e4,"harvested_w_per_node":500.,"idle_w_per_node":1500.,"workload_w_per_node":2500.},{"layer":"AI","node_count":1e3,"harvested_w_per_node":0.,"idle_w_per_node":100.,"workload_w_per_node":400.}]}
VISION_CLAIM={"name":"self-running-everywhere-vision","layers":[{"layer":"EDGE","node_count":1e10,"harvested_w_per_node":50e-6,"idle_w_per_node":5e-6,"workload_w_per_node":20e-6},{"layer":"ORBITAL","node_count":1e4,"harvested_w_per_node":5000.,"idle_w_per_node":1500.,"workload_w_per_node":2500.},{"layer":"AI","node_count":1e3,"harvested_w_per_node":500.,"idle_w_per_node":100.,"workload_w_per_node":400.}]}
def emit_receipt(path,s):
 r={"spec":"innovulis-omnipresent-mesh/1.1","timestamp_utc":time.time(),"surface":"omnipresent-ai-mesh","scenario_name":s["name"],"computed":classify(s["layers"]),"physics_gates":[{"claim":"Room-temperature ambient-pressure superconductor exists","verdict":"ACTION_REQUIRED"},{"claim":"Whole-system perpetual/self-running energy","verdict":"PHYSICALLY_IMPOSSIBLE"}],"physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."};Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(r,indent=2));return r
if __name__=="__main__":
 emit_receipt("evidence/omnipresent_honest_deployment.json",HONEST_DEPLOYMENT);emit_receipt("evidence/omnipresent_vision_claim.json",VISION_CLAIM)
