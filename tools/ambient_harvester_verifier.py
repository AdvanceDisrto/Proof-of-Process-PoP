#!/usr/bin/env python3
import json,time
from pathlib import Path
DENSITIES={"barometric_mw_per_m2":1.2,"teg_uw_per_cm2":100.,"radiative_uw_per_cm2":80.,"piezo_uw_per_cm2":1.}
def compute_harvested_w(i):
 if any(v<0 for v in i.values()): raise ValueError("negative area")
 return DENSITIES["barometric_mw_per_m2"]*1e-3*i["barometric_m2"]+DENSITIES["teg_uw_per_cm2"]*1e-6*i["teg_cm2"]+DENSITIES["radiative_uw_per_cm2"]*1e-6*i["radiative_cm2"]+DENSITIES["piezo_uw_per_cm2"]*1e-6*i["piezo_cm2"]
def classify(i,idle_w,useful_load_w):
 if idle_w<0 or useful_load_w<0: raise ValueError("negative load")
 h=compute_harvested_w(i);r=idle_w+useful_load_w
 return {"verdict":"BEVERLY_CLASS_RUNNING" if h>=r else "CANNOT_SELF_RUN","harvested_w":h,"required_w":r,"coverage_ratio":h/r if r else 0.}
def emit_receipt(path,i,idle_w,useful_load_w):
 r={"spec":"innovulis-ambient-harvester/1.1","timestamp_utc":time.time(),"surface":"beverly-class-ambient-harvester","computed":classify(i,idle_w,useful_load_w),"pillars":[{"id":"PILLAR-OPEN-SYSTEM","tier":"OBSERVED","gate":"PROVEN_OBSERVED"},{"id":"PILLAR-COLD-SINK","tier":"OBSERVED","gate":"PROVEN_OBSERVED"},{"id":"PILLAR-HIGH-COERCIVITY-MAGNETS","tier":"OBSERVED","gate":"PROVEN_OBSERVED"},{"id":"PILLAR-ROOM-TEMP-AMBIENT-PRESSURE-SUPERCONDUCTOR","tier":"INTEGRATED","gate":"ACTION_REQUIRED"}],"physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."};Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(r,indent=2));return r
if __name__=="__main__":
 emit_receipt("evidence/ambient_beverly_class.json",{"barometric_m2":.01,"teg_cm2":1.,"radiative_cm2":0.,"piezo_cm2":0.},1e-6,0.)
 emit_receipt("evidence/ambient_motor_claim.json",{"barometric_m2":1.,"teg_cm2":1000.,"radiative_cm2":1000.,"piezo_cm2":1000.},100000.,0.)
