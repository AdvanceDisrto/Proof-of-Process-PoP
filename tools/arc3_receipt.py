import hashlib,json,time
CAP=1.15
def jcs(o): return json.dumps(o,sort_keys=True,separators=(",",":")).encode()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()
def state(s): return getattr(s,"name",str(s)).upper()
def level_rhae(h,a,s):
    if s!="WIN": return 0.0,"not_won"
    if h is None: return 0.0,"no_baseline"
    if a<=0: return 0.0,"no_actions"
    return min((h/a)**2,CAP),"ok"
def build(raw,game,baseline):
    if hasattr(raw,"__dict__") and not isinstance(raw,dict): raw=raw.__dict__
    ls=raw.get("levels") or raw.get("level_results") or raw.get("results") or []
    rows=[]
    for i,x in enumerate(ls,1):
        if hasattr(x,"__dict__") and not isinstance(x,dict): x=x.__dict__
        a=int(x.get("actions",x.get("action_count",0)) or 0); s=state(x.get("state","UNKNOWN")); h=baseline.get(str(x.get("level",i)))
        r,w=level_rhae(h,a,s)
        rows.append({"game":game,"level":int(x.get("level",i)),"state":s,"agent_actions":a,"human_baseline":h,"rhae":round(r,6),"rhae_reason":w,"tier":"VERIFIED_PROCESS" if w=="ok" else "ACTION_REQUIRED","gate":"ACTION_REQUIRED"})
    n=sum(x["level"]*x["rhae"] for x in rows); d=sum(x["level"] for x in rows) or 1
    rec={"spec":"innovulis-arc-agi-3/1.0","issued_utc":time.time(),"game":game,"levels":rows,"game_rhae_weighted":round(n/d,6),"levels_completed":sum(x["tier"]=="VERIFIED_PROCESS" for x in rows),"levels_total":len(rows),"physical_gate":"ACTION_REQUIRED","the_central_rule":"A level that did not WIN is not a solved level."}
    rec["receipt_sha256"]=sha(jcs(rec)); return rec
def verify(r):
    e=[]; body={k:v for k,v in r.items() if k!="receipt_sha256"}
    if sha(jcs(body))!=r.get("receipt_sha256"):e.append("receipt_sha256_mismatch")
    rows=r.get("levels",[])
    for x in rows:
        q,w=level_rhae(x.get("human_baseline"),int(x.get("agent_actions",0)),x.get("state"))
        if abs(q-x.get("rhae",-1))>1e-9:e.append("rhae_mismatch")
        if x.get("tier")!=("VERIFIED_PROCESS" if w=="ok" else "ACTION_REQUIRED"):e.append("tier_mismatch")
        if x.get("gate")!="ACTION_REQUIRED":e.append("gate_open")
    n=sum(x["level"]*x["rhae"] for x in rows);d=sum(x["level"] for x in rows) or 1
    if abs(n/d-r.get("game_rhae_weighted",-1))>1e-6:e.append("weighted_rhae_mismatch")
    if sum(x.get("tier")=="VERIFIED_PROCESS" for x in rows)!=r.get("levels_completed"):e.append("levels_completed_mismatch")
    if r.get("physical_gate")!="ACTION_REQUIRED":e.append("physical_gate_not_closed")
    return {"ok":not e,"errors":e}
