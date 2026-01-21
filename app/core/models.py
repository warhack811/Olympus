"""
Mami AI - Models Facade
=======================
This file acts as a facade for backward compatibility.
It re-exports models from their new domain-specific locations.
"""

# Re-export Auth Models
from app.auth.models import (
    User,
    UserPreference,
    UserProfileFact,
    UsageCounter,
    Session,
    Invite,
)

# Re-export Chat Models
from app.chat.models import (
    Conversation,
    Message,
    ConversationSummary,
    Feedback,
    AnswerCache,
)

# Re-export System Models
from app.core.system_models import (
    ModelPreset,
    AIIdentityConfig,
    ConversationSummarySettings,
    AlertHistory,
)
