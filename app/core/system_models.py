"""
Mami AI - System & Config Models
================================
Extracted from app.core.models to break circular dependencies.
"""

from typing import Optional, TYPE_CHECKING, Dict, Any
from datetime import datetime

from sqlalchemy import Column, Text, JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.chat.models import Conversation

class ModelPreset(SQLModel, table=True):
    """
    Model kişilik şablonları.
    """
    __tablename__ = "model_presets"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None

    # Prompt Mühendisliği
    system_prompt_template: str = Field(sa_column=Column(Text))

    # Model Parametreleri
    temperature: float = Field(default=0.7)
    max_tokens: int | None = Field(default=None)
    model_name: str | None = Field(default=None)

    # Erişim
    is_global: bool = Field(default=False)
    owner_id: int | None = Field(default=None, foreign_key="users.id")

    # İlişkiler
    owner: Optional["User"] = Relationship(back_populates="presets")
    conversations: list["Conversation"] = Relationship(back_populates="preset")


class AIIdentityConfig(SQLModel, table=True):
    """
    AI kimlik yapılandırması (Singleton).
    """
    __tablename__ = "ai_identity_config"

    id: int = Field(default=1, primary_key=True)

    display_name: str = Field(default="Akıllı Asistan")
    developer_name: str = Field(default="bu sistemin geliştiricileri")
    product_family: str = Field(default="bu sohbet sistemi")

    short_intro: str = Field(
        sa_column=Column(Text),
        default=(
            "Ben kullanıcıların sorularına yanıt vermek ve yardımcı olmak için tasarlanmış bir yapay zeka asistanıyım."
        ),
    )

    forbid_provider_mention: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationSummarySettings(SQLModel, table=True):
    """
    Sohbet özeti sistemi ayarları (Singleton).
    """
    __tablename__ = "conversation_summary_settings"

    id: int = Field(default=1, primary_key=True)

    summary_enabled: bool = Field(default=True)
    summary_first_threshold: int = Field(default=12, ge=1)
    summary_update_step: int = Field(default=10, ge=1)
    summary_max_messages: int = Field(default=40, ge=5)

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AlertHistory(SQLModel, table=True):
    """
    Alert history kaydı.
    
    Sistem tarafından tetiklenen tüm alert'lerin history'sini tutar.
    """
    __tablename__ = "alert_history"

    id: int | None = Field(default=None, primary_key=True)
    
    # Alert bilgileri
    alert_type: str = Field(index=True)  # error_rate, response_time, disk_space, memory_usage, endpoint_down
    severity: str = Field(index=True)    # info, warning, critical
    message: str = Field(sa_column=Column(Text))
    
    # Alert verisi (JSON)
    data: Dict[str, Any] = Field(sa_column=Column(JSON), default={})
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Retention policy için
    expires_at: datetime | None = Field(default=None, index=True)
