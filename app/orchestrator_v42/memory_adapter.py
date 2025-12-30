# app/orchestrator_v42/memory_adapter.py
"""
Memory Adapter - Blueprint v1 Section 8

4-Layer Memory Aggregation:
- Layer 1: Working Memory (Redis)
- Layer 2: User Profile (PostgreSQL)
- Layer 3: Semantic Memory (ChromaDB)
- Layer 4: Conversation Archive (PostgreSQL)

Kullanım:
    from app.orchestrator_v42.memory_adapter import get_memory_context
    
    context = await get_memory_context(user_id, message, flags, trace_id)
"""

import asyncio
import logging
import time
from typing import Any

from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.interfaces import MemoryContext, LayerResult, AggregationResult

logger = logging.getLogger("orchestrator.memory_adapter")


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

async def get_memory_context(
    user_id: str | None, 
    message: str, 
    flags: OrchestratorFeatureFlags, 
    trace_id: str
) -> dict[str, Any]:
    """
    Legacy API - Gateway ile uyumluluk için.
    
    Yeni 4-layer sistemi çağırır ve eski formata dönüştürür.
    """
    if not flags.memory_enabled:
        return {
            "ran": False,
            "dry_run": False,
            "item_count": 0,
            "items": [],
            "notes": "Hafıza kapalı"
        }
        
    if not user_id or user_id.lower() in ["unknown", "bilinmiyor", "none"]:
        return {
            "ran": False,
            "dry_run": False, 
            "item_count": 0,
            "items": [],
            "notes": "Geçersiz Kullanıcı ID"
        }
    
    # Dry-Run Kontrolü
    if flags.memory_dry_run:
        return {
            "ran": True,
            "dry_run": True,
            "item_count": 1,
            "items": ["(Dry-run) 4-layer memory simülasyonu."],
            "notes": "Hafıza dry-run modu aktif."
        }
    
    # 4-Layer Aggregation çağır
    try:
        # Orijinal username'i koru (semantic memory için)
        # user_id zaten string olarak geliyor (username)
        username_str = user_id  # Orijinal username
        
        # Int ID'ye çevirmeye çalış (profile ve archive için)
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            # Username ise, database'den ID al
            try:
                from app.core.users import get_or_create_user
                user_obj = get_or_create_user(user_id)
                user_id_int = user_obj.id
            except Exception:
                user_id_int = 1  # Fallback default user
        
        result = await get_aggregated_context(
            user_id=user_id_int,
            username=username_str,  # Orijinal username'i de geçir
            message=message,
            flags=flags,
            trace_id=trace_id
        )
        
        # Legacy formata dönüştür
        context = result.context
        items = []
        
        # Profile facts
        for fact in context.profile_facts[:3]:
            items.append(f"[Profil] {fact.get('key', '')}: {fact.get('value', '')}")
        
        # Semantic memories
        for mem in context.semantic_memories[:3]:
            items.append(f"[Hafıza] {mem.get('text', '')[:150]}")
        
        # Session summary
        if context.session_summary:
            items.insert(0, f"[Oturum] {context.session_summary[:200]}")
        
        return {
            "ran": True,
            "dry_run": False,
            "item_count": context.total_items,
            "items": items,
            "notes": f"4-layer: {len(result.layer_results)} katman sorgulandı, {result.total_latency_ms:.0f}ms",
            # Yeni alanlar (backward compatible)
            "context": context,
            "prompt_context": context.to_prompt_context()
        }
        
    except Exception as e:
        logger.error(f"[{trace_id}] 4-Layer aggregation hatası: {e}")
        # Fallback to legacy
        return await _fallback_legacy(user_id, message, flags, trace_id)


# =============================================================================
# 4-LAYER AGGREGATION
# =============================================================================

async def get_aggregated_context(
    user_id: int,
    message: str,
    flags: OrchestratorFeatureFlags,
    trace_id: str,
    username: str | None = None  # Semantic memory için orijinal username
) -> AggregationResult:
    """
    4-Layer Memory Aggregation.
    
    Blueprint v1 Section 8 uyumlu tam hafıza bağlamı.
    
    Args:
        user_id: Kullanıcı ID (int)
        message: Kullanıcı mesajı
        flags: Feature flags
        trace_id: İzleme ID
        username: Orijinal username (semantic memory için)
        
    Returns:
        AggregationResult: Tüm katmanların sonucu
    """
    start_time = time.time()
    context = MemoryContext()
    layer_results: list[LayerResult] = []
    
    # Semantic memory için username belirle
    semantic_username = username or str(user_id)
    
    # Paralel olarak tüm katmanları sorgula
    tasks = []
    
    # Layer 1: Working Memory (Redis) - Eğer etkin ise
    if getattr(flags, 'working_memory_enabled', False):
        tasks.append(("working_memory", _fetch_working_memory(user_id, trace_id)))
    
    # Layer 2: User Profile (PostgreSQL)
    if flags.memory_enabled:
        tasks.append(("user_profile", _fetch_user_profile(user_id, trace_id)))
    
    # Layer 3: Semantic Memory (ChromaDB) - USERNAME kullan
    if flags.memory_enabled:
        tasks.append(("semantic_memory", _fetch_semantic_memory(semantic_username, message, flags, trace_id)))
    
    # Layer 4: Conversation Archive (Sadece gerektiğinde)
    if flags.memory_enabled:
        tasks.append(("conversation_archive", _fetch_conversation_archive(user_id, message, trace_id)))
    
    # Paralel çalıştır
    if tasks:
        results = await asyncio.gather(
            *[task[1] for task in tasks],
            return_exceptions=True
        )
        
        for i, (layer_name, _) in enumerate(tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                layer_results.append(LayerResult(
                    layer_name=layer_name,
                    success=False,
                    latency_ms=0,
                    item_count=0,
                    error=str(result)
                ))
                context.errors.append(f"{layer_name}: {result}")
            else:
                layer_data, latency_ms = result
                layer_results.append(LayerResult(
                    layer_name=layer_name,
                    success=True,
                    latency_ms=latency_ms,
                    item_count=layer_data.get("item_count", 0)
                ))
                context.layers_queried.append(layer_name)
                
                # Context'e merge et
                _merge_layer_data(context, layer_name, layer_data)
    
    total_latency = (time.time() - start_time) * 1000
    context.total_latency_ms = total_latency
    
    logger.info(f"[{trace_id}] Memory aggregation: layers={len(layer_results)}, "
                f"items={context.total_items}, latency={total_latency:.0f}ms")
    
    return AggregationResult(
        context=context,
        layer_results=layer_results,
        total_latency_ms=total_latency
    )


# =============================================================================
# LAYER FETCHERS
# =============================================================================

async def _fetch_working_memory(user_id: int, trace_id: str) -> tuple[dict[str, Any], float]:
    """Layer 1: Working Memory (Redis)."""
    start = time.time()
    
    try:
        from app.memory.working_memory import WorkingMemory
        
        # Son mesajları al
        messages = await WorkingMemory.get_recent_messages(user_id)
        summary = await WorkingMemory.get_session_summary(user_id)
        instant_facts = await WorkingMemory.get_facts(user_id)  # get_facts() kullan
        
        latency = (time.time() - start) * 1000
        
        return {
            "recent_messages": messages,
            "session_summary": summary,
            "instant_facts": instant_facts,
            "item_count": len(messages) + len(instant_facts) + (1 if summary else 0)
        }, latency
        
    except ImportError:
        logger.debug(f"[{trace_id}] Working Memory module not available")
        return {"item_count": 0}, (time.time() - start) * 1000
    except Exception as e:
        logger.warning(f"[{trace_id}] Working Memory error: {e}")
        return {"item_count": 0}, (time.time() - start) * 1000


async def _fetch_user_profile(user_id: int, trace_id: str) -> tuple[dict[str, Any], float]:
    """Layer 2: User Profile (PostgreSQL)."""
    start = time.time()
    
    try:
        from app.services.user_profile_service import UserProfileService
        
        profile_context = await UserProfileService.get_profile_context(user_id)
        
        latency = (time.time() - start) * 1000
        
        return {
            "facts": profile_context.get("facts", []),
            "summary": profile_context.get("summary", ""),
            "item_count": profile_context.get("fact_count", 0)
        }, latency
        
    except ImportError:
        logger.debug(f"[{trace_id}] UserProfileService not available")
        return {"item_count": 0}, (time.time() - start) * 1000
    except Exception as e:
        logger.warning(f"[{trace_id}] User Profile error: {e}")
        return {"item_count": 0}, (time.time() - start) * 1000


async def _fetch_semantic_memory(
    username: str,  # String username (not int ID)
    message: str, 
    flags: OrchestratorFeatureFlags,
    trace_id: str
) -> tuple[dict[str, Any], float]:
    """Layer 3: Semantic Memory (ChromaDB)."""
    start = time.time()
    
    try:
        from app.memory.store import search_memories
        
        max_items = min(getattr(flags, 'memory_max_items', 5), 10)
        
        # Username string olarak direkt kullan
        found = await search_memories(username=username, query=message, max_items=max_items)
        
        memories = [
            {
                "id": getattr(m, "id", ""),
                "text": getattr(m, "text", str(m)),
                "created_at": getattr(m, "created_at", ""),
                "importance": getattr(m, "importance", 0.5),
            }
            for m in found
        ]
        
        latency = (time.time() - start) * 1000
        
        return {
            "memories": memories,
            "item_count": len(memories)
        }, latency
        
    except ImportError:
        logger.debug(f"[{trace_id}] Memory store not available")
        return {"item_count": 0}, (time.time() - start) * 1000
    except Exception as e:
        logger.warning(f"[{trace_id}] Semantic Memory error: {e}")
        return {"item_count": 0}, (time.time() - start) * 1000


async def _fetch_conversation_archive(
    user_id: int, 
    message: str, 
    trace_id: str
) -> tuple[dict[str, Any], float]:
    """Layer 4: Conversation Archive (PostgreSQL)."""
    start = time.time()
    
    try:
        from app.memory.conversation_archive import ConversationArchive
        
        archive_context = await ConversationArchive.get_archive_context(user_id, message)
        
        latency = (time.time() - start) * 1000
        
        if not archive_context.get("should_search", False):
            return {"item_count": 0}, latency
        
        return {
            "results": archive_context.get("results", []),
            "summary": archive_context.get("summary", ""),
            "item_count": len(archive_context.get("results", []))
        }, latency
        
    except ImportError:
        logger.debug(f"[{trace_id}] Conversation Archive not available")
        return {"item_count": 0}, (time.time() - start) * 1000
    except Exception as e:
        logger.warning(f"[{trace_id}] Archive error: {e}")
        return {"item_count": 0}, (time.time() - start) * 1000


# =============================================================================
# HELPERS
# =============================================================================

def _merge_layer_data(context: MemoryContext, layer_name: str, data: dict[str, Any]) -> None:
    """Layer verisini MemoryContext'e merge eder."""
    
    if layer_name == "working_memory":
        context.recent_messages = data.get("recent_messages", [])
        context.session_summary = data.get("session_summary")
        context.instant_facts = data.get("instant_facts", [])
        
    elif layer_name == "user_profile":
        context.profile_facts = data.get("facts", [])
        context.profile_summary = data.get("summary", "")
        
    elif layer_name == "semantic_memory":
        context.semantic_memories = data.get("memories", [])
        
    elif layer_name == "conversation_archive":
        context.archive_results = data.get("results", [])
        context.archive_summary = data.get("summary", "")


def _resolve_user_id(user_id_str: str) -> int:
    """String user_id'yi int'e çevirir."""
    try:
        return int(user_id_str)
    except (ValueError, TypeError):
        # Username olabilir, user resolver kullan
        try:
            from app.core.users import get_or_create_user
            user = get_or_create_user(user_id_str)
            return user.id
        except Exception:
            # Fallback: hash of username
            return abs(hash(user_id_str)) % (10 ** 9)


async def _fallback_legacy(
    user_id: str, 
    message: str, 
    flags: OrchestratorFeatureFlags,
    trace_id: str
) -> dict[str, Any]:
    """
    Legacy fallback - eski ChromaDB-only sistem.
    
    4-layer başarısız olursa buraya düşer.
    """
    try:
        from app.memory.store import search_memories
        
        max_items = max(0, min(int(flags.memory_max_items), 20))
        found_items = await search_memories(username=user_id, query=message, max_items=max_items)
        
        formatted_items = []
        for item in found_items:
            text_val = getattr(item, "text", str(item))
            if len(text_val) > 240:
                text_val = text_val[:237] + "..."
            created_at = getattr(item, "created_at", "bilinmiyor")
            formatted_items.append(f"[{created_at}] {text_val}")
            
        return {
            "ran": True,
            "dry_run": False,
            "item_count": len(formatted_items),
            "items": formatted_items,
            "notes": f"Legacy fallback: {len(formatted_items)} kayıt."
        }
        
    except Exception as e:
        logger.error(f"[{trace_id}] Legacy fallback hatası: {e}")
        return {
            "ran": True,
            "dry_run": False,
            "item_count": 0,
            "items": [],
            "notes": f"Hafıza hatası: {str(e)}"
        }
