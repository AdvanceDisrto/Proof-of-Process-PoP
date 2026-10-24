from tools.arc3_receipt import build,verify
def test_nonwin_stays_closed():
 r=build({"game":"ls20","levels":[{"level":1,"state":"PLAYING","actions":10}]},"ls20",{"1":5});assert r["levels"][0]["tier"]=="ACTION_REQUIRED" and verify(r)["ok"]
def test_win_with_baseline():
 r=build({"game":"ls20","levels":[{"level":1,"state":"WIN","actions":10}]},"ls20",{"1":5});assert r["levels"][0]["tier"]=="VERIFIED_PROCESS" and verify(r)["ok"]
def test_missing_baseline():
 r=build({"game":"ls20","levels":[{"level":1,"state":"WIN","actions":10}]},"ls20",{});assert r["levels"][0]["rhae_reason"]=="no_baseline" and r["levels"][0]["tier"]=="ACTION_REQUIRED"
def test_forged_rhae():
 r=build({"game":"ls20","levels":[{"level":1,"state":"PLAYING","actions":10}]},"ls20",{"1":5});r["levels"][0]["rhae"]=1.0;assert not verify(r)["ok"]
def test_forged_gate():
 r=build({"game":"ls20","levels":[{"level":1,"state":"WIN","actions":10}]},"ls20",{"1":5});r["physical_gate"]="MEASURED_PASS";assert not verify(r)["ok"]
def test_cap():
 r=build({"game":"ls20","levels":[{"level":1,"state":"WIN","actions":10}]},"ls20",{"1":5});assert r["levels"][0]["rhae"]==0.25
