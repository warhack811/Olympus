"""
Mami AI - Groq API & Query Builder
==================================

Bu modül Groq API çağrıları ve arama sorgusu üretimi yapar.

Sorumluluklar:
    - Groq API çağrıları (çoklu anahtar rotasyonu)
    - INTERNET için arama sorgusu üretimi
    - Hafıza kayıt kararları

Kullanım:
    from app.chat.decider import call_groq_api_async, build_search_queries_async

    # Groq API çağrısı
    response = await call_groq_api_async(messages, model="llama-3.3-70b")

    # İnternet araması için sorgu üretimi
    queries = await build_search_queries_async("Dolar kuru nedir?")
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

# Modül logger'ı
logger = logging.getLogger(__name__)

# --- LIVE TRACE ---
try:
    from app.core.live_tracer import LiveTracer
except ImportError:
    class LiveTracer:
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def model_select(*args, **kwargs): pass
# ------------------

# =============================================================================
# YAPILANDIRMA
# =============================================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
"""Groq API endpoint URL'si."""

DEFAULT_GROQ_TIMEOUT = 15.0
"""Varsayılan API zaman aşımı (saniye)."""


# =============================================================================
# LAZY IMPORTS & API KEY YÖNETİMİ
# =============================================================================


def _get_settings():
    """Ayarları lazy import ile yükler."""
    from app.config import get_settings
    return get_settings()


# =============================================================================
# LLM GENERATOR BRIDGE (Atlas Governance)
# =============================================================================
_GENERATOR = None


def _get_llm_generator():
    """Governance + KeyManager + Budget ile Groq adapter'ı döndürür."""
    global _GENERATOR
    if _GENERATOR is None:
        from app.core.llm import LLMGenerator
        from app.core.llm.adapters import groq_adapter

        _GENERATOR = LLMGenerator(providers={"groq": groq_adapter})
    return _GENERATOR


def get_available_keys() -> list[str]:
    """
    Tüm geçerli Groq API anahtarlarını döndürür. (Public Alias)
    """
    return _get_available_keys()

def _get_available_keys() -> list[str]:
    """
    Tüm geçerli Groq API anahtarlarını döndürür.

    Boş olmayan anahtarlar rotasyon için sırayla denenir.
    """
    settings = _get_settings()
    keys = [
        settings.GROQ_API_KEY,
        settings.GROQ_API_KEY_BACKUP,
        settings.GROQ_API_KEY_4,
        getattr(settings, "GROQ_API_KEY_3", None),
    ]
    return [k for k in keys if k]


# =============================================================================
# GROQ API FONKSİYONLARI
# =============================================================================


async def call_groq_api_async(
    messages: list[dict[str, str]],
    model: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    timeout: float = DEFAULT_GROQ_TIMEOUT,
) -> str | None:
    """
    Groq Chat API çağrısı (async) - yeni LLMGenerator üzerinden governance/key rotasyonu.
    """
    generator = _get_llm_generator()
    from app.core.llm.generator import LLMRequest

    request = LLMRequest(
        role="decider",
        messages=messages,
        temperature=temperature,
        metadata={"override_model": model} if model else None,
    )
    result = await generator.generate(request)
    if result.ok:
        return result.text
    LiveTracer.warning("GROQ", f"Decider failed: {result.text}")
    return None


async def call_groq_api_safe_async(
    messages: list[dict[str, str]],
    model: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    timeout: float = DEFAULT_GROQ_TIMEOUT,
    max_retries: int = 2,
) -> tuple[str | None, str | None]:
    """
    Retry mekanizmalı ve Fallback zincirli güvenli Groq API çağrısı.
    
    1. İstenen model (veya governance default) denenir (KeyManager rotasyonu ile).
    2. Başarısız olursa, FALLBACK_CHAINS yapılandırmasındaki alternatifler denenir.
    
    Args:
        messages: Mesaj listesi
        model: Model adı (opsiyonel, governance'dan alınır)
    """
    settings = _get_settings()
    
    # Model belirtilmemişse governance'dan al
    if not model:
        from app.core.llm.governance import governance
        chain = governance.get_model_chain("synthesizer")
        primary_model = chain[0] if chain else "llama-3.3-70b-versatile"
    else:
        primary_model = model
    
    # 1. Denenecek Modelleri Belirle
    attempt_models = [primary_model]
    
    # Fallback zincirini ekle
    fallbacks = settings.FALLBACK_CHAINS.get(primary_model, settings.FALLBACK_CHAINS.get("default", []))
    for fm in fallbacks:
        if fm not in attempt_models:
            attempt_models.append(fm)
            
    last_error: str | None = None
    
    for active_model in attempt_models:
        if active_model != primary_model:
            logger.warning(f"[GROQ_SAFE] Model Fallback: {primary_model} -> {active_model}")
            
        # call_groq_api_async zaten kendi içinde Key Rotasyonu (5 deneme) yapıyor.
        # Bu yüzden burada tekrar retry loop'a gerek yok, model değiştirmek daha mantıklı.
        
        content = await call_groq_api_async(
            messages=messages,
            model=active_model,
            json_mode=json_mode,
            temperature=temperature,
            timeout=timeout,
        )
        
        if content:
            # Eğer fallback ile yanıt alındıysa logla
            if active_model != primary_model:
                logger.info(f"[GROQ_SAFE] Fallback başarısı: {active_model}")
            return content, None
            
        last_error = f"model_failed_{active_model}"

    logger.critical(f"[GROQ_SAFE] TÜM MODEL ZİNCİRİ BAŞARISIZ! {attempt_models}")
    return None, "all_models_failed"


async def call_groq_api_stream_async(
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.7,
    timeout: float = DEFAULT_GROQ_TIMEOUT,
) -> AsyncGenerator[str, None]:
    """
    Streaming Groq API çağrısı (LLMGenerator üzerinden).
    """
    generator = _get_llm_generator()
    from app.core.llm.generator import LLMRequest

    request = LLMRequest(
        role="decider",
        messages=messages,
        temperature=temperature,
        metadata={"override_model": model} if model else None,
    )
    async for chunk in generator.generate_stream(request):
        yield chunk


# =============================================================================
# SİSTEM PROMPTLARI
# =============================================================================

# DECIDER_SYSTEM_PROMPT silindi - SmartRouter artık action belirliyor

MEMORY_DECIDER_SYSTEM_PROMPT = """
Sen Mami AI'ın Hafıza Yöneticisisin. Görevin, konuşma akışından kullanıcıyla ilgili ÖNEMLİ bilgileri yakalamak ve kategorize etmektir.

## 1. HAFIZA TİPLERİ (YENİ SİSTEM 🧠)
Bilgiyi yakalamadan önce şu 4 kategoriden hangisine girdiğine karar ver:

1.  **🔍 FACT (type="fact"):** Kalıcı, değişmez gerçekler.
    *   *Örnek:* "Kullanıcı vegan", "Kullanıcı 30 yaşında", "Kullanıcı İstanbul'da yaşıyor".
    *   *Süre:* Kalıcı.

2.  **📅 EVENT (type="event"):** Geleceğe yönelik planlar, randevular veya zamanlı işler.
    *   *Örnek:* "Yarın saat 15:00'te doktor randevusu var", "Haftaya tatile gidiyor".
    *   *Süre:* Olay gerçekleşene kadar.

3.  **⚡ STATE (type="state"):** Geçici durumlar, duygular veya anlık bağlam.
    *   *Örnek:* "Kullanıcı bugün yorgun hissediyor", "Şu an Python projesi debug ediyor".
    *   *Süre:* Kısa vadeli (24-48 saat).

4.  **🗑️ NOISE (type="noise"):** Gereksiz bilgi. SAKLAMA.
    *   *Örnek:* "Hava güzel", "Selam naber", "Teşekkürler", Genel sohbet dolgusu, AI'ın kendi cevapları.

## 2. KARAR MEKANİZMASI (CHAIN OF THOUGHT)
Karar vermeden önce şu adımları izle:
1.  **Analiz:** Kullanıcı ne dedi? Bu bilgi kişisel mi yoksa genel mi?
2.  **Kategori:** Fact, Event veya State mi? Yoksa Noise mu?
3.  **Önem:** 0.0 (Gereksiz) ile 1.0 (Kritik) arasında puan ver.
4.  **Kontrol:** Bu bilgi mevcut hafızayla çelişiyor mu? (Örn: "Evliyim" dedikten sonra "Bekarım" demesi).

## 3. JSON ÇIKTI FORMATI
Kesinlikle sadece geçerli bir JSON döndür. Yorum yok.

```json
{
  "reasoning": "Kullanıcı yarın için bir plan belirtti, bu bir Event.",
  "store": true,
  "memory": "Kullanıcının yarın saat 14:00'te toplantısı var",
  "type": "event",
  "importance": 0.8,
  "topic": "schedule",
  "invalidate": []
}
```

Eğer SAKLANMAYACAKSA (Noise):
```json
{
  "reasoning": "Kullanıcı sadece selam verdi, bilgi değeri yok.",
  "store": false
}
```

## ÖNEMLİ KURALLAR:
*   MÜMKÜN OLDUĞUNCA AZ KAYIT AL. Sadece *gerçekten* işe yarayacak bilgileri sakla.
*   "type" alanı zorunludur (fact, event, state).
*   Geçici duyguları "state" olarak kaydet, "fact" yapma.
""".strip()

# RAG_DECIDER_SYSTEM_PROMPT ve CONVERSATION_SUMMARY_SYSTEM silindi - Kullanılmıyordu


# run_decider_async silindi - SmartRouter artık action belirliyor
# build_search_queries_async kullanılmalı

# -----------------------------------------------------------------------------
# QUERY BUILDER (Secenek B - Yeni Sistem)
# -----------------------------------------------------------------------------

QUERY_BUILDER_PROMPT = """
You are a search query generator. Given a user's question, create 1-3 optimized web search queries.

Guidelines:
- For finance (dolar, euro, altın): Add "kuru bugün güncel" to make it time-specific
- For weather: Add city name if mentioned + "hava durumu"
- For sports: Add team name + "son maç skor"
- For news: Add "son dakika" or "güncel haber"
- Keep queries in Turkish

Output JSON: {"queries": [{"id": "q1", "query": "..."}, {"id": "q2", "query": "..."}]}
"""


async def build_search_queries_async(message: str, semantic: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """
    INTERNET akışı için arama sorguları üretir.

    Özellikler:
    - SmartRouter'dan bağımsız çalışır
    - Sadece sorgu oluşturmaya odaklanır
    - Semantic analiz sonuçlarını kullanabilir

    Args:
        message: Kullanıcı mesajı
        semantic: Semantic analiz sonuçları (opsiyonel)

    Returns:
        List[Dict]: [{"id": "q1", "query": "..."}]
    """
    # Domain bazlı basit kontrol
    domain = semantic.get("domain", "general") if semantic else "general"
    text_lower = message.lower()

    # 1. Hızlı template kontrolü (LLM çağrısı gerekmez)
    if domain == "finance" or any(kw in text_lower for kw in ["dolar", "euro", "altın", "kur"]):
        for currency in ["dolar", "euro", "altın", "sterlin"]:
            if currency in text_lower:
                return [{"id": "q1", "query": f"{currency} TL kuru bugün güncel"}]

    if domain == "weather" or "hava" in text_lower:
        # Şehir çıkarımı
        cities = ["istanbul", "ankara", "izmir", "bursa", "antalya", "trabzon", "adana"]
        city = next((c for c in cities if c in text_lower), "türkiye")
        return [{"id": "q1", "query": f"{city} hava durumu"}]

    # 2. LLM ile akıllı sorgu üretimi
    llm_messages = [
        {"role": "system", "content": QUERY_BUILDER_PROMPT},
        {"role": "user", "content": message},
    ]

    content = await call_groq_api_async(llm_messages, json_mode=True, temperature=0.2)
    if content:
        try:
            data = json.loads(content)
            queries = data.get("queries", [])
            if queries:
                logger.info(f"[QUERY_BUILDER] LLM generated {len(queries)} queries")
                return queries
        except json.JSONDecodeError:
            logger.warning("[QUERY_BUILDER] JSON parse hatası, fallback'e geçiliyor")

    # 3. Fallback: Ham mesajı sorgu olarak kullan
    return [{"id": "q1", "query": message}]


async def decide_memory_storage_async(
    message: str, answer: str, existing_memories: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Hafıza kayıt kararını LLM'e sorar.

    Conflict detection: Mevcut hafızalarla çelişki varsa
    eski kayıtları invalidate eder.

    Args:
        message: Kullanıcı mesajı
        answer: Asistan yanıtı
        existing_memories: Mevcut ilgili hafızalar

    Returns:
        Dict: {store, memory, importance, category, invalidate}
    """
    existing_memories = existing_memories if existing_memories is not None else []

    # Mevcut hafızaları context olarak ekle
    memory_context = ""
    if existing_memories:
        memory_context = "\n\n## MEVCUT İLGİLİ HAFIZALAR:\n"
        for m in existing_memories:
            mid = m.get("id", "unknown")
            mtext = m.get("text", "")
            memory_context += f"- ID: {mid} | Text: {mtext}\n"

    user_content = f"Kullanıcı: {message}\nAsistan: {answer}{memory_context}"

    messages = [
        {"role": "system", "content": MEMORY_DECIDER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    content = await call_groq_api_async(messages, json_mode=True, temperature=0.2)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

    return {"store": False}


# decide_rag_storage_async ve summarize_conversation_for_rag_async silindi - Hiç çağrılmıyordu
