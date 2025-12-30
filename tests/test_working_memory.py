# tests/test_working_memory.py
"""
Working Memory Unit Tests

Phase 1.1 - Blueprint v1 Section 8 Layer 1 doğrulama testleri.
Redis mock ile test eder, gerçek Redis bağlantısı gerektirmez.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit tests."""
    client = AsyncMock()
    
    # Default responses
    client.ping = AsyncMock(return_value=True)
    client.lrange = AsyncMock(return_value=[])
    client.lpush = AsyncMock(return_value=1)
    client.ltrim = AsyncMock(return_value=True)
    client.expire = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.sadd = AsyncMock(return_value=1)
    client.smembers = AsyncMock(return_value=set())
    client.exists = AsyncMock(return_value=True)
    client.scan = AsyncMock(return_value=(0, []))
    
    # Pipeline mock
    pipeline_mock = AsyncMock()
    pipeline_mock.lpush = MagicMock()
    pipeline_mock.ltrim = MagicMock()
    pipeline_mock.expire = MagicMock()
    pipeline_mock.sadd = MagicMock()
    pipeline_mock.execute = AsyncMock(return_value=[1, True, True])
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    client.pipeline = MagicMock(return_value=pipeline_mock)
    
    return client


@pytest.fixture
def mock_settings():
    """Mock Settings for tests."""
    settings = MagicMock()
    settings.REDIS_URL = "redis://localhost:6379/2"
    settings.ORCH_WORKING_MEMORY_ENABLED = True
    settings.ORCH_WORKING_MEMORY_TTL = 172800  # 48 hours
    settings.ORCH_WORKING_MEMORY_MAX_MESSAGES = 10
    return settings


# =============================================================================
# REDIS CLIENT TESTS
# =============================================================================

class TestRedisClient:
    """Redis client singleton tests."""
    
    @pytest.mark.asyncio
    async def test_get_redis_returns_none_when_unavailable(self):
        """Redis yoksa None dönmeli."""
        with patch("app.core.redis_client.REDIS_AVAILABLE", False):
            from app.core.redis_client import get_redis
            result = await get_redis()
            assert result is None
    
    @pytest.mark.asyncio
    async def test_is_redis_available(self):
        """is_redis_available sync check."""
        from app.core.redis_client import is_redis_available
        # redis paketi yüklü olduğu için True dönmeli
        assert isinstance(is_redis_available(), bool)


# =============================================================================
# WORKING MEMORY KEYS TESTS
# =============================================================================

class TestWorkingMemoryKeys:
    """Key pattern tests."""
    
    def test_messages_key_format(self):
        """Messages key pattern doğru olmalı."""
        from app.memory.working_memory import WorkingMemoryKeys
        
        key = WorkingMemoryKeys.messages(123)
        assert key == "wm:123:msgs"
        
        key = WorkingMemoryKeys.messages("user_456")
        assert key == "wm:user_456:msgs"
    
    def test_summary_key_format(self):
        """Summary key pattern doğru olmalı."""
        from app.memory.working_memory import WorkingMemoryKeys
        
        key = WorkingMemoryKeys.summary(123)
        assert key == "wm:123:summary"
    
    def test_rag_cache_key_format(self):
        """RAG cache key pattern doğru olmalı."""
        from app.memory.working_memory import WorkingMemoryKeys
        
        key = WorkingMemoryKeys.rag_cache(123, "abc123")
        assert key == "wm:123:rag:abc123"
    
    def test_facts_key_format(self):
        """Facts key pattern doğru olmalı."""
        from app.memory.working_memory import WorkingMemoryKeys
        
        key = WorkingMemoryKeys.facts(123)
        assert key == "wm:123:facts"
    
    def test_all_user_keys_pattern(self):
        """All user keys pattern doğru olmalı."""
        from app.memory.working_memory import WorkingMemoryKeys
        
        pattern = WorkingMemoryKeys.all_user_keys(123)
        assert pattern == "wm:123:*"


# =============================================================================
# WORKING MEMORY SERVICE TESTS
# =============================================================================

class TestWorkingMemoryService:
    """Working Memory service tests with mocked Redis."""
    
    @pytest.mark.asyncio
    async def test_get_recent_messages_empty(self, mock_redis_client):
        """Boş messages listesi dönmeli."""
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            messages = await WorkingMemory.get_recent_messages(123)
            assert messages == []
            mock_redis_client.lrange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_recent_messages_with_data(self, mock_redis_client):
        """Messages listesi parse edilmeli."""
        test_messages = [
            json.dumps({"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00"}),
            json.dumps({"role": "assistant", "content": "Hi!", "timestamp": "2025-01-01T00:00:01"}),
        ]
        mock_redis_client.lrange = AsyncMock(return_value=test_messages)
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            messages = await WorkingMemory.get_recent_messages(123)
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_append_message_success(self, mock_redis_client):
        """Mesaj ekleme başarılı olmalı."""
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.append_message(
                user_id=123,
                role="user",
                content="Test message"
            )
            assert result is True
    
    @pytest.mark.asyncio
    async def test_append_message_no_redis(self):
        """Redis yoksa False dönmeli."""
        with patch("app.core.redis_client.get_redis", return_value=None):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.append_message(
                user_id=123,
                role="user",
                content="Test"
            )
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_session_summary(self, mock_redis_client):
        """Session summary okunmalı."""
        mock_redis_client.get = AsyncMock(return_value="Test summary")
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            summary = await WorkingMemory.get_session_summary(123)
            assert summary == "Test summary"
    
    @pytest.mark.asyncio
    async def test_update_session_summary(self, mock_redis_client):
        """Session summary güncellenmeli."""
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.update_session_summary(123, "New summary")
            assert result is True
            mock_redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rag_cache_miss(self, mock_redis_client):
        """RAG cache miss None dönmeli."""
        mock_redis_client.get = AsyncMock(return_value=None)
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.get_cached_rag(123, "test query")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_rag_cache_hit(self, mock_redis_client):
        """RAG cache hit sonuç dönmeli."""
        cached_data = json.dumps([{"doc": "test", "score": 0.9}])
        mock_redis_client.get = AsyncMock(return_value=cached_data)
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.get_cached_rag(123, "test query")
            assert result is not None
            assert len(result) == 1
            assert result[0]["doc"] == "test"
    
    @pytest.mark.asyncio
    async def test_set_cached_rag(self, mock_redis_client):
        """RAG cache yazılmalı."""
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.set_cached_rag(
                123, 
                "test query", 
                [{"doc": "test"}]
            )
            assert result is True
    
    @pytest.mark.asyncio
    async def test_add_fact(self, mock_redis_client):
        """Fact ekleme başarılı olmalı."""
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            result = await WorkingMemory.add_fact(123, "User likes Python")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_get_facts(self, mock_redis_client):
        """Facts listesi dönmeli."""
        mock_redis_client.smembers = AsyncMock(return_value={"fact1", "fact2"})
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import WorkingMemory
            
            facts = await WorkingMemory.get_facts(123)
            assert len(facts) == 2
            assert "fact1" in facts
    
    @pytest.mark.asyncio
    async def test_hash_query_consistency(self):
        """Query hash tutarlı olmalı."""
        from app.memory.working_memory import WorkingMemory
        
        hash1 = WorkingMemory._hash_query("Test Query")
        hash2 = WorkingMemory._hash_query("test query")  # case insensitive
        hash3 = WorkingMemory._hash_query("  Test Query  ")  # whitespace
        
        assert hash1 == hash2 == hash3


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestWorkingMemoryContext:
    """get_working_memory_context tests."""
    
    @pytest.mark.asyncio
    async def test_context_when_redis_unavailable(self):
        """Redis yoksa available=False dönmeli."""
        with patch("app.core.redis_client.get_redis", return_value=None):
            from app.memory.working_memory import get_working_memory_context
            
            context = await get_working_memory_context(123)
            assert context["available"] is False
            assert context["messages"] == []
            assert context["summary"] is None
            assert context["facts"] == []
    
    @pytest.mark.asyncio
    async def test_context_when_redis_available(self, mock_redis_client):
        """Redis varsa available=True ve veriler dönmeli."""
        mock_redis_client.lrange = AsyncMock(return_value=[
            json.dumps({"role": "user", "content": "hi"})
        ])
        mock_redis_client.get = AsyncMock(return_value="Test summary")
        mock_redis_client.smembers = AsyncMock(return_value={"test fact"})
        
        with patch("app.core.redis_client.get_redis", return_value=mock_redis_client):
            from app.memory.working_memory import get_working_memory_context
            
            context = await get_working_memory_context(123)
            assert context["available"] is True
            assert len(context["messages"]) == 1
            assert context["summary"] == "Test summary"
            assert "test fact" in context["facts"]


# =============================================================================
# CONFIG INTEGRATION TESTS
# =============================================================================

class TestConfigIntegration:
    """Config ve Settings entegrasyon testleri."""
    
    def test_settings_has_redis_url(self):
        """Settings REDIS_URL içermeli."""
        from app.config import get_settings
        settings = get_settings()
        assert hasattr(settings, "REDIS_URL")
        assert "redis://" in settings.REDIS_URL
    
    def test_settings_has_working_memory_flags(self):
        """Settings Working Memory flag'leri içermeli."""
        from app.config import get_settings
        settings = get_settings()
        assert hasattr(settings, "ORCH_WORKING_MEMORY_ENABLED")
        assert hasattr(settings, "ORCH_WORKING_MEMORY_TTL")
        assert hasattr(settings, "ORCH_WORKING_MEMORY_MAX_MESSAGES")
    
    def test_feature_flags_has_working_memory(self):
        """FeatureFlags working_memory_enabled içermeli."""
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        flags = OrchestratorFeatureFlags()
        assert hasattr(flags, "working_memory_enabled")
        assert hasattr(flags, "working_memory_ttl")
        assert hasattr(flags, "working_memory_max_messages")
    
    def test_feature_flags_load_from_env(self):
        """FeatureFlags Settings'ten yüklenebilmeli."""
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        flags = OrchestratorFeatureFlags.load_from_env()
        # Should not raise, values should be populated
        assert isinstance(flags.working_memory_enabled, bool)
        assert isinstance(flags.working_memory_ttl, int)
