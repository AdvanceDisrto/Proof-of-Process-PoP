import hashlib
from collections import deque
def members(s):
    try:return list(s)
    except TypeError:return [getattr(s,n) for n in dir(s) if n.isupper()]
def akey(a): return getattr(a,"name",str(a))
def skey(f):
    g=getattr(f,"frame",None)
    if isinstance(g,(list,tuple)):
        q=[]
        for r in g:q.extend(r if isinstance(r,(list,tuple)) else [r])
        g=bytes((x if isinstance(x,int) else 0)&255 for x in q)
    if g is None:g=b""
    return hashlib.sha256(bytes(g)+str(getattr(f,"state","UNKNOWN")).encode()).hexdigest()[:16]
def label(f):return getattr(getattr(f,"state","UNKNOWN"),"name",str(getattr(f,"state","UNKNOWN"))).upper()
class ILogicAgent:
    def __init__(self,max_probes=64):
        self.model={};self.actions={};self.plan=deque();self.max_probes=max_probes;self.budget={};self.wins=set();self.stats={"probes":0,"plans":0,"stalls":0,"steps":0}
    def is_done(self,frames,latest):return label(latest)=="WIN"
    def set_action_space(self,space):
        self.actions={akey(a):a for a in members(space)}
    def observe(self,prev,action,nxt):
        p,n=skey(prev),skey(nxt);l=label(nxt);self.model[(p,akey(action))]=(n,l);self.stats["steps"]+=1
        if l=="WIN":self.wins.add(n)
    def choose_action(self,frames,latest):
        s=skey(latest)
        if label(latest)=="WIN":return next(iter(self.actions.values()))
        unknown=[k for k in sorted(self.actions) if not k.upper().startswith("RESET") and (s,k) not in self.model and self.budget.get(s,0)<self.max_probes]
        if unknown:
            self.budget[s]=self.budget.get(s,0)+1;self.stats["probes"]+=1;return self.actions[unknown[0]]
        q=deque([(s,[])]);seen={s};found=None
        while q and found is None:
            node,path=q.popleft()
            for (src,k),(dst,lab) in self.model.items():
                if src!=node:continue
                if dst in self.wins or lab=="WIN":found=path+[k];break
                if dst not in seen:seen.add(dst);q.append((dst,path+[k]))
        if found:self.plan=deque(found);self.stats["plans"]+=1;return self.actions[self.plan.popleft()]
        self.stats["stalls"]+=1
        ks=[k for k in sorted(self.actions) if not k.upper().startswith("RESET")]
        if not ks:raise RuntimeError("no actions")
        return self.actions[ks[0]]
