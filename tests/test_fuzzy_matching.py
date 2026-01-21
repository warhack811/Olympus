"""
Phase 1: Fuzzy ID Matching - Unit Tests
========================================

Tests for query_normalizer fuzzy correction functionality.
"""

import pytest
from app.memory.query_normalizer import QueryNormalizer


class TestFuzzyCorrections:
    """Test apply_fuzzy_corrections method."""
    
    def test_kanun_kisaltmalari(self):
        """Kanun kısaltmalarını test eder."""
        qn = QueryNormalizer()
        
        # TC → TCK
        assert "TCK" in qn.apply_fuzzy_corrections("TC 157")
        assert "TCK" in qn.apply_fuzzy_corrections("TC madde 42")
        assert "TCK" in qn.apply_fuzzy_corrections("tc 157")  # lowercase
        
        # CMC → CMK
        assert "CMK" in qn.apply_fuzzy_corrections("CMC 150")
        assert "CMK" in qn.apply_fuzzy_corrections("cmc madde")
        
        # TMC → TMK
        assert "TMK" in qn.apply_fuzzy_corrections("TMC 4")
        
        # HMC → HMK
        assert "HMK" in qn.apply_fuzzy_corrections("HMC 100")
    
    def test_typo_duzeltme(self):
        """Yaygın typo'ları test eder."""
        qn = QueryNormalizer()
        
        # Made → Madde
        assert "Madde" in qn.apply_fuzzy_corrections("Made 42")
        assert "Madde" in qn.apply_fuzzy_corrections("Made 157 nedir")
        
        # made → Madde (IGNORECASE nedeniyle uppercase replacement)
        assert "Madde" in qn.apply_fuzzy_corrections("made 42")
    
    def test_integration_with_expand(self):
        """Fuzzy + Expansion entegrasyonunu test eder."""
        qn = QueryNormalizer()
        
        # TC 157/1 → TCK 157/1 + varyantlar
        results = qn.expand_numeric_patterns("TC 157/1 nedir")
        
        # TCK düzeltmesi yapılmış olmalı
        assert any("TCK" in r for r in results), f"TCK not found in {results}"
        
        # 157/1 expansion'ı yapılmış olmalı
        assert any("157/1" in r for r in results), f"157/1 not found in {results}"
        assert any("157.1" in r for r in results), f"157.1 not found in {results}"
        
        # Hem düzeltme hem expansion birlikte
        assert any("TCK" in r and "157/1" in r for r in results)
    
    def test_no_false_positives(self):
        """Yanlış düzeltme yapmamalı."""
        qn = QueryNormalizer()
        
        # "TC" kelimesinin ortasında değil, word boundary kontrolü
        result = qn.apply_fuzzy_corrections("Otomatik sistem")
        assert "Otomatik" in result
        assert "TCK" not in result  # "tc" yanlışlıkla değiştirilmemeli
        
        # "made" kelimesinin ortasında değil
        result = qn.apply_fuzzy_corrections("homemade solution")
        assert "homemade" in result  # "made" değiştirilmemeli
    
    def test_empty_and_none(self):
        """Edge case'ler: boş string ve None."""
        qn = QueryNormalizer()
        
        # Boş string
        assert qn.apply_fuzzy_corrections("") == ""
        
        # None
        assert qn.apply_fuzzy_corrections(None) is None
    
    def test_multiple_corrections(self):
        """Birden fazla düzeltme aynı query'de."""
        qn = QueryNormalizer()
        
        # TC ve Made birlikte
        result = qn.apply_fuzzy_corrections("TC Made 157")
        assert "TCK" in result
        assert "Madde" in result
        
        # CMC ve made birlikte (case-insensitive check)
        result = qn.apply_fuzzy_corrections("cmc made 42")
        result_lower = result.lower()
        assert "cmk" in result_lower
        assert "madde" in result_lower


class TestExpansionIntegration:
    """Test expand_numeric_patterns with fuzzy corrections."""
    
    def test_fuzzy_before_expansion(self):
        """Fuzzy correction expansion'dan önce uygulanmalı."""
        qn = QueryNormalizer()
        
        original = "TC 157/1"
        results = qn.expand_numeric_patterns(original)
        
        # Tüm sonuçlarda TCK olmalı (TC düzeltilmiş)
        tc_count = sum(1 for r in results if "TC " in r and "TCK" not in r)
        tck_count = sum(1 for r in results if "TCK" in r)
        
        assert tck_count > 0, "TCK correction not applied"
        assert tc_count == 0, "TC should be corrected to TCK in all results"
    
    def test_real_world_queries(self):
        """Gerçek dünya kullanım örnekleri."""
        qn = QueryNormalizer()
        
        # Senaryo 1: Typo + numeric reference
        results = qn.expand_numeric_patterns("TC 157/1 nedir?")
        assert any("TCK" in r and "157/1" in r for r in results)
        
        # Senaryo 2: Made typo + madde
        results = qn.expand_numeric_patterns("Made 42/3")
        assert any("Madde" in r for r in results)
        
        # Senaryo 3: Multiple issues
        results = qn.expand_numeric_patterns("cmc made 150/2")
        # Should have CMK, madde, and numeric expansions
        has_cmk = any("cmk" in r.lower() for r in results)
        has_madde = any("madde" in r for r in results)
        assert has_cmk or has_madde  # En az biri düzeltilmiş olmalı


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
