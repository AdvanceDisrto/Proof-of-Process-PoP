import argparse,json,time
from pathlib import Path
from agents.ilogic_agent import ILogicAgent

def scorecard_dict(sc,game):
    if isinstance(sc,dict): return sc
    out={"game":game,"levels":[]}
    games=getattr(sc,"games",[]) or []
    for env in games:
        if getattr(env,"id",None) and str(env.id).split("-")[0]!=game: continue
        runs=getattr(env,"runs",[]) or []
        if not runs: continue
        run=runs[-1]
        acts=list(getattr(run,"level_actions",[]) or [])
        bases=list(getattr(run,"level_baseline_actions",[]) or [])
        state=getattr(run,"state","UNKNOWN")
        completed=int(getattr(run,"levels_completed",0) or 0)
        for i,a in enumerate(acts,1):
            out["levels"].append({"level":i,"state":"WIN" if i<=completed else str(state),"actions":int(a or 0),"human_baseline": bases[i-1] if i<=len(bases) else None})
        if out["levels"]: return out
    raw=getattr(sc,"__dict__",{})
    return raw if raw else out

def main(game,max_actions,out):
 import arc_agi
 from arcengine import GameAction,GameState
 arc=arc_agi.Arcade();env=arc.make(game,save_recording=True,include_frame_data=True)
 ag=ILogicAgent();ag.set_action_space(env.action_space)
 cur=getattr(env,"observation",None)
 if cur is None and hasattr(env,"reset"):cur=env.reset()
 if cur is None:raise RuntimeError("no initial observation")
 prev=None;steps=0;t=time.time();resets=0;stalls=0
 while steps<max_actions:
  if ag.is_done([],cur): break
  if getattr(cur,"state",None)==GameState.GAME_OVER:
   resets+=1; cur=env.reset(); prev=None
   if resets>25: break
   continue
  a=ag.choose_action([],cur)
  if getattr(a,"is_complex",lambda:False)():
   if hasattr(a,"set_data"): a.set_data({"x":32,"y":32})
   else:
    try:a.action_data={"x":32,"y":32}
    except Exception:pass
  nxt=env.step(a,reasoning=getattr(a,"reasoning",None),data=getattr(a,"action_data",None) or {})
  if prev is not None:ag.observe(prev,a,nxt)
  prev,cur=cur,nxt;steps+=1
 sc=arc.get_scorecard();raw=scorecard_dict(sc,game)
 raw["_agent_run"]={"game":game,"actions":steps,"seconds":round(time.time()-t,3),"resets":resets,"agent_stats":ag.stats}
 p=Path(out);p.mkdir(parents=True,exist_ok=True)
 (p/f"scorecard_{game}.json").write_text(json.dumps(raw,indent=2,default=str))
 (p/f"play_{game}.json").write_text(json.dumps(raw["_agent_run"],indent=2))
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--max-actions",type=int,default=5000);ap.add_argument("--out",default="evidence");a=ap.parse_args();main(a.game,a.max_actions,a.out)
