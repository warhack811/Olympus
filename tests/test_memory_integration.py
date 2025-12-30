# tests/test_memory_integration.py
"""
Memory Integration Unit Tests

Phase 1.5 - Blueprint v1 Section 8 4-Layer Integration testleri.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock


# =============================================================================
# MEMORY CONTEXT TESTS
# =============================================================================

class TestMemoryContext:
    """MemoryContext dataclass testleri."""
    
    def test_create_empty_context(self):
        """Boş context oluşturulabilmeli."""
        from app.orchestrator_v42.interfaces import MemoryContext
        
        ctx = MemoryContext()
        
        assert ctx.is_empty is True
        assert ctx.total_items == 0
        assert ctx.layers_queried == []
    
    def test_total_items_calculation(self):
        """Item sayısı doğru hesaplanmalı."""
        from app.orchestrator_v42.interfaces import MemoryContext
        
        ctx = MemoryContext(
            recent_messages=[{"role": "user", "content": "test"}],
            profile_facts=[{"key": "name", "value": "Ahmet"}],
            semantic_memories=[{"text": "memory1"}, {"text": "memory2"}],
            instant_facts=["fact1"]
        )
        
        assert ctx.total_items == 5  # 1 + 1 + 2 + 1
        assert ctx.is_empty is False
    
    def test_to_prompt_context(self):
        """Prompt context string oluşturulabilmeli."""
        from app.orchestrator_v42.interfaces import MemoryContext
        
        ctx = MemoryContext(
            profile_summary="Kullanıcı: Ahmet, Yazılımcı",
            session_summary="Python konuşuluyor"
        )
        
        prompt = ctx.to_prompt_context()
        
        assert "[KULLANICI PROFİLİ]" in prompt
        assert "Ahmet" in prompt
        assert "[OTURUM ÖZETİ]" in prompt
    
    def test_to_prompt_context_empty(self):
        """Boş context boş string vermeli."""
        from app.orchestrator_v42.interfaces import MemoryContext
        
        ctx = MemoryContext()
        prompt = ctx.to_prompt_context()
        
        assert prompt == ""


# =============================================================================
# LAYER RESULT TESTS
# =============================================================================

class TestLayerResult:
    """LayerResult testleri."""
    
    def test_successful_result(self):
        """Başarılı layer sonucu."""
        from app.orchestrator_v42.interfaces import LayerResult
        
        result = LayerResult(
            layer_name="working_memory",
            success=True,
            latency_ms=15.5,
            item_count=3
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failed_result(self):
        """Başarısız layer sonucu."""
        from app.orchestrator_v42.interfaces import LayerResult
        
        result = LayerResult(
            layer_name="user_profile",
            success=False,
            latency_ms=5.0,
            item_count=0,
            error="Database connection failed"
        )
        
        assert result.success is False
        assert "Database" in result.error


# =============================================================================
# AGGREGATION RESULT TESTS
# =============================================================================

class TestAggregationResult:
    """AggregationResult testleri."""
    
    def test_all_successful(self):
        """Tüm layer'lar başarılı."""
        from app.orchestrator_v42.interfaces import (
            MemoryContext, LayerResult, AggregationResult
        )
        
        result = AggregationResult(
            context=MemoryContext(),
            layer_results=[
                LayerResult("layer1", True, 10, 5),
                LayerResult("layer2", True, 20, 3),
            ],
            total_latency_ms=30
        )
        
        assert result.all_successful is True
    
    def test_partial_failure(self):
        """Bazı layer'lar başarısız."""
        from app.orchestrator_v42.interfaces import (
            MemoryContext, LayerResult, AggregationResult
        )
        
        result = AggregationResult(
            context=MemoryContext(),
            layer_results=[
                LayerResult("layer1", True, 10, 5),
                LayerResult("layer2", False, 20, 0, "Error"),
            ]
        )
        
        assert result.all_successful is False


# =============================================================================
# MEMORY ADAPTER LEGACY API TESTS
# =============================================================================

class TestMemoryAdapterLegacyAPI:
    """Legacy get_memory_context API testleri."""
    
    @pytest.mark.asyncio
    async def test_memory_disabled(self):
        """Memory kapalıysa ran=False dönmeli."""
        from app.orchestrator_v42.memory_adapter import get_memory_context
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        
        flags = OrchestratorFeatureFlags(memory_enabled=False)
        
        result = await get_memory_context(
            user_id="123",
            message="test",
            flags=flags,
            trace_id="test-trace"
        )
        
        assert result["ran"] is False
        assert "kapalı" in result["notes"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_user_id(self):
        """Geçersiz user_id için ran=False."""
        from app.orchestrator_v42.memory_adapter import get_memory_context
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        
        flags = OrchestratorFeatureFlags(memory_enabled=True)
        
        result = await get_memory_context(
            user_id="unknown",
            message="test",
            flags=flags,
            trace_id="test-trace"
        )
        
        assert result["ran"] is False
        assert "Geçersiz" in result["notes"]
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(self):
        """Dry-run modunda simülasyon dönmeli."""
        from app.orchestrator_v42.memory_adapter import get_memory_context
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        
        flags = OrchestratorFeatureFlags(
            memory_enabled=True,
            memory_dry_run=True
        )
        
        result = await get_memory_context(
            user_id="123",
            message="test",
            flags=flags,
            trace_id="test-trace"
        )
        
        assert result["ran"] is True
        assert result["dry_run"] is True


# =============================================================================
# 4-LAYER AGGREGATION TESTS
# =============================================================================

class TestFourLayerAggregation:
    """4-Layer aggregation testleri."""
    
    @pytest.mark.asyncio
    async def test_aggregation_with_mocked_layers(self):
        """Mock layer'lar ile aggregation."""
        from app.orchestrator_v42.memory_adapter import get_aggregated_context
        from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
        
        flags = OrchestratorFeatureFlags(memory_enabled=True)
        
        # Mock all layer fetchers
        with patch('app.orchestrator_v42.memory_adapter._fetch_working_memory', new_callable=AsyncMock) as mock_wm, \
             patch('app.orchestrator_v42.memory_adapter._fetch_user_profile', new_callable=AsyncMock) as mock_up, \
             patch('app.orchestrator_v42.memory_adapter._fetch_semantic_memory', new_callable=AsyncMock) as mock_sm, \
             patch('app.orchestrator_v42.memory_adapter._fetch_conversation_archive', new_callable=AsyncMock) as mock_ca:
            
            mock_wm.return_value = ({"item_count": 2, "recent_messages": [{}, {}]}, 10)
            mock_up.return_value = ({"item_count": 1, "facts": [{"key": "name", "value": "Test"}], "summary": "Test User"}, 15)
            mock_sm.return_value = ({"item_count": 3, "memories": [{}, {}, {}]}, 20)
            mock_ca.return_value = ({"item_count": 0}, 5)
            
            result = await get_aggregated_context(
                user_id=123,
                message="test query",
                flags=flags,
                trace_id="test-trace"
            )
            
            # All layers should be queried (profile, semantic, archive - working memory needs flag)
            assert len(result.layer_results) >= 3
            assert result.context is not None
            # Latency should be recorded
            assert result.total_latency_ms >= 0


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Yardımcı fonksiyon testleri."""
    
    def test_resolve_user_id_numeric(self):
        """Numeric string çevrilmeli."""
        from app.orchestrator_v42.memory_adapter import _resolve_user_id
        
        result = _resolve_user_id("123")
        assert result == 123
    
    def test_resolve_user_id_string(self):
        """String username hash olmalı."""
        from app.orchestrator_v42.memory_adapter import _resolve_user_id
        
        # Non-numeric string should return a hash
        result = _resolve_user_id("john_doe")
        
        # Should return a hash-based int (user resolver will fail, fallback to hash)
        assert isinstance(result, int)
        assert result > 0


# =============================================================================
# MERGE LAYER DATA TESTS
# =============================================================================

class TestMergeLayerData:
    """Layer data merge testleri."""
    
    def test_merge_working_memory(self):
        """Working memory merge."""
        from app.orchestrator_v42.interfaces import MemoryContext
        from app.orchestrator_v42.memory_adapter import _merge_layer_data
        
        ctx = MemoryContext()
        data = {
            "recent_messages": [{"role": "user"}],
            "session_summary": "Test summary",
            "instant_facts": ["fact1", "fact2"]
        }
        
        _merge_layer_data(ctx, "working_memory", data)
        
        assert len(ctx.recent_messages) == 1
        assert ctx.session_summary == "Test summary"
        assert len(ctx.instant_facts) == 2
    
    def test_merge_user_profile(self):
        """User profile merge."""
        from app.orchestrator_v42.interfaces import MemoryContext
        from app.orchestrator_v42.memory_adapter import _merge_layer_data
        
        ctx = MemoryContext()
        data = {
            "facts": [{"key": "name", "value": "Ahmet"}],
            "summary": "Yazılımcı"
        }
        
        _merge_layer_data(ctx, "user_profile", data)
        
        assert len(ctx.profile_facts) == 1
        assert ctx.profile_summary == "Yazılımcı"
