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
from typing import Any, Literal, List, Dict

# RAG v2 modülleri
from app.memory import rag_v2
from app.core.telemetry.service import telemetry
from app.schemas.rdr import EventType
from app.core.terminal import log

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
            logger.error(f"[RAG_SERVICE] Text ingestion failed: {e}", exc_info=True)
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
            logger.error(f"[RAG_SERVICE] File not found: {path}", exc_info=False)  # File not found doesn't need traceback
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
                logger.error(f"[RAG_SERVICE] File read error: {e}", exc_info=True)
                return 0

    # =========================================================================
    # ARAMA (RETRIEVAL)
    # =========================================================================

    async def search(
        self,
        query: str,
        owner: str = "global",
        limit: int = 5,
        scope: Scope = None,
        mode: str = "fast",
        conversation_id: str | None = None,
        continue_mode: bool = False,
    ) -> list[dict]:
        """
        Belgeler içinde anlamsal ve lexical arama yapar.
        
        Args:
            query: Arama sorgusu
            owner: Belge sahibi
            limit: Döndürülecek sonuç sayısı
            scope: Arama kapsamı
            mode: "fast" (Hızlı) veya "deep" (Derin/Rerank)
            conversation_id: Konuşma kimliği (Pinleme için)
            continue_mode: Kaldığın yerden devam etme modu
            
        Returns:
            list[dict]: Arama sonuçları
        """
        results = []

        try:
            v2_docs = await rag_v2.search_documents_v2(
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
            
            # Multi-document summarization (if detected)
            from app.memory import rag_v2_multi_doc
            
            if rag_v2_multi_doc.detect_multi_doc_query(query):
                logger.info("[RAG Service] Multi-doc query detected")
                
                try:
                    multi_doc_result = await rag_v2_multi_doc.generate_multi_doc_summary(
                        query=query,
                        candidates=v2_docs[:15],
                        top_k_per_doc=3
                    )
                    
                    if multi_doc_result and multi_doc_result.get("summary"):
                        # Prepend summary to results
                        summary_chunk = {
                            "id": "multi_doc_summary",
                            "text": multi_doc_result["summary"],
                            "metadata": {
                                "filename": "🔍 ÇOKLU BELGE ÖZETİ",
                                "page": 0,
                                "chunk_index": -999,
                                "upload_id": None,
                                "score": 0.0,
                                "is_multi_doc_summary": True,
                                "sources": multi_doc_result["sources_breakdown"],
                                "total_docs": multi_doc_result["total_docs"]
                            },
                            "score": 0.0
                        }
                        
                        results.insert(0, summary_chunk)
                        logger.info(f"[RAG Service] Multi-doc summary from {multi_doc_result['total_docs']} docs")
                
                except Exception as e:
                    logger.warning(f"[RAG Service] Multi-doc summary failed: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"[RAG_SERVICE] Search error: {e}", exc_info=True)

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

    async def get_shadow_context(self, query: str, owner: str) -> str:
        """
        [SHADOW SEARCH] - Plânlama aşamasında doküman farkındalığı sağlar.
        Hangi belgelerin ne kadar alakalı olduğunu özetler.
        """
        try:
            # Sadece Vektör araması (en hızlısı ve hafif olanı)
            # [FIX] scope parametresi eklendi
            v2_docs = await rag_v2.search_documents_v2(query=query, owner=owner, scope="user", top_k=3, mode="fast")

            if not v2_docs:
                log.info("🔍 [SHADOW SEARCH] Sonuç bulunamadı.")
                return ""

            # Alakalı belgeleri ve skorları topla
            relevant_files = {}
            for d in v2_docs:
                fname = d.get("filename", "Bilinmeyen")
                # V2 distance score (lower is better)
                score = d.get("score", 1.0)
                relevance = max(0, int((1 - score) * 100))

                if fname not in relevant_files or relevance > relevant_files[fname]:
                    relevant_files[fname] = relevance

            # Raporlama eşiği: Hibrit arama sayesinde %30'a düşürüldü (Daha hassas)
            items = [f"{name} (%{score} alaka)" for name, score in relevant_files.items() if score > 30]
            
            if items:
                log.info(f"🔍 [SHADOW SEARCH] Tespit Edildi: {', '.join(items)}")
            else:
                log.info(f"🔍 [SHADOW SEARCH] Düşük Alaka: {list(relevant_files.values())}")
            
            # [TELEMETRY] Emit discovery event
            if items:
                telemetry.emit(
                    EventType.RETRIEVAL,
                    {"op": "shadow_discovery", "files": list(relevant_files.keys()), "top_score": max(relevant_files.values())},
                    component="rag_service"
                )

            if not relevant_files:
                return ""

            # Tüm tespit edilenleri (zayıf olsa bile) orkestratöre haber ver
            all_detected = [f"{name} (%{score})" for name, score in relevant_files.items()]
            return f"\n[SHADOW SEARCH]: Soruyla alakalı olabilecek belgeler tespit edildi: {', '.join(all_detected)}. Eğer bu belgelerden spesifik bilgi gerekiyorsa 'document_tool' aracını plânına ekle."

        except Exception as e:
            log.error("🔍 [SHADOW SEARCH] Kritik Hata", e)
            return ""


# Global instance
rag_service = RagService()
