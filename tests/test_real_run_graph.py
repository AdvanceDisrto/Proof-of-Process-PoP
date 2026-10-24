from tools.pop_graph import CognitiveGraph
from tools.mmr import sha
PLAY={"game":"ls20","actions":5000,"agent_stats":{"probes":68,"plans":0,"stalls":4932,"steps":4999},"terminal_state":"GameState.GAME_OVER"}
RECEIPT={"spec":"innovulis-arc-agi-3/1.0","game":"ls20","levels":[],"game_rhae_weighted":0.0,"levels_completed":0,"levels_total":0,"physical_gate":"ACTION_REQUIRED","the_central_rule":"A level that did not WIN is not a solved level.","receipt_sha256":"sha256:2b20191d412c695f2e15c51be9d3dc215273b249389a07714c3e5304cc5a8f18"}
SCORECARD={"card_id":"7dee7a04-ad90-4ae9-b294-2b289f24328b","score":0.0,"environments":[]}
SPU={"spec":"innovulis-spu-evidence/1.0","state":"VERIFIED_PROCESS","physical_gate":"ACTION_REQUIRED","surfaces":{"cpp_reference":"VERIFIED_PROCESS","rtl_simulation":"VERIFIED_PROCESS","materialization":"BLOCKED"}}
def test_real_ls20_graph():
 g=CognitiveGraph(sha(b"ls20-run-2026-10-24"))
 g.add_raw_node("play_ls20",None,"execution_trace",PLAY)
 g.add_raw_node("receipt_ls20","play_ls20","arc_receipt",RECEIPT)
 g.add_raw_node("scorecard_ls20","receipt_ls20","scorecard",SCORECARD)
 g.add_raw_node("spu_evidence",None,"spu_receipt",SPU)
 r=g.to_receipt()
 assert r["node_count"]==4 and r["verified_count"]==4 and r["pruned_count"]==0
 assert r["physical_gate"]=="ACTION_REQUIRED"
 assert r["registry_root"].startswith("sha256:")
