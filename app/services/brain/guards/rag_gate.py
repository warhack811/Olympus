"""
Mami AI - Intelligent RAG Gate (Brain Edition)
-----------------------------------------------
Legacy Orchestrator v4.2 RAG Gate mantığının Brain Engine (v4.4) uyarlaması.
Gereksiz RAG (Hafıza Arama) çağrılarını engelleyerek maliyet ve hız tasarrufu sağlar.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RAGGate:
    """
    RAG Akıllı Kapısı - Mesajın içeriğine göre doküman araması gerekip gerekmediğine karar verir.
    """
    
    # RAG gerektiren anahtar kelimeler
    RAG_KEYWORDS = [
        "doküman", "sözleşme", "pdf", "dosya", "rapor", "kaynak", 
        "arşiv", "bilgi bankası", "hafıza", "hatırla", "geçmiş",
        "madde", "kanun", "yasa", "nedir", "ne der", "nasıl"
    ]
    
    # Selamlaşma kelimeleri (Filtreleme için)
    GREETING_KEYWORDS = ["selam", "merhaba", "günaydın", "iyi günler", "hey", "nasılsın"]

    def decide(self, message: str, intent: str = "general") -> Dict[str, Any]:
        """
        RAG araması yapılıp yapılmayacağına karar verir.
        
        Returns:
            {
                "decision": "on" | "off",
                "reason": str,
                "confidence": float
            }
        """
        msg_lower = message.lower().strip()
        
        # 1. Uzunluk Kontrolü (Çok kısa mesajlar için RAG gereksiz)
        if len(msg_lower) < 5:
            return {
                "decision": "off",
                "reason": "mesaj_cok_kisa",
                "confidence": 1.0
            }

        # 2. Selamlaşma Kontrolü
        # Eğer mesaj sadece selamlaşma içeriyorsa ve RAG keyword yoksa kapat
        is_greeting = any(kw in msg_lower for kw in self.GREETING_KEYWORDS)
        has_rag_keyword = any(kw in msg_lower for kw in self.RAG_KEYWORDS)
        
        if is_greeting and not has_rag_keyword and len(msg_lower) < 20:
            return {
                "decision": "off",
                "reason": "selamlasma_saptandi",
                "confidence": 0.9
            }

        # 3. Intent Bazlı Karar
        # Eğer niyet 'search' veya 'image' değilse ve RAG keyword varsa aç
        if intent == "search":
             # Search zaten internete bakacağı için iç hafıza (RAG) opsiyonel olabilir
             # Ama niyet 'search' ise genellikle güncel bilgi aranıyordur.
             pass

        if has_rag_keyword:
            return {
                "decision": "on",
                "reason": "keyword_match",
                "confidence": 0.95
            }

        # 4. Varsayılan Karar (Complexity yüksekse veya orta uzunluktaysa açık kalsın)
        if len(msg_lower) > 10:
            return {
                "decision": "on",
                "reason": "complex_query_candidate",
                "confidence": 0.7
            }

        return {
            "decision": "off",
            "reason": "default_low_signal",
            "confidence": 0.6
        }

# Singleton instance
rag_gate = RAGGate()
