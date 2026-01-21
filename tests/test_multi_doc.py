"""
Phase 4: Multi-Document Summarization - Unit Tests
===================================================

Tests for multi-doc query detection and comparative summarization.
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestMultiDocDetection:
    """Test detect_multi_doc_query function."""
    
    def test_detect_comparison_keywords(self):
        """Test detection of comparison keywords."""
        from app.memory.rag_v2_multi_doc import detect_multi_doc_query
        
        # Positive cases
        assert detect_multi_doc_query("sözleşme A ve B karşılaştır") is True
        assert detect_multi_doc_query("iki belge arasındaki fark") is True
        assert detect_multi_doc_query("tüm raporlar") is True
        assert detect_multi_doc_query("belgeler arasında ortak noktalar") is True
        assert detect_multi_doc_query("her doküman") is True
        
        # Negative cases  
        assert detect_multi_doc_query("TCK 157 nedir") is False
        assert detect_multi_doc_query("madde 42 açıkla") is False
        assert detect_multi_doc_query("bu konu hakkında bilgi") is False
    
    def test_detect_plural_forms(self):
        """Test detection of plural document references."""
        from app.memory.rag_v2_multi_doc import detect_multi_doc_query
        
        # Plural forms (multi-doc)
        assert detect_multi_doc_query("bu belgelerde ne var") is True
        assert detect_multi_doc_query("sözleşmeleri incele") is True
        assert detect_multi_doc_query("dokümanlar nerede") is True
        
        # Singular forms (not multi-doc)
        assert detect_multi_doc_query("belge nerede") is False
        assert detect_multi_doc_query("sözleşme oku") is False
    
    def test_edge_cases(self):
        """Test edge cases."""
        from app.memory.rag_v2_multi_doc import detect_multi_doc_query
        
        # Empty query
        assert detect_multi_doc_query("") is False
        
        # Single word
        assert detect_multi_doc_query("test") is False
        
        # Case insensitivity (lowercase ve title case çalışıyor)
        # NOTE: Python Türkçe uppercase "I" problemi var
        assert detect_multi_doc_query("karşılaştır") is True
        assert detect_multi_doc_query("Karşılaştır") is True  # Title case


class TestMultiDocSummarization:
    """Test generate_multi_doc_summary function."""
    
    @pytest.mark.asyncio
    async def test_generate_summary_success(self):
        """Test successful multi-doc summary generation."""
        from app.memory.rag_v2_multi_doc import generate_multi_doc_summary
        
        # Mock candidates from 2 different documents
        candidates = [
            {"text": "Doc A content", "filename": "doc_a.pdf", "upload_id": "id_a", "score": 0.1, "page_number": 1},
            {"text": "Doc A more", "filename": "doc_a.pdf", "upload_id": "id_a", "score": 0.2, "page_number": 2},
            {"text": "Doc B content", "filename": "doc_b.pdf", "upload_id": "id_b", "score": 0.15, "page_number": 1},
            {"text": "Doc B more", "filename": "doc_b.pdf", "upload_id": "id_b", "score": 0.25, "page_number": 2},
        ]
        
        with patch('app.providers.llm.groq.GroqProvider') as mock_provider:
            mock_instance = AsyncMock()
            mock_instance.generate.return_value = "Doc A says X, while Doc B says Y. Main difference is Z."
            mock_provider.return_value = mock_instance
            
            result = await generate_multi_doc_summary(
                query="compare doc A and doc B",
                candidates=candidates,
                top_k_per_doc=2
            )
            
            # Assertions
            assert result is not None
            assert result["summary"] is not None
            assert len(result["summary"]) > 20
            assert result["total_docs"] == 2
            assert len(result["sources_breakdown"]) == 2
            
            # LLM was called
            mock_instance.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_summary_single_doc(self):
        """Test that single-document returns no summary."""
        from app.memory.rag_v2_multi_doc import generate_multi_doc_summary
        
        # Only 1 document
        candidates = [
            {"text": "Content", "filename": "doc.pdf", "upload_id": "id_a", "score": 0.1, "page_number": 1},
            {"text": "More content", "filename": "doc.pdf", "upload_id": "id_a", "score": 0.2, "page_number": 2},
        ]
        
        result = await generate_multi_doc_summary(
            query="test",
            candidates=candidates
        )
        
        # Should return None summary (need >= 2 docs)
        assert result["summary"] is None
        # total_docs may be 0 or 1 depending on how docs are grouped
        assert result["total_docs"] in [0, 1]
    
    @pytest.mark.asyncio
    async def test_generate_summary_empty_candidates(self):
        """Test empty candidates list."""
        from app.memory.rag_v2_multi_doc import generate_multi_doc_summary
        
        result = await generate_multi_doc_summary(
            query="test",
            candidates=[]
        )
        
        assert result["summary"] is None
        assert result["total_docs"] == 0
    
    @pytest.mark.asyncio
    async def test_generate_summary_llm_failure(self):
        """Test LLM failure handling."""
        from app.memory.rag_v2_multi_doc import generate_multi_doc_summary
        
        candidates = [
            {"text": "Doc A", "filename": "a.pdf", "upload_id": "id_a", "score": 0.1, "page_number": 1},
            {"text": "Doc B", "filename": "b.pdf", "upload_id": "id_b", "score": 0.1, "page_number": 1},
        ]
        
        with patch('app.providers.llm.groq.GroqProvider') as mock_provider:
            mock_instance = AsyncMock()
            mock_instance.generate.side_effect = Exception("API Error")
            mock_provider.return_value = mock_instance
            
            result = await generate_multi_doc_summary(
                query="test",
                candidates=candidates
            )
            
            # Should return None summary on error
            assert result["summary"] is None
            assert result["total_docs"] == 2  # Still tracks doc count
    
    @pytest.mark.asyncio
    async def test_top_k_per_doc_limiting(self):
        """Test that top_k_per_doc limits chunks per document."""
        from app.memory.rag_v2_multi_doc import generate_multi_doc_summary
        
        # 5 chunks from doc A, but top_k_per_doc=2
        candidates = [
            {"text": f"Doc A chunk {i}", "filename": "a.pdf", "upload_id": "id_a", "score": i*0.1, "page_number": i}
            for i in range(5)
        ] + [
            {"text": "Doc B chunk", "filename": "b.pdf", "upload_id": "id_b", "score": 0.1, "page_number": 1}
        ]
        
        with patch('app.providers.llm.groq.GroqProvider') as mock_provider:
            mock_instance = AsyncMock()
            mock_instance.generate.return_value = "Summary text"
            mock_provider.return_value = mock_instance
            
            result = await generate_multi_doc_summary(
                query="test",
                candidates=candidates,
                top_k_per_doc=2  # Only 2 chunks per doc
            )
            
            # Should use max 2 chunks per doc
            # Doc A: 2 chunks, Doc B: 1 chunk (has only 1)
            sources = result["sources_breakdown"]
            doc_a_source = next(s for s in sources if s["upload_id"] == "id_a")
            assert doc_a_source["chunk_count"] == 2  # Limited to top_k_per_doc


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
