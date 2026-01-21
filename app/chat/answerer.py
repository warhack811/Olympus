"""
Mami AI - Yanıt Üretici (Groq Answerer)
=======================================

Bu modül, Groq API kullanarak yüksek kaliteli yanıtlar üretir.

Özellikler:
    - Dinamik temperature (domain/risk bazlı)
    - Chain-of-Thought desteği (karmaşık sorular için)
    - Context injection (RAG, hafıza)
    - Streaming desteği
    - Thinking block filtreleme

Kullanım:
    from app.chat.answerer import generate_answer, generate_answer_stream

    # Tek seferlik yanıt
    answer = await generate_answer(
        message="Python'da liste nasıl oluşturulur?",
        context="Kullanıcı yeni başlayan bir geliştirici"
    )

    # Streaming yanıt
    async for chunk in generate_answer_stream(message, context):
        print(chunk, end="")
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, cast

# Modül logger'ı
logger = logging.getLogger(__name__)

# =============================================================================
# NOT: SYSTEM_PROMPT_UNIVERSAL silindi.
# Sistem promptları artık compiler.py üzerinden build_system_prompt() ile üretiliyor.
# =============================================================================


# =============================================================================
# LAZY IMPORTS
# =============================================================================


def _get_imports():
    """Import döngüsünü önlemek için lazy import."""
    from app.ai.prompts.identity import enforce_model_identity, get_ai_identity
    from app.config import get_settings
    from app.services.response_processor import full_post_process

    return (
        get_settings,
        get_ai_identity,
        enforce_model_identity,
        full_post_process,
        CORE_PROMPT,
    )


# =============================================================================
# DİNAMİK TEMPERATURE HESAPLAMA
# =============================================================================


def get_dynamic_temperature(
    analysis: dict[str, Any] | None = None, style_profile: dict[str, Any] | None = None
) -> float:
    """
    Domain, risk seviyesi ve KULLANICI TERCİHLERİNE göre dinamik temperature hesaplar.

    Temperature Seviyeleri:
        - Düşük (0.1-0.3): Deterministik, doğruluk kritik
        - Orta (0.4-0.6): Dengeli
        - Yüksek (0.7-1.0): Yaratıcı

    Args:
        analysis: Semantic analiz sonuçları
        style_profile: Kullanıcı stil tercihleri (tone, creativity vb.)

    Returns:
        float: Hesaplanan temperature değeri (0.0-1.0)
    """
    if not analysis and not style_profile:
        return 0.6  # Varsayılan dengeli

    # Domain bazlı base temperature
    domain = analysis.get("domain", "general")
    domain_temps = {
        # Kritik doğruluk gerektiren alanlar
        "finance": 0.2,
        "health": 0.2,
        "legal": 0.2,
        "weather": 0.1,
        "sports": 0.3,
        # Teknik alanlar
        "code": 0.4,
        "tech": 0.4,
        # Sosyal/kişisel alanlar
        "personal": 0.6,
        "relationships": 0.6,
        "mental_health": 0.5,
        # Yaratıcı alanlar
        "creative": 0.8,
        "story": 0.85,
        # Hassas ama özgür tartışma
        "politics": 0.5,
        "religion": 0.5,
        "sex": 0.6,
        # Genel
        "general": 0.6,
    }
    base_temp = domain_temps.get(domain, 0.6)

    # Risk seviyesine göre düşür
    risk_level = analysis.get("risk_level", "low")
    if risk_level == "high":
        base_temp = min(base_temp, 0.3)
    elif risk_level == "medium":
        base_temp = min(base_temp, 0.5)

    # Intent tipine göre ayarla
    intent_type = analysis.get("intent_type", "")
    if intent_type in ("explicit_instruction", "advice_high_risk"):
        base_temp = min(base_temp, 0.3)
    elif intent_type in ("story", "emotional_support"):
        base_temp = max(base_temp, 0.6)

    # Creativity override
    creativity = analysis.get("creativity_level", "")
    if creativity == "high":
        base_temp = max(base_temp, 0.75)
    elif creativity == "low":
        base_temp = min(base_temp, 0.35)

    # -------------------------------------------------------------------------
    # STİL BAZLI MODİFİKASYONLAR (Kullanıcı Tercihleri)
    # -------------------------------------------------------------------------
    if style_profile:
        # 1. Ton Bazlı Değişim
        tone = style_profile.get("tone", "neutral")
        if tone == "friendly":
            base_temp += 0.05
        elif tone == "humorous":
            base_temp += 0.15
        elif tone == "serious":
            base_temp -= 0.10
        elif tone == "empathetic":
            base_temp += 0.05

        # 2. Formality Bazlı Değişim
        formality = style_profile.get("formality", "medium")
        if formality == "low":  # Samimi
            base_temp += 0.05
        elif formality == "high":  # Resmi
            base_temp -= 0.05

        # 3. Yaratıcı Mod Kontrolü
        # (Eğer kullanıcı özellikle 'creative' bir mod seçtiyse)
        # NOT: Kullanıcı "Emniyet kemeri yok" dediği için burada
        # riskli domain olsa bile artışa izin veriyoruz (kısmi).

    # Sonuç sınırlandırma (0.0 - 1.0 arası)
    final_temp = max(0.0, min(1.0, base_temp))

    return round(final_temp, 2)


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================





# =============================================================================
# ANA YANIT FONKSİYONLARI
# =============================================================================


async def generate_answer(
    message: str,
    analysis: dict[str, Any] | None = None,
    context: str | None = None,
    system_prompt: str | None = None,
    source: str | None = None,
    history: list[dict[str, str]] | None = None,
    style_profile: dict[str, Any] | None = None,
    images: list[str] | None = None,
) -> str:
    """
    Groq API ile tek seferlik yanıt üretir.

    Args:
        message: Kullanıcı mesajı
        analysis: Semantic analiz sonuçları
        context: RAG/hafıza bağlamı
        system_prompt: Özel sistem prompt'u
        source: Yanıt kaynağı (loglama için)
        history: Sohbet geçmişi

    Returns:
        str: Üretilen yanıt
    """
    (
        get_settings,
        get_ai_identity,
        enforce_model_identity,
        full_post_process,
        CORE_PROMPT,
    ) = _get_imports()
    settings = get_settings()

    # Shared helper imports
    from app.chat.stream_manager import _clean_thinking_block

    # Dinamik temperature (Style profile ile)
    temperature = get_dynamic_temperature(analysis, style_profile)
    logger.debug(f"[ANSWERER] Temperature: {temperature}")

    # AI kimliği
    identity = get_ai_identity()
    identity_block = (
        f"KİMLİK: Adın {identity.display_name}. {identity.short_intro}\n"
        "GİZLİLİK: Sağlayıcı isimlerini (Google, Groq, Llama vb.) asla söyleme.\n"
    )

    # Sistem prompt (Zorunlu)
    base_system = system_prompt or "Sen yardımcı bir asistansın."

    # Semantic analiz bazlı ek talimatlar
    extra_instructions = []

    if analysis:
        complexity = analysis.get("complexity", "medium")
        requires_step = analysis.get("requires_step_by_step", False)

        if complexity == "high" or requires_step:
            extra_instructions.append(
                "🧠 DÜŞÜNME TALİMATI: Bu karmaşık bir soru. Cevaplamadan önce problemi parçalara ayır ve adım adım çöz."
            )

        response_length = analysis.get("preferred_response_length", "medium")
        if response_length == "brief":
            extra_instructions.append("📏 UZUNLUK: Kısa ve öz cevap ver (1-3 cümle).")
        elif response_length == "detailed":
            extra_instructions.append("📏 UZUNLUK: Detaylı ve kapsamlı cevap ver.")

        if analysis.get("is_structured_request"):
            extra_instructions.append("📊 FORMAT: Yapılandırılmış veri isteniyor. Tablo veya liste formatı kullan.")

        if analysis.get("force_no_hallucination"):
            extra_instructions.append("⚠️ DOĞRULUK: Sadece kesin bildiğin verileri paylaş. Tahmin yapma.")

    # NOT: Stil enjeksiyonu artik processor.py tarafindan build_system_prompt() ile yapiliyor.
    # Burada tekrar eklemeye gerek yok.

    extra_block = "\n".join(extra_instructions) if extra_instructions else ""

    final_system = f"{base_system}\n\n{identity_block}"
    if extra_block:
        final_system += f"\n\n{extra_block}"

    messages: list[dict[str, str]] = [{"role": "system", "content": final_system}]

    # History ekle
    _append_history(messages, history)

    # Kullanıcı mesajı
    user_content = _build_user_content(message, context)
    messages.append({"role": "user", "content": user_content})

    try:
        from app.chat.decider import _get_llm_generator
        from app.core.llm.generator import LLMRequest
        from app.core.llm.governance import governance

        # Governance'dan model zincirini al
        chain = governance.get_model_chain("synthesizer")
        answer_model = chain[0] if chain else "llama-3.3-70b-versatile"
        
        generator = _get_llm_generator()
        request = LLMRequest(
            role="answer",
            messages=messages,
            temperature=temperature,
            metadata={
                "override_model": answer_model,
                "system_prompt": None,  # sistem mesajı messages içinde
            },
        )

        result = await generator.generate(request)
        if not result.ok:
            return "😔 (Sistem) Yanıt üretilemedi. Lütfen tekrar dene."
        raw_answer = result.text

        # DEBUG LOG: LLM RAW RESPONSE
        logger.info("=" * 50)
        logger.info("LLM HAM YANIT BAŞLANGIÇ")
        logger.info("=" * 50)
        logger.info(f"Uzunluk: {len(raw_answer)}")
        logger.info(f"İlk 500 karakter:\n{repr(raw_answer[:500])}")
        logger.info(f"Kod bloğu var mı: {'```' in raw_answer}")

        # Kod bloğu başlangıçlarını bul
        code_starts = re.findall(r"```[^\n]*", raw_answer)
        logger.info(f"Kod bloğu başlangıçları: {code_starts}")

        logger.info("=" * 50)
        logger.info("LLM HAM YANIT BİTİŞ")
        logger.info("=" * 50)
        cleaned = _clean_thinking_block(raw_answer, strip=False)

        # Context for answer shaping
        shaper_context = {"user_message": message}
        if analysis and "persona" in analysis:
            shaper_context["persona"] = analysis["persona"]

        try:
            processed = full_post_process(cleaned, context=shaper_context)
        except Exception as e:
            logger.warning(f"[ANSWERER] full_post_process failed: {e}", exc_info=True)
            processed = cleaned  # Fallback to unprocessed

        final = enforce_model_identity("groq", processed)

        return final

    except Exception as e:
        logger.error(f"[ANSWERER] Hata: {e}", exc_info=True)
        return "⚠️ Bir hata oluştu. Lütfen daha sonra tekrar dene."


async def generate_answer_stream(
    message: str,
    analysis: dict[str, Any] | None = None,
    context: str | None = None,
    system_prompt: str | None = None,
    source: str | None = None,
    history: list[dict[str, str]] | None = None,
    style_profile: dict[str, Any] | None = None,
    images: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Groq API ile streaming yanıt üretir.

    Hibrit yaklaşım: Tüm cevap alınıp formatlanır,
    sonra kelime bazlı hızlı stream edilir.

    Args:
        message: Kullanıcı mesajı
        analysis: Semantic analiz sonuçları
        context: RAG/hafıza bağlamı
        system_prompt: Özel sistem prompt'u
        source: Yanıt kaynağı
        history: Sohbet geçmişi

    Yields:
        str: Yanıt parçaları
    """
    (
        get_settings,
        get_ai_identity,
        enforce_model_identity,
        full_post_process,
        full_post_process,
    ) = _get_imports()
    settings = get_settings()

    temperature = get_dynamic_temperature(analysis, style_profile)
    logger.debug(f"[ANSWERER_STREAM] Temperature: {temperature}")

    identity = get_ai_identity()
    identity_block = (
        f"KİMLİK: Adın {identity.display_name}. {identity.short_intro}\n"
        "GİZLİLİK: Sağlayıcı isimlerini (Google, Groq, Llama vb.) asla söyleme.\n"
    )

    base_system = system_prompt or "Sen yardımcı bir asistansın."

    extra_instructions = []
    if analysis:
        complexity = analysis.get("complexity", "medium")
        if complexity == "high" or analysis.get("requires_step_by_step", False):
            extra_instructions.append(
                "🧠 DÜŞÜNME TALİMATI: Bu karmaşık bir soru. Cevaplamadan önce problemi parçalara ayır ve adım adım çöz."
            )

    extra_block = "\n".join(extra_instructions) if extra_instructions else ""

    final_system = f"{base_system}\n\n{identity_block}"
    if extra_block:
        final_system += f"\n\n{extra_block}"

    messages: list[dict[str, str]] = [{"role": "system", "content": final_system}]
    _append_history(messages, history)

    user_content = _build_user_content(message, context)

    # -------------------------------------------------------------------------
    # GÖRSEL İŞLEME (VISION) VE MODEL SEÇİMİ
    # -------------------------------------------------------------------------

    from app.core.llm.governance import governance
    
    # Governance'dan model zincirini al
    chain = governance.get_model_chain("synthesizer")
    answer_model = chain[0] if chain else "llama-3.3-70b-versatile"
    is_vision_request = False

    if images and len(images) > 0:
        is_vision_request = True
        # Groq Llama 4 Vision Models (Dec 2025)
        # Scout: 17B (Faster, prioritized for testing)
        answer_model = "meta-llama/llama-4-scout-17b-16e-instruct"

        import base64
        import os

        # Multimodal içerik listesi
        content_list = [{"type": "text", "text": user_content}]

        for img_path in images:
            try:
                # Path'i absolute yap (veya data/uploads ekle)
                # user_routes'da "data/uploads/{user}/images/..." olarak dönüyor
                # Eğer full path değilse 'data/uploads' ekle
                real_path = img_path
                if not os.path.exists(real_path) and "uploads" in img_path:
                    # Belki relative path'tir?
                    real_path = os.path.join("data", "uploads", img_path.split("uploads/")[-1])
                elif not os.path.exists(real_path):
                    # Direkt data/uploads altına bak
                    real_path = os.path.join("data", "uploads", img_path)

                if os.path.exists(real_path):
                    with open(real_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        ext = os.path.splitext(real_path)[1].lower().replace(".", "")
                        if ext == "jpg":
                            ext = "jpeg"
                        mime_type = f"image/{ext}"

                        content_list.append(
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"}}
                        )
                else:
                    logger.warning(f"[VISION] Dosya bulunamadı: {real_path} (Raw: {img_path})")
            except Exception as e:
                logger.error(f"[VISION] Resim okuma hatası: {e}", exc_info=True)

        # Eğer görsel başarıyla eklendiyse multimodal mesaj yap
        if len(content_list) > 1:
            messages.append({"role": "user", "content": content_list})
        else:
            # Görsel okunamadıysa text devam et
            messages.append({"role": "user", "content": user_content})
    else:
        # Standart text mesajı
        messages.append({"role": "user", "content": user_content})

    try:
        from app.chat.streaming_buffer import StreamingBuffer
        from app.chat.decider import _get_llm_generator
        from app.core.llm.generator import LLMRequest

        generator = _get_llm_generator()

        async def safe_stream_generator():
            try:
                req = LLMRequest(
                    role="answer",
                    messages=messages,
                    temperature=temperature,
                    metadata={"override_model": answer_model},
                )
                internal_gen = generator.generate_stream(req)

                retry_needed = False
                async for chunk in internal_gen:
                    if is_vision_request and "[ERROR]" in chunk and "scout" in answer_model:
                        retry_needed = True
                        break
                    yield chunk

                if retry_needed:
                    logger.warning("[VISION] Scout Model Error! Switching to Maverick...", exc_info=True)
                    fallback_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
                    fallback_req = LLMRequest(
                        role="answer",
                        messages=messages,
                        temperature=temperature,
                        metadata={"override_model": fallback_model},
                    )
                    async for chunk in generator.generate_stream(fallback_req):
                        yield chunk

            except Exception as e:
                logger.error(f"[ANSWERER] Stream wrapper error: {e}", exc_info=True)
                yield f"⚠️ Stream hatası: {e}"

        chunk_source = cast(AsyncGenerator[str, None], safe_stream_generator())

        # 1. Tüm cevabı topla (memory-safe buffer ile)
        buffer = StreamingBuffer(max_chunks=1000)  # ~100KB max

        from app.chat.stream_manager import thinking_filter_async
        try:
            async for chunk in thinking_filter_async(chunk_source):
                buffer.append(chunk)

            # Finalize buffer (memory cleared automatically)
            full_response = buffer.finalize()
        finally:
            buffer.clear()  # Ensure cleanup

        # DEBUG LOG: LLM RAW RESPONSE (STREAM) - disabled for production
        # logger.debug(f"[ANSWERER_STREAM] Response length: {len(full_response)}")

        # 2. Post-processing
        # Context for answer shaping
        shaper_context = {"user_message": message}
        if analysis and "persona" in analysis:
            shaper_context["persona"] = analysis["persona"]

        processed_response = full_post_process(full_response, context=shaper_context)
        final_response = enforce_model_identity("groq", processed_response)

        # 3. Kelime bazlı stream
        words = final_response.split(" ")
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word

    except Exception as e:
        logger.error(f"[ANSWERER_STREAM] Hata: {e}", exc_info=True)
        yield "⚠️ Bir hata oluştu. Lütfen daha sonra tekrar dene."
