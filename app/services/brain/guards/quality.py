"""
Mami AI - Quality Gate (Atlas Sovereign Edition)
------------------------------------------------
Üretilen yanıtların kalite kriterlerine uygunluğunu denetler.

Temel Sorumluluklar:
1. Dil Uyumluluğu: Türkçe karakter kuralları
2. Format Denetimi: Kod bloklarının varlığı
3. Uzunluk Kontrolü: Çok kısa yanıtlar
4. Tekrar Tespiti: Döngü (looping) kontrolü
5. Markdown Doğrulaması: Kapanmamış bloklar
6. Red Tespiti: Standart AI kaçamak yanıtları
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Tuple
from collections import Counter

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Tespit edilen bir kalite sorununu tanımlayan sınıf."""
    check: str     # 'DİL', 'FORMAT', 'UZUNLUK', 'TEKRAR' vb.
    details: str   # Teknik detay
    severity: str  # 'WARNING' veya 'BLOCKER'


class QualityGate:
    """Üretilen yanıtların kalitesini denetleyen kapı."""
    
    # Türkçe karakterler
    TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
    
    # Sık karıştırılan İngilizce kelimeler
    COMMON_ENGLISH_WORDS = [
        "message", "actually", "basically", "literally", "really",
        "because", "about", "think", "maybe", "something", "anything",
        "please", "sorry", "thank", "thanks", "welcome", "hello", "bye",
        "probably", "definitely", "obviously", "honestly", "seriously",
        "anyway", "however", "therefore", "although", "though",
        "amazing", "awesome", "great", "good", "nice", "cool", "okay",
        "understand", "know", "feel", "want", "need", "like", "love",
        "just", "only", "also", "too", "very", "much", "more", "less",
        "the", "and", "for", "with", "from", "that", "this", "which",
        "what", "where", "when", "why", "who", "how",
        "yes", "yeah", "yep", "nope", "sure",
    ]
    
    # Red ifadeleri
    REFUSAL_PHRASES = [
        "as an ai language model",
        "i cannot",
        "yapay zeka modeli olarak",
        "bunu yapamam"
    ]
    
    # Argo / Samimi kelimeler (Professional tonda yasaklı)
    SLANG_WORDS = ["lan", "yav", "moruk", "kanka", "hacı", "aga", "bro", "naber"]
    
    def check_quality(self, text: str, intent: str = "chat", persona: str = "friendly") -> Tuple[bool, List[QualityIssue]]:
        """
        Nihai yanıtı kalite süzgecinden geçirir.
        
        Returns:
            (geçti_mi, sorunlar_listesi)
        """
        issues = []
        is_passed = True
        
        # 1. Uzunluk Kontrolü
        if len(text.strip()) < 10:
            issues.append(QualityIssue(
                check="LENGTH",
                details=f"Yanıt çok kısa ({len(text)} karakter)",
                severity="WARNING"
            ))
        
        # 2. Format Kontrolü (Kodlama)
        if intent in ["coding", "debug", "refactor"]:
            if "```" not in text:
                issues.append(QualityIssue(
                    check="FORMAT",
                    details="Kodlama niyeti ama kod bloğu yok",
                    severity="WARNING"
                ))
        
        # 3. Dil Kontrolü (Türkçe karakter)
        if intent not in ["coding", "math"]:
            has_tr_char = any(c in text for c in self.TR_CHARS)
            if not has_tr_char and len(text) > 50:
                issues.append(QualityIssue(
                    check="LANGUAGE",
                    details="Türkçe karakter bulunamadı",
                    severity="WARNING"
                ))
        
        # 4. Ret Tespiti
        text_lower = text.lower()
        if any(p in text_lower for p in self.REFUSAL_PHRASES):
            issues.append(QualityIssue(
                check="REFUSAL",
                details="Model cevap vermeyi reddetti",
                severity="WARNING"
            ))
        
        # 5. Tekrar/Döngü Kontrolü
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
        if lines:
            most_common = Counter(lines).most_common(1)
            if most_common and most_common[0][1] >= 3:
                issues.append(QualityIssue(
                    check="LOOP",
                    details=f"Tekrar tespit: '{most_common[0][0][:20]}...'",
                    severity="BLOCKER"
                ))
        
        # 6. Markdown Sözdizimi
        if text.count("```") % 2 != 0:
            issues.append(QualityIssue(
                check="MARKDOWN",
                details="Kapanmamış kod bloğu",
                severity="WARNING"
            ))
        
        # 7. İngilizce Kelime Tespiti
        if intent not in ["coding", "debug", "refactor", "math"]:
            english_words = self._check_english_words(text)
            if english_words:
                issues.append(QualityIssue(
                    check="LANGUAGE_PURITY",
                    details=f"İngilizce kelimeler: {', '.join(english_words[:5])}",
                    severity="WARNING"
                ))

        # 8. Stil ve Ton Tutarlılığı (Style Guard - ATLAS Port)
        if persona in ["professional", "expert", "teacher"]:
            found_slang = [w for w in self.SLANG_WORDS if w in text_lower]
            if found_slang:
                issues.append(QualityIssue(
                    check="STYLE_CONSISTENCY",
                    details=f"Profesyonel tonda uygunsuz kelimeler: {', '.join(found_slang)}",
                    severity="WARNING"
                ))
        
        # BLOCKER varsa geçişi engelle
        if any(i.severity == "BLOCKER" for i in issues):
            is_passed = False
            telemetry.emit(
                EventType.SYSTEM,
                {"type": "quality_blocked", "issues": len(issues)},
                component="quality_gate"
            )
        
        return is_passed, issues
    
    def _check_english_words(self, text: str) -> List[str]:
        """Metinde sık karıştırılan İngilizce kelimeleri tespit et."""
        # Kod bloklarını çıkar
        clean_text = re.sub(r'```[\s\S]*?```', '', text)
        clean_text = re.sub(r'`[^`]+`', '', clean_text)
        
        found_english = []
        words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text.lower())
        
        for word in words:
            if word in self.COMMON_ENGLISH_WORDS:
                if word not in found_english:
                    found_english.append(word)
        
        return found_english
    
    def fix_unclosed_blocks(self, text: str) -> str:
        """Kapanmamış markdown bloklarını onar."""
        if text.count("```") % 2 != 0:
            text = text + "\n```"
        return text


# Singleton
quality_gate = QualityGate()
