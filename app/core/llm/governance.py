"""
Model governance katmanı.

- Rol bazlı model zincirleri (birincil + fallback)
- Sağlayıcı tespiti (groq/gemini vb.)
- Env/config üzerindeki model override'larını destekler.
- Model tanımları: app/core/constants.py MODEL_GOVERNANCE (TEK KAYNAK)
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

from app.config import get_settings
from app.core.constants import MODEL_GOVERNANCE

logger = logging.getLogger("app.core.llm.governance")


class ModelGovernance:
    """Rol bazlı model zinciri yönetimi."""

    def __init__(self) -> None:
        # Model tanımları constants.py'den alınır (TEK KAYNAK)
        pass

    def _build_from_settings(self) -> Dict[str, List[str]]:
        """Config zincirleri oluşturur (her çağrıda güncel env için)."""
        config_chains: Dict[str, List[str]] = {}
        try:
            settings = get_settings()
            raw = getattr(settings, "ROLE_MODEL_CHAINS", {}) or {}
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, dict):
                for role, chain in raw.items():
                    if isinstance(chain, list):
                        config_chains[role] = [str(m) for m in chain if m]
        except Exception as exc:  # noqa: BLE001
            logger.warning("ROLE_MODEL_CHAINS parse failed: %s", exc)

        # Sıra: constants.py (MASTER) -> config zincirleri (override)
        merged = {**MODEL_GOVERNANCE, **config_chains}
        for role, chain in merged.items():
            merged[role] = self._dedup(chain)
        return merged

    @staticmethod
    def _dedup(chain: List[str]) -> List[str]:
        seen = set()
        deduped = []
        for model in chain:
            if not model or model in seen:
                continue
            seen.add(model)
            deduped.append(model)
        return deduped

    def get_model_chain(self, role: str) -> List[str]:
        """Role göre (env + statik) model listesi döner."""
        merged = self._build_from_settings()
        chain = merged.get(role, merged.get("logic", []))  # 'logic' varsayılan uzman
        if not chain:
            logger.warning("Governance zinciri boş (role=%s)", role)
        return chain

    def with_override(self, role: str, override_model: str | None) -> List[str]:
        """
        Override modeli varsa başa ekler, yoksa standard zinciri döner.
        """
        chain = self.get_model_chain(role)
        if not override_model:
            return chain
        return self._dedup([override_model] + chain)

    @staticmethod
    def detect_provider(model_id: str | None) -> str:
        """Model adına göre sağlayıcıyı belirler (groq varsayılan)."""
        if not model_id:
            return "groq"
        mid = model_id.lower()
        if any(token in mid for token in ("gemini", "google")):
            return "gemini"
        if "openai" in mid:
            return "groq"
        return "groq"


# Tekil instance
governance = ModelGovernance()
