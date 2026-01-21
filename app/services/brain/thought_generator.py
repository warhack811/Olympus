"""
Mami AI - Dynamic Thought Generator
------------------------------------
LLM-based context-aware thought generation for ChatGPT-like transparency.

Industry Pattern:
- OpenAI o1: Reasoning tokens
- Claude 3: Thinking process
- Perplexity: Query understanding
"""

import logging
import re
import random
from typing import Dict, Optional
# Lazy imports for test compatibility:
# - from app.core.llm.generator import LLMGenerator, LLMRequest (in _llm_generate)
# - from app.core.cache import redis_client (in generate_thought)

logger = logging.getLogger(__name__)


class ThoughtGenerator:
    """
    Generates context-aware, human-like thoughts during AI processing.
    """
    
    TIMEOUT = 2.0  # Max 2 seconds for thought generation
    CACHE_TTL = 3600  # Cache similar contexts for 1 hour
    
    # Fallback templates (reliability)
    FALLBACK_TEMPLATES = {
        "search": [
            "'{query}' hakkında bilgi topluyorum...",
            "Web'de '{query}' araştırması yapıyorum...",
        ],
        "document_query": [
            "Belgelerinizi '{query}' için tarıyorum...",
            "Dokümanlarınızda '{query}' arıyorum...",
        ],
        "image_gen": [
            "Hayal ettiğiniz görseli oluşturuyorum...",
            "'{prompt}' vizyonunuzu dijital tuvale aktarıyorum...",
        ],
        "synthesis": [
            "Topladığım bilgileri sentezliyorum...",
            "Verileri harmanlayıp cevabımı hazırlıyorum...",
        ],
        "memory_write": [
            "Bu bilgiyi kaydediyorum...",
            "Hatırlayacağım.",
        ],
        "intent_planning": [
            "Neyi istediğinizi anlıyorum...",
            "Planımı yapıyorum...",
        ],
        "strategy_planning": [
            "Strateji belirliyorum...",
            "Adım adım ilerleyeceğim...",
        ]
    }
    
    @classmethod
    async def generate_thought(
        cls,
        task_type: str,
        user_context: Dict,
        action_params: Dict,
        personality_mode: str = "friendly",
        allow_fallback: bool = False  # DEFAULT: LLM MANDATORY
    ) -> str:
        """
        Generate dynamic thought for a task.
        
        Args:
            task_type: "search", "document_query", "image_gen", "synthesis", 
                      "memory_write", "intent_planning"
            user_context: User context from context_enricher
            action_params: Task-specific parameters
            personality_mode: "friendly", "professional", "casual"
            allow_fallback: If True, allows template fallback on LLM failure.
                           If False (DEFAULT), raises exception on LLM failure.
                           
        Returns:
            Generated thought string
            
        Raises:
            RuntimeError: If LLM generation fails and allow_fallback=False
            
        Example:
            >>> thought = await thought_generator.generate_thought(
            ...     task_type="search",
            ...     user_context={"mood": "curious"},
            ...     action_params={"query": "Bitcoin"},
            ...     allow_fallback=False  # LLM MANDATORY
            ... )
        """
        
        # Try cache first
        cache_key = cls._generate_cache_key(task_type, user_context, action_params)
        
        try:
            from app.core.cache import redis_client
            cached_thought = await redis_client.get(cache_key)
            if cached_thought:
                logger.debug(f"[ThoughtGenerator] Cache HIT for {task_type}")
                return cached_thought.decode() if isinstance(cached_thought, bytes) else cached_thought
        except Exception as e:
            logger.debug(f"[ThoughtGenerator] Cache read failed: {e}")
        
        # Generate with LLM
        try:
            thought = await cls._llm_generate(
                task_type, user_context, action_params, personality_mode
            )
            
            # Cache successful result
            try:
                from app.core.cache import redis_client
                await redis_client.setex(cache_key, cls.CACHE_TTL, thought)
            except Exception as e:
                logger.debug(f"[ThoughtGenerator] Cache write failed: {e}")
            
            return thought
            
        except Exception as e:
            logger.error(f"[ThoughtGenerator] LLM generation failed: {e}")
            
            if allow_fallback:
                # Fallback to template ONLY if explicitly allowed
                logger.warning(f"[ThoughtGenerator] Using template fallback for {task_type}")
                return ThoughtGenerator._fallback_template(task_type, action_params)
            else:
                # NO FALLBACK - LLM is MANDATORY
                error_msg = (
                    f"Thought generation MUST use LLM (allow_fallback=False). "
                    f"LLM failed for task_type={task_type}: {e}"
                )
                logger.error(f"[ThoughtGenerator] {error_msg}")
                raise RuntimeError(error_msg)
    
    @classmethod
    async def _llm_generate(
        cls,
        task_type: str,
        user_context: Dict,
        action_params: Dict,
        personality_mode: str
    ) -> str:
        """LLM call for thought generation."""
        # Lazy imports
        from app.core.llm.generator import LLMGenerator, LLMRequest
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter
        from app.core.prompts import build_thought_prompt
        
        # Build context-aware prompt
        prompt = build_thought_prompt(
            task_type=task_type,
            user_context=user_context,
            action_params=action_params,
            personality_mode=personality_mode
        )
        
        # Initialize generator if needed
        # ThoughtGenerator uses a specialized fast model role (or defaults to general fallback)
        generator = LLMGenerator()
        if "groq" not in generator.providers:
            generator.register_provider("groq", groq_adapter)
            
        request = LLMRequest(
            role="thought", # specialized role for thoughts
            prompt=prompt,
            temperature=0.7,
            max_tokens=150
        )
        
        result = await generator.generate(request, timeout=cls.TIMEOUT)
        
        if result.ok:
            thought = result.text.strip()
            # Sanitize
            thought = cls._sanitize(thought)
            return thought
        else:
            raise Exception(f"Thought generation failed: {result.text}")
    
    @staticmethod
    def _sanitize(text: str) -> str:
        """Remove meta-commentary and unwanted patterns."""
        # Remove "I will...", "I'm going to..."
        text = re.sub(r"^(I will|I'm going to|Let me)\s+", "", text, flags=re.IGNORECASE)
        # Remove quotes around entire response
        text = text.strip('"\'')
        # Remove trailing punctuation duplication
        text = re.sub(r'([.!?])\1+', r'\1', text)
        return text
    
    @staticmethod
    def _fallback_template(task_type: str, params: Dict) -> str:
        """Reliable template fallback."""
        templates = ThoughtGenerator.FALLBACK_TEMPLATES.get(
            task_type,
            ["İşlem devam ediyor..."]
        )
        
        template = random.choice(templates)
        
        # Simple template variable replacement
        try:
            return template.format(**params)
        except (KeyError, ValueError):
            # If template vars don't match, return plain
            return template
    
    @staticmethod
    def _generate_cache_key(
        task_type: str,
        user_context: Dict,
        action_params: Dict
    ) -> str:
        """Generate deterministic cache key."""
        # Use mood, expertise, and action type for caching
        mood = user_context.get("mood", "neutral")
        expertise = user_context.get("expertise_level", "intermediate")
        
        # Extract key action params
        action_str = "_".join(str(v)[:20] for v in action_params.values())
        
        key_parts = [task_type, mood, expertise, action_str]
        return hash(tuple(key_parts)) % (10 ** 8)  # 8-digit hash


# Singleton
thought_generator = ThoughtGenerator()
