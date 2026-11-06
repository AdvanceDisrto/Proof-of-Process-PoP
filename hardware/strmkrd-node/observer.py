"""STRMKRD Rev0 headless Linux observation loop.

Reads REAL I2C only (no mock fallback in this executable), validates fixed-point
values with Z3, and emits clearly UNAUTHENTICATED JSON lines. This is an
untrusted measurement observation stream; it must never be labeled hardware-
attested, mint a QoW receipt, or claim an iSPU photonic engine is present.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
import json
import signal
import sys
import time
import importlib.util

def load_bringup():
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location("strmkrd_rev0_bringup",here/"bringup.py")
    import sys as _sys
    mod=importlib.util.module_from_spec(spec)
    _sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

bringup=load_bringup()

def check_observation(observation:dict)->dict:
    """Software solver proves only exact integer bounds, not sensor correctness."""
    from z3 import Int,Solver,Not,And,unsat,sat
    if observation.get("source_tier")!="UNAUTHENTICATED_I2C_OBSERVATION":
        raise ValueError("wrong evidence source")
    temp=observation["temperature"]
    power=observation["power_meter"]
    temp_units=temp["temperature_sixteenths_c"]
    if type(temp_units) is not int:
        raise ValueError("noninteger temperature")
    if temp.get("source_tier")!="UNAUTHENTICATED_I2C_OBSERVATION":
        raise ValueError("sensor tier mismatch")
    v=Decimal(power["bus_v"])
    watts=Decimal(power["power_w"])
    if not (v.is_finite() and watts.is_finite()):
        raise ValueError("nonfinite power values")
    # Z3 integer input: volts scaled by 1.25 millivolt/bit.
    bus_ticks=int(v/Decimal("0.00125"))
    if Decimal(bus_ticks)*Decimal("0.00125")!=v:
        raise ValueError("voltage not on INA226 register grid")
    t=Int("temp_sixteenths_c"); b=Int("bus_voltage_ticks")
    solver=Solver()
    solver.add(t==temp_units,b==bus_ticks)
    policy=And(t>=-640,t<=2000,b>=0,b<=28800)
    solver.add(Not(policy))
    r=solver.check()
    verdict="PROVEN_TRUE" if r==unsat else "REFUTED_FALSE" if r==sat else "UNKNOWN"
    return {
        "policy_id":"STRMKRD_REV0_SENSOR_NOMINAL_INPUT_RANGE_V1",
        "source_tier":"UNAUTHENTICATED_I2C_OBSERVATION",
        "axioms":{"temperature_sixteenths_c":temp_units,"ina_bus_1p25mv_ticks":bus_ticks},
        "claim":{"min_temp_sixteenths":-640,"max_temp_sixteenths":2000,
                 "min_bus_ticks":0,"max_bus_ticks":28800},
        "verdict":verdict,
        "does_not_prove":["sensor calibration","device identity","electrical safety",
                          "photonic computation","measured energy integral"],
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus",type=int,default=1)
    parser.add_argument("--ina-address",type=lambda s:int(s,0),default=0x40)
    parser.add_argument("--interval-sec",type=float,default=60)
    parser.add_argument("--once",action="store_true")
    args=parser.parse_args()
    if args.interval_sec<0.1 or args.interval_sec>3600:
        parser.error("invalid interval")
    stop=False
    def request_stop(_signal,_frame):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    while not stop:
        try:
            obs=bringup.hardware_probe(args.bus,args.ina_address,False)
            evaluated=check_observation(obs)
        except (OSError,RuntimeError,ValueError,KeyError) as exc:
            print(json.dumps({"status":"HALT_HARDWARE_EVIDENCE","error_type":type(exc).__name__,
                              "hardware_gate":"NOT_VERIFIED"}),file=sys.stderr,flush=True)
            return 2
        print(json.dumps({"spec":"strmkrd/rev0/hardware-observation-with-smt/v1",
              "observation":obs,"smt_evaluation":evaluated,
              "authenticity":"NOT_VERIFIED","qow_receipt":"NOT_MINTED",
              "pop_receipt":"NOT_MINTED"},separators=(",",":")),flush=True)
        if args.once:break
        remaining=args.interval_sec
        while remaining>0 and not stop:
            sleep_for=min(remaining,0.5)
            time.sleep(sleep_for)
            remaining-=sleep_for
    return 0

if __name__=="__main__":
    raise SystemExit(main())
