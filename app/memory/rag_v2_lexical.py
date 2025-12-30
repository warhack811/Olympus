import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "rag_v2_fts.db")


def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_fts():
    """Initialize FTS5 virtual table."""
    try:
        with _get_connection() as conn:
            # Check if FTS5 is supported is implied by success of this query
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS rag_v2_fts
            USING fts5(
                content,
                owner,
                scope,
                filename,
                upload_id,
                page_number UNINDEXED,
                chunk_index UNINDEXED,
                tokenize='unicode61'
            );
            """)
    except Exception as e:
        logger.warning(f"[RAG v2 Lexical] Init failed (FTS5 might be missing): {e}")


def add_chunks_to_fts(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
) -> bool:
    """
    Batch insert chunks into FTS index.
    """
    try:
        with _get_connection() as conn:
            data = []
            for i, doc in enumerate(documents):
                meta = metadatas[i]
                data.append(
                    (
                        doc,
                        meta.get("owner", ""),
                        meta.get("scope", "user"),
                        meta.get("filename", ""),
                        meta.get("upload_id", ""),
                        meta.get("page_number", 0),
                        meta.get("chunk_index", 0),
                    )
                )

            conn.executemany(
                """
                INSERT INTO rag_v2_fts (
                    content, owner, scope, filename, upload_id, page_number, chunk_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                data,
            )
            return True
    except Exception as e:
        logger.error(f"[RAG v2 Lexical] Batch add failed: {e}")
        return False


def upsert_chunk(
    owner: str,
    scope: str,
    filename: str,
    upload_id: str,
    page_number: int,
    chunk_index: int,
    content: str,
) -> bool:
    """Insert or replace chunk in FTS index."""
    try:
        with _get_connection() as conn:
            # FTS5 does not support primary keys directly in the same way for upsert usually.
            # But we can just redundant insert or delete-then-insert.
            # To avoid duplicates if we re-ingest, best to delete matches first by ID if we had one.
            # Here we identify by specific fields.

            # Simple approach: Delete row if exact match exists (not robust without explicit ID)
            # But FTS tables have implicit rowid.
            # We will just INSERT. Users should clear DB if re-ingesting fully or we handle it upstream.
            # For this task: Simple INSERT.

            # Better: use a separate lookup table? No, keep it simple.
            # Let's try to delete matching chunk first to support "update".
            # "DELETE FROM rag_v2_fts WHERE filename=? AND chunk_index=? ..." is slow on FTS.
            # FTS is designed for text search, not structured updates.
            # Delete existing exact match to avoid duplicates (Append-only fix)
            conn.execute(
                """
                DELETE FROM rag_v2_fts
                WHERE owner=? AND scope=? AND filename=? AND upload_id=? AND page_number=? AND chunk_index=?
                """,
                (owner, scope, filename, upload_id, page_number, chunk_index),
            )

            conn.execute(
                "INSERT INTO rag_v2_fts (content, owner, scope, filename, upload_id, page_number, chunk_index) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (content, owner, scope, filename, upload_id, page_number, chunk_index),
            )
        return True
    except Exception as e:
        logger.warning(f"[RAG v2 Lexical] Upsert failed: {e}")
        return False


def lexical_search(query: str, owner: str, scope: str, top_k: int = 50) -> list[dict]:
    """
    Perform legacy lexical search using FTS5 and BM25 ranking (simulated or built-in).
    SQLite FTS5 has 'bm25(rag_v2_fts)' function.
    """
    try:
        # FTS5 özel karakterlerini escape et
        # FTS5'te sorunlu karakterler: . " ' ( ) * : ^
        import re

        sanitized_query = query
        # FTS5 özel karakterlerini escape et (soru işareti dahil)
        # ? karakteri FTS5'te özel anlam taşımaz ama SQL parametresi ile karıştırılabilir
        # Kullanıcı aramasında geçen ? işaretini kaldırıyoruz
        sanitized_query = re.sub(r'[."\'()*:^?!]', " ", sanitized_query)
        # Çoklu boşlukları tek boşluğa indir
        sanitized_query = re.sub(r"\s+", " ", sanitized_query).strip()

        if not sanitized_query:
            return []

        with _get_connection() as conn:
            # FTS5'te birden fazla kelime OR ile birleştirilmeli
            words = sanitized_query.split()
            if len(words) > 1:
                content_query = " OR ".join(words)
            else:
                content_query = sanitized_query

            # MATCH formatı: content:... AND owner:...
            # Değerleri çift tırnak içine alarak güvenli hale getiriyoruz
            fts_query = f'content:({content_query}) AND owner:"{owner}" AND scope:"{scope}"'

            cursor = conn.execute(
                """
                SELECT
                    filename,
                    page_number,
                    chunk_index,
                    upload_id,
                    content,
                    bm25(rag_v2_fts) as score
                FROM rag_v2_fts
                WHERE rag_v2_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (fts_query, top_k),
            )

            results = []
            for row in cursor:
                # bm25 in sqlite fts5: smaller is better (more negative usually or close to 0?)
                # Actually sqlite bm25 returns negative values (more negative is better) OR
                # positive values where smaller is better?
                # Standard BM25 is Higher is Better.
                # SQLite FTS5 `bm25()` returns a score where *smaller* (more negative) is better?
                # Documentation says: "The lower the value, the more relevant the result."

                results.append(
                    {
                        "filename": row[0],
                        "page_number": int(row[1]) if row[1] is not None else 0,
                        "chunk_index": int(row[2]) if row[2] is not None else 0,
                        "upload_id": row[3],
                        "text": row[4],
                        "bm25_score": row[5],
                    }
                )

            return results

    except Exception as e:
        logger.warning(f"[RAG v2 Lexical] Search failed: {e}")
        return []
