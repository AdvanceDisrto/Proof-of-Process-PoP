from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
names=["SPU_Vector_Lane_4Wide.sv","SPU_Vector_Group_32x4.sv","SPU_Sovereign_Core.sv","SPU_Systolic_Tensor_Core.sv","SPU_Top_Sovereign_Matrix.sv","SPU_Sovereign_10240_Lock.sv"]
m=ROOT/"rtl/ispu10240/SHA256SUMS.v1.5"
expected={}
for line in m.read_text().splitlines():
 if line and not line.startswith("#"):
  h,n=line.split(None,1); expected[n]=h
assert list(expected)==names, "manifest order/hierarchy mismatch"
for n in names:
 got=hashlib.sha256((ROOT/"rtl/ispu10240"/n).read_bytes()).hexdigest()
 assert got==expected[n], f"custody mismatch: {n}"
print("iSPU10240 V1.5 custody: PASS")
