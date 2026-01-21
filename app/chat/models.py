"""
Mami AI - Chat Domain Models
============================
Extracted from app.core.models to break circular dependencies.
"""

from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.core.system_models import ModelPreset

class Conversation(SQLModel, table=True):
    """
    Sohbet ana kaydı.
    """
    __tablename__ = "conversations"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str | None = Field(default="Yeni Sohbet")

    preset_id: int | None = Field(default=None, foreign_key="model_presets.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # İlişkiler
    user: Optional["User"] = Relationship(back_populates="conversations")
    preset: Optional["ModelPreset"] = Relationship(back_populates="conversations")
    messages: list["Message"] = Relationship(
        back_populates="conversation", sa_relationship_kwargs={"cascade": "all, delete"}
    )
    summary: Optional["ConversationSummary"] = Relationship(
        back_populates="conversation", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Message(SQLModel, table=True):
    """
    Sohbet mesajları.
    """
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)

    role: str = Field(index=True)  # user, bot, system
    content: str = Field(sa_column=Column(Text))

    # Ek metadata (JSON)
    extra_metadata: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # İlişki
    conversation: Conversation | None = Relationship(back_populates="messages")


class ConversationSummary(SQLModel, table=True):
    """
    Sohbet özeti.
    """
    __tablename__ = "conversation_summaries"

    conversation_id: str = Field(primary_key=True, foreign_key="conversations.id", index=True)
    summary: str = Field(sa_column=Column(Text))
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Özet güncellendiğindeki mesaj sayısı
    message_count_at_update: int = Field(default=0)

    # Önem Puanı (1-10)
    importance: int = Field(default=1, ge=1, le=10)
    
    # Ayıklanan varlıklar ve duygu durumu (JSON)
    entities: list[str] = Field(default=[], sa_column=Column(JSON))
    mood: Optional[str] = Field(default=None, max_length=50)

    # Son özetlenen mesajın ID'si
    last_message_id: int | None = Field(default=None)

    # İlişki
    conversation: Optional["Conversation"] = Relationship(back_populates="summary")


class Feedback(SQLModel, table=True):
    """
    Kullanıcı geri bildirimleri.
    """
    __tablename__ = "feedback"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: str | None = Field(default=None, foreign_key="conversations.id")

    message_content: str = Field(sa_column=Column(Text))
    feedback_type: str = Field(max_length=10)  # like, dislike

    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship()
    conversation: Optional["Conversation"] = Relationship()


class AnswerCache(SQLModel, table=True):
    """
    AI yanıt önbelleği.
    """
    __tablename__ = "answer_cache"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    cache_key: str = Field(index=True, max_length=128)
    question: str = Field(sa_column=Column(Text))
    answer: str = Field(sa_column=Column(Text))

    engine: str = Field(max_length=32)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None, index=True)

    user: Optional["User"] = Relationship()
