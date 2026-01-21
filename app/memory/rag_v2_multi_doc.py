"""
RAG v2 Multi-Document Summarization
====================================

Handles multi-document queries and generates comparative summaries.

Example queries:
- "sözleşme A ve B ücret farkı"
- "tüm raporlardaki tutarsızlıklar"
- "belgeler arasında ortak noktalar"
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def detect_multi_doc_query(query: str) -> bool:
    """
    Detects if a query is asking about multiple documents.
    
    Multi-doc indicators:
        - "karşılaştır", "fark", "arasında"
        - "belgeler", "dokümanlar", "sözleşmeler" (plural)
        - "tüm", "her", "all"
        - Comparative language patterns
    
    Args:
        query: User query string
    
    Returns:
        True if multi-doc query detected, False otherwise
    """
    query_lower = query.lower()
    
    # Multi-doc keywords
    multi_doc_keywords = [
        'karşılaştır', 'karşılaştırma', 'fark', 'farklar', 'arasında',
        'ikisi', 'her ikisi', 'her iki', 'ikiside',
        'belgeler', 'dokümanlar', 'sözleşmeler', 'raporlar',
        'hangi belge', 'hangi doküman',
        'tüm', 'tümü', 'her', 'hepsi',
        'ortak', 'benzer', 'farklı',
        'tutarsızlık', 'uyumsuzluk'
    ]
    
    if any(kw in query_lower for kw in multi_doc_keywords):
        logger.info(f"[Multi-Doc] Multi-doc query detected: '{query[:50]}...'")
        return True
    
    return False


async def generate_multi_doc_summary(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k_per_doc: int = 3
) -> Dict[str, Any]:
    """
    Generates a comparative summary from multiple documents.
    
    Process:
    1. Group chunks by document (upload_id)
    2. Select top K chunks per document
    3. Generate LLM-based comparative summary
    4. Return structured result with summary + sources
    
    Args:
        query: Original user query
        candidates: List of chunk candidates from RAG search
        top_k_per_doc: Number of chunks to use per document (default: 3)
    
    Returns:
        Dict with:
            - summary: Comparative summary text
            - sources_breakdown: List of {filename, upload_id, chunk_count}
            - total_docs: Number of unique documents used
    """
    from app.providers.llm.groq import GroqProvider
    
    # Group by document
    docs_map: Dict[str, List[Dict]] = {}
    for chunk in candidates:
        upload_id = chunk.get("upload_id")
        if not upload_id:
            continue
        
        if upload_id not in docs_map:
            docs_map[upload_id] = []
        docs_map[upload_id].append(chunk)
    
    # Need at least 2 documents for multi-doc summary
    if len(docs_map) < 2:
        logger.info("[Multi-Doc] Not enough unique documents for multi-doc summary")
        return {"summary": None, "sources_breakdown": [], "total_docs": 0}
    
    # Select top K per document
    selected_chunks = []
    sources_breakdown = []
    
    for upload_id, chunks in docs_map.items():
        # Sort by score (lower is better for distance)
        sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 1.0))
        top_chunks = sorted_chunks[:top_k_per_doc]
        
        selected_chunks.extend(top_chunks)
        
        sources_breakdown.append({
            "filename": top_chunks[0].get("filename", "Unknown"),
            "upload_id": upload_id,
            "chunk_count": len(top_chunks)
        })
    
    # Limit total chunks for cost control (max 15 chunks)
    if len(selected_chunks) > 15:
        selected_chunks = selected_chunks[:15]
        logger.info(f"[Multi-Doc] Limited to 15 chunks for cost control")
    
    # Build context for LLM
    context_parts = []
    for idx, chunk in enumerate(selected_chunks):
        filename = chunk.get("filename", "Unknown")
        page = chunk.get("page_number", "?")
        text = chunk.get("text", "")[:500]  # First 500 chars
        
        context_parts.append(f"[Belge: {filename}, Sayfa {page}]\n{text}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Generate comparative summary
    try:
        provider = GroqProvider()
        
        prompt = f"""Kullanıcı Sorusu: "{query}"

Aşağıda farklı belgelerden alınmış ilgili metin parçaları bulunuyor.
Bu belgeleri karşılaştırarak kullanıcının sorusuna yanıt ver.

Yanıtın:
- Belgeler arasındaki farkları vurgula
- Ortak noktaları belirt
- Her belge için ayrı bilgi ver
- Netlik için belge adlarını kullan

Belgeler:
{context}

Karşılaştırmalı Özet:"""
        
        summary = await provider.generate(
            prompt,
            system_prompt="Sen bir karşılaştırmalı analiz uzmanısın. Belgeler arası farkları net şekilde açıklarsın.",
            temperature=0.3,
            max_tokens=300
        )
        
        summary = summary.strip()
        
        if len(summary) < 20:
            logger.warning("[Multi-Doc] Generated summary too short")
            return {"summary": None, "sources_breakdown": sources_breakdown, "total_docs": len(docs_map)}
        
        logger.info(f"[Multi-Doc] Summary generated from {len(docs_map)} documents, {len(selected_chunks)} chunks")
        
        return {
            "summary": summary,
            "sources_breakdown": sources_breakdown,
            "total_docs": len(docs_map)
        }
        
    except Exception as e:
        logger.error(f"[Multi-Doc] Summary generation failed: {e}", exc_info=True)
        return {"summary": None, "sources_breakdown": sources_breakdown, "total_docs": len(docs_map)}
