import argparse,json,time
from pathlib import Path
from agents.ilogic_agent import ILogicAgent
def main(game,max_actions,out):
 import arc_agi
 from arcengine import GameState
 arc=arc_agi.Arcade();env=arc.make(game,save_recording=True,include_frame_data=True)
 ag=ILogicAgent();ag.set_action_space(env.action_space)
 cur=env.reset()
 if cur is None: raise RuntimeError("reset returned no observation")
 prev=None;steps=0;t=time.time();resets=1
 while steps<max_actions:
  state=getattr(getattr(cur,"state",None),"name",str(getattr(cur,"state","UNKNOWN"))).upper()
  if state=="WIN": break
  if state=="GAME_OVER":
   cur=env.reset();prev=None;resets+=1
   if resets>25: break
   continue
  a=ag.choose_action([],cur)
  step_data={"x":32,"y":32} if getattr(a,"is_complex",lambda:False)() else {}
  nxt=env.step(a,data=step_data,reasoning=getattr(a,"reasoning",None))
  if nxt is None: raise RuntimeError("env.step returned None")
  if prev is not None: ag.observe(prev,a,nxt)
  prev,cur=cur,nxt;steps+=1
 sc=arc.get_scorecard()
 if hasattr(sc,"model_dump"): raw=sc.model_dump(mode="json")
 elif isinstance(sc,dict): raw=sc
 else: raw=getattr(sc,"__dict__",{"repr":repr(sc)})
 raw["_agent_run"]={"game":game,"actions":steps,"seconds":round(time.time()-t,3),"resets":resets,"agent_stats":ag.stats}
 p=Path(out);p.mkdir(parents=True,exist_ok=True)
 (p/f"scorecard_{game}.json").write_text(json.dumps(raw,indent=2,default=str))
 (p/f"play_{game}.json").write_text(json.dumps(raw["_agent_run"],indent=2))
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--max-actions",type=int,default=5000);ap.add_argument("--out",default="evidence");a=ap.parse_args();main(a.game,a.max_actions,a.out)
