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
        logger.info(f"[PLUGIN] Registered: {plugin.name}")
    else:
        logger.warning("[PLUGIN] Plugin has no name attribute")


def get_plugin(name: str) -> Any | None:
    """Plugin'i isimle getir"""
    return _plugins.get(name)


def list_plugins() -> dict[str, Any]:
    """Tum plugin'leri listele"""
    return dict(_plugins)


def load_plugins() -> None:
    """Tum plugin'leri yukle"""
    logger.info("[PLUGIN] Loading plugins...")

    # Plugin loading started

    # Async Image Plugin
    try:
        from app.plugins.async_image.plugin import AsyncImagePlugin

        plugin = AsyncImagePlugin()
        register_plugin(plugin)
        logger.info(f"[PLUGIN] Loaded: async_image v{plugin.version}")
    except ImportError as e:
        logger.debug(f"[PLUGIN] async_image not available: {e}")
    except Exception as e:
        logger.error(f"[PLUGIN] Error loading async_image: {e}")

    # RAG v2 Plugin
    try:
        from app.plugins.rag_v2.plugin import RagV2Plugin

        plugin = RagV2Plugin()
        register_plugin(plugin)
        logger.info(f"[PLUGIN] Loaded: rag_v2 v{plugin.version}")
    except ImportError as e:
        logger.warning(f"[PLUGIN] rag_v2 not available: {e}")
    except Exception as e:
        logger.error(f"[PLUGIN] Error loading rag_v2: {e}")

    # Beautiful Response Plugin
    try:
        from app.plugins.beautiful_response.plugin import BeautifulResponsePlugin

        plugin = BeautifulResponsePlugin()
        register_plugin(plugin)
        logger.info(f"[PLUGIN] Loaded: beautiful_response v{plugin.version}")
    except ImportError as e:
        logger.warning(f"[PLUGIN] beautiful_response not available: {e}")
    except Exception as e:
        logger.error(f"[PLUGIN] Error loading beautiful_response: {e}")

    logger.info(f"[PLUGIN] Total loaded: {len(_plugins)} plugins")


# Auto-load plugins on import
try:
    load_plugins()
except Exception as e:
    logger.error(f"[PLUGIN] Failed to load plugins: {e}")
