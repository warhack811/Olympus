import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock

from app.ai.prompts.compiler import build_system_prompt


def test_rag_v2_inactive_no_strict_rules():
    """Test that strict rules are NOT present when RAG v2 is inactive."""
    prompt = build_system_prompt(user=MagicMock(), rag_v2_active=False)

    assert "RAG v2 - STRICT MODE" not in prompt
    assert "ANSWER CONTRACT" not in prompt
    assert "RAG_V2_STATUS: NO_EVIDENCE_FOUND" not in prompt


def test_rag_v2_active_strict_rules_present():
    """Test that strict rules ARE present when RAG v2 is active."""
    prompt = build_system_prompt(user=MagicMock(), rag_v2_active=True)

    assert "RAG v2 - STRICT MODE" in prompt
    assert "ANSWER CONTRACT" in prompt
    assert "[NO_EVIDENCE_FOUND]" in prompt
    assert "EVIDENCE:" in prompt
    assert "ANSWER:" in prompt


def test_rag_v2_strict_rules_override_content():
    """Test specific content of the strict rules."""
    prompt = build_system_prompt(user=MagicMock(), rag_v2_active=True)

    # Check for extraction quality guard
    assert "extraction_quality: bad" in prompt

    # Check for absolute command
    assert "MUTLAK KURAL" in prompt


if __name__ == "__main__":
    # Manual run helper
    try:
        test_rag_v2_inactive_no_strict_rules()
        print("Inactive test passed")
        test_rag_v2_active_strict_rules_present()
        print("Active test passed")
        test_rag_v2_strict_rules_override_content()
        print("Override test passed")
    except AssertionError as e:
        print(f"Test Failed: {e}")
