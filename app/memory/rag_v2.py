"""
Mami AI - RAG v2 Ingestion (Page-Aware + Multilingual)
======================================================

Handles document ingestion with page-level granularity.
Stores chunks in 'rag_v2_chunks' collection with multilingual embeddings.
Features: Semantic chunking, metadata extraction, query expansion support.
"""

import logging
import re
import sys
import uuid
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, List, Dict
from app.memory.query_normalizer import query_normalizer

# Core DB dependency
try:
    from app.core.database import get_chroma_client
except ImportError:
    pass

# PDF Library
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

logger = logging.getLogger(__name__)

Scope = Literal["global", "user", "conversation", "web"]
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200

# Multilingual embedding model
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_embedding_function = None


def _get_embedding_function():
    """Get multilingual embedding function (cached)."""
    global _embedding_function
    if _embedding_function is None:
        try:
            from chromadb.utils import embedding_functions

            _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME
            )
            logger.info(f"[RAG v2] Loaded embedding model: {EMBEDDING_MODEL_NAME}")
        except Exception as e:
            logger.warning(f"[RAG v2] Failed to load multilingual model, using default: {e}", exc_info=True)
            _embedding_function = None
    return _embedding_function


def _get_rag_v2_collection():
    """Get or create the 'rag_v2_chunks' collection with multilingual embeddings."""
    from app.core.database import get_chroma_client

    client = get_chroma_client()

    ef = _get_embedding_function()
    if ef:
        return client.get_or_create_collection(
            name="rag_v2_chunks", embedding_function=ef, metadata={"hnsw:space": "cosine"}
        )
    else:
        return client.get_or_create_collection(name="rag_v2_chunks", metadata={"hnsw:space": "cosine"})


# ============================================================================
# SEMANTIC CHUNKING
# ============================================================================


def _extract_patterns(text: str) -> Dict[str, Any]:
    """Her türlü dokümanda (Hukuk, Teknik, Tıp) ortak olan yapısal kalıpları ayıklar."""
    # Generic ID/Code patterns (e.g., 157/1, SKU-99, PRJ-102)
    # ChromaDB metadata must be scalar (str, int, float, bool)
    ids = re.findall(r"\b[A-Za-z0-9]+[/. \-][A-Za-z0-9]+\b", text)
    
    patterns = {
        "identifiers": ",".join(list(set(ids))),
        "headers": ""
    }
    # İlk satırı başlık olarak dene
    lines = text.split("\n")
    if lines and len(lines[0]) < 100:
        patterns["headers"] = lines[0].strip()
        
    return patterns


def semantic_chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP
) -> list[tuple[str, dict[str, Any]]]:
    """
    Belge içeriğini anlamsal parçalara ayırır ve yapısal desenleri ayıklar.
    """
    text = (text or "").strip()
    if not text:
        return []

    # Boyut kontrolü
    if len(text) <= chunk_size:
        meta = _extract_patterns(text)
        return [(text, meta)]

    chunks_with_meta = []
    # Paragraflara böl
    paragraphs = re.split(r"\n\s*\n", text)
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para: continue

        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks_with_meta.append((current_chunk.strip(), _extract_patterns(current_chunk)))
            # Overlap ile yeni chunk
            current_chunk = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
            current_chunk += para + "\n\n"

    if current_chunk:
        chunks_with_meta.append((current_chunk.strip(), _extract_patterns(current_chunk)))

    return chunks_with_meta


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """Simple text chunker reusing logic similar to legacy."""
    text = (text or "").strip()
    if not text:
        return []

    # If smaller than chunk size, return as is
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + chunk_size

        # Don't split words if possible
        if end < length:
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= length:
            break

        start = end - overlap

    return chunks


def _sanitize_filename(filename: str) -> str:
    """Normalize filename for ID generation."""
    # Replace non-alphanumeric chars (except .-_) with _
    return re.sub(r"[^a-zA-Z0-9.\-_]", "_", filename)


def add_document_pages_from_pdf(
    file_path: Path,
    filename: str,
    owner: str,
    scope: Scope = "user",
    conversation_id: str | None = None,
    upload_id: str | None = None,
    fail_open: bool = True,
) -> int:
    """
    Ingest a PDF file page-by-page.

    Args:
        upload_id: Optional unique ID for this upload batch. Generated if None.
        fail_open: If True, returns 0 on error instead of raising.

    Returns:
        int: Total chunks added.
    """
    if PyPDF2 is None:
        logger.error("[RAG v2] PyPDF2 not installed.", exc_info=False)  # Missing dependency doesn't need traceback
        return 0

    try:
        collection = _get_rag_v2_collection()
        safe_filename = _sanitize_filename(filename)
        now = datetime.utcnow().isoformat()

        # Generate upload_id if not provided to ensure uniqueness across uploads of same file
        if not upload_id:
            upload_id = str(uuid.uuid4())

        total_chunks_added = 0

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            len(reader.pages)

            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""
                # Kısmi temizlik
                text = text.strip()

                # Debug logging (sadece DEBUG modunda)
                from app.config import get_settings
                settings = get_settings()
                if settings.DEBUG:
                    logger.debug(f"[RAG v2] Page {page_num}: Extracted {len(text)} chars.")

                if len(text) < 10:  # Çok kısa sayfaları atla
                    if settings.DEBUG:
                        logger.debug(f"[RAG v2] Page {page_num} skipped (<10 chars).")
                    continue

                # NEW: Semantic Chunking
                # Returns list of (chunk_text, extracted_meta)
                chunks_data = semantic_chunk_text(text)
                if settings.DEBUG:
                    logger.debug(
                        f"[RAG v2] Page {page_num}: Generated {len(chunks_data) if chunks_data else 0} semantic chunks."
                    )

                if not chunks_data:
                    continue

                ids = []
                documents = []
                metadatas = []

                for chunk_idx, (chunk_text, extracted_meta) in enumerate(chunks_data):
                    # Deterministic ID
                    # owner:safe_filename:upload_id:pX:cY
                    doc_id = f"{owner}:{safe_filename}:{upload_id}:p{page_num}:c{chunk_idx}"

                    # Merge metadata
                    meta = {
                        "scope": scope,
                        "owner": owner,
                        "source": "upload_v2",
                        "filename": filename,
                        "upload_id": upload_id,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "ingest_date": now,
                        **extracted_meta
                    }

                    ids.append(doc_id)
                    documents.append(chunk_text)
                    metadatas.append(meta)

                if documents:
                    # Batch add to Chroma
                    collection.add(ids=ids, documents=documents, metadatas=metadatas)

                    # Add to FTS (Lexical)
                    try:
                        from app.memory.rag_v2_lexical import add_chunks_to_fts

                        add_chunks_to_fts(ids, documents, metadatas)
                    except Exception as e:
                        logger.warning(f"[RAG v2] FTS add failed: {e}", exc_info=True)

                    total_chunks_added += len(documents)
                    logger.info(f"[RAG v2] Processing {filename} Page {page_num}: {len(documents)} chunks added.")
            return total_chunks_added

    except Exception as e:
        # Error logging with traceback (exc_info=True)
        logger.error(f"[RAG v2] PDF processing failed: {type(e).__name__}: {e}", exc_info=True)
        if fail_open:
            return 0
        raise e


async def _rerank_with_llm(query: str, results: List[Dict]) -> List[Dict]:
    """LLM kullanarak bulunan sonuçları anlamsal olarak yeniden puanlar."""
    if not results: return []
    
    from app.providers.llm.groq import GroqProvider
    provider = GroqProvider()
    
    # Sadece ilk 15 sonucu rerank et (Performans/Maliyet)
    to_rerank = results[:15]
    
    # Prompt hazırla
    corpus = "\n".join([f"ID:{i} | İçerik: {res['text'][:300]}..." for i, res in enumerate(to_rerank)])
    
    prompt = f"""
    Kullanıcı Sorgusu: "{query}"
    
    Aşağıdaki doküman parçalarını sorguya en uygun (bilgi veren) olandan en uzağa doğru puanla.
    Sadece JSON formatında bir liste döndür: [id1, id2, ...]
    
    Dokümanlar:
    {corpus}
    """
    
    try:
        # Hafif ve hızlı bir model kullan
        response = await provider.generate(prompt, system_prompt="Sen bir RAG Reranking uzmanısın. Sadece JSON liste döndür.", temperature=0.0)
        # JSON çıkar (defensive)
        import re
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            new_order_ids = json.loads(match.group(0))
            reranked = []
            for idx in new_order_ids:
                if isinstance(idx, int) and idx < len(to_rerank):
                    reranked.append(to_rerank[idx])
            # Geri kalanları ekle
            seen_texts = {r['text'] for r in reranked}
            for r in results:
                if r['text'] not in seen_texts:
                    reranked.append(r)
            return reranked
    except Exception as e:
        logger.warning(f"[RAG Reranker] LLM Reranking failed: {e}", exc_info=True)
    return results


async def _generate_page_summary(
    page_text: str, 
    filename: str, 
    page_num: int
) -> str | None:
    """
    Generate 100-word summary of a page using Groq LLM.
    
    Args:
        page_text: Full page content
        filename: Document name (for context)
        page_num: Page number
    
    Returns:
        Summary text with [SAYFA X ÖZETİ] prefix, or None on failure
    
    Cost: ~$0.0002 per page (400 input + 150 output tokens)
    """
    # Too short pages don't need summarization
    if len(page_text) < 100:
        logger.debug(f"[RAG v2] Page {page_num} too short for summary ({len(page_text)} chars)")
        return None
    
    try:
        from app.providers.llm.groq import GroqProvider
        provider = GroqProvider()
        
        # Truncate to first 2000 chars for cost control
        # 2000 chars ≈ 400 tokens
        content = page_text[:2000]
        
        prompt = f"""Aşağıdaki metin "{filename}" belgesinin {page_num}. sayfasıdır.
Bu sayfayı maksimum 100 kelime ile özetle. Ana konular ve önemli detayları vurgula.

Metin:
{content}

Özet (100 kelime max):"""
        
        summary = await provider.generate(
            prompt,
            system_prompt="Sen bir doküman özet uzmanısın. Kısa ve öz yazarsın.",
            temperature=0.3,
            max_tokens=150
        )
        
        # Validation
        summary = summary.strip()
        if len(summary) < 20:
            logger.warning(f"[RAG v2] Page {page_num} summary too short, skipping", exc_info=False)  # Not an error, just info
            return None
        
        # Add marker for identification
        return f"[SAYFA {page_num} ÖZETİ] {summary}"
        
    except Exception as e:
        logger.error(f"[RAG v2] Page summary generation failed for page {page_num}: {e}", exc_info=True)
        return None


def _determine_doc_count(query: str) -> int:
    """
    Query'nin multi-doc intent içerip içermediğini tespit eder.
    
    Multi-doc indicators:
        - "karşılaştır", "fark", "arasında" keywords
        - "belgeler", "dokümanlar", "sözleşmeler" (plural forms)
        - Query length > 50 chars (complex query heuristic)
    
    Returns:
        8 if multi-doc intent detected, else 5
    """
    query_lower = query.lower()
    
    # Multi-doc keywords
    multi_doc_keywords = [
        'karşılaştır', 'karşılaştırma', 'fark', 'arasında', 
        'ikisi', 'her ikisi', 'her iki', 'ikiside',
        'belgeler', 'dokümanlar', 'sözleşmeler', 'raporlar',
        'hangi belge', 'hangi doküman'
    ]
    
    if any(kw in query_lower for kw in multi_doc_keywords):
        logger.info(f"[RAG v2] Multi-doc intent detected (keyword match): top_k_docs=8")
        return 8
    
    # Long query heuristic (karmaşık sorular genelde multi-doc)
    if len(query) > 50:
        logger.info(f"[RAG v2] Long query detected ({len(query)} chars): top_k_docs=8")
        return 8
    
    # Default (single doc focused)
    return 5


def add_txt_document(
    text: str,
    filename: str,
    owner: str,
    scope: Scope = "user",
    conversation_id: str | None = None,
    upload_id: str | None = None,
    fail_open: bool = True,
) -> int:
    """TXT dökümanını anlamsal parçalara ayırır ve metadata ile zenginleştirir."""
    try:
        collection = _get_rag_v2_collection()
        safe_filename = _sanitize_filename(filename)
        now = datetime.utcnow().isoformat()

        if not upload_id:
            upload_id = str(uuid.uuid4())

        # Genel öreüntüleri ayıkla (Zero-shot)
        chunks_with_meta = semantic_chunk_text(text)
        if not chunks_with_meta:
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk_idx, (chunk, smeta) in enumerate(chunks_with_meta):
            doc_id = f"{owner}:{safe_filename}:{upload_id}:p1:c{chunk_idx}"
            meta = {
                "scope": scope,
                "owner": owner,
                "filename": filename,
                "upload_id": upload_id,
                "page_number": 1,
                "chunk_index": chunk_idx,
                "created_at": now,
                **smeta
            }
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append(meta)

        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            try:
                from app.memory.rag_v2_lexical import upsert_chunk
                for idx, chunk in enumerate(documents):
                    upsert_chunk(owner=owner, scope=scope, filename=filename, upload_id=upload_id, page_number=1, chunk_index=idx, content=chunk)
            except Exception as fts_err:
                logger.warning(f"[RAG v2] FTS indexing failed: {fts_err}", exc_info=True)
            return len(ids)
        return 0
    except Exception as e:
        logger.error(f"[RAG v2] Error adding TXT {filename}: {e}", exc_info=True)
        return 0


async def search_documents_v2(
    query: str,
    owner: str,
    scope: Scope,
    top_k: int = 60,
    mode: str = "fast",
    conversation_id: str | None = None,
    continue_mode: bool = False,
    return_stats: bool = False,
) -> list[dict[str, Any]]:
    """
    Belge araması yapar. 'deep' modda anlamsal yeniden sıralama (reranking) kullanır.
    """
    # 0. Sorgu Genişletme (Zero-shot numeric recall boost)
    expanded_queries = query_normalizer.expand_numeric_patterns(query)
    primary_query = expanded_queries[0]

    # Telemetry setup
    from app.memory import rag_v2_conversation, rag_v2_docs
    from app.memory.rag_v2_telemetry import RAGV2Stats, calculate_query_hash

    # Force Deep Mode for Continue
    if continue_mode:
        mode = "deep"

    start_time = time.time()
    t_dense = 0.0
    t_lexical = 0.0
    t_merge = 0.0

    dense_count = 0
    lexical_count = 0
    merged_count = 0
    used_lexical = False

    # Optimization Stats
    docs_total = 0
    docs_selected = 0
    doc_selection_used = False
    conversation_pinning_used = False

    # Continue Mode Stats
    continue_window_applied = False
    last_page_used = None
    continue_window_size = 0

    try:
        where_filter = {"$and": [{"owner": {"$eq": owner}}, {"scope": {"$eq": str(scope)}}]}
        lexical_filter_ids = None  # List of upload_ids to filter lexical results
        coll = _get_rag_v2_collection()

        # 1. Conversation Pinning
        pinned_id = None
        if conversation_id:
            try:
                # Retrieve Pin & Page State
                pinned_id = rag_v2_conversation.get_active_doc(conversation_id)
                last_page_used = rag_v2_conversation.get_active_page(conversation_id)

                if pinned_id:
                    # Update filter: Add upload_id constraint
                    where_filter["$and"].append({"upload_id": {"$eq": pinned_id}})
                    conversation_pinning_used = True
                    lexical_filter_ids = [pinned_id]
                    logger.info(f"[RAG v2] Using pinned doc: {pinned_id}")

                # Continue Mode Window Logic
                if continue_mode and last_page_used is not None:
                    # Window: last_page to last_page + 5
                    continue_window_size = 5
                    min_page = last_page_used + 1
                    max_page = last_page_used + continue_window_size
                    max_page = last_page_used + continue_window_size

                    where_filter["$and"].append({"page_number": {"$gte": min_page}})
                    where_filter["$and"].append({"page_number": {"$lte": max_page}})

                    continue_window_applied = True
                    logger.info(f"[RAG v2] Continue Mode: Window {min_page}-{max_page} applied.")

            except Exception as e:
                logger.warning(f"[RAG v2] Pinning/Continue error: {e}", exc_info=True)
            except Exception:
                pass

        # 2. Document Selection (Scope Narrowing)
        # Only if not pinned and in Deep mode (to save costs on very broad queries)
        if not pinned_id and mode == "deep":
            try:
                # Seed Search: Get top 50 chunks roughly to see which docs are relevant
                # Using 'fast' dense search logic locally (no recursion)
                seed_results = coll.query(
                    query_texts=[query],
                    n_results=50,
                    where=where_filter,  # Global filter at this point
                )

                seed_candidates = []
                if seed_results and seed_results["ids"] and seed_results["ids"][0]:
                    s_ids = seed_results["ids"][0]
                    s_metas = seed_results["metadatas"][0]
                    s_dists = seed_results["distances"][0] if seed_results["distances"] else [0.0] * len(s_ids)

                    for i, _ in enumerate(s_ids):
                        seed_candidates.append({"upload_id": s_metas[i].get("upload_id"), "score": s_dists[i]})

                if seed_candidates:
                    # Estimate total unique docs involved in top 20
                    unique_seeds = {c["upload_id"] for c in seed_candidates if c.get("upload_id")}
                    docs_total = len(unique_seeds)

                    # Dynamic doc count based on query intent
                    dynamic_top_k = _determine_doc_count(query)
                    selected_ids = rag_v2_docs.get_doc_candidates_from_seeds(
                        seed_candidates, 
                        top_k_docs=dynamic_top_k
                    )

                    if selected_ids:
                        # Apply filter
                        where_filter["$and"].append({"upload_id": {"$in": selected_ids}})
                        doc_selection_used = True
                        docs_selected = len(selected_ids)
                        lexical_filter_ids = selected_ids
                        logger.info(f"[RAG v2] Doc selection active. Selected: {len(selected_ids)} docs.")

            except Exception as e:
                logger.warning(f"[RAG v2] Doc selection failed (fail-open): {e}", exc_info=True)

        if mode == "deep":
            top_k = max(top_k, 200)

        # Dense Search (Vector) - Main Pass
        t0 = time.time()
        results = coll.query(query_texts=[query], n_results=top_k, where=where_filter)
        t_dense = (time.time() - t0) * 1000

        candidates = []

        # Parse Dense Results
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            documents = results["documents"][0]
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)

            for i, doc_id in enumerate(ids):
                meta = metadatas[i]
                cand = {
                    "text": documents[i],
                    "filename": meta.get("filename", "unknown"),
                    "page_number": meta.get("page_number", 0),
                    "chunk_index": meta.get("chunk_index", 0),
                    "upload_id": meta.get("upload_id", ""),
                    "score": distances[i],  # Distance (smaller is better)
                    "score_type": "distance",
                    "id": doc_id,
                }
                candidates.append(cand)
            dense_count = len(candidates)

        # Hybrid Logic (Activated for all modes to ensure keyword precision)
        if mode in ["deep", "fast"]:
            try:
                from app.memory import rag_v2_lexical

                t1 = time.time()
                lexical_results = rag_v2_lexical.lexical_search(query=query, owner=owner, scope=str(scope), top_k=top_k)
                t_lexical = (time.time() - t1) * 1000

                if lexical_results:
                    # Filter Lexical Results in Python
                    if lexical_filter_ids:
                        lexical_results = [l for l in lexical_results if l.get("upload_id") in lexical_filter_ids]

                    used_lexical = True
                    lexical_count = len(lexical_results)

                    t2 = time.time()
                    # Merge Logic
                    # --- RAG v2.5: RRF (Reciprocal Rank Fusion) MERGE LOGIC ---
                    k = 60
                    merged_map = {} # (upload_id, page_number, chunk_index) -> candidate_dict

                    # 1. Rank Dense Results (Smaller distance is better)
                    candidates.sort(key=lambda x: x["score"])
                    for rank, cand in enumerate(candidates, 1):
                        key = (cand.get("upload_id"), cand.get("page_number"), cand.get("chunk_index"))
                        cand["rrf_score"] = 1.0 / (k + rank)
                        cand["fts_matched"] = False
                        merged_map[key] = cand

                    # 2. Rank Lexical Results (More negative BM25 is better)
                    lexical_results.sort(key=lambda x: x["bm25_score"])
                    for rank, lex in enumerate(lexical_results, 1):
                        key = (lex.get("upload_id"), lex.get("page_number"), lex.get("chunk_index"))
                        # RRF Upgrade: Lexical precision is prioritized (1.5x boost) for technical accuracy
                        lex_rrf_contribution = (1.0 / (k + rank)) * 1.5
                        
                        if key in merged_map:
                            merged_map[key]["rrf_score"] += lex_rrf_contribution
                            merged_map[key]["fts_matched"] = True
                        else:
                            # New candidate from lexical search
                            merged_map[key] = {
                                "text": lex["text"],
                                "filename": lex["filename"],
                                "page_number": lex["page_number"],
                                "chunk_index": lex["chunk_index"],
                                "upload_id": lex["upload_id"],
                                "score": 1.0, # Distance padding
                                "rrf_score": lex_rrf_contribution,
                                "fts_matched": True,
                                "score_type": "hybrid_distance"
                            }
                    
                    # 3. Final Selection and Normalization
                    final_candidates = list(merged_map.values())
                    # Sort by RRF score (HIGHER is BETTER)
                    # Tie-break: fts_matched results first
                    final_candidates.sort(key=lambda x: (x["rrf_score"], x.get("fts_matched", False)), reverse=True)
                    
                    # Re-map RRF score to a distance-like 0.0-1.0 range
                    if final_candidates:
                        max_rrf = max(c["rrf_score"] for c in final_candidates)
                        for cand in final_candidates:
                            cand["hybrid_score"] = 1.0 - (cand["rrf_score"] / max_rrf)
                            cand["score_type"] = "hybrid_distance"
                    
                    candidates = final_candidates

                    # 4. RAG v2.5: Parent-Child Context Expansion
                    # If top candidate is very strong, fetch its neighbors for richer context
                    if candidates and candidates[0].get("hybrid_score", 1.0) < 0.2:
                        best = candidates[0]
                        neighbors = expand_neighbors(
                            owner=owner,
                            scope=str(scope),
                            filename=best.get("filename"),
                            page_number=best.get("page_number"),
                            chunk_index=best.get("chunk_index"),
                            radius=1
                        )
                        if neighbors:
                            # Insert neighbors right after the best chunk if they aren't already in candidates
                            seen_keys = {(c.get("upload_id"), c.get("page_number"), c.get("chunk_index")) for c in candidates}
                            new_context = []
                            for n in neighbors:
                                n_key = (n.get("upload_id"), n.get("page_number"), n.get("chunk_index"))
                                if n_key not in seen_keys:
                                    n["score_type"] = "neighbor"
                                    n["hybrid_score"] = best.get("hybrid_score", 0.0) + 0.01 # Slightly lower priority
                                    new_context.append(n)
                            
                            if new_context:
                                candidates = [candidates[0]] + new_context + candidates[1:]
                                logger.info(f"[RAG v2.5] Context Expanded: Added {len(new_context)} neighbors for {best.get('filename')}")

                    t_merge = (time.time() - t2) * 1000

            except Exception as e:
                logger.error(f"[RAG v2] Hybrid search failed: {e}", exc_info=True)
                pass

        merged_count = len(candidates)

        # Auto-Pinning Check
        if conversation_id and not pinned_id and len(candidates) >= 1:
            best = candidates[0]

            # Determine score and margin
            score_type = best.get("score_type", "distance")
            best_score_val = best.get("hybrid_score", best.get("score"))

            # Thresholds aligned with Gating
            # Hybrid < 0.75, Distance < 0.50
            is_good_score = False
            if score_type == "hybrid_distance" and best_score_val < 0.75:
                is_good_score = True
            elif score_type == "distance" and best_score_val < 0.50:
                is_good_score = True

            # Margin Check
            is_valid_margin = True
            if len(candidates) > 1:
                second_score_val = (
                    candidates[1].get("hybrid_score") if score_type == "hybrid_distance" else candidates[1].get("score")
                )
                margin = 0.08
                if (second_score_val and best_score_val) and (second_score_val - best_score_val < margin):
                    is_valid_margin = False

            if is_good_score and is_valid_margin:
                try:
                    rag_v2_conversation.set_active_doc(
                        conversation_id, best.get("upload_id"), last_page=best.get("page_number")
                    )
                    conversation_pinning_used = True  # Technically applied for next turn
                except:
                    pass

        # Update Last Page for Existing Pin
        if conversation_id and pinned_id and candidates:
            try:
                # Update last_page to the furthest page found in top results (to allow scrolling forward)
                # Or just the best result? Let's use best result for stability.
                best_page = candidates[0].get("page_number")
                if best_page:
                    rag_v2_conversation.set_active_doc(conversation_id, pinned_id, last_page=best_page)
            except:
                pass

        # Gather Stats
        best_score = (
            candidates[0].get(
                "hybrid_score" if candidates and candidates[0].get("score_type") == "hybrid_distance" else "score"
            )
            if candidates
            else None
        )
        second_score = (
            candidates[1].get("hybrid_score" if candidates[1].get("score_type") == "hybrid_distance" else "score")
            if len(candidates) > 1
            else None
        )
        best_score_type = candidates[0].get("score_type") if candidates else None

        # 4. DEEP MODE: SEMANTIC RERANKING
        if mode == "deep" and candidates:
            logger.info(f"[RAG v2] Entering Semantic Reranking for {len(candidates)} candidates")
            candidates = await _rerank_with_llm(primary_query, candidates)

        total_latency = (time.time() - start_time) * 1000
        
        if return_stats:
            # Stats generation (simplified for brevity here, should be kept robust)
            return candidates, None 
        return candidates

    except Exception as e:
        logger.error(f"[RAG v2] Search error: {e}", exc_info=True)
        return []


def expand_neighbors(
    owner: str, scope: Scope, filename: str, page_number: int, chunk_index: int, radius: int = 1
) -> list[dict[str, Any]]:
    """
    Find neighbor chunks for a given chunk.

    Returns neighbors sorted by chunk_index.
    """
    try:
        collection = _get_rag_v2_collection()

        # Filter strictly by page context (Using correct ChromaDB $and syntax)
        where_filter = {
            "$and": [
                {"owner": {"$eq": owner}},
                {"scope": {"$eq": str(scope)}},
                {"filename": {"$eq": filename}},
                {"page_number": {"$eq": page_number}}
            ]
        }

        # Fetch all chunks for this page (assuming pages aren't huge)
        results = collection.get(where=where_filter)

        if not results or not results.get("ids"):
            return []

        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])

        neighbors = []
        target_indices = range(chunk_index - radius, chunk_index + radius + 1)

        for i, doc_text in enumerate(documents):
            meta = metadatas[i]
            c_idx = meta.get("chunk_index")

            if c_idx is not None and c_idx in target_indices:
                # Treat neighbors as having very good score (0.0) or inherent relevance
                # But here we just return raw objects
                neighbors.append(
                    {
                        "text": doc_text,
                        "filename": filename,
                        "page_number": page_number,
                        "chunk_index": c_idx,
                        "upload_id": meta.get("upload_id", ""),
                        "score": 0.0,  # Artificial score for neighbors
                        "score_type": "neighbor",
                    }
                )

        # Sort by chunk index to maintain flow
        neighbors.sort(key=lambda x: x.get("chunk_index", 0))

        return neighbors

    except Exception as e:
        logger.error(f"[RAG v2] Expansion error: {e}", exc_info=True)
        return []


# =============================================================================
# DOCUMENT MANAGEMENT FUNCTIONS
# =============================================================================


def list_documents(owner: str, limit: int = 500) -> list[dict[str, Any]]:
    """
    Kullanıcıya ait belgeleri listeler.
    Benzersiz dosya isimlerini döndürür (chunk'lar gruplanır).

    Args:
        owner: Kullanıcı adı
        limit: Maksimum chunk sayısı

    Returns:
        List[Dict]: Benzersiz dosya listesi
    """
    try:
        collection = _get_rag_v2_collection()

        results = collection.get(where={"owner": owner}, limit=limit, include=["metadatas"])

        if not results or not results.get("ids"):
            return []

        # Benzersiz dosyaları topla
        files = {}
        for i, _doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results.get("metadatas") else {}
            fname = meta.get("filename", "Bilinmeyen")
            upload_id = meta.get("upload_id", "")

            # upload_id bazında grupla (aynı dosyanın farklı yüklemeleri)
            key = f"{fname}:{upload_id}"

            if key not in files:
                files[key] = {
                    "filename": fname,
                    "upload_id": upload_id,
                    "created_at": meta.get("created_at", ""),
                    "chunk_count": 1,
                    "page_count": {meta.get("page_number", 1)},
                }
            else:
                files[key]["chunk_count"] += 1
                files[key]["page_count"].add(meta.get("page_number", 1))

        # page_count'u sayıya çevir
        result = []
        for f in files.values():
            f["page_count"] = len(f["page_count"])
            result.append(f)

        logger.info(f"[RAG v2] Listed {len(result)} documents for {owner}")
        return result

    except Exception as e:
        logger.error(f"[RAG v2] List error: {e}", exc_info=True)
        return []


def delete_document(doc_id: str) -> bool:
    """
    Tek bir chunk/doküman siler (ID ile).

    Args:
        doc_id: Silinecek doküman ID'si

    Returns:
        bool: Başarılı ise True
    """
    try:
        collection = _get_rag_v2_collection()
        collection.delete(ids=[doc_id])
        logger.info(f"[RAG v2] Deleted document: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"[RAG v2] Delete error: {e}", exc_info=True)
        return False


def delete_by_filename(filename: str, owner: str) -> int:
    """
    Dosya adına ve sahibine göre tüm chunk'ları siler.

    Args:
        filename: Dosya adı
        owner: Kullanıcı adı

    Returns:
        int: Silinen chunk sayısı
    """
    try:
        collection = _get_rag_v2_collection()

        # Önce eşleşen ID'leri bul
        results = collection.get(where={"$and": [{"filename": filename}, {"owner": owner}]}, limit=5000)

        if not results or not results.get("ids"):
            return 0

        ids_to_delete = results["ids"]
        count = len(ids_to_delete)

        # Sil
        collection.delete(ids=ids_to_delete)

        # FTS tablosundan da sil
        try:
            from app.memory.rag_v2_lexical import _get_connection

            with _get_connection() as conn:
                conn.execute("DELETE FROM rag_v2_fts WHERE filename = ? AND owner = ?", (filename, owner))
        except Exception as e:
            logger.warning(f"[RAG v2] FTS delete failed: {e}", exc_info=True)

        logger.info(f"[RAG v2] Deleted {count} chunks for {filename}")
        return count

    except Exception as e:
        logger.error(f"[RAG v2] Delete by filename error: {e}", exc_info=True)
        return 0


def delete_by_upload_id(upload_id: str, owner: str) -> int:
    """
    Upload ID'ye göre tüm chunk'ları siler.

    Args:
        upload_id: Upload batch ID
        owner: Kullanıcı adı

    Returns:
        int: Silinen chunk sayısı
    """
    try:
        collection = _get_rag_v2_collection()

        results = collection.get(where={"$and": [{"upload_id": upload_id}, {"owner": owner}]}, limit=5000)

        if not results or not results.get("ids"):
            return 0

        ids_to_delete = results["ids"]
        count = len(ids_to_delete)

        collection.delete(ids=ids_to_delete)

        # FTS tablosundan da sil
        try:
            from app.memory.rag_v2_lexical import _get_connection

            with _get_connection() as conn:
                conn.execute("DELETE FROM rag_v2_fts WHERE upload_id = ? AND owner = ?", (upload_id, owner))
        except Exception as e:
            logger.warning(f"[RAG v2] FTS delete failed: {e}", exc_info=True)

        logger.info(f"[RAG v2] Deleted {count} chunks for upload_id {upload_id}")
        return count

    except Exception as e:
        logger.error(f"[RAG v2] Delete by upload_id error: {e}", exc_info=True)
        return 0
