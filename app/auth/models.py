"""
Mami AI - Auth & User Domain Models
===================================
Extracted from app.core.models to break circular dependencies.
"""

from typing import Any, TYPE_CHECKING
from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.chat.models import Conversation, Session, ModelPreset

class User(SQLModel, table=True):
    """
    Kullanıcı ana tablosu.
    """
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    password_hash: str

    # Rol ve izinler
    role: str = Field(default="user")  # admin, user, vip
    is_banned: bool = Field(default=False)

    # Model tercihleri
    selected_model: str = Field(default="groq", max_length=16)  # groq | bela
    bela_unlocked: bool = Field(default=False)

    # Aktif persona/mod (kalıcı - DB'de tutulur)
    active_persona: str = Field(default="friendly", max_length=64)

    # Ek yapılandırma (JSON)
    limits: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    permissions: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Zaman damgası
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # İlişkiler
    preferences: list["UserPreference"] = Relationship(back_populates="user")
    conversations: list["Conversation"] = Relationship(back_populates="user")
    sessions: list["Session"] = Relationship(back_populates="user")
    presets: list["ModelPreset"] = Relationship(back_populates="owner")


class UserPreference(SQLModel, table=True):
    """
    Kullanıcı tercihleri ve persona ayarları.
    """
    __tablename__ = "user_preferences"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    key: str = Field(index=True, max_length=64)
    value: str = Field(sa_column=Column(Text))

    category: str = Field(default="system", index=True)
    source: str = Field(default="explicit")

    is_active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # İlişki
    user: User | None = Relationship(back_populates="preferences")


class UserProfileFact(SQLModel, table=True):
    """
    Kullanıcı Profil Bilgileri - Version History destekli.
    Blueprint v1 Section 8 Layer 2.
    """
    __tablename__ = "user_profile_facts"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Fact verileri
    category: str = Field(max_length=50, index=True)
    key: str = Field(max_length=100, index=True)
    value: str = Field(sa_column=Column(Text))
    
    # LLM Confirmation
    confidence: float = Field(default=0.8)
    source: str = Field(default="inferred", max_length=20)
    confirmed_by: str | None = Field(default=None, max_length=50)
    confirmed_at: datetime | None = Field(default=None)
    
    # Versioning
    version: int = Field(default=1)
    is_active: bool = Field(default=True, index=True)
    superseded_by: int | None = Field(default=None, index=True)
    supersedes: int | None = Field(default=None)
    
    # Cross-validation metadata
    conflicting_fact_id: int | None = Field(default=None)
    conflict_resolved: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None)
    
    # Ek bilgiler (JSON)
    extra_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class UsageCounter(SQLModel, table=True):
    """
    Günlük kullanım sayacı.
    """
    __tablename__ = "usage_counters"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    usage_date: date = Field(index=True)

    groq_count: int = Field(default=0)
    local_count: int = Field(default=0)
    total_chat_count: int = Field(default=0)

    user: User | None = Relationship()


class Session(SQLModel, table=True):
    """
    Kullanıcı oturumları.
    """
    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    type: str = Field(default="active_session")
    expires_at: datetime = Field(index=True)
    user_agent: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: User | None = Relationship(back_populates="sessions")


class Invite(SQLModel, table=True):
    """
    Davet kodları.
    """
    __tablename__ = "invites"

    code: str = Field(primary_key=True)
    created_by: str = Field(max_length=64)

    is_used: bool = Field(default=False, index=True)
    used_by: str | None = Field(default=None, max_length=64)
    used_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
