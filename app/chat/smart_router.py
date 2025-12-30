"""
Mami AI - Akıllı Model Yönlendirici
===================================

Bu modül, kullanıcı mesajlarını en uygun modele yönlendirir.

Routing Öncelik Sırası:
    1. Tool Intent: IMAGE/INTERNET isteği → İlgili tool
    2. Explicit Local: requested_model="bela" veya force_local → LOCAL
    3. Persona Requirement: requires_uncensored → LOCAL
    4. Content Heuristic: Roleplay/erotik içerik → LOCAL
    5. Default: → GROQ

Kurallar:
    - LOCAL model çıktısı tool çağrısı yapamaz
    - censorship_level=2 ise otomatik local routing kapalı
    - censorship_level=2 ise NSFW image reddedilir

Kullanım:
    from app.chat.smart_router import SmartRouter, RoutingDecision

    router = SmartRouter()
    decision = router.route(
        message="Bana bir resim çiz",
        user=user_obj,
        persona_name="standard",
        requested_model=None,
        force_local=False,
    )

    print(decision.target)  # "IMAGE"
    print(decision.reason)  # "tool_intent_image"
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.models import User

logger = logging.getLogger(__name__)

# --- LIVE TRACE ---
try:
    from app.core.live_tracer import LiveTracer
except ImportError:
    # Fallback stub
    class LiveTracer:
        @staticmethod
        def routing_decision(*args, **kwargs): pass
        @staticmethod
        def model_select(*args, **kwargs): pass
        @staticmethod
        def request_in(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
# ------------------


# =============================================================================
# ENUM & DATA CLASSES
# =============================================================================


class RoutingTarget(str, Enum):
    """Yönlendirme hedefleri."""

    GROQ = "groq"
    LOCAL = "local"
    IMAGE = "image"
    INTERNET = "internet"


class ToolIntent(str, Enum):
    """Tool intent türleri."""

    NONE = "none"
    IMAGE = "image"
    INTERNET = "internet"


@dataclass
class RoutingDecision:
    """
    Routing kararı sonucu.

    Attributes:
        target: Hedef model/tool
        tool_intent: Tool isteği (none, image, internet)
        reason_codes: Karar nedenleri
        censorship_level: Kullanıcı sansür seviyesi
        blocked: İstek reddedildi mi
        block_reason: Reddetme nedeni
        persona_name: Aktif persona adı
        persona_requires_uncensored: Persona sansürsüz model gerektiriyor mu
        final_model: Final yanıtı yazacak model (groq veya local)
        metadata: Ek bilgiler
    """

    target: RoutingTarget
    tool_intent: ToolIntent = ToolIntent.NONE
    reason_codes: list[str] = field(default_factory=list)
    censorship_level: int = 1
    blocked: bool = False
    block_reason: str | None = None
    persona_name: str = "standard"
    persona_requires_uncensored: bool = False
    final_model: str = "groq"  # "groq" veya "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Dict'e dönüştür (logging için)."""
        return {
            "target": self.target.value,
            "tool_intent": self.tool_intent.value,
            "reason_codes": self.reason_codes,
            "censorship_level": self.censorship_level,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "persona_name": self.persona_name,
            "final_model": self.final_model,
        }


# =============================================================================
# CONTENT PATTERNS
# =============================================================================

# Tool intent patterns
IMAGE_PATTERNS = [
    r"(?i)\b(ciz|çiz|resim|gorsel|görsel|draw|paint|illustrate)\b",
    r"(?i)\b(fotograf|fotoğraf|foto|image|picture)\s*(yap|olustur|oluştur|uret|üret)",
    r"(?i)\b(gorsel|görsel)\s*(olustur|oluştur|uret|üret)\b",
    r"^!{1,2}",  # ! veya !! ile başlayan mesajlar = raw image prompt
]

INTERNET_PATTERNS = [
    r"(?i)\b(dolar|euro|sterlin|kur|borsa)\s*(kac|kaç|ne\s*kadar|fiyat)",
    r"(?i)\b(hava\s*durumu|bugun\s*hava|bugün\s*hava|yarin\s*hava|yarın\s*hava)\b",
    r"(?i)\bhava\b.*(bugun|bugün|nasil|nasıl)",
    r"(?i)\b(haber|guncel|güncel|son\s*dakika)\b",
    r"(?i)\b(ara|arat|google|search|internette)\b",
    r"(?i)\b(bitcoin|btc|eth|kripto)\s*(kac|kaç|fiyat)",
]

# Local routing content patterns (explicit)
LOCAL_EXPLICIT_PATTERNS = [
    r"(?i)\b(bela|sansursuz|sansürsüz|filtresiz|uncensored)\b",
    r"(?i)\b(yerel\s*model|local\s*model)\b",
]

# Local routing content patterns (content-based)
LOCAL_CONTENT_PATTERNS = [
    r"(?i)\b(roleplay|rol\s*yap|canlandir|karakter)\b",
    r"(?i)\b(senaryo\s*yaz|hikaye\s*yaz)\b.*\b(yetiskin|erotik|18\+)\b",
    r"(?i)\b(erotik|seksuel|cinsel)\b",
]

# NSFW image patterns
NSFW_IMAGE_PATTERNS = [
    r"(?i)\b(ciplak|çıplak|nude|naked|nsfw)\b",
    r"(?i)\b(seksi|sexy|erotik|erotic)\b.*\b(ciz|çiz|resim|gorsel|görsel)\b",
    r"(?i)\b(yetiskin|yetişkin|adult|18\+)\b.*\b(ciz|çiz|resim|gorsel|görsel)\b",
]


# =============================================================================
# ORCHESTRATOR v5.8 - MODEL CATALOG & INTENT PATTERNS
# =============================================================================

# Model Catalog (Consensus v5.2 - Blueprint compliant)
# strengths: 0-3 score, quality/latency/cost: literal tier
MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "llama-3.1-8b-instant": {
        "strengths": {"coding": 1, "analysis": 1, "creative": 2, "social_chat": 1, "tool_planning": 1, "tr_natural": 2},
        "quality_tier": "med",
        "latency_tier": "fast",
        "cost_tier": "low",
        "can_judge": False,
        "can_rewrite": False,
    },
    "qwen3-32b": {
        "strengths": {"coding": 2, "analysis": 3, "creative": 2, "social_chat": 2, "tool_planning": 3, "tr_natural": 3},
        "quality_tier": "high",
        "latency_tier": "med",
        "cost_tier": "med",
        "can_judge": True,
        "can_rewrite": True,
    },
    "kimi-k2": {
        # social_chat = TR slang / sokak ağzı / doğal samimiyet (VIP Param)
        "strengths": {"coding": 2, "analysis": 2, "creative": 3, "social_chat": 3, "tool_planning": 2, "tr_natural": 3},
        "quality_tier": "high",
        "latency_tier": "med",
        "cost_tier": "med",
        "can_judge": False,
        "can_rewrite": True,
    },
    "gpt-oss-120b": {
        "strengths": {"coding": 3, "analysis": 3, "creative": 2, "social_chat": 1, "tool_planning": 3, "tr_natural": 2},
        "quality_tier": "high",
        "latency_tier": "slow",
        "cost_tier": "high",
        "can_judge": True,
        "can_rewrite": False,
    },
    "llama-70b": {
        "strengths": {"coding": 2, "analysis": 3, "creative": 2, "social_chat": 2, "tool_planning": 2, "tr_natural": 2},
        "quality_tier": "high",
        "latency_tier": "slow",
        "cost_tier": "high",
        "can_judge": True,
        "can_rewrite": False,
    },
}

# Intent types for orchestrator v5.8
INTENT_TYPES = ["code", "analysis", "creative", "social_chat", "research", "tool_use", "rag_query", "general"]

# Domain/intent regex patterns for fallback classification
INTENT_PATTERNS: dict[str, re.Pattern] = {
    "code": re.compile(
        r"(?i)\b(kod|code|python|javascript|script|fonksiyon|function|debug|hata|error|program|algoritma|yaz|yazdir|döngü|dongu|class|sinif|sınıf)\b"
    ),
    "social_chat": re.compile(
        r"(?i)^(merhaba|selam|naber|nasilsin|nasılsın|hey|gunaydin|günaydın|iyi\s*geceler|iyi\s*aksamlar|iyi\s*akshamlar|hos\s*geldin|hoş\s*geldin)\b"
    ),
    "research": re.compile(
        r"(?i)\b(arastir|araştır|incele|analiz\s*et|karsilastir|karşılaştır|ne\s*fark|arasindaki|arasındaki|ozet|özet)\b"
    ),
    "rag_query": re.compile(r"(?i)\b(TCK|madde|kanun|yonetmelik|yönetmelik|belge|dosya|pdf|document|mevzuat|hukuk)\b"),
    "creative": re.compile(r"(?i)\b(hikaye|siir|şiir|roman|senaryo|yaratici|yaratıcı|hayal|fantezi)\b"),
}

# Intent → Primary model mapping (capability-based selection)
INTENT_TO_MODEL: dict[str, str] = {
    "code": "gpt-oss-120b",
    "analysis": "qwen3-32b",
    "creative": "kimi-k2",
    "social_chat": "kimi-k2",
    "research": "qwen3-32b",
    "tool_use": "qwen3-32b",
    "rag_query": "qwen3-32b",
    "general": "qwen3-32b",
}

# Complexity detection patterns
COMPLEXITY_PATTERNS = {
    "high": re.compile(
        r"(?i)\b(karmasik|karmaşık|complex|detayli|detaylı|kapsamli|kapsamlı|optimizasyon|refactor|mimari|architecture)\b"
    ),
    "simple": re.compile(r"(?i)^(evet|hayir|hayır|tamam|ok|tesekkur|teşekkür|peki|anladim|anladım)$"),
}


# =============================================================================
# SMART ROUTER
# =============================================================================


class SmartRouter:
    """
    Akıllı model yönlendirici.

    Kullanıcı mesajını analiz ederek en uygun modele yönlendirir.
    """

    def __init__(self):
        """Router'ı başlatır."""
        # Compiled regex patterns for performance
        self._image_patterns = [re.compile(p) for p in IMAGE_PATTERNS]
        self._internet_patterns = [re.compile(p) for p in INTERNET_PATTERNS]
        self._local_explicit = [re.compile(p) for p in LOCAL_EXPLICIT_PATTERNS]
        self._local_content = [re.compile(p) for p in LOCAL_CONTENT_PATTERNS]
        self._nsfw_image = [re.compile(p) for p in NSFW_IMAGE_PATTERNS]

    # -------------------------------------------------------------------------
    # LAZY IMPORTS
    # -------------------------------------------------------------------------

    def _get_permission_helpers(self):
        """Permission helper'ları lazy import."""
        from app.auth.permissions import (
            can_auto_route_to_local,
            can_generate_nsfw_image,
            get_censorship_level,
            is_censorship_strict,
            user_can_use_image,
            user_can_use_internet,
            user_can_use_local,
        )

        return {
            "user_can_use_local": user_can_use_local,
            "user_can_use_internet": user_can_use_internet,
            "user_can_use_image": user_can_use_image,
            "get_censorship_level": get_censorship_level,
            "can_auto_route_to_local": can_auto_route_to_local,
            "can_generate_nsfw_image": can_generate_nsfw_image,
            "is_censorship_strict": is_censorship_strict,
        }

    def _get_config_service(self):
        """Config service lazy import."""
        try:
            from app.core.dynamic_config import config_service

            return config_service
        except ImportError:
            return None

    # -------------------------------------------------------------------------
    # PATTERN MATCHING
    # -------------------------------------------------------------------------

    def _matches_any(self, text: str, patterns: list[re.Pattern]) -> bool:
        """Herhangi bir pattern eşleşiyor mu?"""
        for pattern in patterns:
            if pattern.search(text):
                return True
        return False

    def _detect_tool_intent(self, message: str) -> ToolIntent:
        """
        Mesajdaki tool intent'i algılar.

        Args:
            message: Kullanıcı mesajı

        Returns:
            ToolIntent: Algılanan intent
        """
        # 1. Image Intent Check
        if self._matches_any(message, self._image_patterns):
            # EXCEPTION: Technical Diagrams/Charts should NOT go to Image Generator
            # unless explicitly asking for "resim" (picture) specifically?

            # Diagram keywords (suffix friendly for Turkish)
            diagram_keywords = [
                r"\b(diyagram|şema|sema|tablo|grafik|chart|diagram|flowchart|algoritma|mermaid)\w*",
                r"\b(akış)\s*(şema|sema)\w*",
                r"\b(kavram)\s*(harita)\w*",
            ]

            # Check for diagram intent
            is_technical_diagram = False
            for p in diagram_keywords:
                if re.search(p, message, re.IGNORECASE):
                    is_technical_diagram = True
                    break

            # BUT: If user explicitly asks for "photorealistic", "gerçekçi", "fotoğraf", "resim"
            # AND "diagram", maybe they want a picture OF a diagram?
            # Generally, if "mermaid" or "akış şeması" is present, we prefer Text.

            if is_technical_diagram:
                # One last check: Does user emphasize IMAGE generation heavily?
                # e.g. "bana akış şemasının fotoğrafını oluştur" -> Image?
                # For now, safe bet is: mixed intent -> Text (because LLM can explain it can't gen header image)
                return ToolIntent.NONE

            return ToolIntent.IMAGE

        if self._matches_any(message, self._internet_patterns):
            return ToolIntent.INTERNET

        return ToolIntent.NONE

    def _detect_local_explicit(self, message: str) -> bool:
        """Explicit local model isteği var mı?"""
        return self._matches_any(message, self._local_explicit)

    def _detect_local_content(self, message: str) -> bool:
        """İçerik bazlı local routing gerekiyor mu?"""
        return self._matches_any(message, self._local_content)

    def _detect_nsfw_image(self, message: str) -> bool:
        """NSFW görsel isteği var mı?"""
        return self._matches_any(message, self._nsfw_image)

    # -------------------------------------------------------------------------
    # PERSONA CHECK
    # -------------------------------------------------------------------------

    def _persona_requires_local(self, persona_name: str | None) -> bool:
        """
        Persona local model gerektiriyor mu?

        Args:
            persona_name: Aktif persona adı

        Returns:
            bool: Local gerekli mi
        """
        if not persona_name:
            return False

        config_service = self._get_config_service()
        if not config_service:
            return False

        try:
            persona = config_service.get_persona(persona_name)
            if persona:
                return persona.get("requires_uncensored", False)
        except Exception as e:
            logger.warning(f"[ROUTER] Persona okuma hatası: {e}")

        return False

    # -------------------------------------------------------------------------
    # ORCHESTRATOR v5.8 - INTENT DETECTION & METADATA
    # -------------------------------------------------------------------------

    def _detect_intent_regex(self, message: str) -> dict[str, Any]:
        """
        Regex-based intent classification (Phase 1 fallback).

        Args:
            message: Kullanıcı mesajı

        Returns:
            Dict with intent, confidence, and signals
        """
        detected_intent = "general"
        confidence = 0.3  # Default low confidence for general
        signals: dict[str, bool] = {
            "rag_needed": False,
            "tool_needed": False,
            "tr_slang_hint": False,
            "exact_match_hint": False,
        }

        # Check patterns in priority order
        for intent_type, pattern in INTENT_PATTERNS.items():
            if pattern.search(message):
                detected_intent = intent_type
                confidence = 0.6  # Regex match = medium confidence
                break

        # RAG signals
        if detected_intent == "rag_query":
            signals["rag_needed"] = True
            signals["exact_match_hint"] = True  # TCK, madde etc. need exact match

        # Tool signals (internet search)
        if self._matches_any(message, self._internet_patterns):
            signals["tool_needed"] = True

        # TR slang hint for social chat
        if detected_intent == "social_chat":
            signals["tr_slang_hint"] = True

        return {
            "intent": detected_intent,
            "confidence": confidence,
            "signals": signals,
        }

    def _detect_complexity(self, message: str) -> str:
        """
        Detect message complexity level.

        Returns:
            "simple", "medium", or "high"
        """
        if COMPLEXITY_PATTERNS["simple"].match(message):
            return "simple"
        if COMPLEXITY_PATTERNS["high"].search(message):
            return "high"

        # Length-based heuristic
        word_count = len(message.split())
        if word_count > 50:
            return "high"
        elif word_count < 10:
            return "simple"

        return "medium"

    def _select_model_for_intent(self, intent: str) -> str:
        """
        Select best model for given intent using MODEL_CATALOG.

        Args:
            intent: Detected intent type

        Returns:
            Model name from catalog
        """
        return INTENT_TO_MODEL.get(intent, "qwen3-32b")

    def _build_orchestrator_metadata(
        self,
        message: str,
        intent_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build orchestrator v5.8 metadata structure.

        Args:
            message: Original user message
            intent_result: Result from _detect_intent_regex

        Returns:
            Orchestrator metadata dict for RoutingDecision.metadata
        """
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        signals = intent_result["signals"]

        selected_model = self._select_model_for_intent(intent)
        complexity = self._detect_complexity(message)

        # Determine required tools
        requires_tools: list[str] = []
        if signals.get("tool_needed"):
            requires_tools.append("web_search")
        if signals.get("rag_needed"):
            requires_tools.append("rag_search")

        # Required capabilities based on intent
        capability_map = {
            "code": ["coding", "high_precision"],
            "analysis": ["analysis", "reasoning"],
            "creative": ["creative", "tr_natural"],
            "social_chat": ["social_chat", "tr_natural"],
            "research": ["analysis", "tool_planning"],
            "rag_query": ["analysis", "tool_planning"],
            "general": ["analysis"],
        }
        required_capabilities = capability_map.get(intent, ["analysis"])

        # Build tasks array (single task for Phase 1)
        tasks = [
            {
                "id": "t1",
                "type": intent,
                "depends_on": [],
                "required_capabilities": required_capabilities,
                "requires_tools": requires_tools,  # List[str] per user patch
                "priority": 1,
            }
        ]

        return {
            "version": "v5.8",
            "tasks": tasks,
            "selected_model": selected_model,
            "complexity": complexity,
            "domain": intent,
            "confidence": confidence,
            "signals": signals,
        }

    async def _detect_intent_llm(
        self,
        message: str,
        user_ctx: dict[str, Any] | None = None,
    ) -> tuple:
        """
        LLM-based intent classification (Phase 2 - not called from route()).

        Args:
            message: User message
            user_ctx: Optional user context

        Returns:
            Tuple of (intent_result, error_code)
            - On success: (intent_dict, None)
            - On timeout: (None, "INTENT_LLM_TIMEOUT")
            - On error: (None, "INTENT_LLM_ERROR")

        Note:
            This method is async and will be integrated in Phase 2
            when the async pipeline is implemented. For Phase 1,
            route() uses _detect_intent_regex() only.
        """
        import asyncio

        # Get timeout from config (default 800ms)
        config_service = self._get_config_service()
        timeout_ms = 800
        if config_service:
            timeout_ms = config_service.get("orchestrator.intent.timeout_ms", 800)

        timeout_ms / 1000.0

        try:
            # TODO Phase 2: Implement actual LLM call with Scout model
            # For now, this is a stub that simulates the interface
            await asyncio.sleep(0.01)  # Simulate minimal async work

            # Stub: Fall back to regex for now
            intent_result = self._detect_intent_regex(message)
            return (intent_result, None)

        except TimeoutError:
            return (None, "INTENT_LLM_TIMEOUT")
        except Exception as e:
            logger.warning(f"[ROUTER] Intent LLM error: {e}")
            return (None, "INTENT_LLM_ERROR")

    # -------------------------------------------------------------------------
    # ANA ROUTING LOGIC
    # -------------------------------------------------------------------------

    def route(
        self,
        message: str,
        user: Optional["User"] = None,
        persona_name: str | None = None,
        requested_model: str | None = None,
        force_local: bool = False,
        semantic: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        """
        Mesajı en uygun modele yönlendirir.

        Öncelik Sırası:
            1. Tool Intent (IMAGE/INTERNET)
            2. Explicit Local (requested_model="bela" veya force_local)
            3. Persona Requirement (requires_uncensored)
            4. Content Heuristic (roleplay/erotik)
            5. Default (GROQ)

        Args:
            message: Kullanıcı mesajı
            user: User nesnesi
            persona_name: Aktif persona adı
            requested_model: İstenen model ("groq" veya "bela")
            force_local: Zorla local model kullan
            semantic: Semantic analiz sonucu (opsiyonel)

        Returns:
            RoutingDecision: Routing kararı
        """
        helpers = self._get_permission_helpers()
        reason_codes: list[str] = []

        # Kullanıcı izinlerini al
        can_use_local = helpers["user_can_use_local"](user)
        can_use_internet = helpers["user_can_use_internet"](user)
        can_use_image = helpers["user_can_use_image"](user)
        censorship_level = helpers["get_censorship_level"](user)
        can_auto_local = helpers["can_auto_route_to_local"](user)
        can_nsfw = helpers["can_generate_nsfw_image"](user)
        helpers["is_censorship_strict"](user)

        # Kullanıcı tercihlerini kontrol et (web araması kapalı mı?)
        web_search_enabled = True
        try:
            from app.services import user_preferences

            if user and hasattr(user, "id") and user.id:
                prefs = user_preferences.get_effective_preferences(user.id, category="features")
                web_search_enabled = prefs.get("web_search", "true").lower() in ("true", "1", "yes", "on")
        except Exception as e:
            logger.warning(f"[ROUTER] Kullanıcı tercihleri kontrol edilemedi: {e}")

        # Persona bilgilerini hesapla
        active_persona = persona_name or "standard"
        persona_uncensored = self._persona_requires_local(active_persona)

        # Final model: requires_uncensored + can_local → local, değilse groq
        final_model = "local" if (persona_uncensored and can_use_local) else "groq"

        # Tool intent algıla (web araması kapalıysa INTERNET intent'i yok sayılır)
        tool_intent = self._detect_tool_intent(message)
        if tool_intent == ToolIntent.INTERNET and not web_search_enabled:
            tool_intent = ToolIntent.NONE
            reason_codes.append("web_search_disabled_by_user_pref")

        # =====================================================================
        # ORCHESTRATOR v5.8: Intent Detection & Metadata (Phase 1 - regex only)
        # =====================================================================
        intent_result = self._detect_intent_regex(message)
        orchestrator_metadata = self._build_orchestrator_metadata(message, intent_result)
        
        # --- LIVE TRACE ---
        LiveTracer.routing_decision(
            route_name=intent_result["intent"], 
            confidence=intent_result["confidence"], 
            reasoning=f"Regex match: {intent_result['intent']}"
        )
        # ------------------

        # =====================================================================
        # PRIORITY 1: TOOL INTENT (IMAGE / INTERNET)
        # =====================================================================

        if tool_intent == ToolIntent.IMAGE:
            # Görsel izni var mı?
            if not can_use_image:
                return RoutingDecision(
                    target=RoutingTarget.GROQ,
                    tool_intent=ToolIntent.NONE,
                    reason_codes=["image_permission_denied"],
                    censorship_level=censorship_level,
                    blocked=True,
                    block_reason="Görsel üretim izniniz bulunmuyor.",
                    persona_name=active_persona,
                    persona_requires_uncensored=persona_uncensored,
                    final_model=final_model,
                    metadata={"orchestrator": orchestrator_metadata},
                )

            # NSFW kontrolü
            is_nsfw = self._detect_nsfw_image(message)
            if is_nsfw and not can_nsfw:
                return RoutingDecision(
                    target=RoutingTarget.GROQ,
                    tool_intent=ToolIntent.NONE,
                    reason_codes=["nsfw_image_blocked", f"censorship_level_{censorship_level}"],
                    censorship_level=censorship_level,
                    blocked=True,
                    block_reason="Bu tür görsel içerik üretim izniniz bulunmuyor.",
                    persona_name=active_persona,
                    persona_requires_uncensored=persona_uncensored,
                    final_model=final_model,
                    metadata={"orchestrator": orchestrator_metadata},
                )

            reason_codes.append("tool_intent_image")
            return RoutingDecision(
                target=RoutingTarget.IMAGE,
                tool_intent=ToolIntent.IMAGE,
                reason_codes=reason_codes,
                censorship_level=censorship_level,
                persona_name=active_persona,
                persona_requires_uncensored=persona_uncensored,
                final_model=final_model,
                metadata={"is_nsfw": is_nsfw, "orchestrator": orchestrator_metadata},
            )

        if tool_intent == ToolIntent.INTERNET:
            if not can_use_internet:
                return RoutingDecision(
                    target=RoutingTarget.GROQ,
                    tool_intent=ToolIntent.NONE,
                    reason_codes=["internet_permission_denied"],
                    censorship_level=censorship_level,
                    blocked=True,
                    block_reason="İnternet araması izniniz bulunmuyor.",
                    persona_name=active_persona,
                    persona_requires_uncensored=persona_uncensored,
                    final_model=final_model,
                    metadata={"orchestrator": orchestrator_metadata},
                )

            reason_codes.append("tool_intent_internet")
            return RoutingDecision(
                target=RoutingTarget.INTERNET,
                tool_intent=ToolIntent.INTERNET,
                reason_codes=reason_codes,
                censorship_level=censorship_level,
                persona_name=active_persona,
                persona_requires_uncensored=persona_uncensored,
                final_model=final_model,
                metadata={"orchestrator": orchestrator_metadata},
            )

        # =====================================================================
        # PRIORITY 2: EXPLICIT LOCAL
        # Bu kategoriye giren istekler kullanıcının BİLİNÇLİ tercihidir:
        # - requested_model="bela"
        # - force_local=True
        # - message'da explicit local trigger kelimesi
        # - PERSONA requires_uncensored (kullanıcı bilinçli mod seçti)
        # =====================================================================

        requested = (requested_model or "").lower()
        explicit_local_message = self._detect_local_explicit(message)
        persona_requires = persona_name and self._persona_requires_local(persona_name)

        # Explicit local isteği var mı?
        if force_local or requested == "bela" or explicit_local_message or persona_requires:
            if can_use_local:
                reason_codes.append("explicit_local_request")
                if force_local:
                    reason_codes.append("force_local_flag")
                if requested == "bela":
                    reason_codes.append("requested_model_bela")
                if explicit_local_message:
                    reason_codes.append("message_contains_local_trigger")
                if persona_requires:
                    reason_codes.append("persona_requires_uncensored")
                    reason_codes.append(f"persona_{persona_name}")

                return RoutingDecision(
                    target=RoutingTarget.LOCAL,
                    tool_intent=ToolIntent.NONE,  # Local model tool çağıramaz
                    reason_codes=reason_codes,
                    censorship_level=censorship_level,
                    persona_name=active_persona,
                    persona_requires_uncensored=bool(persona_requires),
                    final_model="local",  # Explicit local seçildi
                    metadata={"orchestrator": orchestrator_metadata},
                )
            else:
                # İzin yok, Groq'a yönlendir
                reason_codes.append("local_permission_denied")
                reason_codes.append("fallback_to_groq")
                return RoutingDecision(
                    target=RoutingTarget.GROQ,
                    tool_intent=ToolIntent.NONE,
                    reason_codes=reason_codes,
                    censorship_level=censorship_level,
                    persona_name=active_persona,
                    persona_requires_uncensored=bool(persona_requires),
                    final_model="groq",
                    metadata={"orchestrator": orchestrator_metadata},
                )

        # =====================================================================
        # PRIORITY 3: CONTENT HEURISTIC (sadece net sinyallerde - AUTO routing)
        # =====================================================================

        if can_auto_local and self._detect_local_content(message):
            reason_codes.append("content_heuristic_local")
            return RoutingDecision(
                target=RoutingTarget.LOCAL,
                tool_intent=ToolIntent.NONE,
                reason_codes=reason_codes,
                censorship_level=censorship_level,
                persona_name=active_persona,
                persona_requires_uncensored=persona_uncensored,
                final_model="local",
                metadata={"orchestrator": orchestrator_metadata},
            )

        # Semantic analiz bazlı routing (opsiyonel, yavaş olabilir)
        if semantic and can_auto_local:
            domain = semantic.get("domain")
            sensitivity = set(semantic.get("sensitivity", []) or [])

            # SADECE net erotik/roleplay sinyallerde
            # politics/religion için otomatik local YAPMA (yanlış pozitif)
            if domain == "sex" or "sexual_content" in sensitivity:
                reason_codes.append("semantic_sexual_content")
                return RoutingDecision(
                    target=RoutingTarget.LOCAL,
                    tool_intent=ToolIntent.NONE,
                    reason_codes=reason_codes,
                    censorship_level=censorship_level,
                    persona_name=active_persona,
                    persona_requires_uncensored=persona_uncensored,
                    final_model="local",
                    metadata={"orchestrator": orchestrator_metadata},
                )

        # =====================================================================
        # PRIORITY 4: DEFAULT → GROQ
        # =====================================================================

        reason_codes.append("default_groq")
        return RoutingDecision(
            target=RoutingTarget.GROQ,
            tool_intent=ToolIntent.NONE,
            reason_codes=reason_codes,
            censorship_level=censorship_level,
            persona_name=active_persona,
            persona_requires_uncensored=persona_uncensored,
            final_model=final_model,
            metadata={"orchestrator": orchestrator_metadata},
        )

    # -------------------------------------------------------------------------
    # LOGGING
    # -------------------------------------------------------------------------

    def log_decision(
        self,
        decision: RoutingDecision,
        request_id: str | None = None,
        username: str | None = None,
    ) -> None:
        """
        Routing kararını loglar.

        Args:
            decision: Routing kararı
            request_id: İstek ID'si
            username: Kullanıcı adı
        """
        log_data = {
            "request_id": request_id or "unknown",
            "username": username or "unknown",
            **decision.to_dict(),
        }

        if decision.blocked:
            logger.warning(f"[ROUTER] BLOCKED: {log_data}")
        else:
            logger.info(f"[ROUTER] Decision: {log_data}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global router instance
smart_router = SmartRouter()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def route_message(
    message: str,
    user: Optional["User"] = None,
    persona_name: str | None = None,
    requested_model: str | None = None,
    force_local: bool = False,
    semantic: dict[str, Any] | None = None,
) -> RoutingDecision:
    """
    Kısayol fonksiyon - mesajı yönlendirir.

    Args:
        message: Kullanıcı mesajı
        user: User nesnesi
        persona_name: Aktif persona adı
        requested_model: İstenen model
        force_local: Zorla local
        semantic: Semantic analiz

    Returns:
        RoutingDecision: Routing kararı
    """
    return smart_router.route(
        message=message,
        user=user,
        persona_name=persona_name,
        requested_model=requested_model,
        force_local=force_local,
        semantic=semantic,
    )
