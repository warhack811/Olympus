# app/services/user_profile_service.py
"""
User Profile Service - Blueprint v1 Section 8 Layer 2

Özellikler:
- Structured facts (kategori bazlı)
- LLM confirmation (güvenilirlik skorlaması)
- Cross-validation (çelişki kontrolü)
- Version history (geri alınabilir)

Kullanım:
    from app.services.user_profile_service import UserProfileService
    
    # Fact ekleme (otomatik cross-validation)
    result = await UserProfileService.add_fact(user_id, "personal", "name", "Ahmet")
    
    # Tüm aktif factleri al
    facts = await UserProfileService.get_facts(user_id)
    
    # Kategori bazlı sorgulama
    personal = await UserProfileService.get_facts(user_id, category="personal")
"""

import logging
from datetime import datetime
from typing import Any, Literal
from dataclasses import dataclass

from sqlmodel import Session, select

logger = logging.getLogger("orchestrator.user_profile")


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class ConflictResult:
    """Cross-validation sonucu."""
    has_conflict: bool
    existing_fact_id: int | None = None
    existing_value: str | None = None
    conflict_type: str | None = None  # "direct" (aynı key), "semantic" (anlamsal çelişki)


@dataclass
class AddFactResult:
    """Fact ekleme sonucu."""
    success: bool
    fact_id: int | None = None
    action: str = "created"  # created, updated, conflict_detected
    conflict: ConflictResult | None = None
    message: str = ""


@dataclass 
class ConfirmResult:
    """LLM confirmation sonucu."""
    success: bool
    new_confidence: float = 0.0
    confirmed_by: str | None = None


# =============================================================================
# USER PROFILE SERVICE
# =============================================================================

class UserProfileService:
    """
    User Profile yönetim servisi.
    
    Blueprint v1 Section 8 Layer 2 implementasyonu.
    """
    
    # Valid categories
    CATEGORIES = ["personal", "preference", "context", "relationship"]
    
    # Confidence thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.5  # Bu altındaki factler context'e eklenmez
    CONFIRMATION_BOOST = 0.15       # LLM onayı sonrası artış
    
    # ==========================================================================
    # CORE CRUD OPERATIONS
    # ==========================================================================
    
    @classmethod
    async def add_fact(
        cls,
        user_id: int,
        category: str,
        key: str,
        value: str,
        source: str = "inferred",
        confidence: float = 0.8,
        metadata: dict[str, Any] | None = None,
        auto_resolve_conflict: bool = False
    ) -> AddFactResult:
        """
        Yeni fact ekler veya günceller.
        
        Args:
            user_id: Kullanıcı ID
            category: personal, preference, context, relationship
            key: Fact anahtarı (name, job, hobby, etc.)
            value: Fact değeri
            source: inferred, explicit, confirmed
            confidence: 0.0-1.0 güven skoru
            metadata: Ek metadata (JSON)
            auto_resolve_conflict: True ise çakışmayı otomatik çöz (eski versiyon yap)
            
        Returns:
            AddFactResult: Ekleme sonucu
        """
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        # Kategori doğrulama
        if category not in cls.CATEGORIES:
            return AddFactResult(
                success=False,
                action="error",
                message=f"Geçersiz kategori: {category}. İzinli: {cls.CATEGORIES}"
            )
        
        try:
            with get_session() as session:
                # Cross-validation: Aynı key'de aktif fact var mı?
                conflict = await cls._check_conflict(session, user_id, category, key, value)
                
                if conflict.has_conflict:
                    if auto_resolve_conflict:
                        # Eski fact'i supersede et
                        await cls._supersede_fact(session, conflict.existing_fact_id)
                    else:
                        return AddFactResult(
                            success=False,
                            action="conflict_detected",
                            conflict=conflict,
                            message=f"Çakışan fact bulundu (ID: {conflict.existing_fact_id}): '{conflict.existing_value}'"
                        )
                
                # Yeni fact oluştur
                new_fact = UserProfileFact(
                    user_id=user_id,
                    category=category,
                    key=key,
                    value=value,
                    source=source,
                    confidence=confidence,
                    version=1,
                    is_active=True,
                    conflict_resolved=True,
                    extra_data=metadata or {},
                )
                
                # Eğer supersede edildiyse version artır
                if conflict.has_conflict and auto_resolve_conflict:
                    # Eski versiyonu al
                    old_fact = session.get(UserProfileFact, conflict.existing_fact_id)
                    if old_fact:
                        new_fact.version = old_fact.version + 1
                        new_fact.supersedes = old_fact.id
                
                session.add(new_fact)
                session.commit()
                session.refresh(new_fact)
                
                action = "updated" if (conflict.has_conflict and auto_resolve_conflict) else "created"
                logger.info(f"[PROFILE] Fact {action}: user={user_id}, {category}/{key}={value[:50]}")
                
                return AddFactResult(
                    success=True,
                    fact_id=new_fact.id,
                    action=action,
                    message=f"Fact {action}"
                )
                
        except Exception as e:
            logger.error(f"[PROFILE] Fact ekleme hatası: {e}")
            return AddFactResult(
                success=False,
                action="error",
                message=str(e)
            )
    
    @classmethod
    async def get_facts(
        cls,
        user_id: int,
        category: str | None = None,
        min_confidence: float | None = None,
        include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        """
        Kullanıcının factlerini getirir.
        
        Args:
            user_id: Kullanıcı ID
            category: Filtre (None = hepsi)
            min_confidence: Minimum güven skoru filtresi
            include_inactive: Pasif factleri de dahil et
            
        Returns:
            List[dict]: Fact listesi
        """
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                # Query builder
                query = select(UserProfileFact).where(UserProfileFact.user_id == user_id)
                
                if not include_inactive:
                    query = query.where(UserProfileFact.is_active == True)
                
                if category:
                    query = query.where(UserProfileFact.category == category)
                
                if min_confidence is not None:
                    query = query.where(UserProfileFact.confidence >= min_confidence)
                
                # Execute
                facts = session.exec(query).all()
                
                return [
                    {
                        "id": f.id,
                        "category": f.category,
                        "key": f.key,
                        "value": f.value,
                        "confidence": f.confidence,
                        "source": f.source,
                        "version": f.version,
                        "is_active": f.is_active,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in facts
                ]
                
        except Exception as e:
            logger.error(f"[PROFILE] Facts okuma hatası: {e}")
            return []
    
    @classmethod
    async def get_fact_by_key(
        cls,
        user_id: int,
        category: str,
        key: str
    ) -> dict[str, Any] | None:
        """Belirli bir fact'i key'e göre getirir."""
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                query = select(UserProfileFact).where(
                    UserProfileFact.user_id == user_id,
                    UserProfileFact.category == category,
                    UserProfileFact.key == key,
                    UserProfileFact.is_active == True
                )
                fact = session.exec(query).first()
                
                if not fact:
                    return None
                
                return {
                    "id": fact.id,
                    "category": fact.category,
                    "key": fact.key,
                    "value": fact.value,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "version": fact.version,
                }
        except Exception as e:
            logger.error(f"[PROFILE] Fact by key hatası: {e}")
            return None
    
    # ==========================================================================
    # LLM CONFIRMATION
    # ==========================================================================
    
    @classmethod
    async def confirm_fact(
        cls,
        fact_id: int,
        new_confidence: float,
        confirmed_by: str = "llm"
    ) -> ConfirmResult:
        """
        LLM confirmation sonrası fact güvenini günceller.
        
        Args:
            fact_id: Fact ID
            new_confidence: Yeni güven skoru (0.0-1.0)
            confirmed_by: Onaylayan (llm model adı)
            
        Returns:
            ConfirmResult: Onay sonucu
        """
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                fact = session.get(UserProfileFact, fact_id)
                if not fact:
                    return ConfirmResult(success=False)
                
                # Güven skorunu güncelle
                fact.confidence = min(1.0, new_confidence)
                fact.source = "confirmed"
                fact.confirmed_by = confirmed_by
                fact.confirmed_at = datetime.utcnow()
                fact.updated_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(f"[PROFILE] Fact confirmed: id={fact_id}, confidence={new_confidence}")
                
                return ConfirmResult(
                    success=True,
                    new_confidence=fact.confidence,
                    confirmed_by=confirmed_by
                )
                
        except Exception as e:
            logger.error(f"[PROFILE] Confirmation hatası: {e}")
            return ConfirmResult(success=False)
    
    # ==========================================================================
    # CROSS-VALIDATION
    # ==========================================================================
    
    @classmethod
    async def _check_conflict(
        cls,
        session: Session,
        user_id: int,
        category: str,
        key: str,
        new_value: str
    ) -> ConflictResult:
        """
        Çakışma kontrolü yapar.
        
        Kontroller:
        1. Aynı category/key'de aktif fact var mı?
        2. Değer farklı mı? (aynıysa çakışma yok)
        """
        from app.core.models import UserProfileFact
        
        query = select(UserProfileFact).where(
            UserProfileFact.user_id == user_id,
            UserProfileFact.category == category,
            UserProfileFact.key == key,
            UserProfileFact.is_active == True
        )
        existing = session.exec(query).first()
        
        if not existing:
            return ConflictResult(has_conflict=False)
        
        # Aynı değerse çakışma yok
        if existing.value.strip().lower() == new_value.strip().lower():
            return ConflictResult(has_conflict=False)
        
        return ConflictResult(
            has_conflict=True,
            existing_fact_id=existing.id,
            existing_value=existing.value,
            conflict_type="direct"
        )
    
    @classmethod
    async def _supersede_fact(cls, session: Session, fact_id: int) -> bool:
        """Eski fact'i superseded olarak işaretler."""
        from app.core.models import UserProfileFact
        
        fact = session.get(UserProfileFact, fact_id)
        if not fact:
            return False
        
        fact.is_active = False
        fact.updated_at = datetime.utcnow()
        
        return True
    
    @classmethod
    async def resolve_conflict(
        cls,
        fact_id: int,
        keep_new: bool = True
    ) -> bool:
        """
        Çakışmayı çözer.
        
        Args:
            fact_id: Çakışan yeni fact ID
            keep_new: True = yeni fact kalır, eski supersede edilir
        """
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                fact = session.get(UserProfileFact, fact_id)
                if not fact or not fact.conflicting_fact_id:
                    return False
                
                if keep_new:
                    # Eski fact'i deaktive et
                    await cls._supersede_fact(session, fact.conflicting_fact_id)
                    fact.supersedes = fact.conflicting_fact_id
                else:
                    # Yeni fact'i sil
                    fact.is_active = False
                
                fact.conflict_resolved = True
                fact.conflicting_fact_id = None
                session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"[PROFILE] Conflict resolution hatası: {e}")
            return False
    
    # ==========================================================================
    # VERSION HISTORY
    # ==========================================================================
    
    @classmethod
    async def get_fact_history(cls, user_id: int, category: str, key: str) -> list[dict[str, Any]]:
        """Bir fact'in versiyon geçmişini getirir."""
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                query = select(UserProfileFact).where(
                    UserProfileFact.user_id == user_id,
                    UserProfileFact.category == category,
                    UserProfileFact.key == key
                ).order_by(UserProfileFact.version.desc())
                
                facts = session.exec(query).all()
                
                return [
                    {
                        "id": f.id,
                        "value": f.value,
                        "version": f.version,
                        "is_active": f.is_active,
                        "confidence": f.confidence,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in facts
                ]
        except Exception as e:
            logger.error(f"[PROFILE] History hatası: {e}")
            return []
    
    @classmethod
    async def rollback_fact(cls, user_id: int, fact_id: int, to_version: int) -> bool:
        """Fact'i belirli bir versiyona geri alır."""
        from app.core.database import get_session
        from app.core.models import UserProfileFact
        
        try:
            with get_session() as session:
                # Hedef versiyonu bul
                target = session.exec(
                    select(UserProfileFact).where(
                        UserProfileFact.user_id == user_id,
                        UserProfileFact.id == fact_id,
                        UserProfileFact.version == to_version
                    )
                ).first()
                
                if not target:
                    return False
                
                # Şu anki aktif versiyonu deaktive et
                current = session.exec(
                    select(UserProfileFact).where(
                        UserProfileFact.user_id == user_id,
                        UserProfileFact.category == target.category,
                        UserProfileFact.key == target.key,
                        UserProfileFact.is_active == True
                    )
                ).first()
                
                if current and current.id != target.id:
                    current.is_active = False
                    current.updated_at = datetime.utcnow()
                
                # Hedefi aktive et
                target.is_active = True
                target.updated_at = datetime.utcnow()
                
                session.commit()
                logger.info(f"[PROFILE] Rollback: fact_id={fact_id} to v{to_version}")
                return True
                
        except Exception as e:
            logger.error(f"[PROFILE] Rollback hatası: {e}")
            return False
    
    # ==========================================================================
    # CONTEXT GENERATION (Gateway için)
    # ==========================================================================
    
    @classmethod
    async def get_profile_context(
        cls,
        user_id: int,
        min_confidence: float | None = None
    ) -> dict[str, Any]:
        """
        Gateway için profil bağlamı döndürür.
        
        Returns:
            dict: {
                "facts": [...],
                "summary": str,
                "fact_count": int
            }
        """
        threshold = min_confidence or cls.MIN_CONFIDENCE_THRESHOLD
        facts = await cls.get_facts(user_id, min_confidence=threshold)
        
        # Kategori bazlı özet oluştur
        by_category: dict[str, list[str]] = {}
        for f in facts:
            cat = f["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"{f['key']}: {f['value']}")
        
        summary_parts = []
        for cat, items in by_category.items():
            if items:
                summary_parts.append(f"[{cat.upper()}] " + "; ".join(items[:3]))
        
        return {
            "facts": facts,
            "summary": " | ".join(summary_parts) if summary_parts else "",
            "fact_count": len(facts),
            "available": True
        }
