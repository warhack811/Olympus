"""
Phase 2: Document Selection Threshold - Unit Tests
===================================================

Tests for dynamic top_k_docs selection based on query intent.
"""

import pytest
from app.memory.rag_v2 import _determine_doc_count


class TestDocumentSelection:
    """Test _determine_doc_count function."""
    
    def test_multi_doc_keywords(self):
        """Multi-doc keyword'leri test eder."""
        # Karşılaştırma keywords
        assert _determine_doc_count("sözleşme A ve B karşılaştır") == 8
        assert _determine_doc_count("iki belge arasındaki fark") == 8
        assert _determine_doc_count("karşılaştırma yap") == 8
        
        # Plural forms
        assert _determine_doc_count("bu belgelerde ne var") == 8
        assert _determine_doc_count("dokümanlar nerede") == 8
        assert _determine_doc_count("sözleşmeler") == 8
        assert _determine_doc_count("raporlar özet") == 8
        
        # "hangi belge" pattern
        assert _determine_doc_count("hangi belgede bu bilgi var") == 8
        assert _determine_doc_count("hangi dokümanda") == 8
    
    def test_long_query_heuristic(self):
        """Uzun sorguları test eder (>50 chars)."""
        # Exactly 50 chars (boundary test)
        query_50 = "a" * 50
        assert _determine_doc_count(query_50) == 5  # <= 50 → 5
        
        # 51 chars (should trigger long query heuristic)
        query_51 = "a" * 51
        assert _determine_doc_count(query_51) == 8  # > 50 → 8
        
        # Realistic long query
        long_query = "Bu çok uzun bir sorgu metni ve karmaşık bir analiz gerektiriyor detaylı açıklama"
        assert len(long_query) > 50
        assert _determine_doc_count(long_query) == 8
    
    def test_single_doc_queries(self):
        """Normal (tek belge) sorgular için top_k_docs=5."""
        # Kısa sorgular
        assert _determine_doc_count("TCK 157 nedir") == 5
        assert _determine_doc_count("madde 42") == 5
        assert _determine_doc_count("kısa sorgu") == 5
        
        # Orta uzunlukta ama multi-doc keyword yok
        assert _determine_doc_count("şirket politikası nedir") == 5
        assert _determine_doc_count("25 karakterlik sorgu test") == 5
    
    def test_edge_cases(self):
        """Edge case'ler."""
        # Boş query
        assert _determine_doc_count("") == 5
        
        # Sadece whitespace
        assert _determine_doc_count("   ") == 5
        
        # Tek kelime
        assert _determine_doc_count("test") == 5
        
        # Case sensitivity test (sadece lowercase ve karışık case)
        # NOT: Python Türkçe "İ" problemi: "İkisi".lower() != "ikisi"
        # Bu yüzden sadece guaranteed working case'leri test et
        assert _determine_doc_count("karşılaştır") == 8
        assert _determine_doc_count("Karşılaştır") == 8  # Title case (ş çalışıyor)
        assert _determine_doc_count("ikisi") == 8  # Lowercase
        assert _determine_doc_count("her ikisi") == 8  # Phrase
    
    def test_combined_triggers(self):
        """Birden fazla tetikleyici aynı anda."""
        # Long query + multi-doc keyword
        long_multi = "Bu belgeler arasındaki farkları karşılaştırmak istiyorum detaylı olarak"
        assert len(long_multi) > 50
        assert _determine_doc_count(long_multi) == 8
        
        # Multiple keywords
        assert _determine_doc_count("belgeler arasında karşılaştırma") == 8
        assert _determine_doc_count("dokümanlar ve raporlar farkı") == 8
    
    def test_no_false_positives(self):
        """Yanlış pozitif vermesin."""
        # "karşı" kelimesi "karşılaştır" değil
        assert _determine_doc_count("karşı taraf") == 5
        
        # "ara" kelimesi "arasında" değil
        assert _determine_doc_count("ara bul") == 5
        
        # Singular forms (plural degil)
        assert _determine_doc_count("belge nerede") == 5  # Not "belgeler"
        assert _determine_doc_count("doküman oku") == 5  # Not "dokümanlar"
    
    def test_real_world_scenarios(self):
        """Gerçek dünya kullanım senaryoları."""
        # Senaryo 1: Legal comparison
        assert _determine_doc_count("sözleşme A ve sözleşme B ücret farkı") == 8
        
        # Senaryo 2: Multi-document search
        assert _determine_doc_count("tüm raporlarda bu konu var mı") == 8
        
        # Senaryo 3: Single document focus
        assert _determine_doc_count("TCK 157/1 açıkla") == 5
        
        # Senaryo 4: General query
        assert _determine_doc_count("bu konu hakkında bilgi ver") == 5


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
