"""
Central allowlist for image style/preset tokens.

Kaynaklar:
- style_profile mapping (processor.py içindeki image_style/image_lighting vb.)
- image_settings.defaultStyle seçenekleri (frontend imageSettings)

Bu modül hem guard hem de prompt builder tarafından paylaşılarak
hardcode tekrarını önler.
"""

from __future__ import annotations

from typing import Iterable, Set

# Style profile mapping’te kullanılan ekler
STYLE_PROFILE_TOKENS = {
    # image_style mappings
    "photorealistic",
    "raw photo",
    "cinematic lighting",
    "anime style",
    "studio ghibli style",
    "vibrant colors",
    "digital art",
    "concept art",
    "trending on artstation",
    "oil painting",
    "canvas texture",
    "classic art style",
    "3d render",
    "unreal engine 5",
    "octane render",
    # lighting
    "dramatic cinematographic lighting",
    "dramatic lighting",
    "studio lighting",
    "soft natural lighting",
    # safety framing
    "balanced framing",
}

# image_settings.defaultStyle seçenekleri
DEFAULT_STYLE_TOKENS = {
    # realistic
    "photorealistic",
    "raw photo",
    "cinematic lighting",
    # anime
    "anime style",
    "vibrant colors",
    "cel shading",
    # artistic
    "digital art",
    "concept art",
    # 3d
    "3d render",
    "unreal engine 5",
    "octane render",
    # sketch
    "pencil sketch",
    "hand drawn",
    "line art",
    # pixel
    "pixel art",
    "16-bit",
    "retro game style",
    "pixelated",
}


def get_allowed_style_tokens(extra: Iterable[str] | None = None) -> Set[str]:
    """
    Allowlist’i tek noktadan üretir; guard ve builder paylaşır.
    """
    tokens = set(STYLE_PROFILE_TOKENS) | set(DEFAULT_STYLE_TOKENS)
    if extra:
        tokens |= {t for t in extra if t}
    # normalize lowercase; dedupe by lower
    normalized = set()
    for t in tokens:
        if t:
            normalized.add(t.strip().lower())
    return normalized

