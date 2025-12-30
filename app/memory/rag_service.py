"""
Mami AI - Unified RAG Service (v2 Only)
=======================================

Tüm RAG işlemleri için tek giriş noktası.
Artık sadece RAG v2 (page-aware, hybrid search) kullanılıyor.

Kullanım:
    from app.memory.rag_service import rag_service

    # Belge Ekleme
    rag_service.add_file(file_path, filename, owner)

    # Arama
    results = rag_service.search(query, owner="john")

    # Listeleme
    docs = rag_service.list_user_documents(owner="john")

    # Silme
    rag_service.delete_document_by_filename(filename, owner)
"""

import logging
from pathlib import Path
from typing import Any, Literal

# RAG v2 modülleri
from app.memory import rag_v2

logger = logging.getLogger(__name__)

Scope = Literal["global", "user", "conversation", "web"]


class RagService:
    """RAG işlemlerini yöneten merkezi servis (v2 tabanlı)."""

    # =========================================================================
    # BELGE EKLEME (INGESTION)
    # =========================================================================

    def add_text(
        self, text: str, filename: str, owner: str, scope: Scope = "user", conversation_id: str | None = None
    ) -> int:
        """Metin içeriğini RAG sistemine ekler."""
        try:
            return rag_v2.add_txt_document(
                text=text, filename=filename, owner=owner, scope=scope, conversation_id=conversation_id
            )
        except Exception as e:
            logger.error(f"[RAG_SERVICE] Text ingestion failed: {e}")
            return 0

    def add_file(
        self,
        file_path: str | Path,
        filename: str,
        owner: str,
        scope: Scope = "user",
        conversation_id: str | None = None,
    ) -> int:
        """Dosyadan belge ekler (PDF veya text)."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[RAG_SERVICE] File not found: {path}")
            return 0

        # PDF için page-aware ingestion
        if filename.lower().endswith(".pdf"):
            return rag_v2.add_document_pages_from_pdf(
                file_path=path, filename=filename, owner=owner, scope=scope, conversation_id=conversation_id
            )
        else:
            # Text dosyaları
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                return self.add_text(text, filename, owner, scope, conversation_id)
            except Exception as e:
                logger.error(f"[RAG_SERVICE] File read error: {e}")
                return 0

    # =========================================================================
    # ARAMA (RETRIEVAL)
    # =========================================================================

    def search(
        self,
        query: str,
        owner: str,
        scope: Scope | None = None,
        limit: int = 5,
        conversation_id: str | None = None,
        continue_mode: bool = False,
        mode: str = "deep",
    ) -> list[dict[str, Any]]:
        """
        RAG araması yapar (Hybrid: Vector + Lexical).

        Args:
            query: Arama sorgusu
            owner: Kullanıcı adı
            scope: Erişim kapsamı
            limit: Maksimum sonuç
            conversation_id: Conversation pinning için
            continue_mode: Devam modu (sonraki sayfalar)
            mode: "fast" (sadece vector) veya "deep" (hybrid)

        Returns:
            List[Dict]: Arama sonuçları
        """
        results = []

        try:
            v2_docs = rag_v2.search_documents_v2(
                query=query,
                owner=owner,
                scope=scope or "user",
                top_k=limit * 2,  # Re-ranking için fazla çek
                conversation_id=conversation_id,
                mode=mode,
                continue_mode=continue_mode,
            )

            for d in v2_docs:
                results.append(
                    {
                        "id": d.get("id"),
                        "text": d.get("text"),
                        "metadata": {
                            "filename": d.get("filename"),
                            "page": d.get("page_number"),
                            "chunk_index": d.get("chunk_index"),
                            "upload_id": d.get("upload_id"),
                            "score": d.get("hybrid_score", d.get("score")),
                        },
                        "score": d.get("hybrid_score", d.get("score")),
                    }
                )
        except Exception as e:
            logger.error(f"[RAG_SERVICE] Search error: {e}")

        return results[:limit]

    # =========================================================================
    # YÖNETİM (MANAGEMENT)
    # =========================================================================

    def delete_document(self, doc_id: str) -> bool:
        """Tek bir chunk/doküman siler (ID ile)."""
        return rag_v2.delete_document(doc_id)

    def delete_document_by_filename(self, filename: str, owner: str) -> int:
        """Dosya adına göre tüm chunk'ları siler."""
        return rag_v2.delete_by_filename(filename, owner)

    def delete_by_upload_id(self, upload_id: str, owner: str) -> int:
        """Upload ID'ye göre tüm chunk'ları siler."""
        return rag_v2.delete_by_upload_id(upload_id, owner)

    def list_user_documents(self, owner: str) -> list[dict[str, Any]]:
        """Kullanıcının belgelerini listeler."""
        return rag_v2.list_documents(owner=owner)


# Global instance
rag_service = RagService()
