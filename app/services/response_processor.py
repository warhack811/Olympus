"""
Response Post-Processing Service
Plugin sistemi ile çalışır - app/plugins/response_enhancement
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def post_process_response(text: str) -> str:
    """Basit temizlik işlemleri"""
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    # DANGEROUS: re.sub(r'[ \t]+', ' ', text) breaks code indentation!
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)

    return text


def clean_thinking_blocks(text: str) -> str:
    """Thinking bloklarını temizle"""
    if not text:
        return ""

    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"^.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)

    return text.strip()


def format_code_blocks(text: str) -> str:
    """Kod bloklarını düzelt"""
    if not text:
        return ""

    # [CODE_BLOCK_{}] placeholder'larını düzelt
    # Model bazen bu placeholder formatını kullanıyor, bunları gerçek kod bloklarına çevir
    placeholder_pattern = r"\[CODE_BLOCK_\{?\}?\]"
    if re.search(placeholder_pattern, text):
        # Placeholder'ı kaldır ve uyarı ver
        text = re.sub(placeholder_pattern, "", text)
        logger.warning("[CODE_BLOCK] Placeholder bulundu ve kaldırıldı - model markdown formatını kullanmalı")

    # Eksik kod bloğu kapanışlarını düzelt
    code_block_count = text.count("```")
    if code_block_count % 2 != 0:
        text = text + "\n```"
        logger.warning("[CODE_BLOCK] Eksik kapanış bulundu ve eklendi")

    return text


def full_post_process(text: str, options: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> str:
    """
    Response Enhancement Plugin ile tam işleme.

    Args:
        text: Ham model cevabı
        options: İşleme seçenekleri (preset: minimal/normal/rich)
        context: Bağlam (user_message, persona, vb.)

    Returns:
        İşlenmiş cevap
    """
    if not text:
        return ""

    from app.plugins import get_plugin

    # Temel temizlik
    text = clean_thinking_blocks(text)
    text = post_process_response(text)

    # Beautiful Response Plugin (Primary Enhancer)
    beautiful_plugin = get_plugin("beautiful_response")

    if beautiful_plugin and beautiful_plugin.is_enabled():
        try:
            prev_len = len(text)
            text = beautiful_plugin.process_response(text=text, context=context, options=options)
            logger.info(f"[POST_PROCESS] Beautiful Response: {prev_len} -> {len(text)} chars")
        except Exception as e:
            logger.error(f"[POST_PROCESS] Beautiful Response failed: {e}")
    else:
        # Fallback to simple formatting if plugin is disabled
        logger.debug("[POST_PROCESS] Beautiful Response not enabled, using basic formatting")
        text = format_code_blocks(text)

    # Final debug logging (disabled for production)
    # logger.debug(f"[POST_PROCESS] Final output: {len(text)} chars")
    return text


def get_preset_config(preset: str = "professional") -> dict[str, Any]:
    """
    Preset konfigürasyonları

    Args:
        preset: 'minimal', 'normal', 'rich', 'professional'

    Returns:
        Config dict
    """
    presets = {
        "minimal": {
            "format_level": "minimal",
        },
        "normal": {
            "format_level": "normal",
        },
        "rich": {
            "format_level": "rich",
        },
        "professional": {
            "format_level": "professional",
        },
    }

    return presets.get(preset, presets["professional"])
