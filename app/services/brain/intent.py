"""
Mami AI - Multi-Tier Intent Manager (Atlas Sovereign Edition)
-------------------------------------------------------------
Kullanıcı mesajından niyet (intent) çıkarır ve yürütme planı (OrchestrationPlan) oluşturur.

Katmanlı Analiz Mimarisi:
- Tier 1 (Regex): Hızlı pattern matching
- Tier 2 (Semantic): Qdrant ile benzer niyetleri arama (hazırlık)
- Tier 3 (LLM): Karmaşık sorgular için model çağrısı
- Phase 3B: LLM Gray Classifier (production-ready)
"""

import re
import json
import logging
import os
import time
import hashlib
from typing import Any, Optional, Dict, List, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass

from app.core.constants import (
    PERSONAL_TRIGGERS, PERSONAL_OVERRIDES, TASK_TRIGGERS,
    FOLLOWUP_TRIGGERS, GENERAL_TRIGGERS, MODEL_GOVERNANCE
)
from app.core.prompts import ORCHESTRATOR_PROMPT

from app.core.terminal import log
logger = logging.getLogger(__name__)

# --- PYDANTIC MODELS ---
class TaskSpec(BaseModel):
    """DAG yürütücüsü için görev tanımı."""
    id: str
    type: str  # 'generation', 'tool', 'memory_control'
    specialist: Optional[str] = None
    tool_name: Optional[str] = None
    instruction: Optional[str] = None
    thought: Optional[str] = None  # Dinamik süreç düşüncesi
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)


class OrchestrationPlan(BaseModel):
    """Orkestratör tarafından oluşturulan yürütme planı."""
    intent: str
    confidence: float = 0.9
    tasks: List[TaskSpec] = Field(default_factory=list)
    reasoning: str = ""
    user_thought: str = ""
    router_thoughts: List[str] = Field(default_factory=list)
    is_follow_up: bool = False
    detected_topic: str = "SAME"
    context_focus: str = ""
    rewritten_query: Optional[str] = None
    proactive_hints: List[str] = Field(default_factory=list)
    orchestrator_model: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- HELPER FUNCTIONS / NORMALIZATION ---
def asciify(text: str) -> str:
    """Türkçe karakterleri ASCII'ye çevirir ve lowercase yapar."""
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return text.translate(tr_map).lower()


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    return re.sub(r"[^a-z0-9çğıöşü\s]", " ", lowered)


# --- INTENT CONTRACT (V1) ---
@dataclass
class IntentDecision:
    intent: str  # "image" | "text"
    confidence: float
    source: str  # "signal"|"rules"|"llm"|"fallback"
    matched_terms: List[str]
    rules_score: float
    normalized_text: str
    llm_reason: Optional[str] = None


# --- PHASE 3B: FEATURE FLAGS & SETTINGS ---
ENABLE_INTENT_LLM = bool(os.getenv("ENABLE_INTENT_LLM", "0") in ("1", "true", "True"))
INTENT_LLM_TIMEOUT_S = float(os.getenv("INTENT_LLM_TIMEOUT_S", "1.2"))
INTENT_LLM_MODEL = os.getenv("INTENT_LLM_MODEL", "llama-3.1-8b-instant")
INTENT_LLM_CACHE_TTL_S = int(os.getenv("INTENT_LLM_CACHE_TTL_S", "300"))

# --- SIGNALS / RULES ---
IMAGE_ROOTS = ["ciz", "olustur", "boya", "resim", "foto", "gorsel", "draw", "generate", "image"]
SUFFIXES = ["yorum", "yorsun", "yoruz", "dim", "dım", "dum", "düm", "acak", "ecek", "miş", "mış", "muş", "müş", "ma", "me", "mak", "mek", "ım", "im", "um", "üm", "iyorum"]
STOPLIST = ["resim dersi", "fotoğraf çektim", "evimi boyadım", "duvarı boyadım", "boyacı"]

# --- PHASE 3B: LLM RESULT MODEL ---
class IntentLLMResult(BaseModel):
    """Strict JSON result from LLM classifier."""
    is_image: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


# --- PHASE 3B: TTL CACHE ---
_intent_llm_cache: Dict[str, Tuple[float, IntentLLMResult]] = {}


def _get_cache_key(normalized_text: str) -> str:
    """Generate cache key from normalized text."""
    return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()


# --- PHASE 3B: LLM GRAY CLASSIFIER ---
def classify_image_intent_llm(message: str) -> IntentLLMResult:
    """
    Production-ready LLM classifier for gray zone intent detection.
    
    Features:
    - Strict JSON parsing with Pydantic validation
    - Timeout protection (INTENT_LLM_TIMEOUT_S)
    - TTL caching for idempotency
    - Fallback on errors
    """
    import httpx
    from app.core.resilience import key_manager
    
    # Normalize and prepare
    norm = normalize_text(message)
    preview = message[:80]
    
    # Check cache
    cache_key = _get_cache_key(norm)
    now = time.time()
    if cache_key in _intent_llm_cache:
        expires, cached_result = _intent_llm_cache[cache_key]
        if now < expires:
            logger.debug(f"[INTENT_LLM] Cache hit for: {preview}")
            return cached_result
        else:
            del _intent_llm_cache[cache_key]
    
    # Get API key
    api_key = key_manager.get_best_key(INTENT_LLM_MODEL)
    if not api_key:
        logger.warning("[INTENT_LLM] No API key available")
        result = IntentLLMResult(is_image=False, confidence=0.5, reason="no_api_key")
        _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
        return result
    
    # System prompt
    system_prompt = (
        "You are a classifier. Determine whether the user is asking to GENERATE an image now. "
        "Not about photos they took, not discussing art class. "
        'Output ONLY strict JSON: {"is_image": true|false, "confidence": 0..1, "reason": "..."}.'
    )
    
    try:
        # Call LLM with timeout
        with httpx.Client(timeout=INTENT_LLM_TIMEOUT_S) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": INTENT_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
        
        if response.status_code == 200:
            key_manager.report_success(api_key, INTENT_LLM_MODEL)
            raw_content = response.json()["choices"][0]["message"]["content"]
            
            # Parse strict JSON
            try:
                data = json.loads(raw_content)
                result = IntentLLMResult(**data)
                logger.debug(f"[INTENT_LLM] Success: is_image={result.is_image} conf={result.confidence:.2f} msg='{preview}'")
                
                # Cache and return
                _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
                return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[INTENT_LLM] JSON parse error: {e}")
                result = IntentLLMResult(is_image=False, confidence=0.5, reason="parse_error")
                _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
                return result
        else:
            key_manager.report_error(api_key, response.status_code, f"HTTP {response.status_code}", INTENT_LLM_MODEL)
            logger.warning(f"[INTENT_LLM] API error {response.status_code}")
            result = IntentLLMResult(is_image=False, confidence=0.5, reason=f"http_{response.status_code}")
            _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
            return result
            
    except httpx.TimeoutException:
        logger.warning(f"[INTENT_LLM] Timeout after {INTENT_LLM_TIMEOUT_S}s")
        result = IntentLLMResult(is_image=False, confidence=0.5, reason="timeout")
        _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
        return result
    except Exception as e:
        logger.error(f"[INTENT_LLM] Unexpected error: {e}")
        result = IntentLLMResult(is_image=False, confidence=0.5, reason="error")
        _intent_llm_cache[cache_key] = (now + INTENT_LLM_CACHE_TTL_S, result)
        return result


def _stem_tokens(norm_ascii: str) -> List[str]:
    """Stem tokens by removing suffixes (longest first)."""
    # Sort suffixes by length (longest first) for greedy matching
    sorted_suffixes = sorted(SUFFIXES, key=len, reverse=True)
    stems = []
    for tok in norm_ascii.split():
        for suf in sorted_suffixes:
            if tok.endswith(suf) and len(tok) > len(suf):
                tok = tok[: -len(suf)]
                break
        stems.append(tok)
    return stems


def decide_intent(message: str, user_mode: Optional[str] = None) -> IntentDecision:
    norm = normalize_text(message)
    norm_ascii = asciify(norm)
    preview = norm[:80]

    stripped = message.strip().lower()
    if user_mode == "image":
        return IntentDecision("image", 1.0, "signal", ["user_mode=image"], 1.0, norm)
    if user_mode == "text":
        return IntentDecision("text", 1.0, "signal", ["user_mode=text"], 0.0, norm)
    if stripped.startswith(("/image", "!img", "!image")):
        return IntentDecision("image", 1.0, "signal", [stripped.split()[0]], 1.0, norm)

    stems = _stem_tokens(norm_ascii)
    matched = [root for root in IMAGE_ROOTS if any(tok.startswith(root) for tok in stems)]
    rules_score = 0.0
    if matched:
        rules_score += 0.6
        if any(r in stems for r in ("ciz", "olustur", "boya", "draw", "generate")):
            rules_score += 0.2
    
    # Stoplist check on normalized ASCII text
    stoplist_ascii = [asciify(s) for s in STOPLIST]
    if any(stop in norm_ascii for stop in stoplist_ascii):
        rules_score = 0.0
    
    rules_score = max(0.0, min(1.0, rules_score))

    # Phase 3B: LLM Gray Classifier Integration
    # Gray zone: 0.35 <= rules_score <= 0.75
    is_gray = 0.35 <= rules_score <= 0.75
    cache_hit = False
    
    if is_gray and ENABLE_INTENT_LLM:
        # Call LLM classifier
        llm_result = classify_image_intent_llm(message)
        cache_hit = _get_cache_key(norm) in _intent_llm_cache
        
        if llm_result.is_image and llm_result.confidence >= 0.6:
            intent = "image"
            confidence = max(llm_result.confidence, 0.75)
            source = "llm"
            llm_reason = llm_result.reason
        else:
            intent = "text"
            confidence = max(0.5, llm_result.confidence)
            source = "llm"
            llm_reason = llm_result.reason
        
        decision = IntentDecision(intent, confidence, source, matched, rules_score, norm, llm_reason)
        # Reduced logging for production
        logger.debug(
            f"[INTENT] {decision.intent} src={decision.source} conf={decision.confidence:.2f} "
            f"score={decision.rules_score:.2f} terms={decision.matched_terms} "
            f"cache_hit={cache_hit} llm_reason={llm_reason} norm='{preview}'"
        )
        return decision
    
    # Phase 3A: Rules-based decision
    if rules_score >= 0.75:
        decision = IntentDecision("image", rules_score, "rules", matched, rules_score, norm)
    elif rules_score <= 0.25:
        decision = IntentDecision("text", 1 - rules_score, "rules", matched, rules_score, norm)
    else:
        # Gray fallback without LLM
        decision = IntentDecision("text", 0.5, "rules", matched, rules_score, norm)

    logger.debug(
        f"[INTENT] {decision.intent} src={decision.source} conf={decision.confidence:.2f} "
        f"score={decision.rules_score:.2f} terms={decision.matched_terms} "
        f"cache_hit={cache_hit} norm='{preview}'"
    )
    return decision


def detect_intent_regex(message: str) -> tuple[str, float, List[str]]:
    """
    Hızlı intent tespiti (signals + rules). LLM path bu fazda kapalı.
    Dönüş: (intent, confidence, thoughts)
    """
    # logger.debug(f"[INTENT_DEBUG] detect_intent_regex called with: '{message}'")
    decision = decide_intent(message)
    # logger.debug(f"[INTENT_DEBUG] decide_intent result: intent={decision.intent}, score={decision.rules_score}")
    thoughts: List[str] = []
    
    # Phase3A marker with stoplist detection
    # Check if stoplist was triggered by looking for score=0.0 with source=rules
    stoplist_ascii = [asciify(s) for s in STOPLIST]
    msg_ascii = asciify(message)
    stoplist_hit = any(stop in msg_ascii for stop in stoplist_ascii)
    
    if stoplist_hit and decision.source == "rules":
        thoughts.append("Phase3A: stoplist -> text")
    else:
        thoughts.append(f"Phase3A: source={decision.source} score={decision.rules_score:.2f} terms={decision.matched_terms}")
    
    if decision.intent == "image":
        return "image", decision.confidence, thoughts

    msg = asciify(message.strip())

    SEARCH_KEYWORDS = ["nedir", "kimdir", "nasil", "kac", "nerede", "hava", "haber", "borsa", "dolar", "fiyat", "ne kadar", "son dakika"]
    matched = next((kw for kw in SEARCH_KEYWORDS if re.search(rf"\b{kw}\b", msg)), None)
    if matched:
        thoughts.append(f"'{matched}' hakkında güncel bilgi aradığınızı anlıyorum.")
        return "search", 0.95, thoughts

    MEMORY_KEYWORDS = ["beni unut", "hafizani sil", "temizle", "kimim", "neler biliyorsun"]
    matched = next((kw for kw in MEMORY_KEYWORDS if kw in msg), None)
    if matched:
        thoughts.append(f"Hafıza yönetimi talebi ('{matched}') algıladım.")
        return "memory_control", 0.95, thoughts

    matched = next((kw for kw in PERSONAL_OVERRIDES if kw in msg), None)
    if matched:
        thoughts.append(f"Kişisel bir soru ('{matched}') fark ettim.")
        return "personal", 0.85, thoughts

    matched = next((kw for kw in TASK_TRIGGERS if kw in msg), None)
    if matched:
        thoughts.append(f"Metinde görev komutu ('{matched}') bulundu.")
        return "task", 0.85, thoughts

    matched = next((kw for kw in FOLLOWUP_TRIGGERS if kw in msg), None)
    if matched:
        thoughts.append(f"Konuşmanın devamı niteliğinde ('{matched}') olduğunu anlıyorum.")
        return "followup", 0.8, thoughts

    CODING_KEYWORDS = ["kod", "code", "python", "javascript", "function", "class", "debug", "hata"]
    matched = next((kw for kw in CODING_KEYWORDS if re.search(rf"\b{kw}\b", msg)), None)
    if matched:
        thoughts.append(f"Yazılım/kodlama ('{matched}') odaklı.")
        return "coding", 0.9, thoughts

    DOC_KEYWORDS = ["dosya", "belge", "dokuman", "pdf", "tck", "yonetmelik", "kanun", "rapor", "bilgi fişi", "oku", "incele"]
    matched = next((kw for kw in DOC_KEYWORDS if kw in msg), None)
    if matched:
        thoughts.append(f"Belgelerle ilgili soru ('{matched}') algıladım.")
        return "document", 0.9, thoughts

    thoughts.append("Genel sohbet modundayım.")
    return "general", 0.6, thoughts
