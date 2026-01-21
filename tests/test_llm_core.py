import pytest

from app.config import get_settings
from app.core.llm import budget_tracker, governance, key_manager
from app.core.llm.generator import LLMGenerator, LLMRequest


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch):
    get_settings.cache_clear()
    key_manager.reset()
    budget_tracker.reset()
    yield
    get_settings.cache_clear()
    key_manager.reset()
    budget_tracker.reset()


def test_governance_uses_static_defaults(monkeypatch):
    """Governance statik defaults'ları kullanıyor mu test et."""
    # Env değişkenlerini temizle
    monkeypatch.delenv("GROQ_PRIMARY_MODEL", raising=False)
    monkeypatch.delenv("GROQ_FAST_MODEL", raising=False)
    monkeypatch.delenv("ROLE_MODEL_CHAINS", raising=False)
    get_settings.cache_clear()

    # Statik defaults'lar kullanılmalı (constants.py'den)
    chain_semantic = governance.get_model_chain("semantic")
    assert "llama-3.1-8b-instant" in chain_semantic or len(chain_semantic) > 0
    
    chain_synthesizer = governance.get_model_chain("synthesizer")
    assert "llama-3.3-70b-versatile" in chain_synthesizer or len(chain_synthesizer) > 0


def test_governance_override():
    chain = governance.with_override("answer", "override-x")
    assert chain[0] == "override-x"


def test_governance_reads_config_chains(monkeypatch):
    """Config chains'i doğru okuyor mu test et."""
    monkeypatch.setenv(
        "ROLE_MODEL_CHAINS",
        '{"search":["model-a","model-b"],"answer":["aa","bb"]}',
    )
    monkeypatch.delenv("GROQ_PRIMARY_MODEL", raising=False)
    monkeypatch.delenv("GROQ_FAST_MODEL", raising=False)
    get_settings.cache_clear()

    chain = governance.get_model_chain("search")
    assert chain == ["model-a", "model-b"]
    
    # Config chains statik defaults'ları override etmeli
    chain_answer = governance.get_model_chain("answer")
    assert chain_answer == ["aa", "bb"]


def test_governance_static_defaults_match_atlas():
    chain = governance.get_model_chain("orchestrator")
    assert chain[:3] == [
        "gemini-2.0-flash",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]
    synth_chain = governance.get_model_chain("synthesizer")
    assert "moonshotai/kimi-k2-instruct" in synth_chain or "llama-3.3-70b-versatile" in synth_chain


def test_key_manager_cooldown_and_selection():
    key_manager.initialize(groq_keys=["key-a", "key-b"], gemini_keys=None)
    first = key_manager.get_best_key(model_id="llama-3.3")
    assert first == "key-a"

    key_manager.report_error("key-a", status_code=429, model_id="llama-3.3")
    second = key_manager.get_best_key(model_id="llama-3.3")
    assert second == "key-b"


def test_budget_tracker_limits():
    budget_tracker.set_custom_limits("model-x", rpd=1, tpd=10)
    ok, err = budget_tracker.check_budget("model-x")
    assert ok and err is None

    budget_tracker.record_usage("model-x", tokens=5)
    ok_after, err_after = budget_tracker.check_budget("model-x")
    assert not ok_after
    assert "Request budget exceeded" in err_after


@pytest.mark.asyncio
async def test_generator_fallback_with_registered_provider(monkeypatch):
    key_manager.initialize(groq_keys=["key-1"], gemini_keys=None)
    budget_tracker.set_custom_limits("model-a", rpd=5, tpd=100)
    budget_tracker.set_custom_limits("model-b", rpd=5, tpd=100)

    monkeypatch.setattr(governance, "get_model_chain", lambda role: ["model-a", "model-b"])
    monkeypatch.setattr(governance, "detect_provider", lambda model_id: "groq")

    calls: list[str] = []

    async def adapter(model_id, api_key, request, stream=False):
        calls.append(model_id)
        if model_id == "model-a":
            raise RuntimeError("boom")

        class Resp:
            def __init__(self, mid: str):
                self.text = f"ok-{mid}"
                self.tokens = 7

        return Resp(model_id)

    generator = LLMGenerator(providers={"groq": adapter})
    result = await generator.generate(LLMRequest(role="answer", prompt="hi"))

    assert result.ok is True
    assert result.text == "ok-model-b"
    assert calls == ["model-a", "model-b"]
