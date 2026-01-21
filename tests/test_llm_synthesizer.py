import pytest

from app.core.llm import LLMSynthesizer, LLMGenerator
from app.core.llm import governance, key_manager, budget_tracker
from app.core.llm.generator import LLMRequest


@pytest.fixture(autouse=True)
def _reset():
    key_manager.reset()
    budget_tracker.reset()
    governance.get_model_chain("synthesizer")  # touch cache path
    yield
    key_manager.reset()
    budget_tracker.reset()


@pytest.mark.asyncio
async def test_synthesizer_fallback(monkeypatch):
    key_manager.initialize(groq_keys=["k1"], gemini_keys=None)
    budget_tracker.set_custom_limits("m1", rpd=5, tpd=100)
    budget_tracker.set_custom_limits("m2", rpd=5, tpd=100)

    monkeypatch.setattr(governance, "get_model_chain", lambda role: ["m1", "m2"])
    monkeypatch.setattr(governance, "detect_provider", lambda model_id: "groq")

    calls = []

    async def adapter(model_id, api_key, request: LLMRequest, stream=False):
        calls.append(model_id)
        if model_id == "m1":
            raise RuntimeError("boom")

        class Resp:
            def __init__(self, mid: str):
                self.text = f"synth-{mid}"

        return Resp(model_id)

    generator = LLMGenerator(providers={"groq": adapter})
    synth = LLMSynthesizer(generator)
    result = await synth.synthesize("hello")

    assert result.ok
    assert result.text == "synth-m2"
    assert calls == ["m1", "m2"]


@pytest.mark.asyncio
async def test_synthesizer_stream(monkeypatch):
    key_manager.initialize(groq_keys=["k1"], gemini_keys=None)
    budget_tracker.set_custom_limits("m1", rpd=5, tpd=100)

    monkeypatch.setattr(governance, "get_model_chain", lambda role: ["m1"])
    monkeypatch.setattr(governance, "detect_provider", lambda model_id: "groq")

    async def adapter(model_id, api_key, request: LLMRequest, stream=False):
        async def gen():
            yield "a"
            yield "b"

        return gen()

    generator = LLMGenerator(providers={"groq": adapter})
    synth = LLMSynthesizer(generator)

    chunks = []
    async for c in synth.synthesize_stream("x"):
        chunks.append(c)

    assert chunks == ["a", "b"]
