from buddy_brain import LANGUAGES, BuddyRequest, brain_config, language_catalog

def test_language_catalog_is_nonempty_and_grouped() -> None:
    catalog = language_catalog()
    assert catalog["count"] >= 40
    assert len(catalog["groups"]) >= 6
    assert "Python" in catalog["languages"]

def test_brain_is_fail_closed_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("BUDDY_AI_BASE_URL", raising=False)
    monkeypatch.delenv("BUDDY_AI_MODEL", raising=False)
    assert brain_config() is None

def test_request_bounds() -> None:
    req = BuddyRequest(message="write a function", mode="generate", language="Rust")
    assert req.language == "Rust"
    assert "Rust" in LANGUAGES["systems"]
