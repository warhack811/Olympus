"""
Orchestrator v5.8 Router Upgrade - Phase 1 Verification Tests
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from app.chat.smart_router import MODEL_CATALOG, SmartRouter

# =============================================================================
# MOCK FIXTURES
# =============================================================================


@dataclass
class MockUser:
    """Test icin mock User sinifi (Repo modeli stubu)."""

    id: int = 1
    username: str = "test_user_phase1"
    bela_unlocked: bool = False
    is_banned: bool = False
    selected_model: str | None = None
    permissions: dict[str, Any] | None = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {
                "user_can_use_local": True,
                "user_can_use_internet": True,
                "user_can_use_image": True,
                "can_auto_route_to_local": True,
                "can_generate_nsfw_image": False,
                "get_censorship_level": 1,
                "is_censorship_strict": False,
            }


@pytest.fixture
def mock_user():
    return MockUser()


@pytest.fixture
def router():
    return SmartRouter()


# =============================================================================
# TESTS
# =============================================================================


class TestModelCatalog:
    def test_catalog_has_required_models(self):
        """Katalogda zorunlu 5 model var mi?"""
        expected_models = ["kimi-k2", "gpt-oss-120b", "llama-3.1-8b-instant", "qwen3-32b", "llama-70b"]
        for model in expected_models:
            assert model in MODEL_CATALOG, f"{model} katalogda eksik"

    def test_catalog_schema_compliance(self):
        """Katalog semasi v5.8 ile uyumlu mu?"""
        for _model, spec in MODEL_CATALOG.items():
            assert "strengths" in spec
            # 6 strength alani zorunlu
            required_strengths = {"coding", "analysis", "creative", "social_chat", "tool_planning", "tr_natural"}
            assert all(k in spec["strengths"] for k in required_strengths)

            assert "quality_tier" in spec
            assert "latency_tier" in spec
            assert "cost_tier" in spec
            assert "can_rewrite" in spec
            assert isinstance(spec["can_rewrite"], bool)


class TestIntentDetectionRegex:
    def test_social_chat_intent(self, router, mock_user):
        """'Nasılsın?' -> social_chat + kimi-k2"""
        decision = router.route("Nasılsın?", user=mock_user)
        orch = decision.metadata.get("orchestrator", {})

        assert orch.get("version") == "v5.8"
        assert orch.get("selected_model") == "kimi-k2"

        task = orch.get("tasks", [{}])[0]
        assert task.get("type") == "social_chat"
        # Capability check
        assert "social_chat" in task.get("required_capabilities", [])

        # Signal check
        signals = orch.get("signals", {})
        assert signals.get("tr_slang_hint") is True

    def test_code_intent(self, router, mock_user):
        """'Python script yaz' -> code + gpt-oss-120b"""
        decision = router.route("Bana bir Python script yaz", user=mock_user)
        orch = decision.metadata.get("orchestrator", {})

        assert orch.get("selected_model") == "gpt-oss-120b"
        task = orch.get("tasks", [{}])[0]
        assert task.get("type") == "code"
        assert "coding" in task.get("required_capabilities", [])

    def test_rag_query_signals(self, router, mock_user):
        """'TCK 157 nedir?' -> rag/tool signals"""
        decision = router.route("TCK 157 nedir?", user=mock_user)
        orch = decision.metadata.get("orchestrator", {})

        signals = orch.get("signals", {})
        task = orch.get("tasks", [{}])[0]

        # Phase 1: regex sinyali rag_needed=True yapar
        assert signals.get("rag_needed") is True
        assert signals.get("exact_match_hint") is True
        assert task.get("type") == "rag_query"
        # Requires tools list check - STRICT CHECK per Phase 1.1
        assert "rag_search" in task.get("requires_tools", [])
        assert isinstance(task.get("requires_tools"), list)

    def test_internet_tool_consistency(self, router, mock_user):
        """'Bugün dolar kaç?' -> tool_needed + web_search"""
        # "dolar" or "fiyat" usually triggers internet patterns
        decision = router.route("Dolar ne kadar oldu?", user=mock_user)
        orch = decision.metadata.get("orchestrator", {})

        signals = orch.get("signals", {})
        task = orch.get("tasks", [{}])[0]

        assert signals.get("tool_needed") is True
        assert "web_search" in task.get("requires_tools", [])

    def test_metadata_structure(self, router, mock_user):
        """Metadata yapisi dogru mu (complexity vs)"""
        decision = router.route("Karincalar nasil uyur?", user=mock_user)
        orch = decision.metadata.get("orchestrator", {})

        assert "complexity" in orch
        assert orch["complexity"] in ["simple", "medium", "high"]
        assert "tasks" in orch
        assert isinstance(orch["tasks"], list)
        assert len(orch["tasks"]) == 1
        assert "confidence" in orch


class TestIntentLLMExtension:
    """Async LLM intent detection unit tests (called directly)"""

    @pytest.mark.asyncio
    async def test_llm_intent_timeout(self, router):
        """LLM timeout -> INTENT_LLM_TIMEOUT donmeli"""
        with patch("asyncio.sleep", side_effect=asyncio.TimeoutError):
            result, error = await router._detect_intent_llm("test")
            assert result is None
            assert error == "INTENT_LLM_TIMEOUT"

    @pytest.mark.asyncio
    async def test_llm_intent_error(self, router):
        """Generic error -> INTENT_LLM_ERROR"""
        with patch("asyncio.sleep", side_effect=Exception("Boom")):
            result, error = await router._detect_intent_llm("test")
            assert result is None
            assert error == "INTENT_LLM_ERROR"

    @pytest.mark.asyncio
    async def test_llm_intent_success_stub(self, router):
        """Stub basarili donus -> regex result"""
        result, error = await router._detect_intent_llm("Python yaz")
        assert error is None
        assert result["intent"] == "code"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
