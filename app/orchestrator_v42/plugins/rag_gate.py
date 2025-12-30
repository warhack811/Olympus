# app/orchestrator_v42/plugins/rag_gate.py

import logging
from typing import Dict, Any

logger = logging.getLogger("orchestrator.rag_gate")

def decide(intent_report: Dict[str, Any], capability_report: Dict[str, Any], message: str) -> Dict[str, Any]:
    """
    RAG Akıllı Kapısı (Intelligent Gate).
    
    Hangi mesaja RAG (Doküman Arama) uygulanacağına deterministik olarak karar verir.
    3 Aşamalı Kontrol:
    1. Sinyal (Signal): Intent, Capability veya Anahtar Kelime var mı?
    2. Hızlı Kontrol (Quick Check): Mesaj çok kısa veya selamlaşma mı?
    3. Karar (Decision): Sinyal VAR ve Hızlı Kontrol GEÇTİ ise -> ON.
    
    Returns:
        RagGateReport (dict)
    """
    try:
        # Varsayılanlar
        decision = "off"
        signal_reasons = []
        quick_check = {"passed": False, "reason": "Baslamadi"}
        notes = []
        
        # Helper to safely get attribute or item
        def safe_get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # --- 1. SİNYAL KONTROLÜ ---
        
        # A. Intent Sinyali
        rag_dec = safe_get(intent_report, "rag_decision")
        if rag_dec == "on":
            signal_reasons.append("intent_rag_on")
            
        # B. Yetenek Sinyali
        caps = safe_get(capability_report, "required_capabilities", [])
        if "dokuman_arama" in caps or "arsiv_tarama" in caps:
            signal_reasons.append("capability_rag")
            
        # C. Anahtar Kelime Sinyali (Fallback)
        rag_keywords = ["doküman", "sözleşme", "pdf", "dosya", "rapor", "kaynak", "arşiv", "bilgi bankası"]
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in rag_keywords):
            signal_reasons.append("keyword_match")
            
        # --- 2. HIZLI KONTROL (QUICK CHECK) ---
        
        # A. Uzunluk Kontrolü
        if len(message) < 12: # Çok kısa mesajlar (Sinyal olsa bile KAPALI)
            quick_check = {"passed": False, "reason": "mesaj_cok_kisa"}
            notes.append("Mesaj RAG için çok kısa (<12 karakter).")
        
        # B. Selamlaşma Kontrolü (Sadece 'selam', 'merhaba' vb. içeren kısa mesajlar)
        elif len(message) < 20 and any(x in msg_lower for x in ["selam", "merhaba", "günaydın", "iyi günler"]):
             # Amaç RAG keywords içermiyorsa
             if not any(kw in msg_lower for kw in rag_keywords):
                quick_check = {"passed": False, "reason": "selamlasma_saptandi"}
                notes.append("Selamlaşma mesajı, RAG gereksiz.")
             else:
                quick_check = {"passed": True, "reason": "uygun"}
        else:
             quick_check = {"passed": True, "reason": "uygun"}
             
        # --- 3. KARAR (DECISION) ---
        
        if signal_reasons and quick_check["passed"]:
            decision = "on"
            notes.append("RAG sinyali doğrulandı.")
        else:
            decision = "off"
            if not signal_reasons:
                notes.append("RAG sinyali yok.")
            else:
                notes.append(f"Sinyal var ama hızlı kontrol geçilemedi ({quick_check['reason']}).")

        # Rapor Oluştur
        return {
            "decision": decision,
            "signal_reasons": signal_reasons,
            "quick_check": quick_check,
            "notes": " | ".join(notes)
        }

    except Exception as e:
        logger.error(f"RAG Gate error: {e}")
        # Fail-closed (Kapalı kalması daha güvenli)
        return {
            "decision": "off",
            "signal_reasons": ["error"],
            "quick_check": {"passed": False, "reason": "exception"},
            "notes": f"Hata oluştu: {e}"
        }
