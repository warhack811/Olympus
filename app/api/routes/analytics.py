"""
Frontend Analytics API Routes

Frontend'den gelen analytics event'lerini işler ve backend'e kaydeder.

Gereksinimler:
- 5.1: Login event'i ekle
- 5.2: Chat message event'i ekle
- 5.3: Image generation event'i ekle
- 5.4: Event'leri backend'e gönder
"""

from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.core.logger import get_logger
from app.core.models import User
from app.core.analytics import track_event

logger = get_logger(__name__)
router = APIRouter()

# =============================================================================
# ŞEMALAR
# =============================================================================


class AnalyticsEventIn(BaseModel):
    """Frontend'den gelen analytics event'i."""

    event_type: str = Field(
        ...,
        description="Event türü (login, chat_start, message_sent, image_generated)",
    )
    user_id: int | str = Field(..., description="Kullanıcı ID'si")
    timestamp: str = Field(..., description="Event zamanı (ISO 8601)")
    data: Optional[dict[str, Any]] = Field(None, description="Event verisi")


class AnalyticsEventsIn(BaseModel):
    """Frontend'den gelen analytics event'leri (batch)."""

    events: list[AnalyticsEventIn] = Field(..., description="Event'ler")


class AnalyticsEventOut(BaseModel):
    """Analytics event çıktı modeli."""

    success: bool
    message: str
    events_processed: int


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/analytics/events", response_model=AnalyticsEventOut)
async def receive_analytics_events(
    body: AnalyticsEventsIn,
    user: User = Depends(get_current_active_user),
) -> AnalyticsEventOut:
    """
    Frontend'den gelen analytics event'lerini alır ve backend'e kaydeder.

    Requirement 5.4: Event'leri backend'e gönder

    Args:
        body: Analytics event'leri
        user: Mevcut kullanıcı

    Returns:
        AnalyticsEventOut: İşlem sonucu
    """
    if not body.events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="En az bir event gönderilmeli",
        )

    # User ID'si None kontrolü
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )

    processed_count = 0

    try:
        for event in body.events:
            # Event türünü doğrula
            valid_event_types = ["login", "chat_start", "message_sent", "image_generated"]
            if event.event_type not in valid_event_types:
                logger.warning(
                    f"[Analytics] Geçersiz event türü: {event.event_type} (user_id={user.id})"
                )
                continue

            # Event'i track et
            track_event(
                event_type=event.event_type,
                user_id=user.id,
                data=event.data or {},
            )

            processed_count += 1

            # Event türüne göre log'la
            if event.event_type == "login":
                logger.info(f"[Analytics] Login event: user_id={user.id}")
            elif event.event_type == "chat_start":
                logger.debug(
                    f"[Analytics] Chat start event: user_id={user.id}, "
                    f"conversation_id={event.data.get('conversation_id') if event.data else None}"
                )
            elif event.event_type == "message_sent":
                logger.debug(
                    f"[Analytics] Message sent event: user_id={user.id}, "
                    f"message_length={event.data.get('message_length') if event.data else None}"
                )
            elif event.event_type == "image_generated":
                logger.debug(
                    f"[Analytics] Image generated event: user_id={user.id}, "
                    f"model={event.data.get('model') if event.data else None}"
                )

    except Exception as e:
        logger.error(f"[Analytics] Event processing hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics event'leri işlenirken hata oluştu",
        )

    logger.info(
        f"[Analytics] {processed_count}/{len(body.events)} event işlendi (user_id={user.id})"
    )

    return AnalyticsEventOut(
        success=True,
        message=f"{processed_count} event başarıyla işlendi",
        events_processed=processed_count,
    )

