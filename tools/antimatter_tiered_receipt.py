#!/usr/bin/env python3
import json,time
from pathlib import Path
AM_C=299792458.;AM_MP=1.67262192369e-27;AM_CHEM=4.4e7
def compute(): return {"e_per_collision_j":2*AM_MP*AM_C*AM_C,"energy_density_j_per_kg":AM_C*AM_C,"ratio_vs_chemical":AM_C*AM_C/AM_CHEM}
def emit(path):
 c=compute();claims=[{"id":"AM-LAW-001","claim":"p+pbar rest-energy release is 2*m_p*c^2","tier":"LAW","gate":"PROVEN_LAW","value_j":c["e_per_collision_j"]},{"id":"AM-LAW-002","claim":"mass-energy ceiling is c^2 J/kg","tier":"LAW","gate":"PROVEN_LAW","value_j_per_kg":c["energy_density_j_per_kg"]},{"id":"AM-OBS-001","claim":"Antiprotons can be trapped for extended laboratory durations","tier":"OBSERVED","gate":"EVIDENCE_REFERENCE_REQUIRED"},{"id":"AM-SIM-001","claim":"Magnetic-nozzle performance model","tier":"SIMULATED","gate":"SIMULATED"},{"id":"AM-INT-001","claim":"Integrated beamed-core antimatter engine","tier":"INTEGRATED","gate":"ACTION_REQUIRED"},{"id":"AM-FLT-001","claim":"Antimatter spacecraft flight beyond Earth orbit","tier":"FLIGHT","gate":"ACTION_REQUIRED"}]
 r={"spec":"innovulis-antimatter-tiered-evidence/1.1","timestamp_utc":time.time(),"claims":claims,"engine_physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."};Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(r,indent=2));return r
if __name__=="__main__": emit("evidence/antimatter_tiered_receipt.json")
