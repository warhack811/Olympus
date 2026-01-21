"""
Orchestrator - Intent Detection & DAG Planning
===============================================
Reference: backups/standalone_router/Atlas/orchestrator.py

Responsibilities:
1. Intent detection with context
2. DAG (task) planning
3. Query rewriting
4. State management integration
5. ModelGovernance-based LLM calls with fallback

IMPORTANT: Uses existing OrchestrationPlan from intent.py
"""

from __future__ import annotations

import logging
import json
import re
from typing import Dict, Any, Optional, List

from app.services.brain.intent import OrchestrationPlan, TaskSpec
from app.core.llm.generator import LLMGenerator, LLMRequest

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrator for intent detection and task planning.
    Uses ModelGovernance "orchestrator" role for LLM calls.
    """
    
    def __init__(self, llm_generator: Optional[LLMGenerator] = None):
        """
        Args:
            llm_generator: Optional LLMGenerator instance. If None, will be created.
        """
        self.llm_generator = llm_generator
    
    async def plan(
        self,
        message: str,
        user_id: str,
        session_id: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> OrchestrationPlan:
        """
        Create execution plan for user message.
        """
        # 1. Build orchestrator prompt
        prompt = self._build_prompt(message, history or [], context or "")
        
        # 2. Call LLM with ModelGovernance fallback
        if not self.llm_generator:
            self.llm_generator = LLMGenerator()
            # Auto-register providers based on ModelGovernance requirements
            await self._auto_register_providers()
        
        request = LLMRequest(
            role="orchestrator",
            prompt=prompt,
            temperature=0.1,
            metadata={
                "format": "json",
                "images": images
            }
        )
        
        # POINT 6: Orchestrator Planning Thought (LLM-driven)
        planning_thought = "Planımı yapıyorum..."
        try:
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            
            user_context = await context_enricher.get_user_context(user_id, message, history or [])
            
            planning_thought = await thought_generator.generate_thought(
                task_type="intent_planning",
                user_context=user_context,
                action_params={"message": message[:100], "user_id": user_id},
                personality_mode="professional",
                allow_fallback=False
            )
            logger.info(f"[POINT 6 - Orchestrator Planning Thought]: {planning_thought}")
            
        except Exception as e:
            logger.warning(f"[POINT 6] Planning thought generation failed: {e}")
        
        logger.info(f"[Orchestrator] Planning for message: {message[:50]}...")
        
        try:
            result = await self.llm_generator.generate(request, timeout=20.0)
            
            if not result.ok:
                logger.error(f"[Orchestrator] LLM generation failed: {result.text}")
                return self._fallback_plan(message)
            
            # 3. Parse LLM response
            plan_data = self._parse_response(result.text)
            
            # 4. Build OrchestrationPlan (Production Ready Mapping)
            final_plan = OrchestrationPlan(
                tasks=[TaskSpec(**task) for task in plan_data.get("tasks", [])],
                intent=plan_data.get("intent", "general"),
                confidence=plan_data.get("confidence", 0.95),
                is_follow_up=plan_data.get("is_follow_up", False),
                reasoning=plan_data.get("reasoning", ""),  # Top-level reasoning
                user_thought=plan_data.get("planning_thought", plan_data.get("user_thought", planning_thought)),
                detected_topic=plan_data.get("detected_topic", "SAME"),
                context_focus=plan_data.get("context_focus", ""),
                rewritten_query=plan_data.get("rewritten_query"),
                orchestrator_model=result.model,
                metadata={
                    "model_used": result.model,
                    "attempts": 1
                }
            )
            
            logger.info(f"[Orchestrator] Plan created. Intent: {final_plan.intent}, Tasks: {len(final_plan.tasks)}")
            return final_plan
            
        except Exception as e:
            logger.error(f"[Orchestrator] Planning failed: {e}")
            return self._fallback_plan(message)
    
    async def _auto_register_providers(self) -> None:
        """Auto-register providers based on ModelGovernance requirements."""
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        # Get all unique providers needed for orchestrator role
        orchestrator_chain = governance.get_model_chain("orchestrator")
        providers_needed = set()
        
        for model_id in orchestrator_chain:
            provider_name = governance.detect_provider(model_id)
            providers_needed.add(provider_name)
        
        # Register required providers
        provider_adapters = {
            "groq": groq_adapter,
            "gemini": gemini_adapter
        }
        
        for provider in providers_needed:
            if provider in provider_adapters and provider not in self.llm_generator.providers:
                self.llm_generator.register_provider(provider, provider_adapters[provider])
                logger.info(f"[Orchestrator] Auto-registered provider: {provider}")
    
    def _build_prompt(self, message: str, history: List[Dict], context: str) -> str:
        """Build orchestrator prompt."""
        from app.core.prompts import ORCHESTRATOR_PROMPT
        from app.core.constants import HISTORY_LIMITS
        
        limit = HISTORY_LIMITS.get("orchestrator", 10)
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-limit:]])

        
        try:
            return ORCHESTRATOR_PROMPT.format(
                message=message,
                history=history_text,
                context=context
            )
        except Exception as e:
            logger.warning(f"Failed to format ORCHESTRATOR_PROMPT: {e}")
            return f"Analyze message: {message}\nContext: {context}\nReturn JSON plan."
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM JSON response."""
        # Try to extract JSON from response
        # Sometimes LLM wraps JSON in ```json ... ```
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Fallback: look for generic { ... }
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            json_text = json_match.group(1) if json_match else response_text.strip()
        
        try:
            data = json.loads(json_text)
            # Ensure tasks is a list
            if "tasks" not in data or not isinstance(data["tasks"], list):
                data["tasks"] = []
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[Orchestrator] JSON parse failed: {e}. Response: {response_text[:200]}")
            # Return basic structure to avoid crash
            return {
                "intent": "general",
                "is_follow_up": False,
                "tasks": []
            }
    
    def _fallback_plan(self, message: str) -> OrchestrationPlan:
        """Safe fallback plan when orchestrator fails."""
        logger.warning("[Orchestrator] Using fallback plan")
        
        return OrchestrationPlan(
            tasks=[
                TaskSpec(
                    id="t1",
                    type="generation",
                    specialist="logic",
                    instruction=f"Lütfen şu mesaja cevap ver: {message[:100]}",
                    dependencies=[]
                )
            ],
            intent="general",
            reasoning="LLM planning failed, using safety fallback.",
            user_thought="Anladım, hemen cevaplıyorum.",
            metadata={"fallback": True}
        )


# Singleton instance
orchestrator = Orchestrator()
