# app/orchestrator_v42/interfaces.py
"""
Orchestrator Interfaces - Blueprint v1 Section 8

Type definitions and protocol interfaces for memory system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


# =============================================================================
# MEMORY CONTEXT DATACLASS
# =============================================================================

@dataclass
class MemoryContext:
    """
    4-Layer Memory Aggregation Result.
    
    Blueprint v1 Section 8 uyumlu hafıza bağlamı.
    Gateway bu yapıyı kullanarak tüm katmanlardan gelen veriyi birleştirir.
    """
    
    # Layer 1: Working Memory (Redis)
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    session_summary: str | None = None
    instant_facts: list[str] = field(default_factory=list)
    
    # Layer 2: User Profile (PostgreSQL)
    profile_facts: list[dict[str, Any]] = field(default_factory=list)
    profile_summary: str = ""
    
    # Layer 3: Semantic Memory (ChromaDB)
    semantic_memories: list[dict[str, Any]] = field(default_factory=list)
    
    # Layer 4: Conversation Archive (PostgreSQL)
    archive_results: list[dict[str, Any]] = field(default_factory=list)
    archive_summary: str = ""
    
    # Meta
    layers_queried: list[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """
        LLM prompt'a eklenecek context string oluşturur.
        
        Returns:
            str: Formatlanmış context
        """
        parts = []
        
        # Profile (en önce - kullanıcı kimliği)
        if self.profile_summary:
            parts.append(f"[KULLANICI PROFİLİ]\n{self.profile_summary}")
        
        # Session summary
        if self.session_summary:
            parts.append(f"[OTURUM ÖZETİ]\n{self.session_summary}")
        
        # Instant facts (yeni öğrenilen bilgiler)
        if self.instant_facts:
            facts_str = "\n".join(f"• {f}" for f in self.instant_facts[:5])
            parts.append(f"[HATIRLA]\n{facts_str}")
        
        # Semantic memories
        if self.semantic_memories:
            mem_str = "\n".join(f"• {m.get('text', '')[:150]}" for m in self.semantic_memories[:3])
            parts.append(f"[İLGİLİ HATIRALARI]\n{mem_str}")
        
        # Archive (geçmiş sohbetler)
        if self.archive_summary:
            parts.append(f"[GEÇMİŞ SOHBETLER]\n{self.archive_summary}")
        
        return "\n\n".join(parts) if parts else ""
    
    @property
    def total_items(self) -> int:
        """Toplam memory item sayısı."""
        return (
            len(self.recent_messages) +
            len(self.profile_facts) +
            len(self.semantic_memories) +
            len(self.archive_results) +
            len(self.instant_facts)
        )
    
    @property
    def is_empty(self) -> bool:
        """Context boş mu?"""
        return self.total_items == 0 and not self.session_summary


# =============================================================================
# CONTEXT PROVIDER PROTOCOL
# =============================================================================

class ContextProvider(Protocol):
    """
    Router'ın bildiği tek interface.
    
    Blueprint v1: "Router sadece bu interface'i bilir, implementasyonu bilmez."
    """
    
    async def get_context(self, user_id: int, message: str) -> MemoryContext:
        """
        Kullanıcı ve mesaj için memory context döndürür.
        
        Args:
            user_id: Kullanıcı ID
            message: Kullanıcı mesajı
            
        Returns:
            MemoryContext: 4-layer aggregated context
        """
        ...


# =============================================================================
# LAYER RESULT DATACLASSES
# =============================================================================

@dataclass
class LayerResult:
    """Tek bir layer'ın sonucu."""
    layer_name: str
    success: bool
    latency_ms: float
    item_count: int
    error: str | None = None


@dataclass
class AggregationResult:
    """4-layer aggregation sonucu."""
    context: MemoryContext
    layer_results: list[LayerResult] = field(default_factory=list)
    total_latency_ms: float = 0.0
    
    @property
    def all_successful(self) -> bool:
        """Tüm layer'lar başarılı mı?"""
        return all(r.success for r in self.layer_results)
