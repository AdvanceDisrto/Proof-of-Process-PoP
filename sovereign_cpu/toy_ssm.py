from __future__ import annotations
import math, random
class TinySSM:
    """Dependency-free recurrent CPU model for deterministic smoke tests, not a frontier model."""
    def __init__(self,vocab=32,dim=16,seed=7):
        r=random.Random(seed); self.vocab,self.dim=vocab,dim
        self.emb=[[r.uniform(-.1,.1) for _ in range(dim)] for _ in range(vocab)]
        self.w=[[r.uniform(-.1,.1) for _ in range(dim)] for _ in range(dim)]
        self.head=[[r.uniform(-.1,.1) for _ in range(dim)] for _ in range(vocab)]
    def step(self,token,state):
        x=self.emb[token%self.vocab]; return [math.tanh(.8*state[i]+sum(self.w[i][j]*x[j] for j in range(self.dim))) for i in range(self.dim)]
    def logits(self,state): return [sum(row[j]*state[j] for j in range(self.dim)) for row in self.head]
def run_smoke(tokens):
    m=TinySSM(); state=[0.0]*m.dim; out=[]
    for token in tokens:
        state=m.step(token,state); out.append(max(range(m.vocab),key=lambda k:m.logits(state)[k]))
    return out
if __name__=="__main__": print(run_smoke([1,2,3,4,5]))
