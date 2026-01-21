"""
Placeholder IntentManager class for backward compatibility.
This allows backend to start while intent system is being refactored.
"""

from typing import Any, Optional
from app.services.brain.intent import OrchestrationPlan, detect_intent_regex


class IntentManager:
    """
    Placeholder intent manager.
    Real implementation should handle multi-tier intent classification.
    """
    
    async def analyze_with_context(self, ctx: Any) -> OrchestrationPlan:
        """
        Analyzes user message and returns orchestration plan using LLM-based Orchestrator.
        
        Args:
            ctx: RequestContext object with user message and metadata
        
        Returns:
            OrchestrationPlan with tasks
        """
        from app.services.brain.orchestrator import orchestrator
        
        message = getattr(ctx, 'message', '') or getattr(ctx, 'query', '')
        user_id = getattr(ctx, 'user_id', 'anonymous')
        session_id = getattr(ctx, 'session_id', 'unknown')
        history = getattr(ctx, 'history_list', [])
        memory = getattr(ctx, 'memory_context', '')
        
        # Call production orchestrator
        return await orchestrator.plan(
            message=message,
            user_id=user_id,
            session_id=session_id,
            history=history,
            context=memory,
            images=getattr(ctx, 'images', None)
        )


# Global singleton instance
intent_manager = IntentManager()
