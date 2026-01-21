from typing import Any

from app.core.logger import get_logger
from app.memory.rag_service import rag_service

# from app.core.feature_flags import is_rag_v2_enabled_for_user, feature_enabled # Lazy import

logger = get_logger(__name__)

# Sabitler
GROQ_HISTORY_LIMIT = 24
CONTEXT_CHAR_LIMIT = 8000
HISTORY_TOKEN_BUDGET_GROQ = 3000
HISTORY_TOKEN_BUDGET_LOCAL = 1500
CONTEXT_TRUNCATED_NOTICE = "### BAĞLAM KISALTILDI\nBağlam çok uzun olduğu için sadece son kısımlar korunuyor."


class ContextService:
    """Chat context ve history yönetiminden sorumlu servis."""

    @staticmethod
    def _truncate_context_text(content: str) -> str:
        """Context metnini akıllıca truncate eder."""
        from app.services.context_truncation_manager import context_manager

        if len(content) <= CONTEXT_CHAR_LIMIT:
            return content

        return context_manager.truncate_text_smart(content, char_limit=CONTEXT_CHAR_LIMIT, add_notice=True)

    @staticmethod
    def _format_context_block(title: str, lines: list[str]) -> str:
        return f"### {title}\n" + "\n".join(lines).strip()

    @staticmethod
    def build_history_budget(
        username: str,
        conversation_id: str | None,
        *,
        token_budget: int,
    ) -> list[dict[str, str]]:
        """Token budget'a göre sohbet geçmişi oluşturur."""
        if not conversation_id:
            return []

        from app.memory.conversation import load_messages
        from app.services.context_truncation_manager import context_manager

        messages = load_messages(username, conversation_id)
        if not messages:
            return []

        cooked: list[dict[str, str]] = []
        for msg in messages:
            text = getattr(msg, "content", getattr(msg, "text", ""))
            if not text:
                continue
            role = msg.role
            role = "assistant" if role == "bot" else role
            if role not in ("user", "assistant"):
                continue
            cooked.append({"role": role, "content": text})

        if not cooked:
            return []

        selected, was_truncated = context_manager.truncate_messages_by_importance(
            cooked, token_budget, preserve_system=False
        )

        if was_truncated:
            logger.info(f"[HISTORY] {len(cooked)} mesaj → {len(selected)} mesaj (importance-based)")

        return selected

    @staticmethod
    def normalize_groq_history(raw_history: list[dict[str, str]]) -> list[dict[str, str]]:
        """History'yi Groq formatına normalize eder."""
        normalized: list[dict[str, str]] = []
        for entry in raw_history:
            role = entry.get("role")
            content = entry.get("content")
            if not content:
                continue
            mapped_role = "assistant" if role == "bot" else role
            if mapped_role not in {"user", "assistant"}:
                continue
            normalized.append({"role": mapped_role, "content": content})
        return normalized

    @staticmethod
    def build_memory_hint(memory_blocks: dict[str, Any]) -> str:
        """Memory bloklarından prompt hint'i oluşturur."""
        hints = []
        if memory_blocks.get("summary"):
            hints.append(f"Önceki konuşma özeti: {memory_blocks['summary']}")
        if memory_blocks.get("personal"):
            hints.append(f"Kişisel hafıza: {'; '.join(memory_blocks['personal'])}")
        if memory_blocks.get("recent"):
            hints.append(f"Son mesajlar: {memory_blocks['recent']}")
        return "\n".join(filter(None, hints)).strip()

    @classmethod
    async def build_enhanced_context(
        cls,
        username: str,
        message: str,
        conversation_id: str | None,
        user: Any | None = None,
        rag_v2_continue_mode: bool = False,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Zenginleştirilmiş context oluşturur.
        """
        from app.memory.conversation import get_conversation_summary_text
        from app.memory.store import search_memories
        from app.services.query_enhancer import enhance_query_for_search

        sections: list[str] = []

        # 1. Sohbet özeti
        if conversation_id:
            try:
                summary = get_conversation_summary_text(conversation_id)
                if summary:
                    summary_block = f"📋 ÖNCEKİ SOHBET ÖZETİ:\n{summary}"
                    sections.append(summary_block)
            except Exception as exc:
                logger.error(f"[CONTEXT] Summary okunamadı: {exc}")

        # 2. Multi-query memory search
        try:
            search_queries = await enhance_query_for_search(message, max_queries=3)
        except Exception as e:
            logger.debug(f"[CONTEXT] Query enhancement failed, using original: {e}")
            search_queries = [message]

        all_memories = []
        seen_memory_texts = set()

        for query in search_queries:
            try:
                results = await search_memories(username, query, max_items=15)
                for mem in results:
                    text = getattr(mem, "text", "")
                    if text and text not in seen_memory_texts:
                        seen_memory_texts.add(text)
                        all_memories.append(mem)
            except Exception as exc:
                logger.error(f"[CONTEXT] Hafıza aranamadı: {exc}")

        # Importance'a göre sırala
        def get_memory_score(memory) -> float:
            importance = getattr(memory, "importance", 0.5)
            relevance = getattr(memory, "relevance", getattr(memory, "score", 0.5))
            return (importance * 0.6) + (relevance * 0.4)

        sorted_memories = sorted(all_memories, key=get_memory_score, reverse=True)

        all_texts = [getattr(m, "text", "").strip() for m in sorted_memories if getattr(m, "text", "")]
        critical_texts = all_texts[:8]
        other_texts = all_texts[8:]

        profile_lines = []
        if critical_texts:
            profile_lines.append("🧠 Kullanıcı hakkında bilinen önemli bilgiler:")
            profile_lines.extend(f"- {item}" for item in critical_texts)

        other_lines = []
        seen_texts = set(critical_texts)
        for stripped in other_texts:
            if stripped not in seen_texts:
                other_lines.append(f"- {stripped}")
                seen_texts.add(stripped)

        if profile_lines:
            sections.append(cls._format_context_block("KULLANICI PROFİLİ (ÖNEMLİ)", profile_lines))
        if other_lines:
            sections.append(cls._format_context_block("İLGİLİ HAFIZALAR", other_lines))

        # RAG dokümanları (Query Expansion + Multi-Query + V2 Service)
        rag_lines = []
        seen_doc_ids = set()

        # Query expansion: "tck 157" -> ["tck 157", "madde 157", "157"]
        try:
            from app.memory.query_expander import get_search_queries

            rag_queries = get_search_queries(message, max_queries=4)
            logger.debug(f"[CONTEXT] Expanded queries: {rag_queries}")
        except Exception:
            rag_queries = search_queries

        try:
            deduplicated_docs = []
            for q in rag_queries:
                # rag_service varsayılan olarak v2 kullanır, continue_mode destekler
                docs = rag_service.search(
                    q, owner=username, limit=5, conversation_id=conversation_id, continue_mode=rag_v2_continue_mode
                )

                for doc in docs:
                    doc_id = doc.get("id")
                    if doc_id not in seen_doc_ids:
                        seen_doc_ids.add(doc_id)
                        deduplicated_docs.append(doc)

            for doc in deduplicated_docs[:8]:
                text = doc.get("text", "") or ""
                meta = doc.get("metadata", {}) or {}
                filename = meta.get("filename", "Doküman")

                preview = (text[:1000] + "...") if len(text) > 1000 else text
                rag_lines.append(f"- [{filename}] {preview}")

        except Exception as exc:
            logger.error(f"[CONTEXT] RAG service error: {exc}")

        if rag_lines:
            rag_header = [
                "⚠️ ÖNEMLİ: Aşağıdaki belgeler kullanıcının yüklediği dosyalardan alınmıştır.",
                "SADECE bu belgelerdeki bilgileri kullanarak yanıt ver.",
                "Kendi bilgini veya tahminini EKLEME.",
                "",
            ]
            rag_header.extend(rag_lines)
            sections.append(cls._format_context_block("İLGİLİ BELGELER (RAG) - MUTLAKA KULLAN", rag_header))

        header = "📚 BAĞLAM BİLGİLERİ\n\n"
        full_context = header + "\n\n".join(sections)

        # Decider için memory structured data
        memories_for_decider = []
        for m in sorted_memories:
            memories_for_decider.append(
                {
                    "id": getattr(m, "id", "unknown"),
                    "text": getattr(m, "text", ""),
                    "importance": getattr(m, "importance", 0.5),
                }
            )

        return cls._truncate_context_text(full_context), memories_for_decider


# Global instance
context_service = ContextService()
