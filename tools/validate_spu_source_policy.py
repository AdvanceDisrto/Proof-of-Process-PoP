from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=[root/"rtl/ispu10240",root/"rtl/route_partition_1024.sv",root/"src",root/"include"]
bad=["MOCK_ZKP","FAKE_PHYSICAL","FABRICATED_SILICON=true","tapeoutReady=true","real20MiBSramProven=true"]
hits=[]
for base in paths:
    for p in base.rglob("*") if base.is_dir() else [base]:
        if p.is_file() and p.suffix in {".sv",".cpp",".hpp",".h",".py",".sh"}:
            s=p.read_text(errors="ignore")
            for token in bad:
                if token in s: hits.append(f"{p}:{token}")
if hits:
    print("SOURCE_POLICY_FAIL")
    print("\n".join(hits))
    raise SystemExit(1)
print("SOURCE_POLICY_PASS")
