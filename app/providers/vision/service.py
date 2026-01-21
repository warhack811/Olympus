"""
Mami AI - Vision Service (Atlas Sovereign Edition)
-------------------------------------------------
Görsel analiz motoru - Gemini 2.0 Flash ile resim betimleme.

Temel Sorumluluklar:
1. Görsel Analizi: JPEG/PNG formatındaki görselleri metne dökme
2. Kota Yönetimi: 429 hatalarında exponential backoff
3. Güvenli Geri Dönüş: Hata durumunda akışı kırmadan mesaj döndürme
"""

import asyncio
import logging
from typing import Optional

from app.config import get_settings
from app.core.prompts import VISION_SYSTEM_PROMPT
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Gemini 2.0 Flash modelini kullanarak görseli analiz eder.
    
    Args:
        image_bytes: Görsel verisi (bytes)
        mime_type: MIME tipi (default: image/jpeg)
    
    Returns:
        Görsel betimleme metni veya hata mesajı
    """
    max_retries = 3
    retry_delay = 2
    
    settings = get_settings()
    gemini_keys = settings.get_gemini_api_keys()
    
    if not gemini_keys:
        logger.warning("[VisionService] No Gemini API key available")
        return "Görsel analiz edilemedi (API anahtarı eksik)."
    
    # Telemetry start
    telemetry.emit(
        EventType.TOOL_EXECUTION,
        {"tool": "vision_engine", "status": "start", "size_bytes": len(image_bytes)},
        component="vision"
    )
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_keys[0])
        
        for attempt in range(max_retries):
            try:
                # Image part
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )
                
                # Vision analysis
                response = await client.aio.models.generate_content(
                    model=settings.VISION_MODEL,
                    contents=[VISION_SYSTEM_PROMPT, image_part]
                )
                
                if not response or not response.text:
                    return "Görsel analiz edilemedi veya boş yanıt döndü."
                
                # Telemetry success
                telemetry.emit(
                    EventType.TOOL_EXECUTION,
                    {"tool": "vision_engine", "status": "success", "attempt": attempt + 1},
                    component="vision"
                )
                
                return response.text.strip()
                
            except Exception as e:
                error_str = str(e).lower()
                if "resourceexhausted" in error_str or "429" in error_str:
                    logger.warning(
                        f"[VisionService] 429 (Attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {retry_delay}s..."
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        telemetry.emit(
                            EventType.TOOL_EXECUTION,
                            {"tool": "vision_engine", "status": "error", "error": "quota_exhausted"},
                            component="vision"
                        )
                        return "Görsel analiz edilemedi (Sistem Yoğunluğu). Lütfen tekrar deneyin."
                else:
                    logger.error(f"[VisionService] Error: {e}")
                    telemetry.emit(
                        EventType.TOOL_EXECUTION,
                        {"tool": "vision_engine", "status": "error", "error": str(e)},
                        component="vision"
                    )
                    return f"Görsel analiz hatası: {str(e)}"
        
    except ImportError:
        logger.error("[VisionService] google-genai package not installed")
        return "Görsel analiz edilemedi (SDK eksik)."
    except Exception as e:
        logger.error(f"[VisionService] Unexpected error: {e}")
        return "Görsel analiz edilemedi (Beklenmeyen hata)."
    
    return "Görsel analiz edilemedi."


class VisionService:
    """Vision Service singleton wrapper."""
    
    @staticmethod
    async def analyze(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        return await analyze_image(image_bytes, mime_type)


vision_service = VisionService()
