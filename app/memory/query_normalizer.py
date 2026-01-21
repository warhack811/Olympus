import re
import unicodedata
from typing import List, Set

class QueryNormalizer:
    """
    Kural tabanlı (hardcoded) yapılar yerine, her türlü dokümanda (Hukuk, Teknik, Tıp) 
    ortak olan karakter ve sayı kalıplarını standartlaştıran genel katman.
    """

    @staticmethod
    def normalize_turkish(text: str) -> str:
        """Türkçe karakterleri standart forma sokar."""
        if not text:
            return ""
        # Küçük harfe çevir ve normalize et
        text = text.lower()
        # unicode normalizasyonu (nfc)
        text = unicodedata.normalize('NFC', text)
        return text

    @staticmethod
    def apply_fuzzy_corrections(query: str) -> str:
        """
        Common typo'ları ve kısaltmaları düzelt.
        
        Examples:
            "TC 157" → "TCK 157"
            "CMC 150" → "CMK 150"
            "Made 42" → "Madde 42"
        
        Returns:
            Corrected query
        """
        if not query:
            return query
        
        # Kısaltma düzeltmeleri (word boundary ile)
        corrections = {
            r'\bTC\b': 'TCK',          # Türk Ceza Kanunu
            r'\bCMC\b': 'CMK',         # Ceza Muhakemesi Kanunu
            r'\bTMC\b': 'TMK',         # Türk Medeni Kanunu
            r'\bHMC\b': 'HMK',         # Hukuk Muhakemeleri Kanunu
            r'\bMade\b': 'Madde',      # Typo (başlık case)
            r'\bmade\b': 'madde',      # Typo (lowercase)
        }
        
        corrected = query
        for pattern, replacement in corrections.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected

    @staticmethod
    def expand_numeric_patterns(query: str) -> List[str]:
        """
        Sayısal referansları (157/1, 157.1, 157-1) birbirine dönüştürerek 
        arama kapsamını genişletir.
        """
        # ÖNCE fuzzy correction uygula
        query = QueryNormalizer.apply_fuzzy_corrections(query)
        
        # Sayı-slash-sayı kalıbını bul (Örn: 157/1)
        # Sorumlu karakterleri koru
        pattern = r"(\d+)[/.\-](\d+)"
        matches = re.finditer(pattern, query)
        
        candidates = [query]
        for match in matches:
            v1, v2 = match.groups()
            # Farklı yazım varyasyonlarını ekle
            candidates.append(f"{v1}/{v2}")
            candidates.append(f"{v1}.{v2}")
            candidates.append(f"{v1}-{v2}")
            candidates.append(f"{v1} {v2}")
            
        return list(set(candidates))

    @staticmethod
    def sanitize_for_fts(query: str) -> str:
        """SQLite FTS5 için güvenli ve temiz bir sorgu hazırlar."""
        # 1. Sayısal referanslardaki karakterleri geçici olarak koru (157/1 -> 157_S_1)
        query = re.sub(r"(\d+)/(\d+)", r"\1_S1_\2", query)
        query = re.sub(r"(\d+)\.(\d+)", r"\1_S2_\2", query)

        # 2. Tehlikeli karakterleri temizle
        query = re.sub(r'[,"\'()*:^?!\\+=<>]', " ", query)

        # 3. Geçici etiketleri geri çevir
        query = query.replace("_S1_", "/")
        query = query.replace("_S2_", ".")
        
        # 4. Çoklu boşlukları temizle
        query = re.sub(r"\s+", " ", query).strip()
        return query

    @staticmethod
    def get_semantic_focal_points(query: str) -> List[str]:
        """
        Sorgudaki 'odak noktası' olabilecek (Sayılar, Büyük Harfli Terimler) 
        kısımları ayıklayarak Reranker'a yardımcı olur.
        """
        focal_points = []
        # Sayısal referanslar
        focal_points.extend(re.findall(r"\d+[/.\-]\d+", query))
        # Tekil maddeler/numaralar
        focal_points.extend(re.findall(r"\d+", query))
        # 2+ karakterli büyük harfler (Terimler)
        focal_points.extend(re.findall(r"\b[A-ZÇĞİÖŞÜ]{2,}\b", query))
        
        return list(set(focal_points))

# Singleton instance
query_normalizer = QueryNormalizer()
