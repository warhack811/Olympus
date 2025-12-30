# tests/test_conversation_archive.py
"""
Conversation Archive Unit Tests

Phase 1.4 - Blueprint v1 Section 8 Layer 4 doğrulama testleri.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock


# =============================================================================
# DATE RANGE DETECTOR TESTS
# =============================================================================

class TestDateRangeDetector:
    """Tarih aralığı algılama testleri."""
    
    def test_detect_gecen_hafta(self):
        """'geçen hafta' ifadesi algılanmalı."""
        from app.memory.conversation_archive import DateRangeDetector
        
        result = DateRangeDetector.detect("Geçen hafta ne konuşmuştuk?")
        
        assert result is not None
        start, end = result
        assert (datetime.utcnow() - start).days <= 8  # ~7 gün önce
    
    def test_detect_dun(self):
        """'dün' ifadesi algılanmalı."""
        from app.memory.conversation_archive import DateRangeDetector
        
        result = DateRangeDetector.detect("Dün ne konuştuk?")
        
        assert result is not None
        start, end = result
        assert (datetime.utcnow() - start).days <= 2
    
    def test_detect_son_n_gun(self):
        """'son X gün' ifadesi algılanmalı."""
        from app.memory.conversation_archive import DateRangeDetector
        
        result = DateRangeDetector.detect("Son 5 gün içinde ne yaptık?")
        
        assert result is not None
        start, end = result
        assert (datetime.utcnow() - start).days <= 6
    
    def test_detect_last_week_english(self):
        """'last week' İngilizce algılanmalı."""
        from app.memory.conversation_archive import DateRangeDetector
        
        result = DateRangeDetector.detect("What did we discuss last week?")
        
        assert result is not None
    
    def test_detect_no_date(self):
        """Tarih ifadesi yoksa None dönmeli."""
        from app.memory.conversation_archive import DateRangeDetector
        
        result = DateRangeDetector.detect("Python nedir?")
        
        assert result is None
    
    def test_should_search_archive_positive(self):
        """Arşiv anahtar kelimeleri algılanmalı."""
        from app.memory.conversation_archive import DateRangeDetector
        
        assert DateRangeDetector.should_search_archive("Geçen hafta ne konuşmuştuk?") is True
        assert DateRangeDetector.should_search_archive("Daha önce söylemiştim") is True
        assert DateRangeDetector.should_search_archive("Hatırla bana") is True
    
    def test_should_search_archive_negative(self):
        """Normal sorgular arşiv tetiklememeli."""
        from app.memory.conversation_archive import DateRangeDetector
        
        assert DateRangeDetector.should_search_archive("Python nedir?") is False
        assert DateRangeDetector.should_search_archive("Hava nasıl?") is False


# =============================================================================
# ROLLING SUMMARY TESTS
# =============================================================================

class TestRollingSummary:
    """Rolling summary testleri."""
    
    @pytest.mark.asyncio
    async def test_trigger_at_interval(self):
        """8. turn'da tetiklenmeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        with patch.object(ConversationArchive, '_update_summary_async', new_callable=AsyncMock):
            result = await ConversationArchive.trigger_rolling_summary(
                conversation_id="conv123",
                turn_count=8
            )
            
            assert result.triggered is True
            assert result.conversation_id == "conv123"
            assert "interval_reached" in result.reason
    
    @pytest.mark.asyncio
    async def test_no_trigger_before_interval(self):
        """8'in altında tetiklenmemeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        result = await ConversationArchive.trigger_rolling_summary(
            conversation_id="conv123",
            turn_count=5
        )
        
        assert result.triggered is False
        assert "interval_not_reached" in result.reason
    
    @pytest.mark.asyncio
    async def test_trigger_at_multiple_intervals(self):
        """16, 24 vb. turn'larda da tetiklenmeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        with patch.object(ConversationArchive, '_update_summary_async', new_callable=AsyncMock):
            result_16 = await ConversationArchive.trigger_rolling_summary(
                conversation_id="conv123",
                turn_count=16
            )
            
            assert result_16.triggered is True
    
    @pytest.mark.asyncio
    async def test_force_trigger(self):
        """force=True ile her zaman tetiklenmeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        with patch.object(ConversationArchive, '_update_summary_async', new_callable=AsyncMock):
            result = await ConversationArchive.trigger_rolling_summary(
                conversation_id="conv123",
                turn_count=3,
                force=True
            )
            
            assert result.triggered is True


# =============================================================================
# CRITICAL INFO DETECTION TESTS
# =============================================================================

class TestCriticalInfoDetection:
    """Kritik bilgi algılama testleri."""
    
    def test_detect_name_request(self):
        """'Beni X diye çağır' algılanmalı."""
        from app.memory.conversation_archive import ConversationArchive
        
        assert ConversationArchive.has_critical_info("Beni Ahmet diye çağır") is True
        assert ConversationArchive.has_critical_info("Adım Mehmet") is True
    
    def test_detect_remember_request(self):
        """'Hatırla' algılanmalı."""
        from app.memory.conversation_archive import ConversationArchive
        
        assert ConversationArchive.has_critical_info("Hatırla: yarın toplantım var") is True
        assert ConversationArchive.has_critical_info("Unutma: proje deadline'ı") is True
    
    def test_no_critical_info(self):
        """Normal mesajlar kritik değil."""
        from app.memory.conversation_archive import ConversationArchive
        
        assert ConversationArchive.has_critical_info("Hava nasıl?") is False
        assert ConversationArchive.has_critical_info("Python nedir?") is False


# =============================================================================
# ARCHIVE CONTEXT TESTS
# =============================================================================

class TestArchiveContext:
    """Gateway entegrasyon testleri."""
    
    @pytest.mark.asyncio
    async def test_get_context_no_search_needed(self):
        """Arşiv araması gerekmiyorsa should_search=False."""
        from app.memory.conversation_archive import ConversationArchive
        
        result = await ConversationArchive.get_archive_context(
            user_id=123,
            query="Python nedir?"
        )
        
        assert result["should_search"] is False
        assert result["results"] == []
        assert result["available"] is True
    
    @pytest.mark.asyncio
    async def test_get_context_with_search(self):
        """Arşiv araması gerekiyorsa should_search=True."""
        from app.memory.conversation_archive import ConversationArchive
        
        with patch.object(ConversationArchive, 'search_past_conversations', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []  # Boş sonuç
            
            result = await ConversationArchive.get_archive_context(
                user_id=123,
                query="Geçen hafta ne konuşmuştuk?"
            )
            
            assert result["should_search"] is True
            assert result["date_range_detected"] is True


# =============================================================================
# RELEVANCE CALCULATION TESTS
# =============================================================================

class TestRelevanceCalculation:
    """Relevance skorlama testleri."""
    
    def test_high_relevance(self):
        """Eşleşen kelimeler yüksek skor vermeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        score = ConversationArchive._calculate_relevance(
            query="Python programlama",
            title="Python öğrenme",
            summary="Bu sohbette Python programlama konuştuk"
        )
        
        assert score > 0.5
    
    def test_low_relevance(self):
        """Eşleşmeyen kelimeler düşük skor vermeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        score = ConversationArchive._calculate_relevance(
            query="Python programlama",
            title="Yemek tarifleri",
            summary="Pasta nasıl yapılır"
        )
        
        assert score < 0.3
    
    def test_empty_query(self):
        """Boş sorgu neutral skor vermeli."""
        from app.memory.conversation_archive import ConversationArchive
        
        score = ConversationArchive._calculate_relevance(
            query="ne nasıl",  # Sadece stop words
            title="Test",
            summary="Test summary"
        )
        
        assert score == 0.5  # Neutral


# =============================================================================
# RESULT TYPE TESTS
# =============================================================================

class TestResultTypes:
    """Result dataclass testleri."""
    
    def test_archive_search_result(self):
        """ArchiveSearchResult testi."""
        from app.memory.conversation_archive import ArchiveSearchResult
        
        result = ArchiveSearchResult(
            conversation_id="conv123",
            title="Test Sohbet",
            summary="Özet",
            relevance_score=0.85,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=10
        )
        
        assert result.conversation_id == "conv123"
        assert result.relevance_score == 0.85
    
    def test_rolling_summary_result(self):
        """RollingSummaryResult testi."""
        from app.memory.conversation_archive import RollingSummaryResult
        
        result = RollingSummaryResult(
            triggered=True,
            conversation_id="conv123",
            reason="interval_reached"
        )
        
        assert result.triggered is True
        assert result.conversation_id == "conv123"
