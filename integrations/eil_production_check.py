"""Read-only external authority + signed graph/witness assessment. No new keys, no broadcasting."""
import argparse,json,sys
try:
    from integrations.eil_production_trust import ProductionGate,bitcoin_core_readonly_lookup
except ModuleNotFoundError:
    from eil_production_trust import ProductionGate,bitcoin_core_readonly_lookup

def main(argv=None):
    p=argparse.ArgumentParser()
    for name in ("root","policy","root-pin","policy-pin","graph","witnesses"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--bitcoin-cli",default="bitcoin-cli")
    a=p.parse_args(argv)
    try:
        with open(a.graph,"r",encoding="utf-8") as f:graph=json.load(f)
        with open(a.witnesses,"r",encoding="utf-8") as f:witnesses=json.load(f)
        gate=ProductionGate(a.root,a.policy,a.root_pin,a.policy_pin)
        outcome=gate.assess(graph,witnesses,lambda txid:bitcoin_core_readonly_lookup(txid,a.bitcoin_cli))
    except (OSError,ValueError,TypeError,RuntimeError,KeyError) as exc:
        outcome={"verdict":"BLOCKED","reason":"INPUT_OR_EXTERNAL_DEPENDENCY:"+type(exc).__name__,"production_trust":"UNVERIFIED"}
    print(json.dumps(outcome,sort_keys=True,indent=2))
    return 0 if outcome["verdict"]=="ACCEPT" else 2
if __name__=="__main__":sys.exit(main())
