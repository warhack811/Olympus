
"""
Mami AI - Reflection Service (Sovereign Core)
-----------------------------------------------
Analyzes episodic memories to generate high-level insights and connections.
Reference: Stanford Generative Agents 'Reflections'.
"""

import json
import logging
from typing import List, Dict, Any
from app.core.llm.generator import LLMGenerator, LLMRequest
from app.core.database import get_session
from app.core.models import ConversationSummary
from sqlmodel import select

logger = logging.getLogger("app.service.brain.reflection")

REFLECTION_PROMPT = """
Aşağıdaki kısa süreli hafıza özetlerini incele ve kullanıcı hakkında 3 ana çıkarım (Reflection) yap.
Bu çıkarımlar, kullanıcının hedefleri, tercihleri veya mevcut projeleri hakkında derinlemesine bilgiler olmalıdır.

### ÖZETLER:
{summaries}

### FORMAT (JSON List):
[
  {{"subject": "USER", "predicate": "CURRENT_PROJECT", "object": "AI Assistant Development", "confidence": 0.9}},
  {{"subject": "USER", "predicate": "PREfers", "object": "Python over Java", "confidence": 0.85}}
]
"""

class ReflectionService:
    def __init__(self):
        self._generator = LLMGenerator()
        # Ensure providers
        from app.core.llm.adapters import groq_adapter
        self._generator.register_provider("groq", groq_adapter)

    async def reflect_on_user(self, user_id: str):
        """Perform recursive reflection on recent memories."""
        logger.info(f"[Reflection] Analyzing memories for user: {user_id}")
        
        with get_session() as session:
            # Get last 10 summaries
            # (In a real system, we'd filter for 'un-reflected' items)
            stmt = select(ConversationSummary).limit(10) # Simplified for Phase 4
            summaries = session.exec(stmt).all()
            
            if len(summaries) < 3:
                return # Not enough material for reflection
            
            text_block = "\n".join([f"- {s.summary}" for s in summaries])
            
            request = LLMRequest(
                role="logic", # Heavy thinking role
                prompt=REFLECTION_PROMPT.format(summaries=text_block),
                temperature=0.2
            )
            
            result = await self._generator.generate(request)
            if not result.ok:
                return
            
            try:
                # Parse reflections
                raw = result.text.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                
                reflections = json.loads(raw)
                
                # Save as Facts via MemoryManager
                from app.services.memory.manager import memory_manager
                for ref in reflections:
                    await memory_manager.save_fact(user_id, ref)
                    logger.info(f"[Reflection] New insight stored: {ref['predicate']} -> {ref['object']}")
                    
            except Exception as e:
                logger.error(f"[Reflection] Failed to parse/save: {e}")

reflection_service = ReflectionService()
