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

import httpx

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
    Groq Chat API çağrısı (async, anahtar rotasyonlu).

    KeyManager ile en uygun anahtarı seçer ve 429 durumunda rotasyon yapar.

    Args:
        messages: OpenAI formatında mesaj listesi
        model: Kullanılacak model
        json_mode: JSON çıktı modu
        temperature: Yaratıcılık seviyesi (0.0-1.0)
        timeout: İstek zaman aşımı

    Returns:
        str veya None: API yanıtı veya hata durumunda None
    """
    # Lazy import to avoid circular defaults if any
    from app.services.api_monitor import api_monitor
    from app.core.key_manager import key_manager
    
    settings = _get_settings()
    model = model or settings.GROQ_DECIDER_MODEL

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        # --- KALİTE OPTİMİZASYONU ---
        "top_p": 0.9,  
        "frequency_penalty": 0.3,  
        "presence_penalty": 0.1,  
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Rotasyon limiti (Kaç farklı anahtar denenecek?)
    # 5 makul bir sayı, sonsuz döngüye girmemesi için.
    MAX_KEY_ATTEMPTS = 5
    
    for attempt in range(MAX_KEY_ATTEMPTS):
        # 1. Anahtar Seçimi
        api_key = key_manager.get_next_key(model=model)
        if not api_key:
            LiveTracer.warning("GROQ", "No API Keys available!")
            logger.error("[GROQ] Kullanılabilir API anahtarı kalmadı (Hepsi cooldown veya limit dışı)!")
            return None

        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(GROQ_API_URL, headers=headers, json=payload)

                # --- API MONITORING ---
                try:
                    # Header update (Rate limits)
                    api_monitor.update_usage(api_key, resp.headers)
                except Exception:
                    pass
                # ----------------------

                resp.raise_for_status()
                
                # Başarılı Yanıt
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                
                if content:
                    # Usage Tracking
                    try:
                        usage = data.get("usage", {})
                        total_tokens = usage.get("total_tokens", 0)
                        api_monitor.increment_usage(api_key, model, total_tokens)
                    except Exception:
                        pass

                    # KeyManager'a başarı bildir
                    key_manager.report_success(api_key, model=model)
                    
                    # Eğer ilk deneme değilse logla
                    if attempt > 0:
                        logger.info(f"[GROQ] Başarılı (Deneme {attempt + 1})")
                        
                    return content
                else:
                    # Boş içerik hatası?
                    logger.warning(f"[GROQ] Boş içerik döndü. Key: ...{api_key[-4:]}")
                    continue

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            
            # KeyManager'a hata bildir (429 ise cooldown başlatır)
            key_manager.report_failure(api_key, status, model=model)
            
            if status == 429:
                LiveTracer.warning("GROQ", f"Rate Limit 429 ({model})")
                logger.warning(f"[GROQ] Rate Limit 429. Rotasyon deneniyor... ({attempt+1}/{MAX_KEY_ATTEMPTS})")
                continue # Sonraki anahtarı dene
                
            # Diğer hatalar (400, 401, 500)
            try:
                error_detail = exc.response.json()
                logger.error(f"[GROQ] HTTP {status} Error: {error_detail}")
            except:
                logger.error(f"[GROQ] HTTP {status} Error: {exc.response.text[:200]}")
                
            if status >= 500:
                # 5xx hatalarında da rotasyon dene
                continue
            else:
                # 400 gibi hatalarda rotasyon yapma, request hatalı
                return None

        except Exception as exc:
            LiveTracer.warning("GROQ", f"Exception: {exc}")
            logger.error(f"[GROQ] Beklenmeyen hata: {exc}")
            # Bağlantı hatası vs olabilir, rotasyon dene
            continue

    logger.critical("[GROQ] TÜM DENEMELER BAŞARISIZ OLDU!")
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
    
    1. İstenen model (veya default) denenir (KeyManager rotasyonu ile).
    2. Başarısız olursa, FALLBACK_CHAINS yapılandırmasındaki alternatifler denenir.
    
    Args:
        messages: Mesaj listesi
        model: Model adı
    """
    settings = _get_settings()
    primary_model = model or settings.GROQ_DECIDER_MODEL
    
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
    Streaming Groq API çağrısı.
    KeyManager entegreli.

    Args:
        messages: Mesaj listesi
        model: Model adı
        temperature: Sıcaklık
        timeout: Zaman aşımı

    Yields:
        str: Yanıt parçaları
    """
    from app.services.api_monitor import api_monitor
    from app.core.key_manager import key_manager
    
    settings = _get_settings()
    model = model or settings.GROQ_DECIDER_MODEL

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        # --- KALİTE OPTİMİZASYONU ---
        "top_p": 0.9, 
        "frequency_penalty": 0.3,  
        "presence_penalty": 0.1, 
    }
    
    # Maksimum deneme sayısı
    MAX_KEY_ATTEMPTS = 5
    
    success = False
    
    for attempt in range(MAX_KEY_ATTEMPTS):
        api_key = key_manager.get_next_key(model=model)
        if not api_key:
             logger.error("[GROQ_STREAM] Kullanılabilir API anahtarı kalmadı!")
             yield "[ERROR] No API keys available."
             return

        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", GROQ_API_URL, headers=headers, json=payload) as resp:
                    # --- API MONITORING ---
                    try:
                        api_monitor.update_usage(api_key, resp.headers)
                    except Exception:
                        pass
                    # ----------------------

                    if resp.status_code == 429:
                        logger.warning(f"[GROQ_STREAM] Rate Limit 429 ({model}). Rotasyon...")
                        key_manager.report_failure(api_key, 429, model=model)
                        continue

                    if resp.status_code >= 400:
                        try:
                            error_body = await resp.aread()
                            error_text = error_body.decode("utf-8", errors="replace")
                        except Exception as e:
                            error_text = f"Error reading body: {e}"

                        logger.error(f"[GROQ_STREAM] HTTP {resp.status_code}: {error_text}")
                        key_manager.report_failure(api_key, resp.status_code, model=model)
                        
                        if resp.status_code >= 500:
                            continue # Retry on server error
                        else:
                            yield f"[ERROR] HTTP {resp.status_code}"
                            return

                    # Başarılı bağlantı
                    key_manager.report_success(api_key, model=model)
                    success = True
                    logger.info(f"[GROQ_STREAM] Başarılı akış başladı. Key: ...{api_key[-4:]}")

                    async for line in resp.aiter_lines():
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]  # len("data: ") = 6
                            if data_str == "[DONE]":
                                return

                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError as e:
                                logger.warning(
                                    f"[GROQ_STREAM] JSON parse error: {e}"
                                )
                                continue
                    return # Başarılı bitiş

        except httpx.HTTPStatusError:
             continue
        except Exception as exc:
            logger.error(f"[GROQ_STREAM] Beklenmeyen hata: {exc}")
            continue

    if not success:
        logger.critical("[GROQ_STREAM] TÜM DENEMELER BAŞARISIZ OLDU!")
        yield " [ERROR] Tüm API anahtarları tükendi veya hata oluştu. "


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
