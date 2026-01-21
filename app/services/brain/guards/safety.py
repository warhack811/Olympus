"""
Mami AI - Safety Gate (Atlas Sovereign Edition)
-----------------------------------------------
Sisteme giren ve çıkan her veriyi zararlı içeriklere karşı denetler.

Temel Sorumluluklar:
1. PII Maskeleme: E-posta, telefon, TCKN gibi kişisel verileri maskeleme
2. Enjeksiyon Engelleme: Prompt injection tespiti
3. AI Guard Entegrasyonu: LlamaGuard kontrolü
4. Beyaz Liste: Zararsız ama riskli görünen kelimeleri hariç tutma
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Tuple

from app.core.telemetry.service import telemetry, EventType
from app.config import get_settings
from app.core.constants import MODEL_GOVERNANCE
from app.core.llm.generator import LLMGenerator, LLMRequest

logger = logging.getLogger(__name__)


@dataclass
class SafetyIssue:
    """Tespit edilen bir güvenlik ihlalini tanımlayan sınıf."""
    type: str      # 'PII', 'ENJEKSİYON', 'AI_ENGELİ'
    details: str   # Teknik detaylar
    severity: str  # 'LOW', 'MEDIUM', 'HIGH'


class SafetyGate:
    """Giriş ve çıkış trafiğini filtreleyen güvenlik kapısı."""
    
    # PII Regex Kalıpları
    PII_PATTERNS = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE_TR": r'\b(?:\+90|0)?\s*5[0-9]{2}\s*[0-9]{3}\s*[0-9]{2}\s*[0-9]{2}\b',
        "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "TCKN": r'\b[1-9]{1}[0-9]{10}\b',
        "IBAN_TR": r'\bTR[0-9]{2}\s*(?:[0-9]{4}\s*){5}[0-9]{2}\b',
    }
    
    # Enjeksiyon Anahtar Kelimeleri
    INJECTION_KEYWORDS = [
        r"ignore previous instructions",
        r"önceki talimatları unut",
        r"give me the system prompt",
        r"sistem talimatlarını ver",
        r"dan mode",
        r"dev mode",
        r"jailbreak",
        r"bypass safety",
        r"<script>",
        r"sql injection"
    ]
    
    # Beyaz Liste
    SAFE_KEYWORDS = [
        "tasarımsal", "limit", "mesaj", "istek", "nasıl", "nedir",
        "analiz", "anlat", "görsel", "resim", "ücret", "fiyat"
    ]
    
    def __init__(self):
        self.injection_patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_KEYWORDS]
        self.pii_patterns = {k: re.compile(v) for k, v in self.PII_PATTERNS.items()}
    
    async def check_input_safety(self, text: str) -> Tuple[bool, str, List[SafetyIssue], str]:
        """
        Kullanıcı girişini güvenlik sorunları için kontrol et.
        
        Returns:
            (güvenli_mi, temizlenmiş_metin, sorunlar_listesi, kullanılan_model)
        """
        issues = []
        sanitized_text = text
        used_model = "regex-rule-based"
        
        # 1. Enjeksiyon Kontrolü
        for pattern in self.injection_patterns:
            if pattern.search(text):
                issues.append(SafetyIssue(
                    type="ENJEKSİYON",
                    details=f"Zararlı kalıp tespit edildi: {pattern.pattern}",
                    severity="HIGH"
                ))
                
                # Telemetry
                telemetry.emit(
                    EventType.SECURITY,
                    {"type": "injection_blocked", "pattern": pattern.pattern[:30]},
                    component="safety_gate"
                )
                
                return False, text, issues, used_model
        
        # 2. PII Kontrolü
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(sanitized_text):
                issues.append(SafetyIssue(
                    type="PII",
                    details=f"{pii_type} verisi tespit edildi",
                    severity="MEDIUM"
                ))
                sanitized_text = pattern.sub(f"[{pii_type}]", sanitized_text)
                
                telemetry.emit(
                    EventType.SECURITY,
                    {"type": "pii_masked", "pii_type": pii_type},
                    component="safety_gate"
                )
        
        # 3. Beyaz Liste Kontrolü
        lowered_text = text.lower()
        if any(word in lowered_text for word in self.SAFE_KEYWORDS):
            if not issues:
                return True, sanitized_text, [
                    SafetyIssue(type="WHITELIST", details="Safe keywords detected", severity="LOW")
                ], "whitelist-bypass"
        
        # 4. LLM Guard Kontrolü (MODEL_GOVERNANCE['safety'])
        settings = get_settings()
        
        if not hasattr(self, '_llm_generator') or not self._llm_generator:
            self._llm_generator = LLMGenerator()
            await self._auto_register_providers()

        request = LLMRequest(
            role="safety",
            prompt=text,
            temperature=0.0,
            max_tokens=10
        )
        
        try:
            result = await self._llm_generator.generate(request)
            if not result.ok:
                logger.warning(f"[SafetyGate] LLM guard check failed: {result.text}")
                return True, sanitized_text, issues, used_model # Safety failure: fail-open but log

            used_model = result.model
            res_lower = (result.text or "").lower().strip()
            if any(x in res_lower for x in ["jailbreak", "injection", "unsafe"]):
                issues.append(SafetyIssue(
                    type="PROMPT_INJECTION",
                    details=f"LLM Guard tespiti: {result.text}",
                    severity="HIGH"
                ))
                
                telemetry.emit(
                    EventType.SECURITY,
                    {"type": "prompt_guard_blocked", "model": used_model, "result": result.text},
                    component="safety_gate"
                )
                
                return False, sanitized_text, issues, used_model
            else:
                telemetry.emit(
                    EventType.SECURITY,
                    {"type": "prompt_guard_safe", "model": used_model},
                    component="safety_gate"
                )
                return True, sanitized_text, issues, used_model
        except Exception as e:
            logger.warning(f"[SafetyGate] LLM guard check error: {e}")
            return True, sanitized_text, issues, used_model # Fallback to safe
    
    async def check_output_safety(self, text: str) -> Tuple[bool, str, List[SafetyIssue]]:
        """Çıkış metnini güvenlik kontrolünden geçir."""
        # PII maskeleme çıkışta da uygula
        sanitized = text
        issues = []
        
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(sanitized):
                sanitized = pattern.sub(f"[{pii_type}]", sanitized)
                issues.append(SafetyIssue(
                    type="PII_OUTPUT",
                    details=f"Output {pii_type} masked",
                    severity="MEDIUM"
                ))
        
        return True, sanitized, issues

    async def _auto_register_providers(self) -> None:
        """Auto-register providers based on ModelGovernance requirements."""
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        safety_chain = governance.get_model_chain("safety")
        providers_needed = set()
        for model_id in safety_chain:
            provider_name = governance.detect_provider(model_id)
            providers_needed.add(provider_name)
        
        provider_adapters = {
            "groq": groq_adapter,
            "gemini": gemini_adapter
        }
        
        for provider in providers_needed:
            if provider in provider_adapters and provider not in self._llm_generator.providers:
                self._llm_generator.register_provider(provider, provider_adapters[provider])
                logger.info(f"[SafetyGate] Auto-registered provider: {provider}")


# Singleton
safety_gate = SafetyGate()
