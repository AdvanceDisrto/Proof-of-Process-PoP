from __future__ import annotations
import argparse,json,time
from pathlib import Path
import torch
import torch.nn as nn
from .tokenizer import SovereignTokenizer
class SSMBlock(nn.Module):
    def __init__(self,dim):
        super().__init__(); self.decay=nn.Parameter(torch.full((dim,),.9)); self.in_proj=nn.Linear(dim,dim); self.out_proj=nn.Linear(dim,dim)
    def forward(self,x):
        state=torch.zeros(x.size(0),x.size(2),device=x.device); outs=[]
        for t in range(x.size(1)):
            state=self.decay*state+torch.tanh(self.in_proj(x[:,t,:])); outs.append(state.unsqueeze(1))
        return self.out_proj(torch.cat(outs,1))
class SovereignSSM(nn.Module):
    def __init__(self,vocab,dim=128):
        super().__init__(); self.emb=nn.Embedding(vocab,dim); self.ssm=SSMBlock(dim); self.head=nn.Linear(dim,vocab)
    def forward(self,tokens): return self.head(self.ssm(self.emb(tokens)))
def train(text,steps=100,dim=128,lr=.003,seed=7,out="sovereign_cpu_model.pt"):
    torch.manual_seed(seed); tok=SovereignTokenizer(); tok.train_on_text(text); ids=tok.encode(text)
    if len(ids)<4: raise ValueError("training corpus is too small")
    x=torch.tensor([ids[:-1]],dtype=torch.long); y=torch.tensor([ids[1:]],dtype=torch.long); model=SovereignSSM(len(tok.vocab),dim).cpu(); opt=torch.optim.AdamW(model.parameters(),lr=lr); loss_fn=nn.CrossEntropyLoss(); started=time.time(); last=0.0
    for step in range(1,steps+1):
        opt.zero_grad(); logits=model(x); loss=loss_fn(logits.reshape(-1,len(tok.vocab)),y.reshape(-1)); loss.backward(); opt.step(); last=float(loss)
    torch.save({"state_dict":model.state_dict(),"vocab":tok.vocab,"dim":dim,"steps":steps,"seed":seed},out)
    return {"status":"PASS","device":"cpu","steps":steps,"vocab":len(tok.vocab),"parameters":sum(p.numel() for p in model.parameters()),"final_loss":last,"elapsed_seconds":round(time.time()-started,3),"artifact":str(out)}
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("corpus"); ap.add_argument("--steps",type=int,default=100); ap.add_argument("--dim",type=int,default=128); ap.add_argument("--out",default="sovereign_cpu_model.pt"); a=ap.parse_args(); print(json.dumps(train(Path(a.corpus).read_text(encoding="utf-8"),a.steps,a.dim,out=a.out),indent=2))
