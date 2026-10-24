import argparse,json,time
from pathlib import Path
from agents.ilogic_agent import ILogicAgent
def main(game,max_actions,out):
 import arc_agi
 arc=arc_agi.Arcade();env=arc.make(game);ag=ILogicAgent();ag.set_action_space(env.action_space)
 cur=getattr(env,"observation",None)
 if cur is None and hasattr(env,"reset"):cur=env.reset()
 if cur is None:raise RuntimeError("no initial observation")
 prev=None;steps=0;t=time.time()
 while steps<max_actions and not ag.is_done([],cur):
  a=ag.choose_action([],cur);nxt=env.step(a)
  if prev is not None:ag.observe(prev,a,nxt)
  prev,cur=cur,nxt;steps+=1
 sc=arc.get_scorecard();raw=sc if isinstance(sc,dict) else getattr(sc,"__dict__",{"repr":repr(sc)})
 p=Path(out);p.mkdir(parents=True,exist_ok=True)
 (p/f"scorecard_{game}.json").write_text(json.dumps(raw,indent=2,default=str))
 (p/f"play_{game}.json").write_text(json.dumps({"game":game,"actions":steps,"seconds":round(time.time()-t,3),"agent_stats":ag.stats,"terminal_state":str(getattr(cur,"state",None))},indent=2))
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--game",required=True);ap.add_argument("--max-actions",type=int,default=5000);ap.add_argument("--out",default="evidence");a=ap.parse_args();main(a.game,a.max_actions,a.out)
