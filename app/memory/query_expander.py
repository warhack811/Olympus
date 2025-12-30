"""
Mami AI - Query Expander
========================

Expands search queries with synonyms and variations for better RAG retrieval.
Uses a local Turkish dictionary - no external API calls.
"""

import re

# Turkish legal synonyms dictionary
TURKISH_SYNONYMS = {
    # Suç tipleri
    "dolandırıcılık": ["hile", "aldatma", "aldatıcı davranış", "hileli davranış"],
    "hırsızlık": ["çalma", "gasp", "yağma", "mal kaçırma"],
    "gasp": ["yağma", "zorla alma", "gasıp"],
    "tehdit": ["korkutma", "gözdağı", "yıldırma"],
    "şantaj": ["tehdit", "zorla para alma"],
    "sahtecilik": ["evrak sahteciliği", "belge sahteciliği", "taklit"],
    "rüşvet": ["irtikap", "zimmet", "yolsuzluk"],
    "cinsel taciz": ["taciz", "cinsel istismar", "sarkıntılık"],
    "kasten öldürme": ["cinayet", "adam öldürme", "katil", "katletme"],
    "yaralama": ["darp", "müessir fiil", "eziyet"],
    # Ceza terimleri
    "hapis": ["hapis cezası", "mahkumiyet", "tutukluluk"],
    "para cezası": ["adli para cezası", "idari para cezası"],
    "ceza": ["yaptırım", "müeyyide", "cezai yaptırım"],
    # Genel terimler
    "suç": ["suç işleme", "cürüm", "kabahat"],
    "sanık": ["fail", "suçlu", "zanlı"],
    "mağdur": ["kurban", "zarar gören"],
    "mahkeme": ["yargı", "adliye", "yargılama"],
    # Kısaltmalar
    "tck": ["türk ceza kanunu", "ceza kanunu"],
    "cmk": ["ceza muhakemesi kanunu"],
    "tmk": ["türk medeni kanunu", "medeni kanun"],
}

# Article number patterns
ARTICLE_PATTERNS = [
    (r"tck\s*(\d+)", ["tck {0}", "madde {0}", "{0}. madde"]),
    (r"madde\s*(\d+)", ["madde {0}", "{0}. madde", "tck {0}"]),
    (r"(\d+)\.\s*madde", ["{0}. madde", "madde {0}"]),
]


def expand_query(query: str, max_expansions: int = 5) -> list[str]:
    """
    Expand a query with synonyms and variations.

    Args:
        query: Original search query
        max_expansions: Maximum number of expanded queries to return

    Returns:
        List of expanded queries (original + variations)
    """
    query_lower = query.lower().strip()
    expanded: set[str] = {query}  # Always include original

    # 1. Synonym expansion
    for term, synonyms in TURKISH_SYNONYMS.items():
        if term in query_lower:
            for syn in synonyms[:2]:  # Limit synonyms per term
                expanded.add(query_lower.replace(term, syn))

    # 2. Article number normalization
    for pattern, templates in ARTICLE_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            article_num = match.group(1)
            for template in templates:
                expanded.add(template.format(article_num))

    # 3. Add just the numbers if present (for direct article lookup)
    numbers = re.findall(r"\b(\d+)\b", query)
    for num in numbers:
        expanded.add(num)
        expanded.add(f"madde {num}")

    # Convert to list and limit
    result = list(expanded)[:max_expansions]

    return result


def normalize_article_query(query: str) -> str:
    """
    Normalize article-style queries for better matching.
    e.g., "TCK 157" -> "madde 157"
    """
    query_lower = query.lower().strip()

    # Remove common prefixes
    query_lower = re.sub(r"^(tck|cmk|hmk|tmk)\s*", "", query_lower)

    # Ensure "madde X" format
    match = re.search(r"(\d+)", query_lower)
    if match and "madde" not in query_lower:
        return f"madde {match.group(1)}"

    return query_lower


def get_search_queries(query: str, max_queries: int = 4) -> list[str]:
    """
    Get all search queries for RAG retrieval.
    Combines expansion and normalization.

    Args:
        query: Original user query
        max_queries: Maximum queries to return

    Returns:
        List of queries to search
    """
    queries = set()

    # Original query
    queries.add(query)

    # Normalized version
    normalized = normalize_article_query(query)
    if normalized != query.lower():
        queries.add(normalized)

    # Expanded versions
    expanded = expand_query(query, max_expansions=max_queries)
    queries.update(expanded)

    return list(queries)[:max_queries]
