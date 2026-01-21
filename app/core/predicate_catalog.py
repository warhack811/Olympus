import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)

# Keep file ASCII-only: use unicode escapes for Turkish chars.
_TURKISH_NORMALIZE_MAP = str.maketrans(
    "\u00c7\u011e\u0130\u00d6\u015e\u00dc\u00e7\u011f\u0131\u00f6\u015f\u00fc",
    "CGIOSUcgiosu",
)


def normalize_predicate(value: str) -> str:
    if not value:
        return ""
    cleaned = value.strip().upper().replace(" ", "_").replace("-", "_")
    cleaned = cleaned.translate(_TURKISH_NORMALIZE_MAP)
    cleaned = re.sub(r"[^A-Z0-9_]", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


@dataclass(frozen=True)
class PredicateMeta:
    key: str
    canonical: str
    aliases: List[str]
    category: str
    predicate_type: str
    durability: str
    enabled: bool


class PredicateCatalog:
    def __init__(self, catalog_data: Dict[str, Dict[str, object]], groups: Optional[Dict[str, Set[str]]] = None):
        self.by_key: Dict[str, Dict[str, object]] = catalog_data
        self.alias_map: Dict[str, str] = {}
        self.groups = groups or {}
        self._build_alias_map()

    def _build_alias_map(self) -> None:
        for key, entry in self.by_key.items():
            normalized_key = normalize_predicate(key)
            self.alias_map[normalized_key] = key

            canonical = str(entry.get("canonical", key))
            normalized_canonical = normalize_predicate(canonical)
            self.alias_map[normalized_canonical] = key

            for alias in entry.get("aliases", []) or []:
                normalized_alias = normalize_predicate(str(alias))
                if normalized_alias:
                    self.alias_map[normalized_alias] = key

        logger.info("Predicate catalog loaded: %s predicates, %s mappings", len(self.by_key), len(self.alias_map))

    def resolve_predicate(self, raw_predicate: str) -> Optional[str]:
        normalized = normalize_predicate(raw_predicate)
        return self.alias_map.get(normalized)

    def canonicalize(self, raw_predicate: str, allow_unknown: bool = True) -> Optional[str]:
        resolved = self.resolve_predicate(raw_predicate)
        if resolved:
            return resolved
        return normalize_predicate(raw_predicate) if allow_unknown else None

    def get_entry(self, raw_or_key: str) -> Optional[Dict[str, object]]:
        if not raw_or_key:
            return None
        key = self.resolve_predicate(raw_or_key) or normalize_predicate(raw_or_key)
        return self.by_key.get(key)

    def is_enabled(self, raw_or_key: str) -> bool:
        entry = self.get_entry(raw_or_key)
        if entry is None:
            return True
        return bool(entry.get("enabled", True))

    def get_meta(self, raw_or_key: str) -> Optional[PredicateMeta]:
        entry = self.get_entry(raw_or_key)
        if not entry:
            return None
        key = self.resolve_predicate(raw_or_key) or normalize_predicate(raw_or_key)
        return PredicateMeta(
            key=key,
            canonical=str(entry.get("canonical", key)),
            aliases=[str(a) for a in entry.get("aliases", []) or []],
            category=str(entry.get("category", "general")),
            predicate_type=str(entry.get("type", "ADDITIVE")),
            durability=str(entry.get("durability", "LONG_TERM")),
            enabled=bool(entry.get("enabled", True)),
        )

    def get_predicates_by_group(self, group: str, include_aliases: bool = False) -> List[str]:
        group_key = (group or "general").lower()
        categories = self.groups.get(group_key, {group_key})
        return self._collect_predicates(categories, include_aliases)

    def get_predicates_by_category(self, category: str, include_aliases: bool = False) -> List[str]:
        return self._collect_predicates({(category or "general").lower()}, include_aliases)

    def _collect_predicates(self, categories: Iterable[str], include_aliases: bool) -> List[str]:
        categories_lower = {c.lower() for c in categories}
        results: List[str] = []
        for key, entry in self.by_key.items():
            if not bool(entry.get("enabled", True)):
                continue
            entry_category = str(entry.get("category", "general")).lower()
            if entry_category not in categories_lower:
                continue
            canonical = str(entry.get("canonical", key))
            results.append(canonical)
            if include_aliases:
                results.extend([str(a) for a in entry.get("aliases", []) or []])

        # Deduplicate while preserving order
        seen = set()
        unique_results = []
        for item in results:
            if item and item not in seen:
                seen.add(item)
                unique_results.append(item)
        return unique_results


_DEFAULT_GROUPS: Dict[str, Set[str]] = {
    "identity": {"identity"},
    "hard_facts": {"preference", "relationship", "experience", "goal", "ownership", "location"},
    "soft_signals": {"state", "emotion", "temporal"},
    "preference": {"preference"},
    "relationship": {"relationship"},
    "experience": {"experience"},
    "goal": {"goal"},
    "state": {"state"},
    "location": {"location"},
}

_CATALOG_INSTANCE: Optional[PredicateCatalog] = None


def get_catalog() -> Optional[PredicateCatalog]:
    global _CATALOG_INSTANCE
    if _CATALOG_INSTANCE is not None:
        return _CATALOG_INSTANCE

    catalog_path = Path(__file__).with_name("predicate_catalog.yml")
    if not catalog_path.exists():
        logger.warning("Predicate catalog not found at %s (fail-open).", catalog_path)
        return None

    try:
        with catalog_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.error("Predicate catalog YAML invalid: %s", catalog_path)
            return None
        if "predicates" in data and isinstance(data["predicates"], dict):
            data = data["predicates"]
        _CATALOG_INSTANCE = PredicateCatalog(data, groups=_DEFAULT_GROUPS)
        return _CATALOG_INSTANCE
    except Exception as exc:
        logger.error("Predicate catalog load failed: %s", exc)
        return None


def canonicalize_predicate(raw_predicate: str, allow_unknown: bool = True) -> Optional[str]:
    catalog = get_catalog()
    if catalog:
        return catalog.canonicalize(raw_predicate, allow_unknown=allow_unknown)
    return normalize_predicate(raw_predicate) if allow_unknown else None
