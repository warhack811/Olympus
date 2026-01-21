"""
Mami AI - DAG Task Runner (Atlas Sovereign Edition)
---------------------------------------------------
Orkestratör tarafından oluşturulan iş planını (DAG) analiz eder ve görevleri
bağımlılık sırasına göre paralel veya ardışık olarak çalıştırır.

Temel Sorumluluklar:
1. Bağımlılık Yönetimi: Görevlerin dependencies'ini çözer.
2. Paralel Yürütme: Bağımsız görevleri asyncio.gather ile çalıştırır.
3. Araç Entegrasyonu: Dinamik tool çağrısı.
4. Veri Enjeksiyonu: {tX.output} template değişimi.
5. Hata Toleransı: Graceful degradation.
"""

import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING

from app.services.brain.intent import OrchestrationPlan, TaskSpec
from app.core.constants import MODEL_GOVERNANCE, SPECIALIST_ROLES
from app.core.resilience import CircuitManager
from app.core.terminal import log
from app.core.telemetry.service import telemetry
from app.schemas.rdr import EventType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.brain.request_context import RequestContext

class TaskRunner:
    """Görev akış diyagramını yürüten ana sınıf (DAG Executor)."""
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Yerleşik araçları kaydet."""
        # Tool'lar lazy-load edilecek
        self._tools = {
            "search_tool": self._execute_search,
            "document_tool": self._execute_document_search,
            "flux_tool": self._execute_image_gen,
            "memory_tool": self._execute_memory_query,
            "calculator_tool": self._execute_calculator,
        }

    def _resolve_context_args(
        self,
        ctx: Optional["RequestContext"],
        session_id: Optional[str],
        original_message: Optional[str],
        user_id: Optional[str],
        username: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        if ctx:
            return ctx.session_id, ctx.message, ctx.user_id, ctx.username
        return session_id, original_message, user_id, username
    
    async def _get_session_history(self, session_id: str) -> List[Dict]:
        """
        Get session history for context enrichment.
        
        Returns:
            [{"role": "user", "content": "..."}, ...]
        """
        if not session_id:
            return []
        
        try:
            # Try Redis cache first
            from app.core.cache import redis_client
            import json
            
            history_json = await redis_client.get(f"chat_history:{session_id}")
            if history_json:
                history_bytes = history_json if isinstance(history_json, bytes) else history_json.encode()
                return json.loads(history_bytes.decode())
            
            # Fallback: Session buffer
            # (Assuming session buffer exists, otherwise return empty)
            logger.debug(f"No history found for session {session_id}")
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get session history: {e}")
            return []
    
    async def execute_plan(
        self, 
        plan: Union[OrchestrationPlan, Dict[str, Any]], 
        session_id: str, 
        original_message: str,
        user_id: str = None,
        ctx: Optional["RequestContext"] = None
    ) -> List[Dict[str, Any]]:
        """Geriye dönük uyumluluk: Tüm sonuçları liste olarak döner."""
        session_id, original_message, user_id = self._resolve_context_args(
            ctx, session_id, original_message, user_id
        )
        results = []
        async for event in self.execute_plan_stream(plan, session_id, original_message, user_id):
            if event["type"] == "task_result":
                results.append(event["result"])
        return results

    async def execute_plan_with_context(
        self,
        plan: Union[OrchestrationPlan, Dict[str, Any]],
        ctx: "RequestContext"
    ) -> List[Dict[str, Any]]:
        return await self.execute_plan(plan, ctx.session_id, ctx.message, ctx.user_id, ctx=ctx)
    
    async def execute_plan_stream(
        self, 
        plan: Union[OrchestrationPlan, Dict[str, Any]], 
        session_id: str, 
        original_message: str,
        user_id: str = None,
        username: str = None,
        ctx: Optional["RequestContext"] = None
    ):
        """
        Görev akışını yürütür ve her adımda thought/result olaylarını yield eder.
        
        Yields:
            dict: {"type": "thought", "thought": str} veya
                  {"type": "task_result", "result": dict}
        """
        session_id, original_message, user_id, username = self._resolve_context_args(
            ctx, session_id, original_message, user_id, username
        )
        # Normalize plan
        if isinstance(plan, dict):
            tasks_raw = plan.get("tasks", [])
            tasks = [TaskSpec(**t) if isinstance(t, dict) else t for t in tasks_raw]
        else:
            tasks = [TaskSpec(**t) if isinstance(t, dict) else t for t in plan.tasks]
        
        executed_tasks: Dict[str, Dict] = {}
        remaining_tasks = list(tasks)
        
        while remaining_tasks:
            # Bağımlılıkları çözülmüş görevleri bul
            ready_tasks = [
                t for t in remaining_tasks
                if not t.dependencies or all(dep in executed_tasks for dep in t.dependencies)
            ]
            
            if not ready_tasks:
                logger.warning("[TaskRunner] Circular dependency detected, breaking loop.")
                break
            
            # Paralel yürütme
            layer_coroutines = [
                self._execute_single_task(
                    task=t,
                    intent=plan.intent if hasattr(plan, 'intent') else "general",
                    executed_tasks=executed_tasks,
                    session_id=session_id,
                    original_message=original_message,
                    user_id=user_id,
                    username=username,
                    assistant_message_id=ctx.assistant_message_id if ctx else None
                )
                for t in ready_tasks
            ]
            
            layer_results = await asyncio.gather(*layer_coroutines, return_exceptions=True)
            
            for res in layer_results:
                if isinstance(res, Exception):
                    logger.error(f"[TaskRunner] Task exception: {res}")
                    continue
                    
                task_id = res.get("task_id", "unknown")
                executed_tasks[task_id] = res
                
                # Thought extraction
                thought = res.get("thought")
                if thought:
                    yield {"type": "thought", "thought": thought, "task_id": task_id}
                
                yield {"type": "task_result", "result": res}
            
            # Tamamlananları çıkar
            ready_ids = {t.id for t in ready_tasks}
            remaining_tasks = [t for t in remaining_tasks if t.id not in ready_ids]

    async def execute_plan_stream_with_context(
        self,
        plan: Union[OrchestrationPlan, Dict[str, Any]],
        ctx: "RequestContext"
    ):
        async for event in self.execute_plan_stream(
            plan=plan,
            session_id=ctx.session_id,
            original_message=ctx.message,
            user_id=ctx.user_id,
            username=ctx.username,
            ctx=ctx
        ):
            yield event
    
    async def _execute_single_task(
        self,
        task: TaskSpec,
        intent: str,
        executed_tasks: Dict,
        session_id: str,
        original_message: str,
        user_id: str = None,
        username: str = None,
        assistant_message_id: int = None
    ) -> Dict:
        """Bir görevi tipine göre çalıştırır."""
        start_time = time.time()
        task_id = task.id
        
        try:
            if task.type == "tool":
                result = await self._execute_tool(
                    task, 
                    user_id=user_id, 
                    username=username, 
                    message_id=assistant_message_id,
                    session_id=session_id
                )
            elif task.type in ("generation", "context_clarification"):
                result = await self._execute_generation(
                    task=task,
                    intent=intent,
                    executed_tasks=executed_tasks,
                    original_message=original_message,
                    session_id=session_id,
                    user_id=user_id
                )
            elif task.type == "memory_control":
                result = await self._execute_memory_control(task, user_id)
            else:
                result = {"task_id": task_id, "error": f"Bilinmeyen görev tipi: {task.type}", "status": "failed"}
        except Exception as e:
            logger.error(f"[TaskRunner] Task {task_id} failed: {e}")
            result = {"task_id": task_id, "error": str(e), "status": "failed"}
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        
        # [DYNAMIC THOUGHT] Orchestrator tarafından planlanan düşünceyi fallback olarak ekle
        if not result.get("thought") and hasattr(task, 'thought') and task.thought:
            result["thought"] = task.thought
            
        return result
    
    async def _execute_tool(
        self, 
        task: TaskSpec, 
        user_id: str = "default", 
        username: str = None,
        message_id: int = None,
        session_id: str = None
    ) -> Dict:
        """Aracı çalıştırır."""
        tool_name = task.tool_name
        
        # Circuit Breaker kontrolü
        breaker = CircuitManager.get_breaker(f"tool_{tool_name}")
        if not breaker.can_execute():
            return {
                "task_id": task.id,
                "type": "tool",
                "tool_name": tool_name,
                "error": "Circuit breaker açık, araç geçici olarak devre dışı.",
                "status": "circuit_open"
            }
        
        tool_fn = self._tools.get(tool_name)
        if not tool_fn:
            return {
                "task_id": task.id,
                "type": "tool",
                "tool_name": tool_name,
                "error": f"Tool bulunamadı: {tool_name}",
                "status": "failed"
            }
        
        try:
            # Security: Merging authenticated user context into tool parameters
            params = (task.params or {}).copy()
            params["user_id"] = user_id
            if username:
                params["username"] = username
            if message_id:
                params["message_id"] = message_id
            if session_id:
                params["session_id"] = session_id
            
            # Pass task object for internal thoughts and metadata
            params["task"] = task
            
            result = await tool_fn(**params)
            breaker.record_success()
            # Propagate Unified Sources if tool returned them (e.g. Search Tool)
            unified_sources = None
            if isinstance(result, dict) and "unified_sources" in result:
                unified_sources = result["unified_sources"]

            return {
                "task_id": task.id,
                "type": "tool",
                "tool_name": tool_name,
                "output": result,
                "status": "success",
                "unified_sources": unified_sources # Critical for Engine Stream
            }
        except Exception as e:
            breaker.record_failure()
            return {
                "task_id": task.id,
                "type": "tool",
                "tool_name": tool_name,
                "error": str(e),
                "status": "failed"
            }
    
    async def _execute_generation(
        self,
        task: TaskSpec,
        intent: str,
        executed_tasks: Dict,
        original_message: str,
        session_id: str,
        user_id: str = None
    ) -> Dict:
        """LLM generation görevi çalıştırır - ModelGovernance fallback ile."""
        from app.core.llm.generator import LLMGenerator, LLMRequest
        
        # Dependency injection
        prompt = self._inject_dependencies(task.instruction or original_message, executed_tasks)
        
        # Specialist -> Model mapping (role)
        specialist = task.specialist or "logic"
        
        # Get user context for thought directive
        user_context = {}
        tool_summary = ""
        
        if user_id:
            from app.services.brain.context_enricher import context_enricher
            history = await self._get_session_history(session_id) if session_id else []
            user_context = await context_enricher.get_user_context(user_id, original_message, history)
            tool_summary = self._summarize_executed_tasks(executed_tasks)
        
        # PRODUCTION: Add thought directive to system prompt
        thought_directive = f"""
IMPORTANT: Before providing your final answer, write 1-2 sentences about your thinking process inside <thought></thought> tags.

GOALS:
1. Provide a COMPREHENSIVE answer using as many relevant points as possible from the provided tools.
2. If multiple sources are available, synthesize them to provide a complete picture.
3. Keep the user context in mind:
- Expertise: {user_context.get('expertise_level', 'intermediate')}
- Mood: {user_context.get('mood', 'neutral')}
- Context: {tool_summary if tool_summary else 'none'}

Now provide your final answer.
"""
        
        # Use LLMGenerator with ModelGovernance fallback
        if not hasattr(self, '_llm_generator') or not self._llm_generator:
            self._llm_generator = LLMGenerator()
            # Auto-register providers based on ModelGovernance requirements
            await self._auto_register_providers()
        
        request = LLMRequest(
            role=specialist,  # Uses MODEL_GOVERNANCE[specialist]
            prompt=prompt,
            temperature=0.7,
            metadata={"system_prompt": thought_directive}
        )
        
        try:
            result = await self._llm_generator.generate(request, timeout=30.0)
            
            if not result.ok:
                return {
                    "task_id": task.id,
                    "type": "generation",
                    "error": f"Generation failed: {result.text}",
                    "status": "failed"
                }

            # Thought extraction (Production Ready logic from legacy Atlas)
            import re
            raw_text = result.text or ""
            thought_match = re.search(r"<thought>(.*?)</thought>", raw_text, re.DOTALL | re.IGNORECASE)
            # Remove thought tags from the final output strictly
            clean_text = re.sub(r"<thought>.*?</thought>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
            
            extracted_thought = thought_match.group(1).strip() if thought_match else ""
            if not extracted_thought and hasattr(task, 'thought') and task.thought:
                extracted_thought = task.thought
            
            return {
                "task_id": task.id,
                "type": "generation",
                "output": clean_text,
                "thought": extracted_thought,
                "model": result.model or "unknown",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Generation task failed: {e}")
            return {
                "task_id": task.id,
                "type": "generation",
                "error": f"Generation failed: {str(e)}",
                "status": "failed"
            }
    
    async def _auto_register_providers(self) -> None:
        """Auto-register providers based on ModelGovernance requirements."""
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        # Get all unique providers needed for specialist roles
        providers_needed = set()
        
        # Check all potential specialist roles
        specialist_roles = SPECIALIST_ROLES  # constants.py'den
        for role in specialist_roles:
            try:
                chain = governance.get_model_chain(role)
                for model_id in chain:
                    provider_name = governance.detect_provider(model_id)
                    providers_needed.add(provider_name)
            except Exception:
                continue
        
        # Register required providers
        provider_adapters = {
            "groq": groq_adapter,
            "gemini": gemini_adapter
        }
        
        for provider in providers_needed:
            if provider in provider_adapters and provider not in self._llm_generator.providers:
                self._llm_generator.register_provider(provider, provider_adapters[provider])
                logger.info(f"[TaskRunner] Auto-registered provider: {provider}")
    
    async def _execute_memory_control(self, task: TaskSpec, user_id: str) -> Dict:
        """
        Hafıza kontrol işlemleri - Deletion Service integration.
        Handles deletion requests with 2-step confirmation flow.
        """
        from app.services.memory.deletion import deletion_service
        
        # Get original message from params
        user_input = task.params.get("original_message", "") if task.params else ""
        
        if not user_input:
            return {
                "task_id": task.id,
                "type": "memory_control",
                "error": "No user input provided",
                "status": "failed"
            }
        
        # Check if this is a confirmation step
        confirmation_keywords = ["EVET", "ONAYLIYORUM", "YES", "CONFIRM"]
        if user_input.upper().strip() in confirmation_keywords:
            # Look for token in params (should be passed from previous turn's context)
            token = task.params.get("deletion_token")
            if token:
                result = await deletion_service.confirm_deletion(user_id, token, user_input)
                return {
                    "task_id": task.id,
                    "type": "memory_control",
                    "output": result.get("message", "İşlem tamamlandı"),
                    "deleted_counts": result.get("deleted_counts"),
                    "status": result.get("status", "success")
                }
            else:
                return {
                    "task_id": task.id,
                    "type": "memory_control",
                    "output": "❌ Onay token'ı bulunamadı. Lütfen silme talebini yeniden yapın.",
                    "status": "error"
                }
        
        # Otherwise, it's a new deletion request
        result = await deletion_service.process_deletion_request(user_id, user_input)
        
        return {
            "task_id": task.id,
            "type": "memory_control",
            "output": result.get("message", ""),
            "deletion_token": result.get("token"),  # Store for potential next turn
            "preview": result.get("preview"),
            "status": result.get("status", "success")
        }
    
    def _inject_dependencies(self, prompt: str, executed_tasks: Dict) -> str:
        """{tX.output} ifadelerini gerçek sonuçlarla değiştirir."""
        pattern = r"\{(t\d+)\.output\}"
        
        def replace_match(match):
            task_id = match.group(1)
            if task_id in executed_tasks:
                res = executed_tasks[task_id]
                if res.get("status") == "failed":
                    return f"[Hata: {task_id} verisi alınamadı]"
                return str(res.get("output", ""))
            return match.group(0)
        
        return re.sub(pattern, replace_match, prompt)
    
    def _summarize_executed_tasks(self, executed_tasks: Dict) -> str:
        """Create brief summary of what tools did for synthesis thought."""
        summaries = []
        for task_id, result in executed_tasks.items():
            tool_name = result.get("tool_name")
            if tool_name == "search_tool":
                summaries.append("web araması")
            elif tool_name == "document_tool":
                summaries.append("belge taraması")
            elif tool_name == "flux_tool":
                summaries.append("görsel üretimi")
        
        return ", ".join(summaries) if summaries else "veri toplama"

    
    # --- BUILTIN TOOLS ---
    async def _execute_search(self, query: str = "", **kwargs) -> Dict:
        """Web arama aracı."""
        try:
            from app.search.manager import search_queries_async
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            
            # Get context for dynamic thought
            user_id = kwargs.get("user_id", "default")
            session_id = kwargs.get("session_id")
            history = await self._get_session_history(session_id) if session_id else []
            
            user_context = await context_enricher.get_user_context(user_id, query, history)
            
            # Generate/Retrieve dynamic thought
            task_obj = kwargs.get("task")
            thought = getattr(task_obj, 'thought', None) if task_obj else None
            freshness = kwargs.get("freshness")
            
            if not thought:
                thought = await thought_generator.generate_thought(
                    task_type="search",
                    user_context=user_context,
                    action_params={"query": query, "freshness": freshness},
                    personality_mode=kwargs.get("persona", "friendly"),
                    allow_fallback=True
                )

            search_item = {"query": query}
            if freshness:
                search_item["freshness"] = freshness

            search_results = await search_queries_async([search_item])
            res_obj = search_results.get("q1", {})
            
            # manager.py returns results[q.id] = {"snippets": ..., "structured_data": ...}
            # Handle cases where it might still return just a list (safety)
            if isinstance(res_obj, dict):
                snippets = res_obj.get("snippets", [])
                structured = res_obj.get("structured_data")
            else:
                snippets = res_obj
                structured = None
            
            # Construct Unified Sources & LLM Context
            formatted_sources = []
            llm_context_parts = []
            
            if snippets:
                for idx, s in enumerate(snippets):
                    # Extract fields (handle both dict and SearchSnippet)
                    if isinstance(s, dict):
                        title = s.get("title", "No Title")
                        url = s.get("link", s.get("url", ""))
                        snippet = s.get("snippet", "")
                        favicon = s.get("favicon", "")
                    else:
                        title = getattr(s, "title", "No Title")
                        url = getattr(s, "url", getattr(s, "link", ""))
                        snippet = getattr(s, "snippet", "")
                        favicon = getattr(s, "favicon", "")

                    if idx < 10:  # Increase to 10 for UI (Sovereign Edition)
                        formatted_sources.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "favicon": favicon,
                            "type": "web"
                        })
                    
                    # LLM Context entry (Professional Formatting)
                    llm_context_parts.append(f"### [KAYNAK {idx+1}]\nBAŞLIK: {title}\nURL: {url}\nÖZET: {snippet}\n")

            output_parts = ["\n".join(llm_context_parts)]
            if structured:
                output_parts.append(f"\n[STRUCTURED_DATA]: {structured}")
            
            # Deep Tracing: Log Result Count
            log.info(f"Arama Sonucu: {len(snippets)} kaynak bulundu.")
            
            # Ensure all snippets are JSON serializable
            from dataclasses import asdict
            serializable_snippets = []
            if snippets:
                for s in snippets:
                    if hasattr(s, '__dataclass_fields__'):
                        serializable_snippets.append(asdict(s))
                    else:
                        serializable_snippets.append(s)

            return {
                "query": query, 
                "results": serializable_snippets, 
                "structured_data": structured,
                "unified_sources": formatted_sources,
                "output": "\n".join(output_parts), 
                "thought": thought 
            }
        except Exception as e:
            log.error(f"Search Failed: {e}")
            return {"query": query, "error": str(e), "thought": "İnternette arama yaparken bir sorunla karşılaştım ama diğer verilerle devam ediyorum."}

    async def _execute_document_search(self, query: str = "", **kwargs) -> Dict:
        """Doküman/RAG arama aracı."""
        try:
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            
            # Get context
            owner = kwargs.get("username") or kwargs.get("user_id") or "default"
            user_id = kwargs.get("user_id", "default")
            session_id = kwargs.get("session_id")
            history = await self._get_session_history(session_id) if session_id else []
            
            user_context = await context_enricher.get_user_context(user_id, query, history)
            
            # Generate/Retrieve dynamic thought
            task_obj = kwargs.get("task")
            thought = getattr(task_obj, 'thought', None) if task_obj else None
            
            if not thought:
                thought = await thought_generator.generate_thought(
                    task_type="document_query",
                    user_context=user_context,
                    action_params={"query": query, "owner": owner},
                    personality_mode=kwargs.get("persona", "friendly"),
                    allow_fallback=False  # LLM MANDATORY - Point 2
                )
            
            log.info(f"Doküman Araması: '{query}' (Sahip: {owner})")
            
            # Hybrid search in v2 documents
            results = self._execute_rag_logic(query, owner)
            
            # [TELEMETRY] Emit RAG performance event
            telemetry.emit(
                event_type=EventType.TOOL_EXECUTION,
                component="task_runner.document_tool",
                data={
                    "query": query,
                    "owner": owner,
                    "hit_count": len(results),
                    "status": "success"
                }
            )
            
            formatted_sources = []
            for r in results[:10]:
                meta = r.get("metadata", {})
                formatted_sources.append({
                    "title": meta.get("filename", "Belge"),
                    "url": f"doc://{meta.get('filename', '')}",
                    "snippet": r.get("text", "")[:200] + "...",
                    "type": "document"
                })

            return {
                "query": query,
                "results": results,
                "unified_sources": formatted_sources,
                "output": "\n".join([f"--- DOC: {r.get('metadata', {}).get('filename')} ---\n{r.get('text')}" for r in results]),
                "thought": thought  # Dynamic LLM thought
            }
        except Exception as e:
            log.error(f"Document Tool Failed: {e}")
            return {"query": query, "error": str(e), "thought": "Belgelerinizi tararken teknik bir hata oluştu."}

    def _execute_rag_logic(self, query: str, owner: str) -> List[Dict]:
        """Centralized RAG retrieval logic (formerly in BrainEngine)."""
        from app.memory.rag_service import rag_service
        return rag_service.search(query, owner=owner, limit=8)
    
    async def _execute_image_gen(self, prompt: str = "", **kwargs) -> Dict:
        """Görsel üretim aracı - Atlas Tool entegrasyonu."""
        try:
            from app.providers.tools.image_gen import image_gen_tool
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            
            # Get context
            user_id = kwargs.get("user_id", "default_user")
            username = kwargs.get("username", "unknown")
            message_id = kwargs.get("message_id")
            conversation_id = kwargs.get("session_id") or kwargs.get("conversation_id")
            
            session_id = kwargs.get("session_id")
            history = await self._get_session_history(session_id) if session_id else []
            user_context = await context_enricher.get_user_context(user_id, prompt, history)
            
            # Generate/Retrieve creative thought
            task_obj = kwargs.get("task")
            thought = getattr(task_obj, 'thought', None) if task_obj else None
            if not thought:
                thought = await thought_generator.generate_thought(
                    task_type="image_gen",
                    user_context=user_context,
                    action_params={"prompt": prompt, "style": kwargs.get("style", "flux")},
                    personality_mode=kwargs.get("persona", "creative"),
                    allow_fallback=True
                )

            # FAZE 4: Extract advanced parameters
            priority = kwargs.get("priority", "normal")
            batch_id = kwargs.get("batch_id")
            timeout_seconds = kwargs.get("timeout_seconds", 300)
            
            # Çakışmaları önlemek için kwargs içinden ayıklıyoruz
            kwargs.pop("user_id", None)
            kwargs.pop("username", None)
            kwargs.pop("message_id", None)
            kwargs.pop("session_id", None)
            kwargs.pop("conversation_id", None)
            kwargs.pop("task", None)  # TaskSpec nesnesini çıkar - JSON serileştirilemez
            kwargs.pop("priority", None)  # FAZE 4
            kwargs.pop("batch_id", None)  # FAZE 4
            kwargs.pop("timeout_seconds", None)  # FAZE 4
            
            log.info(f"Görsel İsteği: '{prompt}' (Kullanıcı: {username}, Priority: {priority})")

            result = await image_gen_tool.execute(
                prompt=prompt,
                user_id=user_id,
                username=username,
                message_id=message_id,
                conversation_id=conversation_id,
                priority=priority,  # FAZE 4
                batch_id=batch_id,  # FAZE 4
                timeout_seconds=timeout_seconds,  # FAZE 4
                **kwargs
            )
            return {
                "prompt": prompt, 
                "result": result, 
                "thought": thought  # Dynamic LLM thought
            }
        except Exception as e:
            logger.error(f"[TaskRunner] Image gen execution failed: {e}")
            return {"prompt": prompt, "error": str(e), "thought": "Görseli hazırlarken teknik bir aksaklık oldu, isterseniz farklı bir tarifle tekrar deneyelim."}

    async def _execute_memory_query(self, query: str = "", **kwargs) -> Dict:
        """
        Kullanıcı hafızasından bilgi sorgular.
        Memory store'dan semantik arama yapar.
        """
        try:
            from app.memory.store import search_memories
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            
            # username kullan (search_memories username bekliyor)
            username = kwargs.get("username") or kwargs.get("user_id", "default")
            session_id = kwargs.get("session_id")
            history = await self._get_session_history(session_id) if session_id else []
            
            user_context = await context_enricher.get_user_context(username, query, history)
            
            # Generate thought
            task_obj = kwargs.get("task")
            thought = getattr(task_obj, 'thought', None) if task_obj else None
            
            if not thought:
                thought = await thought_generator.generate_thought(
                    task_type="memory_query",
                    user_context=user_context,
                    action_params={"query": query},
                    personality_mode=kwargs.get("persona", "friendly"),
                    allow_fallback=True
                )
            
            log.info(f"Hafıza Sorgusu: '{query}' (Kullanıcı: {username})")
            
            # Search memories (async, username, max_items parametresi)
            results = await search_memories(username, query, max_items=5)
            
            # Format output - MemoryItem nesneleri text attribute'una sahip
            formatted_results = []
            output_parts = []
            for idx, memory_item in enumerate(results, 1):
                # MemoryItem.text kullan
                content = getattr(memory_item, 'text', str(memory_item))
                importance = getattr(memory_item, 'importance', 0.5)
                formatted_results.append({
                    "index": idx, 
                    "content": content,
                    "importance": importance
                })
                output_parts.append(f"[HAFIZA {idx}] (önem: {importance:.1f}): {content}")
            
            return {
                "query": query,
                "results": formatted_results,
                "output": "\n".join(output_parts) if output_parts else "[Hafızada ilgili bilgi bulunamadı]",
                "thought": thought
            }
        except Exception as e:
            logger.error(f"[TaskRunner] Memory query failed: {e}")
            return {
                "query": query,
                "error": str(e),
                "output": "[Hafıza sorgusunda hata oluştu]",
                "thought": "Hafızamı tararken bir sorun yaşadım."
            }


    async def _execute_calculator(self, expression: str = "", **kwargs) -> Dict:
        """
        Güvenli matematik hesaplama aracı.
        Sadece temel aritmetik işlemleri destekler (eval kullanmaz).
        """
        import ast
        import operator
        
        # Güvenli operatörler
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.FloorDiv: operator.floordiv,
        }
        
        def safe_eval(node):
            """AST tabanlı güvenli değerlendirme."""
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError("Sadece sayılar desteklenir")
            elif isinstance(node, ast.BinOp):
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                op_type = type(node.op)
                if op_type not in operators:
                    raise ValueError(f"Desteklenmeyen operatör: {op_type.__name__}")
                if op_type == ast.Div and right == 0:
                    raise ValueError("Sıfıra bölme hatası")
                return operators[op_type](left, right)
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.op, ast.USub):
                    return -safe_eval(node.operand)
                elif isinstance(node.op, ast.UAdd):
                    return safe_eval(node.operand)
                raise ValueError("Desteklenmeyen unary operatör")
            elif isinstance(node, ast.Expression):
                return safe_eval(node.body)
            else:
                raise ValueError(f"Desteklenmeyen ifade türü: {type(node).__name__}")
        
        # Generate thought
        task_obj = kwargs.get("task")
        thought = getattr(task_obj, 'thought', None) if task_obj else "Hesaplama yapıyorum..."
        
        if not expression:
            return {
                "expression": "",
                "error": "Hesaplanacak ifade belirtilmedi",
                "output": "Hata: Boş ifade",
                "thought": thought
            }
        
        try:
            # Parse and evaluate
            tree = ast.parse(expression, mode='eval')
            result = safe_eval(tree)
            
            # Format result
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            
            log.info(f"Hesaplama: {expression} = {result}")
            
            return {
                "expression": expression,
                "result": result,
                "output": f"{expression} = {result}",
                "thought": thought
            }
        except SyntaxError as e:
            return {
                "expression": expression,
                "error": f"Sözdizimi hatası: {e}",
                "output": f"Hata: Geçersiz matematik ifadesi",
                "thought": "Bu ifadeyi hesaplayamadım, formatı kontrol edelim."
            }
        except ValueError as e:
            return {
                "expression": expression,
                "error": str(e),
                "output": f"Hata: {e}",
                "thought": "Hesaplamada bir sorun var."
            }
        except Exception as e:
            logger.error(f"[TaskRunner] Calculator failed: {e}")
            return {
                "expression": expression,
                "error": str(e),
                "output": f"Hesaplama hatası: {e}",
                "thought": "Teknik bir sorun oluştu."
            }


# Singleton
task_runner = TaskRunner()
