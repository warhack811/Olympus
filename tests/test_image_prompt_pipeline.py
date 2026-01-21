import asyncio
import pytest

from app.chat.processor import build_image_prompt
from app.config import get_settings


@pytest.fixture(autouse=True)
def _stub_translator(monkeypatch):
    async def _fake_translate(messages, temperature=0.0):
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        return f"translated: {user}", None

    monkeypatch.setattr("app.chat.decider.call_groq_api_safe_async", _fake_translate)
    yield


@pytest.mark.asyncio
async def test_deterministic_prompt_same_input_same_hash():
    prompt1, meta1 = await build_image_prompt("kedi resmi", {})
    prompt2, meta2 = await build_image_prompt("kedi resmi", {})
    assert prompt1 == prompt2
    assert meta1["prompt_hash"] == meta2["prompt_hash"]


@pytest.mark.asyncio
async def test_translation_isolation_style_preserved():
    prompt, _meta = await build_image_prompt("anime kedi çiz", {"image_style": "anime"})
    assert "anime style" in prompt
    assert "translated:" in prompt


@pytest.mark.asyncio
async def test_policy_guard_removes_only_policy_tokens():
    prompt, meta = await build_image_prompt("<script>alert(1)</script> kedi", {})
    assert "<script>" not in prompt
    assert "html_tag" in meta["removed_policy_tokens"]


@pytest.mark.asyncio
async def test_no_style_leak_when_default_style_disabled():
    settings = get_settings()
    original = getattr(settings, "APPLY_DEFAULT_STYLE_WHEN_UNSPECIFIED", None)
    object.__setattr__(settings, "APPLY_DEFAULT_STYLE_WHEN_UNSPECIFIED", False)
    try:
        prompt, _meta = await build_image_prompt("sade bir kedi", {}, {"defaultStyle": "realistic"})
        assert "photorealistic" not in prompt
    finally:
        if original is not None:
            object.__setattr__(settings, "APPLY_DEFAULT_STYLE_WHEN_UNSPECIFIED", original)
        else:
            try:
                delattr(settings, "APPLY_DEFAULT_STYLE_WHEN_UNSPECIFIED")
            except Exception:
                pass
