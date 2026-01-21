"""
Phase 3B Tests: LLM Gray Classifier
------------------------------------
Tests for production-ready LLM integration in gray zone (0.35-0.75 rules_score)

Features tested:
- LLM called only in gray zone
- Cache functionality
- Timeout handling
- Error fallback
- No network calls (mocked)
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from app.services.brain.intent import (
    decide_intent,
    classify_image_intent_llm,
    IntentLLMResult,
    _intent_llm_cache,
    _get_cache_key,
    normalize_text,
    ENABLE_INTENT_LLM,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    _intent_llm_cache.clear()
    yield
    _intent_llm_cache.clear()


@pytest.fixture
def enable_llm(monkeypatch):
    """Enable LLM for tests."""
    monkeypatch.setenv("ENABLE_INTENT_LLM", "1")
    # Reload module to pick up env var
    import app.services.brain.intent as intent_module
    monkeypatch.setattr(intent_module, "ENABLE_INTENT_LLM", True)


class TestPhase3B_GrayZoneLLM:
    """Test LLM classifier in gray zone."""
    
    def test_gray_zone_llm_called_when_enabled(self, enable_llm, monkeypatch):
        """Gray zone with ENABLE_INTENT_LLM=1 should call LLM."""
        mock_result = IntentLLMResult(is_image=True, confidence=0.9, reason="test")
        
        with patch('app.services.brain.intent.classify_image_intent_llm', return_value=mock_result) as mock_llm:
            # Message that produces gray zone (rules_score = 0.6)
            message = "görsele ihtiyacım var"
            decision = decide_intent(message)
            
            # Assert LLM was called
            assert mock_llm.called
            assert decision.source == "llm"
            assert decision.intent == "image"
            assert decision.confidence >= 0.75
            assert decision.llm_reason == "test"
    
    def test_gray_zone_llm_not_called_when_disabled(self, monkeypatch):
        """Gray zone with ENABLE_INTENT_LLM=0 should NOT call LLM."""
        monkeypatch.setenv("ENABLE_INTENT_LLM", "0")
        import app.services.brain.intent as intent_module
        monkeypatch.setattr(intent_module, "ENABLE_INTENT_LLM", False)
        
        with patch('app.services.brain.intent.classify_image_intent_llm') as mock_llm:
            message = "görsele ihtiyacım var"
            decision = decide_intent(message)
            
            # Assert LLM was NOT called
            assert not mock_llm.called
            assert decision.source == "rules"
            # Gray fallback without LLM
            assert decision.intent == "text"
    
    def test_high_rules_score_skips_llm(self, enable_llm):
        """High rules_score (>= 0.75) should skip LLM."""
        with patch('app.services.brain.intent.classify_image_intent_llm') as mock_llm:
            # "/image kedi" has rules_score = 1.0 (signal)
            message = "/image kedi"
            decision = decide_intent(message)
            
            assert not mock_llm.called
            assert decision.source == "signal"
            assert decision.intent == "image"
    
    def test_low_rules_score_skips_llm(self, enable_llm):
        """Low rules_score (<= 0.25) should skip LLM."""
        with patch('app.services.brain.intent.classify_image_intent_llm') as mock_llm:
            # Generic text with rules_score = 0.0
            message = "merhaba nasılsın"
            decision = decide_intent(message)
            
            assert not mock_llm.called
            assert decision.source == "rules"
            assert decision.intent == "text"
    
    def test_stoplist_skips_llm(self, enable_llm):
        """Stoplist hit should skip LLM."""
        with patch('app.services.brain.intent.classify_image_intent_llm') as mock_llm:
            message = "evimi boyadım"
            decision = decide_intent(message)
            
            assert not mock_llm.called
            assert decision.source == "rules"
            assert decision.intent == "text"
            assert decision.rules_score == 0.0


class TestPhase3B_LLMClassifier:
    """Test classify_image_intent_llm function."""
    
    def test_llm_classifier_success(self, monkeypatch):
        """Successful LLM call returns parsed result."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"is_image": true, "confidence": 0.85, "reason": "user wants to generate"}'
                }
            }]
        }
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        
        with patch('httpx.Client', return_value=mock_client):
            with patch('app.core.resilience.key_manager.get_best_key', return_value="test-key"):
                result = classify_image_intent_llm("create an image")
                
                assert result.is_image is True
                assert result.confidence == 0.85
                assert result.reason == "user wants to generate"
    
    def test_llm_classifier_parse_error(self, monkeypatch):
        """JSON parse error returns fallback."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": 'invalid json {'
                }
            }]
        }
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        
        with patch('httpx.Client', return_value=mock_client):
            with patch('app.core.resilience.key_manager.get_best_key', return_value="test-key"):
                result = classify_image_intent_llm("test")
                
                assert result.is_image is False
                assert result.confidence == 0.5
                assert result.reason == "parse_error"
    
    def test_llm_classifier_timeout(self, monkeypatch):
        """Timeout returns fallback."""
        import httpx
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException("timeout")
        
        with patch('httpx.Client', return_value=mock_client):
            with patch('app.core.resilience.key_manager.get_best_key', return_value="test-key"):
                result = classify_image_intent_llm("test")
                
                assert result.is_image is False
                assert result.confidence == 0.5
                assert result.reason == "timeout"
    
    def test_llm_classifier_no_api_key(self, monkeypatch):
        """No API key returns fallback."""
        with patch('app.core.resilience.key_manager.get_best_key', return_value=None):
            result = classify_image_intent_llm("test")
            
            assert result.is_image is False
            assert result.confidence == 0.5
            assert result.reason == "no_api_key"
    
    def test_llm_classifier_http_error(self, monkeypatch):
        """HTTP error returns fallback."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        
        with patch('httpx.Client', return_value=mock_client):
            with patch('app.core.resilience.key_manager.get_best_key', return_value="test-key"):
                result = classify_image_intent_llm("test")
                
                assert result.is_image is False
                assert result.confidence == 0.5
                assert result.reason == "http_500"


class TestPhase3B_Cache:
    """Test TTL cache functionality."""
    
    def test_cache_hit_on_second_call(self, enable_llm, monkeypatch):
        """Second call with same message should hit cache."""
        call_count = {"count": 0}
        
        # Mock at httpx level to test cache without bypassing classify_image_intent_llm
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"is_image": true, "confidence": 0.9, "reason": "test"}'
                }
            }]
        }
        
        def mock_post(*args, **kwargs):
            call_count["count"] += 1
            return mock_response
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post = mock_post
        
        with patch('httpx.Client', return_value=mock_client):
            with patch('app.core.resilience.key_manager.get_best_key', return_value="test-key"):
                message = "görsele ihtiyacım var"
                
                # First call
                decision1 = decide_intent(message)
                assert call_count["count"] == 1
                
                # Second call - should use cache
                decision2 = decide_intent(message)
                assert call_count["count"] == 1  # Not incremented - cache hit
                
                assert decision1.intent == decision2.intent
                assert decision1.confidence == decision2.confidence
    
    def test_cache_miss_after_ttl(self, enable_llm, monkeypatch):
        """Cache expires after TTL."""
        monkeypatch.setenv("INTENT_LLM_CACHE_TTL_S", "1")
        
        call_count = {"count": 0}
        
        def mock_classify(message):
            call_count["count"] += 1
            return IntentLLMResult(is_image=True, confidence=0.9, reason="test")
        
        with patch('app.services.brain.intent.classify_image_intent_llm', side_effect=mock_classify):
            message = "görsele ihtiyacım var"
            
            # First call
            decide_intent(message)
            assert call_count["count"] == 1
            
            # Wait for TTL to expire
            time.sleep(1.1)
            
            # Second call - cache expired
            decide_intent(message)
            assert call_count["count"] == 2
    
    def test_cache_different_messages(self, enable_llm):
        """Different messages should not share cache."""
        call_count = {"count": 0}
        
        def mock_classify(message):
            call_count["count"] += 1
            return IntentLLMResult(is_image=True, confidence=0.9, reason="test")
        
        with patch('app.services.brain.intent.classify_image_intent_llm', side_effect=mock_classify):
            decide_intent("görsele ihtiyacım var")
            assert call_count["count"] == 1
            
            decide_intent("bir görsel olabilir mi")
            assert call_count["count"] == 2


class TestPhase3B_Integration:
    """Integration tests for Phase 3B."""
    
    def test_llm_result_affects_decision(self, enable_llm):
        """LLM result with high confidence should return image."""
        mock_result = IntentLLMResult(is_image=True, confidence=0.9, reason="clear image request")
        
        with patch('app.services.brain.intent.classify_image_intent_llm', return_value=mock_result):
            decision = decide_intent("görsele ihtiyacım var")
            
            assert decision.intent == "image"
            assert decision.source == "llm"
            assert decision.confidence >= 0.75
    
    def test_llm_result_low_confidence_returns_text(self, enable_llm):
        """LLM result with low confidence should return text."""
        mock_result = IntentLLMResult(is_image=False, confidence=0.4, reason="not clear")
        
        with patch('app.services.brain.intent.classify_image_intent_llm', return_value=mock_result):
            decision = decide_intent("görsele ihtiyacım var")
            
            assert decision.intent == "text"
            assert decision.source == "llm"
            assert decision.confidence >= 0.4
    
    def test_phase3a_tests_still_pass(self):
        """Ensure Phase 3A tests still work (backward compatibility)."""
        # Signal test
        dec = decide_intent("/image kedi")
        assert dec.intent == "image"
        assert dec.source == "signal"
        
        # Stoplist test
        dec = decide_intent("evimi boyadım")
        assert dec.intent == "text"
        
        # Stemming test
        dec = decide_intent("kedi ciziyorum")
        assert dec.intent == "image"
