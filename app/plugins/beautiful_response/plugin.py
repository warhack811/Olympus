"""
Beautiful Response Plugin - Main Module
Implements the PluginProtocol for integration with Mami AI.
"""

import logging
from typing import Any

from app.core.feature_flags import feature_enabled
from app.plugins.beautiful_response.config import BeautifulResponseConfig

logger = logging.getLogger(__name__)


class BeautifulResponsePlugin:
    """
    Platform Response Plugin

    AI yanıtlarını zenginleştirilmiş blok yapısına (structured blocks) dönüştürür.
    Frontend'in daha zengin bileşenler (Chart, Table, Kanban, vs.) render etmesini sağlar.
    """

    def __init__(self):
        self.name = "beautiful_response"
        self.version = "1.0.0"
        self.description = "Transforms AI responses into beautiful structured blocks"

        # Lazy loading için internal modüller burada tanımlanabilir
        self._processor = None

        logger.info(f"[{self.name.upper()}] Eklenti başlatıldı v{self.version}")

    def is_enabled(self) -> bool:
        """
        Plugin aktif mi kontrolü.
        Feature flag üzerinden kontrol edilir.
        """
        return feature_enabled(BeautifulResponseConfig.FEATURE_FLAG_KEY, default=False)

    def process_response(
        self, text: str, context: dict[str, Any] | None = None, options: dict[str, Any] | None = None
    ) -> str:
        """
        Model cevabını işler.

        Args:
            text: Ham model cevabı
            context: Bağlam (user_message, conversation_id, vb.)
            options: İşleme seçenekleri

        Returns:
            İşlenmiş cevap (şimdilik ham text)
        """
        if not self.is_enabled():
            return text

        try:
            # Parse response into blocks
            from app.plugins.beautiful_response.enhancer import enhance_response
            from app.plugins.beautiful_response.parser import parse_response

            # DEBUG LOG: Input - disabled for production
            # logger.debug(f"[BEAUTIFUL_RESPONSE] Input: {len(text)} chars")

            # 1. Parse -> Structured Blocks
            structured = parse_response(text)

            # 2. Enhance -> Clean Markdown
            enhanced_text = enhance_response(structured)

            # DEBUG LOG: Output - disabled for production
            # logger.debug(f"[BEAUTIFUL_RESPONSE] Output: {len(enhanced_text) if enhanced_text else 0} chars")

            if enhanced_text:
                return enhanced_text

            # If enhancement returned empty (unlikely if parser worked), fallback
            return text

        except Exception as e:
            logger.error(f"[{self.name.upper()}] Yanıt işleme hatası: {e}")
            return text

    def get_info(self) -> dict[str, Any]:
        """Plugin meta verilerini döndür"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.is_enabled(),
        }
