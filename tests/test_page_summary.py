"""
Phase 3: Page Summarization - Unit Tests
==========================================

Tests for post-upload summary processing.
Uses mocks to avoid actual LLM API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path


class TestSummaryProcessor:
    """Test summary processor functions."""
    
    @pytest.mark.asyncio
    async def test_process_document_summaries_success(self):
        """Test successful summary generation."""
        from app.memory import rag_v2_summary_processor
        
        # Mock dependencies (correct module paths)
        with patch('PyPDF2.PdfReader') as mock_pdf_reader_class, \
             patch('app.memory.rag_v2._generate_page_summary') as mock_gen, \
             patch('app.memory.rag_v2._get_rag_v2_collection') as mock_coll, \
             patch('app.memory.rag_v2._sanitize_filename', return_value="test_pdf") as mock_sanitize, \
             patch('app.memory.rag_v2_lexical.upsert_chunk') as mock_fts:
            
            # Mock PDF reader (200 pages)
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Sample page text " * 50  # 800+ chars
            mock_reader_instance.pages = [mock_page] * 200
            mock_pdf_reader_class.return_value = mock_reader_instance
            
            # Mock summary generation (async)
            mock_gen.return_value = "[SAYFA 1 ÖZETİ] Test summary"
            
            # Mock collection
            mock_collection = MagicMock()
            mock_coll.return_value = mock_collection
            
            # Run processor
            # Create a temp file for testing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
                temp_path = tf.name
            
            try:
                stats = await rag_v2_summary_processor.process_document_summaries(
                    upload_id="test_upload",
                    filename="test.pdf",
                    owner="test_user",
                    file_path=temp_path,
                    scope="user"
                )
                
                # Assertions
                assert stats["summaries_generated"] > 0
                assert stats["summaries_added"] > 0
                assert stats["errors"] == 0
                
                # Summary generation was called
                assert mock_gen.call_count > 0
                
                # Collection add was called
                assert mock_collection.add.call_count > 0
            
            finally:
                # Cleanup
                Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_process_document_small_doc_skipped(self):
        """Test that small documents are skipped."""
        from app.memory import rag_v2_summary_processor
        
        with patch('PyPDF2.PdfReader') as mock_pdf:
            # Mock small PDF (50 pages)
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()] * 50
            mock_pdf.return_value = mock_reader
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
                temp_path = tf.name
            
            try:
                stats = await rag_v2_summary_processor.process_document_summaries(
                    upload_id="test_small",
                    filename="small.pdf",
                    owner="test_user",
                    file_path=temp_path
                )
                
                # Should skip (< 100 pages)
                assert stats["summaries_generated"] == 0
                assert stats["summaries_added"] == 0
            
            finally:
                Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_queue_summary_job(self):
        """Test job queuing."""
        from app.memory import rag_v2_summary_processor
        
        # Queue a job
        await rag_v2_summary_processor.queue_summary_job(
            upload_id="test_queue",
            filename="test.pdf",
            owner="test_user",
            file_path="/tmp/test.pdf"
        )
        
        # Check job status
        job = rag_v2_summary_processor.get_job_status("test_queue")
        assert job is not None
        assert job["filename"] == "test.pdf"
        assert job["status"] in ["queued", "processing"]
    
    def test_get_job_status(self):
        """Test job status retrieval."""
        from app.memory import rag_v2_summary_processor
        
        # Non-existent job
        status = rag_v2_summary_processor.get_job_status("nonexistent")
        assert status is None


class TestGeneratePageSummary:
    """Test _generate_page_summary function."""
    
    @pytest.mark.asyncio
    async def test_generate_summary_success(self):
        """Test successful summary generation."""
        from app.memory.rag_v2 import _generate_page_summary
        
        sample_text = "This is a long page text about TCK law. " * 30  # 1200+ chars
        
        with patch('app.providers.llm.groq.GroqProvider') as mock_provider:
            mock_instance = AsyncMock()
            mock_instance.generate.return_value = "This page discusses TCK Article 157."
            mock_provider.return_value = mock_instance
            
            summary = await _generate_page_summary(sample_text, "tck.pdf", 42)
            
            # Assertions
            assert summary is not None
            assert "[SAYFA 42 ÖZETİ]" in summary
            assert len(summary) > 20
            
            # LLM was called
            mock_instance.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_summary_short_text(self):
        """Test that short texts are skipped."""
        from app.memory.rag_v2 import _generate_page_summary
        
        short_text = "Short"
        summary = await _generate_page_summary(short_text, "test.pdf", 1)
        
        # Should return None for short texts
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_generate_summary_llm_failure(self):
        """Test LLM failure handling."""
        from app.memory.rag_v2 import _generate_page_summary
        
        sample_text = "Long text " * 50
        
        with patch('app.providers.llm.groq.GroqProvider') as mock_provider:
            mock_instance = AsyncMock()
            mock_instance.generate.side_effect = Exception("API Error")
            mock_provider.return_value = mock_instance
            
            summary = await _generate_page_summary(sample_text, "test.pdf", 1)
            
            # Should return None on error
            assert summary is None


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
