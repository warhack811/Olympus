# app/memory/working_memory.py
"""
Working Memory - Redis Tabanlı Session Hafızası

Blueprint v1 Section 8 Layer 1 uyumlu:
- Son N mesaj cache (varsayılan 10)
- Session summary
- RAG cache (query-based)
- TTL: 48 saat (configurable)
- Fail-soft: Redis yoksa graceful degradation

Key Yapısı:
- wm:{user_id}:msgs         → Son mesajlar (List)
- wm:{user_id}:summary      → Session özeti (String)
- wm:{user_id}:rag:{hash}   → RAG cache (String/JSON)
- wm:{user_id}:facts        → Anlık facts (Set)
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("orchestrator.working_memory")


# =============================================================================
# KEY PATTERNS (Blueprint v1)
# =============================================================================

class WorkingMemoryKeys:
    """Redis key pattern'leri. Merkezi yönetim için."""
    
    PREFIX = "wm"
    
    @classmethod
    def messages(cls, user_id: int | str) -> str:
        """Son mesajlar listesi: wm:{user_id}:msgs"""
        return f"{cls.PREFIX}:{user_id}:msgs"
    
    @classmethod
    def summary(cls, user_id: int | str) -> str:
        """Session özeti: wm:{user_id}:summary"""
        return f"{cls.PREFIX}:{user_id}:summary"
    
    @classmethod
    def rag_cache(cls, user_id: int | str, query_hash: str) -> str:
        """RAG sorgu cache: wm:{user_id}:rag:{hash}"""
        return f"{cls.PREFIX}:{user_id}:rag:{query_hash}"
    
    @classmethod
    def facts(cls, user_id: int | str) -> str:
        """Anlık facts: wm:{user_id}:facts"""
        return f"{cls.PREFIX}:{user_id}:facts"
    
    @classmethod
    def all_user_keys(cls, user_id: int | str) -> str:
        """Kullanıcının tüm working memory key'leri (pattern)"""
        return f"{cls.PREFIX}:{user_id}:*"


# =============================================================================
# WORKING MEMORY SERVICE
# =============================================================================

class WorkingMemory:
    """
    Working Memory Servisi - Redis backed session cache.
    
    Blueprint v1 Section 8 Layer 1 implementasyonu:
    - Son 10 mesaj + session summary + RAG cache
    - TTL: 48 saat
    - Fail-soft: Redis yoksa None/boş list döner
    
    Tüm metodlar async ve idempotent.
    """
    
    # ==========================================================================
    # CONFIG (Settings'ten yüklenir)
    # ==========================================================================
    
    @classmethod
    def _get_config(cls) -> tuple[int, int]:
        """TTL ve max_messages değerlerini döndürür."""
        try:
            from app.config import get_settings
            s = get_settings()
            return s.ORCH_WORKING_MEMORY_TTL, s.ORCH_WORKING_MEMORY_MAX_MESSAGES
        except Exception:
            return 172800, 10  # 48 saat, 10 mesaj (safe default)
    
    @classmethod
    def _get_ttl(cls) -> int:
        """TTL in seconds."""
        ttl, _ = cls._get_config()
        return ttl
    
    @classmethod
    def _get_max_messages(cls) -> int:
        """Max messages to keep."""
        _, max_msgs = cls._get_config()
        return max_msgs
    
    # ==========================================================================
    # MESSAGES (Son N mesaj)
    # ==========================================================================
    
    @classmethod
    async def get_recent_messages(
        cls, 
        user_id: int | str, 
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Kullanıcının son mesajlarını getirir.
        
        Args:
            user_id: Kullanıcı ID
            limit: Maksimum mesaj sayısı (None = config'den)
            
        Returns:
            List[dict]: Mesaj listesi [{role, content, timestamp}, ...]
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            logger.debug(f"[WM] Redis yok, boş liste dönüyor (user={user_id})")
            return []
        
        try:
            key = WorkingMemoryKeys.messages(user_id)
            max_msgs = limit or cls._get_max_messages()
            
            # Son N mesajı al (LRANGE: 0'dan max_msgs-1'e)
            raw_messages = await client.lrange(key, 0, max_msgs - 1)
            
            messages = []
            for raw in raw_messages:
                try:
                    msg = json.loads(raw)
                    messages.append(msg)
                except json.JSONDecodeError:
                    logger.warning(f"[WM] Geçersiz JSON mesaj: {raw[:50]}")
                    
            return messages
            
        except Exception as e:
            logger.error(f"[WM] Mesaj okuma hatası: {e}")
            return []
    
    @classmethod
    async def append_message(
        cls,
        user_id: int | str,
        role: str,
        content: str,
        extra_metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        Yeni mesaj ekler ve eski mesajları trim eder.
        
        Args:
            user_id: Kullanıcı ID
            role: user | assistant | system
            content: Mesaj içeriği
            extra_metadata: Ek metadata (opsiyonel)
            
        Returns:
            bool: Başarılı ise True
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            logger.debug(f"[WM] Redis yok, mesaj kaydedilmedi (user={user_id})")
            return False
        
        try:
            key = WorkingMemoryKeys.messages(user_id)
            ttl = cls._get_ttl()
            max_msgs = cls._get_max_messages()
            
            # Mesaj objesi
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if extra_metadata:
                message["metadata"] = extra_metadata
            
            # Pipeline: LPUSH + LTRIM + EXPIRE (atomik)
            async with client.pipeline() as pipe:
                pipe.lpush(key, json.dumps(message, ensure_ascii=False))
                pipe.ltrim(key, 0, max_msgs - 1)  # İlk N'i tut
                pipe.expire(key, ttl)
                await pipe.execute()
            
            logger.debug(f"[WM] Mesaj eklendi: user={user_id}, role={role}")
            return True
            
        except Exception as e:
            logger.error(f"[WM] Mesaj ekleme hatası: {e}")
            return False
    
    @classmethod
    async def clear_messages(cls, user_id: int | str) -> bool:
        """Kullanıcının tüm mesajlarını siler."""
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            key = WorkingMemoryKeys.messages(user_id)
            await client.delete(key)
            logger.debug(f"[WM] Mesajlar silindi: user={user_id}")
            return True
        except Exception as e:
            logger.error(f"[WM] Mesaj silme hatası: {e}")
            return False
    
    # ==========================================================================
    # SESSION SUMMARY (Sohbet özeti)
    # ==========================================================================
    
    @classmethod
    async def get_session_summary(cls, user_id: int | str) -> str | None:
        """
        Session özetini getirir.
        
        Returns:
            str | None: Özet metni veya None
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return None
        
        try:
            key = WorkingMemoryKeys.summary(user_id)
            summary = await client.get(key)
            return summary
        except Exception as e:
            logger.error(f"[WM] Özet okuma hatası: {e}")
            return None
    
    @classmethod
    async def update_session_summary(
        cls, 
        user_id: int | str, 
        summary: str,
        refresh_ttl: bool = True
    ) -> bool:
        """
        Session özetini günceller.
        
        Args:
            user_id: Kullanıcı ID
            summary: Özet metni
            refresh_ttl: TTL'i yenile (varsayılan True)
            
        Returns:
            bool: Başarılı ise True
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            key = WorkingMemoryKeys.summary(user_id)
            ttl = cls._get_ttl() if refresh_ttl else None
            
            if ttl:
                await client.setex(key, ttl, summary)
            else:
                await client.set(key, summary)
                
            logger.debug(f"[WM] Özet güncellendi: user={user_id}, len={len(summary)}")
            return True
        except Exception as e:
            logger.error(f"[WM] Özet güncelleme hatası: {e}")
            return False
    
    # ==========================================================================
    # RAG CACHE (Query-based cache)
    # ==========================================================================
    
    @classmethod
    def _hash_query(cls, query: str) -> str:
        """Sorguyu hash'ler (cache key için)."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    @classmethod
    async def get_cached_rag(
        cls, 
        user_id: int | str, 
        query: str
    ) -> list[dict[str, Any]] | None:
        """
        RAG cache'den sonuç getirir.
        
        Args:
            user_id: Kullanıcı ID
            query: Arama sorgusu
            
        Returns:
            List[dict] | None: Cache'lenmiş RAG sonuçları veya None (miss)
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return None
        
        try:
            query_hash = cls._hash_query(query)
            key = WorkingMemoryKeys.rag_cache(user_id, query_hash)
            
            cached = await client.get(key)
            if cached:
                logger.debug(f"[WM] RAG cache HIT: user={user_id}, hash={query_hash}")
                return json.loads(cached)
            
            logger.debug(f"[WM] RAG cache MISS: user={user_id}, hash={query_hash}")
            return None
            
        except Exception as e:
            logger.error(f"[WM] RAG cache okuma hatası: {e}")
            return None
    
    @classmethod
    async def set_cached_rag(
        cls,
        user_id: int | str,
        query: str,
        results: list[dict[str, Any]],
        ttl: int | None = None
    ) -> bool:
        """
        RAG sonuçlarını cache'ler.
        
        Args:
            user_id: Kullanıcı ID
            query: Arama sorgusu
            results: Cache'lenecek RAG sonuçları
            ttl: Cache TTL (saniye, None = 1 saat)
            
        Returns:
            bool: Başarılı ise True
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            query_hash = cls._hash_query(query)
            key = WorkingMemoryKeys.rag_cache(user_id, query_hash)
            cache_ttl = ttl or 3600  # 1 saat varsayılan
            
            await client.setex(key, cache_ttl, json.dumps(results, ensure_ascii=False))
            logger.debug(f"[WM] RAG cached: user={user_id}, hash={query_hash}, ttl={cache_ttl}")
            return True
            
        except Exception as e:
            logger.error(f"[WM] RAG cache yazma hatası: {e}")
            return False
    
    # ==========================================================================
    # INSTANT FACTS (Anlık bilgiler - yeni konuşmada öğrenilen)
    # ==========================================================================
    
    @classmethod
    async def add_fact(cls, user_id: int | str, fact: str) -> bool:
        """
        Anlık fact ekler (Blueprint: Yeni fact gecikmesi önleme).
        
        Args:
            user_id: Kullanıcı ID
            fact: Öğrenilen bilgi
            
        Returns:
            bool: Başarılı ise True
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            key = WorkingMemoryKeys.facts(user_id)
            ttl = cls._get_ttl()
            
            async with client.pipeline() as pipe:
                pipe.sadd(key, fact)
                pipe.expire(key, ttl)
                await pipe.execute()
                
            logger.debug(f"[WM] Fact eklendi: user={user_id}, fact={fact[:50]}")
            return True
        except Exception as e:
            logger.error(f"[WM] Fact ekleme hatası: {e}")
            return False
    
    @classmethod
    async def get_facts(cls, user_id: int | str) -> list[str]:
        """
        Anlık facts'leri getirir.
        
        Returns:
            List[str]: Fact listesi
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return []
        
        try:
            key = WorkingMemoryKeys.facts(user_id)
            facts = await client.smembers(key)
            return list(facts)
        except Exception as e:
            logger.error(f"[WM] Facts okuma hatası: {e}")
            return []
    
    # ==========================================================================
    # UTILITY
    # ==========================================================================
    
    @classmethod
    async def clear_all(cls, user_id: int | str) -> bool:
        """
        Kullanıcının tüm working memory verisini siler.
        
        Returns:
            bool: Başarılı ise True
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            pattern = WorkingMemoryKeys.all_user_keys(user_id)
            
            # SCAN ile key'leri bul ve sil (büyük DB'lerde KEYS kullanma!)
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            
            logger.info(f"[WM] Tüm veriler silindi: user={user_id}, count={deleted}")
            return True
        except Exception as e:
            logger.error(f"[WM] Toplu silme hatası: {e}")
            return False
    
    @classmethod
    async def refresh_ttl(cls, user_id: int | str) -> bool:
        """
        Kullanıcının tüm key'lerinin TTL'ini yeniler.
        
        Aktif kullanıcılar için TTL uzatma.
        """
        from app.core.redis_client import get_redis
        
        client = await get_redis()
        if client is None:
            return False
        
        try:
            ttl = cls._get_ttl()
            keys = [
                WorkingMemoryKeys.messages(user_id),
                WorkingMemoryKeys.summary(user_id),
                WorkingMemoryKeys.facts(user_id),
            ]
            
            for key in keys:
                # Key varsa TTL yenile
                if await client.exists(key):
                    await client.expire(key, ttl)
            
            return True
        except Exception as e:
            logger.error(f"[WM] TTL yenileme hatası: {e}")
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS (Module-level)
# =============================================================================

async def get_working_memory_context(user_id: int | str) -> dict[str, Any]:
    """
    Kullanıcının tüm working memory bağlamını getirir.
    
    Gateway entegrasyonu için kolaylık fonksiyonu.
    
    Returns:
        dict: {
            "messages": [...],
            "summary": str | None,
            "facts": [...],
            "available": bool
        }
    """
    from app.core.redis_client import get_redis
    
    client = await get_redis()
    if client is None:
        return {
            "messages": [],
            "summary": None,
            "facts": [],
            "available": False,
            "reason": "Redis unavailable"
        }
    
    messages = await WorkingMemory.get_recent_messages(user_id)
    summary = await WorkingMemory.get_session_summary(user_id)
    facts = await WorkingMemory.get_facts(user_id)
    
    return {
        "messages": messages,
        "summary": summary,
        "facts": facts,
        "available": True
    }
