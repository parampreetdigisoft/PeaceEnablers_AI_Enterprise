from app.llm.router import llm_router


def test_single_llm_mode_when_only_openai_enabled(monkeypatch):
    cfg = {
        "single_llm_mode": "auto",
        "providers": {
            "openai": {"enabled": True},
            "anthropic": {"enabled": False},
            "openrouter": {"enabled": False},
            "local": {"enabled": False},
        },
        "tiers": {},
        "fallback_order": ["openai"],
        "circuit_breaker": {"enabled": False},
        "semantic_cache": {"enabled": False},
    }
    monkeypatch.setattr(llm_router, "_cfg", lambda: cfg)
    monkeypatch.setattr(llm_router._instances["openai"], "is_configured", lambda: True)
    names = llm_router._candidate_names("evaluation_question")
    assert names == ["openai"]
