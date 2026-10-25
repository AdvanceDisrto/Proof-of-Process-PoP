from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
class SovereignTokenizer:
    def __init__(self): self.vocab={"[PAD]":0,"[UNK]":1,"[BOS]":2,"[EOS]":3}
    def train_on_text(self,text,max_vocab_size=10000):
        counts=Counter(re.findall(r"\\w+|[^\\w\\s]",text.lower(),re.UNICODE))
        for token,_ in counts.most_common(max(0,max_vocab_size-len(self.vocab))):
            if token not in self.vocab:self.vocab[token]=len(self.vocab)
    def encode(self,text):
        toks=re.findall(r"\\w+|[^\\w\\s]",text.lower(),re.UNICODE); return [2]+[self.vocab.get(t,1) for t in toks]+[3]
    def decode(self,ids):
        inv={v:k for k,v in self.vocab.items()}; return " ".join(inv.get(i,"[UNK]") for i in ids if i not in (2,3))
    def save(self,path): Path(path).write_text(json.dumps(self.vocab,sort_keys=True,ensure_ascii=False),encoding="utf-8")
    @classmethod
    def load(cls,path):
        x=cls(); x.vocab=json.loads(Path(path).read_text(encoding="utf-8")); return x
