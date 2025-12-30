# app/memory/conversation_archive.py
"""
Conversation Archive - Blueprint v1 Section 8 Layer 4

Geçmiş sohbet arama ve özet yönetimi:
- Semantic search ile sohbet arşivi sorgulama
- Rolling summary (her 8 turn'da async güncelleme)
- Tarih aralığı filtreleme
- Gateway entegrasyonu için context generation

Kullanım:
    from app.memory.conversation_archive import ConversationArchive
    
    # Geçmiş sohbetlerde ara
    results = await ConversationArchive.search_past_conversations(
        user_id=123,
        query="Geçen hafta ne konuşmuştuk?",
        date_range=(start_date, end_date)
    )
    
    # Rolling summary trigger (her mesaj sonrası)
    triggered = await ConversationArchive.trigger_rolling_summary(conv_id, turn_count)
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass

from sqlmodel import Session, select, col

logger = logging.getLogger("orchestrator.conversation_archive")


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class ArchiveSearchResult:
    """Arşiv arama sonucu."""
    conversation_id: str
    title: str
    summary: str | None
    relevance_score: float
    created_at: datetime
    updated_at: datetime
    message_count: int


@dataclass
class RollingSummaryResult:
    """Rolling summary sonucu."""
    triggered: bool
    conversation_id: str | None = None
    reason: str = ""


# =============================================================================
# DATE RANGE DETECTION
# =============================================================================

class DateRangeDetector:
    """
    Türkçe/İngilizce tarih ifadelerini algılar.
    
    Örnekler:
    - "geçen hafta" → (now - 7 days, now)
    - "dün" → (yesterday, yesterday)
    - "son 3 gün" → (now - 3 days, now)
    """
    
    PATTERNS = [
        # Türkçe
        (r"geçen\s+hafta", lambda: (datetime.utcnow() - timedelta(days=7), datetime.utcnow())),
        (r"bu\s+hafta", lambda: (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday()), datetime.utcnow())),
        (r"dün", lambda: (datetime.utcnow() - timedelta(days=1), datetime.utcnow() - timedelta(days=1))),
        (r"bugün", lambda: (datetime.utcnow().replace(hour=0, minute=0, second=0), datetime.utcnow())),
        (r"son\s+(\d+)\s+gün", lambda m: (datetime.utcnow() - timedelta(days=int(m.group(1))), datetime.utcnow())),
        (r"geçen\s+ay", lambda: (datetime.utcnow() - timedelta(days=30), datetime.utcnow())),
        
        # İngilizce
        (r"last\s+week", lambda: (datetime.utcnow() - timedelta(days=7), datetime.utcnow())),
        (r"yesterday", lambda: (datetime.utcnow() - timedelta(days=1), datetime.utcnow() - timedelta(days=1))),
        (r"last\s+(\d+)\s+days", lambda m: (datetime.utcnow() - timedelta(days=int(m.group(1))), datetime.utcnow())),
    ]
    
    @classmethod
    def detect(cls, query: str) -> tuple[datetime, datetime] | None:
        """
        Sorgudan tarih aralığı algılar.
        
        Returns:
            Tuple[datetime, datetime] | None: (start, end) veya None
        """
        query_lower = query.lower()
        
        for pattern, resolver in cls.PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    if match.groups():
                        return resolver(match)
                    else:
                        return resolver()
                except Exception as e:
                    logger.warning(f"[ARCHIVE] Date detection error: {e}")
        
        return None
    
    @classmethod
    def should_search_archive(cls, query: str) -> bool:
        """
        Sorgu arşiv araması gerektiriyor mu?
        
        Blueprint: "geçen hafta", "daha önce" gibi ifadeler arşiv tetikler.
        """
        archive_keywords = [
            "geçen", "daha önce", "önceki", "hatırla", "konuşmuştuk",
            "last", "before", "previous", "remember", "discussed"
        ]
        
        query_lower = query.lower()
        return any(kw in query_lower for kw in archive_keywords)


# =============================================================================
# CONVERSATION ARCHIVE SERVICE
# =============================================================================

class ConversationArchive:
    """
    Conversation Archive Service - Blueprint v1 Section 8 Layer 4.
    
    Geçmiş sohbet arama ve rolling summary yönetimi.
    """
    
    # Rolling summary trigger interval
    ROLLING_SUMMARY_INTERVAL = 8  # Her 8 turn'da bir
    
    # Search settings
    MAX_SEARCH_RESULTS = 10
    MIN_RELEVANCE_THRESHOLD = 0.3
    
    # ==========================================================================
    # SEMANTIC SEARCH
    # ==========================================================================
    
    @classmethod
    async def search_past_conversations(
        cls,
        user_id: int,
        query: str,
        date_range: tuple[datetime, datetime] | None = None,
        limit: int | None = None
    ) -> list[ArchiveSearchResult]:
        """
        Geçmiş sohbetlerde semantic search yapar.
        
        Args:
            user_id: Kullanıcı ID
            query: Arama sorgusu
            date_range: Tarih aralığı (start, end). None ise tüm geçmiş.
            limit: Maksimum sonuç sayısı
            
        Returns:
            List[ArchiveSearchResult]: Sıralı arama sonuçları
        """
        from app.core.database import get_session
        from app.core.models import Conversation, ConversationSummary, Message
        
        max_results = limit or cls.MAX_SEARCH_RESULTS
        
        # Tarih aralığı algılama
        if date_range is None:
            date_range = DateRangeDetector.detect(query)
        
        try:
            with get_session() as session:
                # Base query: kullanıcının sohbetleri + özetleri
                conversations = await cls._get_user_conversations(
                    session, user_id, date_range
                )
                
                if not conversations:
                    logger.debug(f"[ARCHIVE] No conversations found for user {user_id}")
                    return []
                
                # Özetlerle eşleştir ve skorla
                results = []
                for conv in conversations:
                    # Summary al
                    summary = session.get(ConversationSummary, conv.id)
                    summary_text = summary.summary if summary else ""
                    
                    # Mesaj sayısını al
                    msg_count = await cls._get_message_count(session, conv.id)
                    
                    # Relevance skorla (basit keyword matching, gelecekte LLM)
                    relevance = cls._calculate_relevance(query, conv.title or "", summary_text)
                    
                    if relevance >= cls.MIN_RELEVANCE_THRESHOLD:
                        results.append(ArchiveSearchResult(
                            conversation_id=conv.id,
                            title=conv.title or "Untitled",
                            summary=summary_text if summary_text else None,
                            relevance_score=relevance,
                            created_at=conv.created_at,
                            updated_at=conv.updated_at,
                            message_count=msg_count,
                        ))
                
                # Relevance'a göre sırala
                results.sort(key=lambda x: x.relevance_score, reverse=True)
                
                logger.info(f"[ARCHIVE] Search: user={user_id}, results={len(results[:max_results])}")
                return results[:max_results]
                
        except Exception as e:
            logger.error(f"[ARCHIVE] Search error: {e}")
            return []
    
    @classmethod
    async def _get_user_conversations(
        cls,
        session: Session,
        user_id: int,
        date_range: tuple[datetime, datetime] | None
    ) -> list:
        """Kullanıcının sohbetlerini date range ile filtreler."""
        from app.core.models import Conversation
        
        query = select(Conversation).where(Conversation.user_id == user_id)
        
        if date_range:
            start, end = date_range
            query = query.where(
                Conversation.updated_at >= start,
                Conversation.updated_at <= end
            )
        
        query = query.order_by(col(Conversation.updated_at).desc())
        
        return list(session.exec(query).all())
    
    @classmethod
    async def _get_message_count(cls, session: Session, conv_id: str) -> int:
        """Sohbetteki mesaj sayısını döndürür."""
        from app.core.models import Message
        from sqlalchemy import func
        
        result = session.exec(
            select(func.count()).where(Message.conversation_id == conv_id)
        ).first()
        
        return result or 0
    
    @classmethod
    def _calculate_relevance(cls, query: str, title: str, summary: str) -> float:
        """
        Basit keyword-based relevance hesaplama.
        
        Future: LLM-based semantic matching.
        """
        query_words = set(query.lower().split())
        
        # Stop words çıkar
        stop_words = {"ne", "nasıl", "nerede", "kim", "bu", "şu", "bir", "ve", "ile"}
        query_words = query_words - stop_words
        
        if not query_words:
            return 0.5  # Neutral score for generic queries
        
        # Title ve summary'de keyword ara
        content = f"{title} {summary}".lower()
        
        matches = sum(1 for word in query_words if word in content)
        
        # Normalize (0-1)
        score = matches / len(query_words) if query_words else 0.0
        
        # Boost for longer summaries (more context = more relevant)
        if summary and len(summary) > 100:
            score = min(1.0, score + 0.1)
        
        return score
    
    # ==========================================================================
    # ROLLING SUMMARY
    # ==========================================================================
    
    @classmethod
    async def trigger_rolling_summary(
        cls,
        conversation_id: str,
        turn_count: int,
        force: bool = False
    ) -> RollingSummaryResult:
        """
        Rolling summary güncelleme tetikler.
        
        Blueprint v1: "Her 8 turn'da özet güncelle"
        
        Args:
            conversation_id: Sohbet ID
            turn_count: Mevcut turn sayısı
            force: True ise interval'ı atla
            
        Returns:
            RollingSummaryResult: Tetikleme sonucu
        """
        # Check interval
        should_trigger = force or (turn_count > 0 and turn_count % cls.ROLLING_SUMMARY_INTERVAL == 0)
        
        if not should_trigger:
            return RollingSummaryResult(
                triggered=False,
                reason=f"interval_not_reached (turn={turn_count}, interval={cls.ROLLING_SUMMARY_INTERVAL})"
            )
        
        # Async task olarak tetikle (ana akışı bloklamaz)
        asyncio.create_task(cls._update_summary_async(conversation_id))
        
        logger.info(f"[ARCHIVE] Rolling summary triggered: conv={conversation_id}, turn={turn_count}")
        
        return RollingSummaryResult(
            triggered=True,
            conversation_id=conversation_id,
            reason="interval_reached"
        )
    
    @classmethod
    async def trigger_immediate_summary(cls, conversation_id: str, reason: str) -> RollingSummaryResult:
        """
        Kritik bilgi için anında özet güncelleme.
        
        Blueprint: "Beni X diye çağır", "Hatırla" gibi kritik ifadeler için.
        """
        asyncio.create_task(cls._update_summary_async(conversation_id))
        
        logger.info(f"[ARCHIVE] Immediate summary triggered: conv={conversation_id}, reason={reason}")
        
        return RollingSummaryResult(
            triggered=True,
            conversation_id=conversation_id,
            reason=f"immediate:{reason}"
        )
    
    @classmethod
    async def _update_summary_async(cls, conversation_id: str) -> bool:
        """
        Async olarak sohbet özetini günceller.
        
        Bu fonksiyon create_task ile çağrılır, ana akışı bloklamaz.
        """
        from app.core.database import get_session
        from app.core.models import Conversation, Message, ConversationSummary
        
        try:
            with get_session() as session:
                # Son mesajları al
                messages = session.exec(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(col(Message.created_at).desc())
                    .limit(20)  # Son 20 mesaj
                ).all()
                
                if not messages:
                    return False
                
                # Mesajları formatla
                message_text = "\n".join([
                    f"{'User' if m.role == 'user' else 'Assistant'}: {m.content[:200]}"
                    for m in reversed(messages)
                ])
                
                # Basit özet oluştur (LLM yerine heuristic)
                # Future: LLM call for better summarization
                summary_text = cls._generate_simple_summary(message_text)
                
                # Summary kaydet/güncelle
                existing = session.get(ConversationSummary, conversation_id)
                
                if existing:
                    existing.summary = summary_text
                    existing.updated_at = datetime.utcnow()
                    existing.message_count_at_update = len(messages)
                else:
                    new_summary = ConversationSummary(
                        conversation_id=conversation_id,
                        summary=summary_text,
                        updated_at=datetime.utcnow(),
                        message_count_at_update=len(messages),
                    )
                    session.add(new_summary)
                
                session.commit()
                logger.debug(f"[ARCHIVE] Summary updated: conv={conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"[ARCHIVE] Summary update error: {e}")
            return False
    
    @classmethod
    def _generate_simple_summary(cls, messages: str) -> str:
        """
        Basit heuristic-based özet oluşturur.
        
        Future: LLM ile daha iyi özet.
        """
        # İlk 500 karakter + son 500 karakter
        if len(messages) <= 1000:
            return f"Sohbet içeriği: {messages[:500]}..."
        
        first_part = messages[:500]
        last_part = messages[-500:]
        
        return f"Sohbet başlangıcı: {first_part}... | Son kısım: ...{last_part}"
    
    # ==========================================================================
    # GATEWAY INTEGRATION
    # ==========================================================================
    
    @classmethod
    async def get_archive_context(
        cls,
        user_id: int,
        query: str,
        max_results: int = 3
    ) -> dict[str, Any]:
        """
        Gateway için arşiv context'i döndürür.
        
        Args:
            user_id: Kullanıcı ID
            query: Kullanıcı sorgusu
            max_results: Maksimum sonuç
            
        Returns:
            dict: {
                "should_search": bool,
                "results": List[dict],
                "date_range_detected": bool,
                "summary": str
            }
        """
        # Arşiv araması gerekli mi?
        should_search = DateRangeDetector.should_search_archive(query)
        
        if not should_search:
            return {
                "should_search": False,
                "results": [],
                "date_range_detected": False,
                "summary": "",
                "available": True
            }
        
        # Arama yap
        date_range = DateRangeDetector.detect(query)
        results = await cls.search_past_conversations(
            user_id=user_id,
            query=query,
            date_range=date_range,
            limit=max_results
        )
        
        # Format results
        formatted = [
            {
                "conv_id": r.conversation_id,
                "title": r.title,
                "summary": r.summary,
                "relevance": r.relevance_score,
                "date": r.updated_at.strftime("%Y-%m-%d"),
            }
            for r in results
        ]
        
        # Generate summary for context
        if results:
            summary_parts = [f"'{r.title}' ({r.updated_at.strftime('%d %b')})" for r in results[:3]]
            summary = f"Bulunan ilgili sohbetler: {', '.join(summary_parts)}"
        else:
            summary = "Belirtilen dönemde ilgili sohbet bulunamadı."
        
        return {
            "should_search": True,
            "results": formatted,
            "date_range_detected": date_range is not None,
            "summary": summary,
            "available": True
        }
    
    # ==========================================================================
    # CRITICAL INFO DETECTION
    # ==========================================================================
    
    @classmethod
    def has_critical_info(cls, message: str) -> bool:
        """
        Mesaj kritik bilgi içeriyor mu?
        
        Blueprint: "Beni X diye çağır", "Hatırla" gibi ifadeler.
        """
        critical_patterns = [
            r"beni\s+(.+?)\s+diye\s+çağır",
            r"adım\s+(.+)",
            r"bana\s+(.+?)\s+de",
            r"hatırla.?\s*:",
            r"unutma.?\s*:",
            r"not\s+al",
            r"kaydet",
        ]
        
        message_lower = message.lower()
        
        for pattern in critical_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
