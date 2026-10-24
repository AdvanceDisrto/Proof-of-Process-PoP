import hashlib,json
def jcs(o): return json.dumps(o,sort_keys=True,separators=(",",":")).encode()
def sha_bytes(b): return hashlib.sha256(b).digest()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()
class MMR:
    def __init__(self): self.peaks=[]
    def append(self,leaf):
        n=(0,sha_bytes(leaf))
        while self.peaks and self.peaks[-1][0]==n[0]:
            h,p=self.peaks.pop();n=(h+1,sha_bytes(p+n[1]))
        self.peaks.append(n)
    def root(self):
        if not self.peaks:return sha(b"")
        acc=self.peaks[-1][1]
        for _,p in reversed(self.peaks[:-1]):acc=sha_bytes(p+acc)
        return "sha256:"+acc.hex()
    def peak_count(self): return len(self.peaks)
