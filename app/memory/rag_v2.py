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
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

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
            logger.warning(f"[RAG v2] Failed to load multilingual model, using default: {e}")
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


def _extract_article_number(text: str) -> str | None:
    """Extract Turkish law article number from text (e.g., 'Madde 157')."""
    patterns = [
        r"Madde\s+(\d+)",
        r"MADDE\s+(\d+)",
        r"madde\s+(\d+)",
        r"(\d+)\.\s*[Mm]adde",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_section_title(text: str) -> str | None:
    """Extract section/chapter title from text."""
    patterns = [
        r"^((?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU)\s+(?:KISIM|BÖLÜM|KİTAP))",
        r"^([A-ZÇĞİÖŞÜ\s]{10,})\s*$",
    ]
    for line in text.split("\n")[:5]:
        for pattern in patterns:
            match = re.search(pattern, line.strip())
            if match:
                return match.group(1).strip()
    return None


def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Extract important keywords from text."""
    # Turkish legal keywords
    legal_terms = {
        "suç",
        "ceza",
        "hapis",
        "para",
        "yaptırım",
        "fail",
        "mağdur",
        "hüküm",
        "mahkeme",
        "dava",
        "hak",
        "ihlal",
        "yasak",
        "müeyyide",
        "taksir",
        "kast",
        "teşebbüs",
        "iştirak",
        "zamanaşımı",
        "af",
        "dolandırıcılık",
        "hırsızlık",
        "gasp",
        "tehdit",
        "şantaj",
        "sahtecilik",
        "rüşvet",
        "zimmet",
        "ihtilas",
        "irtikap",
    }

    words = re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ]{4,}\b", text.lower())
    found_keywords = []
    for word in words:
        if word in legal_terms and word not in found_keywords:
            found_keywords.append(word)
            if len(found_keywords) >= max_keywords:
                break
    return found_keywords


def semantic_chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP
) -> list[tuple[str, dict[str, Any]]]:
    """
    Semantic text chunker that preserves context and extracts metadata.

    Returns list of (chunk_text, metadata) tuples.
    """
    text = (text or "").strip()
    if not text:
        return []

    # If smaller than chunk size, return as is with metadata
    if len(text) <= chunk_size:
        meta = {
            "article_number": _extract_article_number(text),
            "section_title": _extract_section_title(text),
            "keywords": _extract_keywords(text),
        }
        return [(text, meta)]

    chunks_with_meta = []

    # Split by paragraphs first
    paragraphs = re.split(r"\n\s*\n", text)

    current_chunk = ""
    current_meta = {"article_number": None, "section_title": None, "keywords": []}

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Check for article number at paragraph start
        article_num = _extract_article_number(para)
        if article_num:
            # Start new chunk at article boundary
            if current_chunk:
                current_meta["keywords"] = _extract_keywords(current_chunk)
                chunks_with_meta.append((current_chunk.strip(), current_meta.copy()))
            current_chunk = para + "\n"
            current_meta = {
                "article_number": article_num,
                "section_title": _extract_section_title(para),
                "keywords": [],
            }
        elif len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n"
        else:
            # Chunk is full, save it
            if current_chunk:
                current_meta["keywords"] = _extract_keywords(current_chunk)
                chunks_with_meta.append((current_chunk.strip(), current_meta.copy()))

            # Start new chunk with overlap
            if len(current_chunk) > overlap:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + para + "\n"
            else:
                current_chunk = para + "\n"
            current_meta = {"article_number": _extract_article_number(para), "section_title": None, "keywords": []}

    # Don't forget the last chunk
    if current_chunk.strip():
        current_meta["keywords"] = _extract_keywords(current_chunk)
        chunks_with_meta.append((current_chunk.strip(), current_meta.copy()))

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
        logger.error("[RAG v2] PyPDF2 not installed.")
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

                print(f"[RAG v2 DEBUG] Page {page_num}: Extracted {len(text)} chars.")
                sys.stdout.flush()

                if len(text) < 10:  # Çok kısa sayfaları atla
                    print(f"[RAG v2 DEBUG] Page {page_num} skipped (<10 chars).")
                    sys.stdout.flush()
                    continue

                # NEW: Semantic Chunking
                # Returns list of (chunk_text, extracted_meta)
                chunks_data = semantic_chunk_text(text)
                print(
                    f"[RAG v2 DEBUG] Page {page_num}: Generated {len(chunks_data) if chunks_data else 0} semantic chunks."
                )
                sys.stdout.flush()

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
                        # Extracted fields
                        "article_number": extracted_meta.get("article_number") or "",
                        "section_title": extracted_meta.get("section_title") or "",
                        "keywords": ",".join(extracted_meta.get("keywords") or []),
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
                        logger.warning(f"[RAG v2] FTS add failed: {e}")

                    total_chunks_added += len(documents)
                    logger.info(f"[RAG v2] Processing {filename} Page {page_num}: {len(documents)} chunks added.")
            return total_chunks_added

    except Exception as e:
        print(f"[RAG v2 ERROR] PDF processing failed: {type(e).__name__}: {e}")
        sys.stdout.flush()
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        logger.error(f"[RAG v2] PDF processing failed: {e}")
        if fail_open:
            return 0
        raise e


def add_txt_document(
    text: str,
    filename: str,
    owner: str,
    scope: Scope = "user",
    conversation_id: str | None = None,
    upload_id: str | None = None,
    fail_open: bool = True,
) -> int:
    """
    Ingest text content as a single page (Page 1).
    """
    try:
        collection = _get_rag_v2_collection()
        safe_filename = _sanitize_filename(filename)
        now = datetime.utcnow().isoformat()

        if not upload_id:
            upload_id = str(uuid.uuid4())

        chunks = chunk_text(text)
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk_idx, chunk in enumerate(chunks):
            # Treat as Page 1
            page_num = 1
            doc_id = f"{owner}:{safe_filename}:{upload_id}:p{page_num}:c{chunk_idx}"

            meta = {
                "scope": scope,
                "owner": owner,
                "source": "upload_v2",
                "filename": filename,
                "conversation_id": conversation_id or "",
                "upload_id": upload_id,
                "page_number": page_num,
                "chunk_index": chunk_idx,
                "page_total_chunks": len(chunks),
                "created_at": now,
            }

            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append(meta)

        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)

            # FTS tablosuna da ekle (hybrid search için)
            try:
                from app.memory.rag_v2_lexical import upsert_chunk

                for idx, chunk in enumerate(documents):
                    upsert_chunk(
                        owner=owner,
                        scope=scope,
                        filename=filename,
                        upload_id=upload_id,
                        page_number=1,  # TXT = sayfa 1
                        chunk_index=idx,
                        content=chunk,
                    )
            except Exception as fts_err:
                logger.warning(f"[RAG v2] FTS indexing failed: {fts_err}")

            logger.info(f"[RAG v2] Ingested TXT {filename}: {len(ids)} chunks. (UploadID: {upload_id})")
            return len(ids)

        return 0

    except Exception as e:
        logger.error(f"[RAG v2] Error adding TXT {filename}: {e}")
        if fail_open:
            return 0
        raise


def search_documents_v2(
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
    Search for documents in RAG v2 collection.

    Search documents with optional Deep Mode and Hybrid Retrieval.

    Mode:
    - "fast": Standard dense search (Vector only).
    - "deep": Vector + Lexical (Hybrid). Higher top_k.

    Args:
        continue_mode: If True, restricts search to subsequent pages of last active doc.
    """
    # Telemetry setup
    import time

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
                logger.warning(f"[RAG v2] Pinning/Continue error: {e}")
            except Exception:
                pass

        # 2. Document Selection (Scope Narrowing)
        # Only if not pinned and in Deep mode (to save costs on very broad queries)
        if not pinned_id and mode == "deep":
            try:
                # Seed Search: Get top 20 chunks roughly to see which docs are relevant
                # Using 'fast' dense search logic locally (no recursion)
                seed_results = coll.query(
                    query_texts=[query],
                    n_results=20,
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

                    # Select top 5 docs
                    selected_ids = rag_v2_docs.get_doc_candidates_from_seeds(seed_candidates, top_k_docs=5)

                    if selected_ids:
                        # Apply filter
                        where_filter["$and"].append({"upload_id": {"$in": selected_ids}})
                        doc_selection_used = True
                        docs_selected = len(selected_ids)
                        lexical_filter_ids = selected_ids
                        logger.info(f"[RAG v2] Doc selection active. Selected: {len(selected_ids)} docs.")

            except Exception as e:
                logger.warning(f"[RAG v2] Doc selection failed (fail-open): {e}")

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

        # Hybrid Logic (Deep Mode)
        if mode == "deep":
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
                    merged_map = {}

                    # Add Dense (init hybrid with dense score)
                    dense_scores = [c["score"] for c in candidates]
                    min_dense = min(dense_scores) if dense_scores else 0.0
                    max_dense = max(dense_scores) if dense_scores else 1.0
                    if max_dense == min_dense:
                        max_dense += 1e-6

                    for c in candidates:
                        # Key: (upload_id, page_number, chunk_index)
                        key = (c.get("upload_id"), c.get("page_number"), c.get("chunk_index"))
                        c["normalized_dense"] = (c["score"] - min_dense) / (max_dense - min_dense)
                        merged_map[key] = c

                    # Add/Merge Lexical
                    # BM25 scores: more negative = better match
                    bm25_scores = [l["bm25_score"] for l in lexical_results]
                    min_bm25 = min(bm25_scores) if bm25_scores else 0.0  # Best score (most negative)
                    max_bm25 = max(bm25_scores) if bm25_scores else 0.0  # Worst score (least negative)
                    if max_bm25 == min_bm25:
                        max_bm25 = min_bm25 + 1e-6

                    # Create set of FTS-matched keys for quick lookup
                    fts_matched_keys = set()

                    for l in lexical_results:
                        key = (l.get("upload_id"), l.get("page_number"), l.get("chunk_index"))
                        fts_matched_keys.add(key)

                        # Normalize: best (most negative) -> 0.0, worst -> 1.0
                        # This way, lower normalized = better match
                        norm_bm25 = (l["bm25_score"] - min_bm25) / (max_bm25 - min_bm25)

                        if key in merged_map:
                            merged_map[key]["bm25_score"] = l["bm25_score"]
                            merged_map[key]["normalized_bm25"] = norm_bm25
                            merged_map[key]["fts_matched"] = True
                        else:
                            merged_map[key] = {
                                "text": l["text"],
                                "filename": l["filename"],
                                "page_number": l["page_number"],
                                "chunk_index": l["chunk_index"],
                                "upload_id": l["upload_id"],
                                "score": 1.0,
                                "normalized_dense": 1.0,
                                "bm25_score": l["bm25_score"],
                                "normalized_bm25": norm_bm25,
                                "fts_matched": True,
                                "score_type": "hybrid_distance",
                            }

                    # Give penalty to chunks that didn't match FTS
                    for key, cand in merged_map.items():
                        if key not in fts_matched_keys:
                            cand["normalized_bm25"] = 1.0  # Worst score for no FTS match
                            cand["fts_matched"] = False

                    # Final Hybrid Score
                    # alpha = 0.7 means 70% dense, 30% lexical
                    # But for exact matches we should boost lexical weight
                    alpha = 0.5  # Equal weight for now
                    final_candidates = []

                    for cand in merged_map.values():
                        d_norm = cand.get("normalized_dense", 1.0)
                        b_norm = cand.get("normalized_bm25", 1.0)

                        # Boost FTS-matched results
                        if cand.get("fts_matched"):
                            b_norm = b_norm * 0.5  # Make FTS matches even better

                        h_score = (alpha * d_norm) + ((1 - alpha) * b_norm)
                        cand["hybrid_score"] = h_score
                        cand["score_type"] = "hybrid_distance"
                        final_candidates.append(cand)

                    final_candidates.sort(key=lambda x: x["hybrid_score"])
                    candidates = final_candidates
                    t_merge = (time.time() - t2) * 1000

            except Exception as e:
                logger.error(f"[RAG v2] Hybrid search failed: {e}")
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

        total_latency = (time.time() - start_time) * 1000

        stats = RAGV2Stats(
            query_hash=calculate_query_hash(query),
            owner=owner,
            scope=str(scope),
            mode_used=mode,
            used_lexical=used_lexical,
            dense_count=dense_count,
            lexical_count=lexical_count,
            merged_count=merged_count,
            best_score=best_score,
            second_score=second_score,
            best_score_type=best_score_type,
            gating_result="retrieval_only",
            latency_ms_total=int(total_latency),
            latency_ms_dense=int(t_dense),
            latency_ms_lexical=int(t_lexical),
            latency_ms_merge=int(t_merge),
            docs_total=docs_total,
            docs_selected=docs_selected,
            doc_selection_used=doc_selection_used,
            conversation_pinning_used=conversation_pinning_used,
            continuation_window_pages=continue_window_size,
            last_page_used=last_page_used,
            page_window_applied=continue_window_applied,
        )
        # Do not write telemetry here; caller is responsible for logging once.
        if return_stats:
            return candidates, stats
        return candidates

    except Exception as e:
        logger.error(f"[RAG v2] Search error: {e}")
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

        # Filter strictly by page context
        where_filter = {"owner": owner, "scope": scope, "filename": filename, "page_number": page_number}

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
        logger.error(f"[RAG v2] Expansion error: {e}")
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
        logger.error(f"[RAG v2] List error: {e}")
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
        logger.error(f"[RAG v2] Delete error: {e}")
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
            logger.warning(f"[RAG v2] FTS delete failed: {e}")

        logger.info(f"[RAG v2] Deleted {count} chunks for {filename}")
        return count

    except Exception as e:
        logger.error(f"[RAG v2] Delete by filename error: {e}")
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
            logger.warning(f"[RAG v2] FTS delete failed: {e}")

        logger.info(f"[RAG v2] Deleted {count} chunks for upload_id {upload_id}")
        return count

    except Exception as e:
        logger.error(f"[RAG v2] Delete by upload_id error: {e}")
        return 0
