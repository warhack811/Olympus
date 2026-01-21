"""
Mami AI - Memory Schemas (Pydantic v2)
--------------------------------------
Hafıza işlemleri için Pydantic modelleri.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ConfidenceLevel(str, Enum):
    """Bilgi güven seviyesi."""
    HARD_FACT = "hard_fact"      # Kesin bilgi (İsim, Yaş)
    SOFT_SIGNAL = "soft_signal"  # Yumuşak sinyal (Tercihler)
    UNCERTAIN = "uncertain"      # Belirsiz


class MemoryDecision(str, Enum):
    """MWG karar sonuçları."""
    DISCARD = "DISCARD"
    SESSION = "SESSION"
    EPHEMERAL = "EPHEMERAL"
    LONG_TERM = "LONG_TERM"
    PROSPECTIVE = "PROSPECTIVE"


class Triplet(BaseModel):
    """Özne-Yüklem-Nesne yapısı."""
    subject: str
    predicate: str
    object: str
    category: str = "general"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    sentiment: str = "neutral" 
    source_turn_id: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, SUPERSEDED, CONFLICTED
    updated_at: Optional[datetime] = None
    
    class Config:
        extra = "ignore"


class MWGResult(BaseModel):
    """Memory Write Gate karar sonucu."""
    decision: MemoryDecision
    ttl_seconds: Optional[int] = None
    reason: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)


class MemoryContext(BaseModel):
    """Kullanıcı bağlam bilgisi."""
    user_id: str
    identity_facts: List[Triplet] = Field(default_factory=list)
    hard_facts: List[Triplet] = Field(default_factory=list)
    soft_signals: List[Triplet] = Field(default_factory=list)
    vector_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    def to_formatted_string(self) -> str:
        """Atlas formatında bağlam stringi oluşturur."""
        parts = []
        
        if self.identity_facts:
            parts.append("[KULLANICI PROFİLİ]")
            for f in self.identity_facts:
                date_hint = f" [TARİH: {f.updated_at.strftime('%Y-%m-%d')}]" if f.updated_at else ""
                parts.append(f"  • {f.predicate}: {f.object}{date_hint}")
        
        if self.hard_facts:
            parts.append("\n[SERT GERÇEKLER]")
            for f in self.hard_facts:
                conf_hint = f" [GÜVEN: {f.confidence:.1f}]"
                date_hint = f" [TARİH: {f.updated_at.strftime('%Y-%m-%d')}]" if f.updated_at else ""
                parts.append(f"  • {f.subject} {f.predicate} {f.object}{conf_hint}{date_hint}")
        
        if self.soft_signals:
            parts.append("\n[YUMUŞAK SİNYALLER]")
            for f in self.soft_signals:
                conf_hint = f" [GÜVEN: {f.confidence:.1f}]"
                date_hint = f" [TARİH: {f.updated_at.strftime('%Y-%m-%d')}]" if f.updated_at else ""
                parts.append(f"  • {f.subject} {f.predicate} {f.object}{conf_hint}{date_hint}")
        
        return "\n".join(parts) if parts else "[Hafıza kaydı yok]"


class ExtractionResult(BaseModel):
    """Triplet çıkarım sonucu."""
    raw_triplets: List[Dict[str, Any]] = Field(default_factory=list)
    cleaned_triplets: List[Triplet] = Field(default_factory=list)
    saved_count: int = 0
    dropped_count: int = 0
