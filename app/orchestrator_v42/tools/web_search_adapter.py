import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.tools.web_search")

async def web_search(query: str, timeout_s: float) -> Dict[str, Any]:
    """
    Gerçek web araması yapar (Legacy Search Manager üzerinden).
    Fail-soft prensibiyle çalışır.
    
    Args:
        query: Arama sorgusu.
        timeout_s: Zaman aşımı süresi (saniye).
        
    Returns:
        Dict: {
            "results": [{"title": str, "snippet": str, "url": str}],
            "notes": str
        }
    """
    try:
        # Legacy search function import (Lazy)
        try:
            from app.search.manager import search_queries_async
        except ImportError:
            return {"results": [], "notes": "Arama servisi import edilemedi."}

        # Sorgu formatı: List[Dict[str, str]]
        # ID vererek dönen dict'ten kolayca alabiliriz
        query_payload = [{"id": "q1", "query": query}]
        
        # Async çağrıyı timeout ile sar
        # search_queries_async zaten async tanımlı
        # Dict[str, List[SearchSnippet]] döner
        
        # Not: search_queries_async içinde zaten httpx timeout var ama 
        # biz Orchestrator bütçesine uymak için dışarıdan da timeout koymalıyız.
        
        search_res = await asyncio.wait_for(
            search_queries_async(query_payload),
            timeout=timeout_s
        )
        
        snippets = search_res.get("q1", [])
        
        results_list = []
        for snip in snippets[:5]: # Max 5 sonuç
            # Snippet objesinden güvenli veri çekme
            title = getattr(snip, "title", "Başlıksız") or "Başlıksız"
            url = getattr(snip, "url", "") or ""
            snippet_text = getattr(snip, "snippet", "") or ""
            
            # Uzun metinleri ve URL'leri kırp (Güvenlik)
            if len(snippet_text) > 300:
                snippet_text = snippet_text[:297] + "..."
            if len(title) > 300:
                title = title[:297] + "..."
            if len(url) > 300:
                url = url[:297] + "..."
                
            results_list.append({
                "title": title,
                "url": url,
                "snippet": snippet_text
            })
            
        return {
            "results": results_list,
            "notes": f"{len(results_list)} sonuç bulundu."
        }
        
    except asyncio.TimeoutError:
        logger.warning(f"Web arama zaman aşımı ({timeout_s}s)")
        return {
            "results": [],
            "notes": "Arama zaman aşımına uğradı."
        }
    except Exception as e:
        logger.error(f"Web arama hatası: {e}")
        return {
            "results": [],
            "notes": f"Web arama hatası: {str(e)}"
        }
