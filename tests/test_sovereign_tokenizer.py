from sovereign_cpu.tokenizer import SovereignTokenizer

def test_tokenizer_round_trip_known_tokens(tmp_path):
    t=SovereignTokenizer(); t.train_on_text("Sovereign intelligence requires local infrastructure.")
    ids=t.encode("Sovereign intelligence.")
    assert ids[0]==2 and ids[-1]==3
    assert "sovereign" in t.decode(ids)
    p=tmp_path/"vocab.json"; t.save(p); assert SovereignTokenizer.load(p).vocab==t.vocab
