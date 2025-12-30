# app/orchestrator_v42/plugins/safety_guard.py

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.safety")

async def check(message: str, username: str | None = None) -> Dict[str, Any]:
    """
    Güvenlik Kalkanı (Safety Guard) - Kural Tabanlı Motor.
    
    Gelen mesajı deterministik kurallara göre tarar ve risk analizi yapar.
    Hata durumunda "failsafe" (güvenli varsayım) modunda çalışır.
    
    Dönüş:
        {
            "input_safe": bool,
            "risk": "none|low|medium|high",
            "notes": str,
            "matched_rules": list[str]
        }
    """
    try:
        # Varsayılanlar
        input_safe = True
        risk = "none"
        notes = []
        matched_rules = []
        
        # 1. Boş İçerik Kontrolü
        if not message or not message.strip():
            matched_rules.append("bos_icerik")
            risk = "low"
            notes.append("Mesaj boş veya sadece boşluktan oluşuyor.")
            # Boş mesaj teknik olarak güvenlidir, işlem gerektirmez.
            return _build_result(True, "low", matched_rules, notes)

        # 2. Uzunluk Kontrolü (>8000 karakter)
        if len(message) > 8000:
            matched_rules.append("asiri_uzun")
            if risk in ["none", "low"]:
                risk = "medium"
            notes.append(f"Mesaj çok uzun ({len(message)} karakter).")

        # 3. PII Tespiti (Regex)
        # E-posta: \b[\w\.-]+@[\w\.-]+\.\w+\b
        if re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', message):
            matched_rules.append("olasi_pii_email")
            if risk in ["none", "low"]:
                risk = "medium"
            notes.append("Olası e-posta adresi tespit edildi.")
            
        # Telefon (Basit): \b\d{10,}\b
        if re.search(r'\b\d{10,}\b', message):
            matched_rules.append("olasi_pii_telefon")
            if risk in ["none", "low"]:
                risk = "medium"
            notes.append("Olası telefon numarası/uzun sayı dizisi tespit edildi.")

        # 4. Yasaklı İçerik (Keyword)
        # "bomba yapımı", "silah yapımı", "zehir hazırlama"
        forbidden_phrases = ["bomba yapımı", "silah yapımı", "zehir hazırlama"]
        message_lower = message.lower()
        
        found_forbidden = False
        for phrase in forbidden_phrases:
            if phrase in message_lower:
                matched_rules.append("yasakli_talep")
                risk = "high"
                input_safe = False
                notes.append(f"Yasaklı ifade tespit edildi: '{phrase}'")
                found_forbidden = True
                break # İlk yasaklı ifade yeterli
        
        # Sonuç Oluşturma
        final_note = " | ".join(notes) if notes else "Güvenli içerik."
        return _build_result(input_safe, risk, matched_rules, [final_note])

    except Exception as e:
        # Fail-safe: Hata olsa bile sistemi kilitleme, logla ve güvenli kabul et (veya riskli işaretle)
        # Prensip: "Fail open" (devam et) mi "Fail closed" (engelle) mi?
        # Şimdilik prodüksiyonu bozmamak için safe=True dönüyoruz ama logluyoruz.
        logger.error(f"Güvenlik modülü hatası: {e}")
        return _build_result(True, "low", ["hata_failsafe"], [f"Güvenlik kontrolü sırasında hata oluştu: {e}"])

def _build_result(safe: bool, risk: str, rules: List[str], notes_list: List[str]) -> Dict[str, Any]:
    return {
        "input_safe": safe,
        "risk": risk,
        "matched_rules": rules,
        "notes": " ".join(notes_list)
    }
