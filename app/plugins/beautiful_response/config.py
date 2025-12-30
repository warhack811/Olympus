"""
Beautiful Response Plugin - Configuration
"""

from typing import Any


class BeautifulResponseConfig:
    """Plugin konfigürasyonu"""

    FEATURE_FLAG_KEY = "beautiful_response_enabled"

    @classmethod
    def get_defaults(cls) -> dict[str, Any]:
        return {"enabled": False, "version": "1.0.0"}
