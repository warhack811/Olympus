from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.core.logger import get_logger
from app.core.models import User
from app.services import user_preferences

logger = get_logger(__name__)
router = APIRouter()

# --- ŞEMALAR ---


class UserPreferenceIn(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    value: str = Field(..., min_length=1)
    category: str | None = "system"


class UserPreferenceOut(BaseModel):
    key: str
    value: str
    category: str
    source: str
    is_active: bool
    updated_at: Any


class UserPreferencesListOut(BaseModel):
    preferences: dict[str, str]


class PersonaOut(BaseModel):
    """Persona çıktı modeli."""

    name: str
    display_name: str
    description: str | None = None
    requires_uncensored: bool = False
    is_active: bool = True
    initial_message: str | None = None


class PersonaListOut(BaseModel):
    """Persona listesi çıktı modeli."""

    personas: list[PersonaOut]
    active_persona: str


class PersonaSelectIn(BaseModel):
    """Persona seçim giriş modeli."""

    persona: str = Field(..., description="Seçilecek persona adı (ör: standard, lover, roleplay)")


class PersonaSelectOut(BaseModel):
    """Persona seçim çıktı modeli."""

    success: bool
    active_persona: str
    message: str


# --- ENDPOINTS ---


@router.get("/preferences", response_model=UserPreferencesListOut)
async def get_my_preferences(category: str | None = None, user: User = Depends(get_current_active_user)):
    # user.id None kontrolü - aktif kullanıcı için olmamalı ama tip güvenliği için
    if user.id is None:
        raise HTTPException(status_code=400, detail="Geçersiz kullanıcı ID")
    prefs = user_preferences.get_effective_preferences(user_id=user.id, category=category)
    return {"preferences": prefs}


@router.post("/preferences", response_model=UserPreferenceOut)
async def set_my_preference(body: UserPreferenceIn, user: User = Depends(get_current_active_user)):
    # user.id None kontrolü - aktif kullanıcı için olmamalı ama tip güvenliği için
    if user.id is None:
        raise HTTPException(status_code=400, detail="Geçersiz kullanıcı ID")

    # category None ise varsayılan değer ata
    category = body.category if body.category else "system"

    pref = user_preferences.set_user_preference(user_id=user.id, key=body.key, value=body.value, category=category)
    return UserPreferenceOut(
        key=pref.key,
        value=pref.value,
        category=pref.category,
        source=pref.source,
        is_active=pref.is_active,
        updated_at=pref.updated_at,
    )


# =============================================================================
# PERSONA / MOD SİSTEMİ API
# =============================================================================


@router.get("/personas", response_model=PersonaListOut)
async def list_personas(user: User = Depends(get_current_active_user)):
    """
    Kullanılabilir persona/mod listesini döndürür.

    Returns:
        PersonaListOut: Persona listesi ve aktif persona
    """
    from app.auth.permissions import user_can_use_local
    from app.core.dynamic_config import config_service

    all_personas = config_service.get_all_personas()
    can_use_local = user_can_use_local(user)

    result = []
    for p in all_personas:
        # requires_uncensored persona'ları sadece local izni olanlar görebilir
        if p.get("requires_uncensored") and not can_use_local:
            continue

        if not p.get("is_active", True):
            continue

        result.append(
            PersonaOut(
                name=p.get("name", ""),
                display_name=p.get("display_name", p.get("name", "")),
                description=p.get("description"),
                requires_uncensored=p.get("requires_uncensored", False),
                is_active=p.get("is_active", True),
                initial_message=p.get("initial_message"),
            )
        )

    return PersonaListOut(personas=result, active_persona=user.active_persona or "standard")


@router.get("/personas/active")
async def get_active_persona(user: User = Depends(get_current_active_user)):
    """
    Kullanıcının aktif persona/modunu döndürür.

    Returns:
        dict: Aktif persona bilgisi
    """
    from app.core.dynamic_config import config_service

    active_name = user.active_persona or "standard"

    persona = config_service.get_persona(active_name)

    # Eğer hala bulunamadıysa (DB'de silinmiş veya pasifse) friendly'ye düş
    if not persona:
        active_name = "friendly"
        persona = config_service.get_persona(active_name)

    if persona:
        return {
            "active_persona": active_name,
            "display_name": persona.get("display_name", active_name),
            "requires_uncensored": persona.get("requires_uncensored", False),
            "initial_message": persona.get("initial_message"),
            "icon": persona.get("icon", "💬"),
        }

    return {
        "active_persona": "friendly",
        "display_name": "Arkadaşça",
        "requires_uncensored": False,
        "initial_message": None,
        "icon": "🤝",
    }


@router.post("/personas/select", response_model=PersonaSelectOut)
async def select_persona(body: PersonaSelectIn, user: User = Depends(get_current_active_user)):
    """
    Kullanıcının aktif persona/modunu değiştirir.

    İş kuralları:
        - Persona bulunamazsa 404
        - requires_uncensored=True ise user_can_use_local kontrolü → 403
        - Başarılıysa DB'de users.active_persona güncellenir

    Args:
        body: Seçilecek persona adı

    Returns:
        PersonaSelectOut: Seçim sonucu
    """

    from app.auth.permissions import user_can_use_local
    from app.core.database import get_session
    from app.core.dynamic_config import config_service

    persona_name = body.persona.lower().strip()

    # 1. Persona'nın var olup olmadığını kontrol et
    persona = config_service.get_persona(persona_name)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona bulunamadı: {persona_name}")

    # 2. Aktif değilse hata
    if not persona.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Bu persona aktif değil: {persona_name}")

    # 3. requires_uncensored kontrolü
    if persona.get("requires_uncensored", False):
        if not user_can_use_local(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Bu modu kullanmak için yerel model izniniz gerekiyor."
            )

    # 4. DB'de güncelle
    with get_session() as session:
        db_user = session.get(User, user.id)
        if db_user:
            db_user.active_persona = persona_name
            session.add(db_user)
            session.commit()
            logger.info(f"[PERSONA] User {user.username} persona değiştirdi: {persona_name}")

    return PersonaSelectOut(
        success=True,
        active_persona=persona_name,
        message=f"Mod değiştirildi: {persona.get('display_name', persona_name)}",
    )
