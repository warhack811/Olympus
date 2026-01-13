"""
Mami AI - Plugin Sistemi
========================

Plugin'ler istege bagli olarak yuklenebilir ve mevcut
ozellikleri genisletir veya yeni ozellikler ekler.

Aktif Pluginler:
    - response_enhancement: Cevap formatlama ve zenginlestirme
    - async_image: Asenkron gorsel uretimi
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Plugin registry
_plugins: dict[str, Any] = {}


@runtime_checkable
class PluginProtocol(Protocol):
    """Plugin arayuzu"""

    name: str
    version: str

    def is_enabled(self) -> bool: ...
    def process_response(self, text: str, context: dict | None = None, options: dict | None = None) -> str: ...


def register_plugin(plugin: Any) -> None:
    """Plugin'i sisteme kaydet"""
    if hasattr(plugin, "name"):
        _plugins[plugin.name] = plugin
        logger.info(f"[EKLENTİ] Kaydedildi: {plugin.name}")
    else:
        logger.warning("[EKLENTİ] Eklentinin 'name' özniteliği bulunamadı")


def get_plugin(name: str) -> Any | None:
    """Plugin'i isimle getir"""
    return _plugins.get(name)


def list_plugins() -> dict[str, Any]:
    """Tum plugin'leri listele"""
    return dict(_plugins)


def load_plugins() -> None:
    """Tum plugin'leri yukle"""
    logger.info("[EKLENTİ] Eklentiler yükleniyor...")

    # Eklenti yükleme başlatıldı

    # Async Image Plugin
    try:
        from app.plugins.async_image.plugin import AsyncImagePlugin

        plugin = AsyncImagePlugin()
        register_plugin(plugin)
        logger.info(f"[EKLENTİ] Yüklendi: async_image v{plugin.version}")
    except ImportError as e:
        logger.debug(f"[EKLENTİ] async_image ulaşılamaz durumda: {e}")
    except Exception as e:
        logger.error(f"[EKLENTİ] async_image yükleme hatası: {e}")

    # RAG v2 Plugin
    try:
        from app.plugins.rag_v2.plugin import RagV2Plugin

        plugin = RagV2Plugin()
        register_plugin(plugin)
        logger.info(f"[EKLENTİ] Yüklendi: rag_v2 v{plugin.version}")
    except ImportError as e:
        logger.warning(f"[EKLENTİ] rag_v2 ulaşılamaz durumda: {e}")
    except Exception as e:
        logger.error(f"[EKLENTİ] rag_v2 yükleme hatası: {e}")

    # Beautiful Response Plugin
    try:
        from app.plugins.beautiful_response.plugin import BeautifulResponsePlugin

        plugin = BeautifulResponsePlugin()
        register_plugin(plugin)
        logger.info(f"[EKLENTİ] Yüklendi: beautiful_response v{plugin.version}")
    except ImportError as e:
        logger.warning(f"[EKLENTİ] beautiful_response ulaşılamaz durumda: {e}")
    except Exception as e:
        logger.error(f"[EKLENTİ] beautiful_response yükleme hatası: {e}")

    logger.info(f"[EKLENTİ] Toplam yüklenen: {len(_plugins)} eklenti")


# Import sırasında otomatik yükle
try:
    load_plugins()
except Exception as e:
    logger.error(f"[EKLENTİ] Eklentiler yüklenemedi: {e}")
