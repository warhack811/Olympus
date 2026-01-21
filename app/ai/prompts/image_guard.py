"""
Image prompt guard (policy vs style split).

- sanitize_user_content: yalnız policy/unsafe/injection temizliği
- validate_style_tokens: allowlist filtresi (style/quality tokenları burada yönetilir)
- sanitize_image_prompt: deprecated wrapper (backward compat)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Tuple

from app.ai.prompts.image_style_allowlist import get_allowed_style_tokens



logger = logging.getLogger(__name__)


def _normalize_for_search(text: str) -> str:
    return text.lower().strip()


def sanitize_user_content(text: str) -> Tuple[str, list[str]]:
    """
    Policy/unsafe/injection temizlik. Style/quality tokenlarına dokunmaz.
    """
    if not text:
        return text, []

    removed: list[str] = []
    cleaned = re.sub(r"<[^>]+>", " ", text)
    if cleaned != text:
        removed.append("html_tag")

    patterns = [
        r"(?:rm\s+-rf\s+/)",
        r"(?:bash\s+-c)",
        r"(?:powershell\s+-Command)",
    ]
    for pat in patterns:
        if re.search(pat, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
            removed.append(pat)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, removed


def validate_style_tokens(tokens: Iterable[str]) -> tuple[list[str], list[str]]:
    """
    Allowlist filtresi. case-insensitive, stable order.
    """
    allowed_set = get_allowed_style_tokens()
    allowed: list[str] = []
    dropped: list[str] = []
    seen: set[str] = set()
    for token in tokens or []:
        if not token:
            continue
        key = token.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        if key in allowed_set:
            allowed.append(token.strip())
        else:
            dropped.append(token.strip())
    return allowed, dropped


def final_check(prompt: str) -> str:
    """
    Ek güvenlik için hafif regex kontrolü; prompt’u değiştirmez, sadece loglar.
    """
    dangerous = [r"\b(base64|BEGIN RSA)\b"]
    for pat in dangerous:
        if re.search(pat, prompt, flags=re.IGNORECASE):
            logger.warning("[IMAGE_GUARD] Dangerous pattern detected, pattern=%s", pat)
    return prompt



