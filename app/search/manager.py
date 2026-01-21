from __future__ import annotations

from app.search.models import SearchQuery, SearchSnippet
from typing import Any

import asyncio
import httpx

from app.config import get_settings
from app.core.logger import get_logger
from app.search.providers.serper import SerperResult, serper_search_async  # Google
from app.search.structured_parser import (
    parse_weather_result, parse_exchange_rate_result, 
    parse_standings_result, parse_sports_fixture_result
)

logger = get_logger(__name__)
settings = get_settings()


# =============================================================================
# SCOUT SUMMARIZATION PROMPT
# =============================================================================
SCOUT_SUMMARIZE_PROMPT = """Sen bir arama sonucu özetleyicisisin. Aşağıdaki web arama sonuçlarını analiz et ve kullanıcının sorusuna yanıt verecek şekilde özetle.

KULLANICI SORUSU: {query}

ARAMA SONUÇLARI:
{snippets}

TALİMATLAR:
1. ÖNEMLİ bilgileri KORU - tarihleri, sayıları, isimleri atma.
2. GEREKSIZ detayları at - reklamlar, tekrarlayan bilgiler, alakasız içerik.
3. ÇELİŞKİLERİ BELIRT ama ÇÖZME - "Kaynak A'ya göre X, ancak Kaynak B'ye göre Y" şeklinde yaz.
4. KAYNAK SAYISINI belirt - "3 kaynağa göre..."
5. Maksimum 3-4 paragraf olsun.
6. Türkçe yaz.

ÖZET:"""


def _convert_serper_results(results: list[SerperResult]) -> list[SearchSnippet]:
    return [SearchSnippet(title=r.title, url=r.url, snippet=r.snippet) for r in results]


async def _summarize_with_scout(query: str, all_snippets: list[SearchSnippet]) -> str:
    """
    Scout modeli kullanarak arama sonuçlarını özetler.
    Önemli bilgileri korur, çelişkileri belirtir ama çözmez.
    """
    if not all_snippets:
        return ""
    
    # Snippet'leri metin formatına çevir
    snippets_text = ""
    for i, s in enumerate(all_snippets, 1):
        snippets_text += f"[{i}] {s.title}\n{s.snippet}\nKaynak: {s.url}\n\n"
    
    prompt = SCOUT_SUMMARIZE_PROMPT.format(query=query, snippets=snippets_text)
    
    try:
        from app.core.llm.generator import LLMGenerator, LLMRequest
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        generator = LLMGenerator()
        # Register providers locally for search manager service
        if "groq" not in generator.providers:
            generator.register_provider("groq", groq_adapter)
        if "gemini" not in generator.providers:
            generator.register_provider("gemini", gemini_adapter)

        request = LLMRequest(
            role="search",
            prompt=prompt,
            temperature=0.3,
            max_tokens=1024
        )
        
        result = await generator.generate(request)
        
        if result.ok:
            logger.info(f"[SEARCH_SUMMARIZE] Summary generated using {result.model}: {len(result.text)} chars")
            return result.text.strip()
        else:
            logger.error(f"[SEARCH_SUMMARIZE] Generation failed: {result.text}")
            return snippets_text
        
    except Exception as e:
        logger.error(f"[SEARCH_SUMMARIZE] Scout summarization failed: {e}")
        # Fallback: Ham snippet'leri döndür
        return snippets_text


async def search_queries_async(
    query_items: list[dict[str, str]],
    summarize: bool = True
) -> dict[str, Any]:
    """
    Decider'dan gelen sorguları asenkron işler.
    Sistem sadece Serper (Google) provider'ını kullanır.
    
    Args:
        query_items: Arama sorguları listesi
        summarize: True ise Scout ile özetleme yapar (varsayılan: True)
    """
    queries: list[SearchQuery] = []
    for idx, q in enumerate(query_items):
        queries.append(
            SearchQuery(
                id=q.get("id", f"q{idx + 1}"),
                query=q.get("query", ""),
            )
        )

    results: dict[str, Any] = {}
    all_collected_snippets: list[SearchSnippet] = []
    original_query = query_items[0].get("query", "") if query_items else ""

    timeout = httpx.Timeout(8.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Paralel yürütme için coroutine listesi oluştur
        search_tasks = []
        task_info = []

        for q in queries:
            if not q.query:
                results[q.id] = []
                continue

            # Freshness parametresini ayıkla (params içinden gelebilir)
            freshness = None
            for item in query_items:
                if item.get("id") == q.id:
                    freshness = item.get("freshness")
                    break

            logger.info(f"[SEARCH] query_id={q.id} query={q.query!r} freshness={freshness}")
            
            search_tasks.append(serper_search_async(q.query, max_results=6, client=client, freshness=freshness))
            task_info.append(q)

        # Hepsini aynı anda çalıştır
        all_serper_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for i, serper_results in enumerate(all_serper_results):
            q = task_info[i]
            
            if isinstance(serper_results, Exception):
                logger.error(f"[SEARCH] Task {q.id} failed: {serper_results}")
                results[q.id] = []
                continue

            snippets = _convert_serper_results(serper_results)
            all_collected_snippets.extend(snippets)
            
            # --- STRUCTURED PARSING (ADVANCED) ---
            # Hava durumu, döviz vb. için özel parserları dene
            structured_data = (
                parse_weather_result(snippets) or 
                parse_exchange_rate_result(snippets, "USD", "TRY") or # Örnek kurlar
                parse_sports_fixture_result(snippets, q.query)
            )

            results[q.id] = {
                "snippets": snippets,
                "structured_data": structured_data,
                "count": len(snippets)
            }

    # --- SCOUT SUMMARIZATION ---
    if summarize and all_collected_snippets:
        summary = await _summarize_with_scout(original_query, all_collected_snippets)
        results["_summary"] = summary
        results["_total_snippets"] = len(all_collected_snippets)
        logger.info(f"[SEARCH] Total snippets: {len(all_collected_snippets)}, Summary ready")

    return results
