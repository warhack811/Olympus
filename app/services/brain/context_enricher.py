"""
Mami AI - Context Enricher
---------------------------
Extracts user context (mood, expertise, recent topic) for thought personalization.
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    Enriches user context for personalized thought generation.
    """
    
    # Mood detection keywords
    FRUSTRATED_KEYWORDS = [
        "çalışmıyor", "hata", "problem", "yardım", "anlamadım",
        "olmadı", "başaramadım", "sorun", "bug"
    ]
    
    CURIOUS_KEYWORDS = [
        "merak", "nasıl", "neden", "öğrenmek", "anlamak",
        "ilginç", "bilmek istiyorum"
    ]
    
    EXCITED_KEYWORDS = [
        "harika", "süper", "mükemmel", "çok iyi", "bayıldım",
        "muhteşem"
    ]
    
    # Technical terms for expertise detection
    TECHNICAL_TERMS = [
        "api", "async", "await", "callback", "promise", "thread",
        "loop", "module", "import", "class", "function", "method",
        "variable", "array", "object", "json", "rest", "graphql"
    ]
    
    @staticmethod
    async def get_user_context(
        user_id: str,
        message: str,
        history: List[Dict[str, str]]
    ) -> Dict:
        """
        Extract user context from message and history.
        
        Returns:
            {
                "user_id": str,
                "recent_topic": str,
                "mood": "neutral" | "frustrated" | "curious" | "excited",
                "expertise_level": "beginner" | "intermediate" | "expert",
                "follow_up_count": int
            }
        """
        
        # 1. Recent topic extraction
        recent_topic = ContextEnricher._extract_recent_topic(history)
        
        # 2. Mood detection
        mood = ContextEnricher._detect_mood(message)
        
        # 3. Expertise level
        expertise_level = ContextEnricher._detect_expertise(message)
        
        # 4. Follow-up count (session continuity)
        follow_up_count = ContextEnricher._count_follow_ups(history)
        
        return {
            "user_id": user_id,
            "recent_topic": recent_topic,
            "mood": mood,
            "expertise_level": expertise_level,
            "follow_up_count": follow_up_count
        }
    
    @staticmethod
    def _extract_recent_topic(history: List[Dict]) -> str:
        """Extract last discussed topic from history."""
        if not history:
            return "genel"
        
        # Check last 3 messages
        for msg in reversed(history[-3:]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                
                # Simple topic extraction (capitalized terms)
                match = re.search(
                    r'(Python|JavaScript|React|Django|FastAPI|Neo4j|AI|Machine Learning|Data Science|Web|API)',
                    content,
                    re.IGNORECASE
                )
                if match:
                    return match.group(1)
        
        return "genel"
    
    @staticmethod
    def _detect_mood(message: str) -> str:
        """Detect user mood from message tone."""
        message_lower = message.lower()
        
        # Check frustrated
        if any(kw in message_lower for kw in ContextEnricher.FRUSTRATED_KEYWORDS):
            return "frustrated"
        
        # Check curious
        if any(kw in message_lower for kw in ContextEnricher.CURIOUS_KEYWORDS):
            return "curious"
        
        # Check excited
        if any(kw in message_lower for kw in ContextEnricher.EXCITED_KEYWORDS):
            return "excited"
        
        return "neutral"
    
    @staticmethod
    def _detect_expertise(message: str) -> str:
        """Detect expertise level from message complexity."""
        message_lower = message.lower()
        
        # Count technical terms
        tech_count = sum(
            1 for term in ContextEnricher.TECHNICAL_TERMS
            if term in message_lower
        )
        
        # Expertise levels
        if tech_count >= 3:
            return "expert"
        elif tech_count >= 1:
            return "intermediate"
        elif len(message.split()) < 5:
            return "beginner"
        else:
            return "intermediate"  # Default
    
    @staticmethod
    def _count_follow_ups(history: List[Dict]) -> int:
        """Count user messages in recent history."""
        if not history:
            return 0
        
        # Count user messages in last 5 turns
        return sum(
            1 for m in history[-5:]
            if m.get("role") == "user"
        )


# Singleton
context_enricher = ContextEnricher()
