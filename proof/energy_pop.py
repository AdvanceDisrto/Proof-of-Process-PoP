import glob,time

def read_energy_uj():
    vals=[]
    for p in glob.glob("/sys/class/powercap/**/energy_uj",recursive=True):
        try: vals.append((p,int(open(p).read().strip())))
        except (OSError,ValueError): pass
    return vals or None

def measure(work):
    before=read_energy_uj(); work(); after=read_energy_uj()
    if not before or not after:return {"state":"ACTION_REQUIRED","measurement":"UNAVAILABLE","energy_consumed_uj":None,"does_not_prove":["physical energy consumption"]}
    b=dict(before); a=dict(after); common=set(b)&set(a)
    if not common:return {"state":"ACTION_REQUIRED","measurement":"UNAVAILABLE","energy_consumed_uj":None,"does_not_prove":["physical energy consumption"]}
    # Avoid inventing wraparound limits. Negative deltas require counter-specific metadata.
    ds=[a[p]-b[p] for p in common]
    if any(d<0 for d in ds):return {"state":"ACTION_REQUIRED","measurement":"COUNTER_WRAP_UNRESOLVED","energy_consumed_uj":None,"does_not_prove":["physical energy consumption"]}
    return {"state":"MEASURED_EXTERNAL","measurement":"RAPL_POWERCAP","energy_consumed_uj":sum(ds),"does_not_prove":["independent calibration of the hardware energy counter"]}
