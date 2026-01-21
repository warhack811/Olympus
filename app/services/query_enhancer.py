"""
Query Enhancement Service
Kullanıcı sorgularını memory ve RAG araması için zenginleştirir.
"""

from __future__ import annotations

import logging

from app.chat.decider import call_groq_api_async
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

QUERY_ENHANCE_PROMPT = """
Sen bir ARAMA SORGUSU OPTİMİZÖRÜSÜN. Kullanıcının mesajını analiz et ve hafıza/veritabanı araması için en etkili sorguları üret.

KURALLAR:
1. Kullanıcı ne soruyorsa, o bilgiyi bulmak için 2-4 farklı arama sorgusu üret
2. Sorgular kısa ve öz olmalı (3-6 kelime)
3. Farklı perspektiflerden arama yap (eş anlamlı, ilişkili kavramlar)
4. Türkçe ve doğal dil kullan

ÖRNEK:
Mesaj: "Kedimin adı neydi?"
Sorgular: ["kedi adı", "evcil hayvan", "kullanıcı kedisi"]

Mesaj: "Geçen hafta ne konuşmuştuk?"
Sorgular: ["son sohbet", "geçen hafta konu", "önceki konuşma"]

JSON Formatı: {"queries": ["sorgu1", "sorgu2", "sorgu3"]}
""".strip()


async def enhance_query_for_search(
    user_message: str,
    max_queries: int = 3,
) -> list[str]:
    """
    Kullanıcı mesajından çoklu arama sorguları üretir.

    Args:
        user_message: Kullanıcının orijinal mesajı
        max_queries: Maksimum sorgu sayısı

    Returns:
        List of search queries (orijinal mesaj dahil)
    """
    from app.core.llm.governance import governance
    
    # Orijinal mesajı her zaman dahil et
    queries = [user_message.strip()]

    # Çok kısa mesajlar için LLM çağırma
    if len(user_message.strip()) < 10:
        return queries

    try:
        messages = [
            {"role": "system", "content": QUERY_ENHANCE_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Governance'dan hızlı model zincirini al
        chain = governance.get_model_chain("fast")
        fast_model = chain[0] if chain else "llama-3.1-8b-instant"

        import json

        content = await call_groq_api_async(
            messages=messages,
            json_mode=True,
            temperature=0.3,
            model=fast_model,
        )

        if content:
            data = json.loads(content)

            additional = []
            if isinstance(data, dict):
                additional = data.get("queries", [])
            elif isinstance(data, list):
                additional = data

            # Orijinal mesajı tekrar ekleme
            for q in additional:
                # q bazen list olabiliyor, string'e çevir
                if isinstance(q, list):
                    q = " ".join(str(x) for x in q)
                if not isinstance(q, str):
                    continue
                q = q.strip()
                if q and q.lower() != user_message.lower() and q not in queries:
                    queries.append(q)
                    if len(queries) >= max_queries + 1:  # +1 for original
                        break

            logger.debug(f"[QUERY_ENHANCE] {user_message[:50]} -> {queries}")

    except Exception as e:
        logger.warning(f"[QUERY_ENHANCE] Hata (fallback to original): {e}")

    return queries
