"""
Mami AI - Sovereign Brain Engine (Atlas Core v4.4)
--------------------------------------------------
Tüm Atlas servislerini (Memory, Intent, TaskRunner, Synthesizer) yöneten ana sınıf.

Temel Sorumluluklar:
1. Trace Management: Her istek için benzersiz trace_id oluşturur.
2. Memory Retrieval: Kullanıcı bağlamını hafızadan çeker.
3. Planning: Intent analizi ve görev planlaması yapar.
4. Execution: DAG task runner ile görevleri yürütür.
5. Synthesis: Sonuçları stream eder.
6. Learning: Arka planda bilgi çıkarımı yapar.
"""

import json
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List, Tuple
from datetime import datetime

from app.services.brain.intent import OrchestrationPlan, detect_intent_regex
from app.services.brain.intent_manager import intent_manager
from app.services.brain.task_runner import task_runner
from app.services.brain.synthesizer import synthesizer
from app.services.brain.guards import safety_gate, quality_gate
from app.core.redis_client import get_redis
from app.core.terminal import log  # Terminal Output
from app.services.memory.manager import memory_manager
from app.providers.llm.groq import GroqProvider
from app.core.telemetry.service import telemetry, EventType
from app.core.telemetry.context import set_trace_id, set_user_id
from app.core.telemetry import counter_store
from app.core.prompts import EXTRACTOR_SYSTEM_PROMPT
from app.core.predicate_catalog import get_catalog
from app.services.brain.memory.prospective import prospective_service
from app.repositories.graph_db import GraphRepository
from app.services.brain.memory.embeddings import embedder
from app.repositories.vector_db import vector_repo
from app.services.brain.guards.rag_gate import rag_gate
from app.services.brain.request_context import RequestContext
from app.memory.rag_service import rag_service

logger = logging.getLogger(__name__)



class BrainEngine:
    """
    Atlas Sovereign Brain Engine - Merkezi karar ve yürütme motoru.
    
    Tüm alt servisleri (Memory, Intent, TaskRunner, Synthesizer) koordine eder.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        intent_mgr=None,
        task_rnr=None,
        synth=None,
        mem_mgr=None
    ):
        """
        Dependency Injection for testability.
        
        Singleton pattern: Ensures initialization happens only once.
        Subsequent calls return early without re-initializing.
        """
        if self._initialized:
            return
        
        self.intent_manager = intent_mgr or intent_manager
        self.task_runner = task_rnr or task_runner
        self.synthesizer = synth or synthesizer
        self.memory_manager = mem_mgr or memory_manager
        self.safety_gate = safety_gate
        self.quality_gate = quality_gate
        self.rag_gate = rag_gate
        self.rag_service = rag_service
        from app.core.llm.generator import LLMGenerator
        self.llm = LLMGenerator() # CENTRALIZED
        asyncio.create_task(self._auto_register_providers())
        
        # [MEMORY MOD] Wiring Graph & Prospective Services
        self.graph_repo = GraphRepository()
        prospective_service.graph_repo = self.graph_repo
        self.prospective_service = prospective_service
        
        # [MEMORY MOD] Wiring Vector Services
        self.embedder = embedder
        self.vector_repo = vector_repo
        
        # Mark initialization as complete (singleton pattern)
        self._initialized = True

    def _init_request_context(
        self,
        user_id: str,
        username: str,
        message: str,
        session_id: Optional[str],
        persona: str,
        style_profile: Optional[Any] = None,
        assistant_message_id: Optional[int] = None,
        images: Optional[List[str]] = None
    ) -> RequestContext:
        trace_id = self._generate_trace_id()
        resolved_session = session_id or user_id
        set_trace_id(trace_id)
        set_user_id(user_id)
        return RequestContext(
            trace_id=trace_id,
            user_id=user_id,
            username=username,
            session_id=resolved_session,
            message=message,
            persona=persona,
            style_profile=style_profile,
            assistant_message_id=assistant_message_id,
            images=images or [] # Vision Support
        )
    async def _memory_retrieval(self, ctx: RequestContext) -> Tuple[str, List[str]]:
        """
        Unified Memory Retrieval via Gateway (v4 Phase 4 Strategy).
        Combines Graph, Vector, and Episodic memories with IDR scoring.
        """
        from app.services.memory.gateway import memory_gateway
        
        thoughts = []
        try:
            # Tek bir çağrı ile tüm kognitif bağlamı al
            context_data = await memory_gateway.get_unified_context(
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                query=ctx.message
            )
            
            # Context'i LLM formatına çevir ve request context'e ekle
            formatted_context = memory_gateway.format_context_for_llm(context_data)
            ctx.append_context(formatted_context)
            
            if context_data.get("episodic_memories"):
                logger.info(f"[Brain] Gateway: Found {len(context_data['episodic_memories'])} episodic memories")
                
        except Exception as e:
            logger.warning(f"[Brain] Unified memory retrieval failed: {e}")
            thoughts.append("Hafızamı tararken bir sorun oluştu ama devam ediyorum.")
            
        return "", thoughts 

    def _generate_trace_id(self) -> str:
        """Benzersiz trace ID oluşturur."""
        return f"trace_{uuid.uuid4().hex[:12]}"

    async def _proactive_memory_hydration(self, ctx: RequestContext, hints: List[str]) -> str:
        """
        Fetches additional context based on proactive hints.
        """
        if not hints:
            return ""
        
        extra_context = []
        logger.info(f"[Brain] Proactive Hydration triggered for hints: {hints}")
        
        try:
            for hint in hints:
                if hint == "FUTURE_PLAN":
                    catalog = get_catalog()
                    if catalog:
                        experience_preds = catalog.get_predicates_by_group("experience", include_aliases=True)
                        experience_preds += catalog.get_predicates_by_group("goal", include_aliases=True)
                    else:
                        experience_preds = ["VISITED", "EXPERIENCED", "PLANNED", "LIKES"]
                    # Fetch past travel/plan related facts
                    results = await self.graph_repo.query(
                        "MATCH (u:User {id: $uid})-[r:FACT]->(n) WHERE r.predicate IN $preds RETURN type(r) as rel, n.name as name LIMIT 5",
                        {"uid": ctx.user_id, "preds": experience_preds}
                    )
                    if results:
                        extra_context.append("\n[GEÇMİŞ PLANLAR/DENEYİMLER]")
                        extra_context.extend([f"  • {r['rel']} {r['name']}" for r in results])
                
                elif hint == "PREFERENCE_RECALL":
                    catalog = get_catalog()
                    if catalog:
                        preference_preds = catalog.get_predicates_by_group("preference", include_aliases=True)
                    else:
                        preference_preds = ["SEVER", "SEVMIYOR", "HOBISI", "FAVORISI"]
                    # Fetch general preferences
                    results = await self.graph_repo.query(
                        "MATCH (u:User {id: $uid})-[r:FACT]->(n) WHERE r.predicate IN $preds RETURN type(r) as rel, n.name as name LIMIT 5",
                        {"uid": ctx.user_id, "preds": preference_preds}
                    )
                    if results:
                        extra_context.append("\n[BİLİNEN TERCİHLER]")
                        extra_context.extend([f"  • {r['rel']} {r['name']}" for r in results])
        except Exception as e:
            logger.warning(f"[Brain] Proactive hydration failed: {e}")
            
        return "\n".join(extra_context) if extra_context else ""

    async def _get_history(self, session_id: str) -> List[Any]:
        """
        Fetches conversation history.
        Strategy: Hot (Redis) -> Warm (SQL).
        """
        history_list = []
        redis_client = None
        if not session_id:
            return history_list

        try:
            # 1. Try Redis (Hot Memory)
            redis_client = await get_redis()
            if redis_client:
                # Key: session:{session_id}:history
                # List of JSON strings
                raw_history = await redis_client.lrange(f"session:{session_id}:history", 0, 9)
                if raw_history:
                    # Redis stores most recent first (LPUSH), need to reverse for chronological
                    # raw_history is [Newest, ..., Oldest]
                    # We want chronological [Oldest, ..., Newest] for context
                    # So we reverse.
                    history_list = [json.loads(m) for m in raw_history]
                    history_list.reverse()
                    from app.config import get_settings
                    settings = get_settings()
                    if settings.DEBUG:
                        logger.debug(f"[Brain] History hit from Redis ({len(history_list)} items)")
                    return history_list
        except Exception as e:
            logger.warning(f"[Brain] Redis history fetch failed: {e}", exc_info=True)

        # 2. Fallback to SQL (Warm Memory)
        try:
            from app.core.database import get_session
            from app.core.models import Message
            from sqlmodel import select, asc
            with get_session() as session:
                stmt = select(Message).where(Message.conversation_id == session_id).order_by(asc(Message.created_at))
                sql_msgs = list(session.exec(stmt).all())
                # Take last 10
                history_list = [{"role": m.role, "content": m.content} for m in sql_msgs[-10:]]
                
                # Async populate Redis (Cache warming)
                if history_list and redis_client:
                    asyncio.create_task(self._warm_redis(session_id, history_list))
                   
                return history_list
        except Exception as e:
            logger.warning(f"[Brain] SQL history fetch failed: {e}")
            return []

    async def _get_history_from_sql(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        if not session_id:
            return []
        try:
            from app.core.database import get_session
            from app.core.models import Message
            from sqlmodel import select, asc
            with get_session() as session:
                stmt = select(Message).where(Message.conversation_id == session_id).order_by(asc(Message.created_at))
                sql_msgs = list(session.exec(stmt).all())
                return [{"role": m.role, "content": m.content} for m in sql_msgs[-limit:]]
        except Exception as e:
            logger.warning(f"[Brain] SQL history fetch failed: {e}")
            return []

    async def _warm_redis(self, session_id: str, messages: List[Dict]):
        """Populates Redis with messages from SQL."""
        try:
            redis_client = await get_redis()
            if not redis_client: return
            
            key = f"session:{session_id}:history"
            await redis_client.delete(key) # Clear old
            
            # Message list is [Oldest, ..., Newest]
            # We want LPUSH so index 0 is newest.
            # So we iterate messages, pushing them. 
            # If we push Oldest, list is [Oldest].
            # Then push Newest, list is [Newest, Oldest].
            # So iterating forward works for LPUSH to store newest at head.
            
            for msg in messages:
                val = json.dumps(msg)
                await redis_client.lpush(key, val)
                
            await redis_client.ltrim(key, 0, 19) # Keep last 20
            await redis_client.expire(key, 3600) # 1 hour TTL
        except Exception as e:
            logger.warning(f"[Brain] Redis warming failed: {e}")
    
    async def process_request(
        self,
        session_id: str = None,
        persona: str = "friendly",
        images: Optional[List[str]] = None
    ) -> str:
        """
        Tek seferlik (non-streaming) request işleme.
        """
        ctx = self._init_request_context(user_id, username, message, session_id, persona, images=images)
        
        # 0. Safety Check (Input)
        is_safe, sanitized_input, issues, safety_model = await self.safety_gate.check_input_safety(ctx.message)
        if not is_safe:
            logger.warning(f"[Brain] Input blocked by safety gate: {issues}")
            return "Üzgünüm, bu isteği güvenlik politikaları nedeniyle işleyemiyorum."
        
        ctx.message = sanitized_input # PII Maskelenmiş metni kullan
        
        # 0. Proactive Due Scanning (Prospective)
        due_tasks = []
        try:
            due_tasks = await self.prospective_service.scan_due_tasks(ctx.user_id)
            if due_tasks:
                logger.info(f"[Brain] Found {len(due_tasks)} due tasks for user {ctx.user_id}")
        except Exception as e:
            logger.warning(f"[Brain] Due scan failed: {e}")
        ctx.due_tasks = due_tasks

        # 1. Telemetry - Start
        try:
            # Fire-and-forget to avoid event loop conflicts
            asyncio.create_task(counter_store.incr_request_try())
        except Exception as e:
            logger.warning(f"[Counters] request_try failed: {e}")
        telemetry.emit(
            EventType.ROUTING,
            {"op": "request_start", "trace_id": ctx.trace_id, "user_id": ctx.user_id},
            component="brain_engine"
        )
        
        # 2a. Memory Context (Basic)
        ctx.memory_context = await self.memory_manager.get_user_context(ctx.user_id, ctx.message)
        
        
        # 2. Hybrid Retrieval (Gateway Integration)
        _, mem_thoughts = await self._memory_retrieval(ctx)
            
        # Inject due tasks into context if any
        if due_tasks:
            task_notes = "\n".join([f"- HATIRLATMA: {t.get('text')} (Zamanı geldi!)" for t in due_tasks])
            ctx.append_context(f"[SİSTEM BİLDİRİMLERİ]\n{task_notes}\n")
        
        # 3. Conversation History
        history_list = await self._get_history(ctx.session_id)
        ctx.set_history(history_list)
        history_dicts = ctx.history_list

        # 4. Intent Analysis & Planning
        plan = await self.intent_manager.analyze_with_context(ctx)
        ctx.plan = plan

        # 4.5 Proactive Hydration
        if plan.proactive_hints:
            extra_msg = await self._proactive_memory_hydration(ctx, plan.proactive_hints)
            if extra_msg:
                ctx.append_context(extra_msg)
                logger.info("[Brain] Context enriched proactively.")
        
        # 5. Task Execution
        results = await self.task_runner.execute_plan_with_context(plan, ctx)
        ctx.task_results = results
        
        # 6. Format tool outputs
        ctx.tool_outputs = self._format_task_results(results)
        
        # 7. Synthesis
        response = await self.synthesizer.synthesize_with_context(
            ctx,
            tool_outputs=ctx.tool_outputs,
            history=history_dicts
        )
        
        # 7.5 Quality & Safety Check (Output)
        _, response, _ = await self.safety_gate.check_output_safety(response)
        is_high_quality, quality_issues = self.quality_gate.check_quality(response, plan.intent, ctx.persona)
        
        if not is_high_quality:
            logger.warning(f"[Brain] Low quality response detected: {quality_issues}")
            # Opsiyonel: Otomatik onarım veya uyarı eklenebilir
            response = self.quality_gate.fix_unclosed_blocks(response)

        ctx.response = response
        
        # 7. Telemetry - End
        telemetry.emit(
            EventType.ROUTING,
            {"op": "request_end", "trace_id": ctx.trace_id, "intent": plan.intent},
            component="brain_engine"
        )
        try:
            await counter_store.incr_request_returned()
        except Exception as e:
            logger.warning(f"[Counters] request_returned failed: {e}")
        
        # 8. Background Learning (Fact + Vector + Redis Upsert)
        asyncio.create_task(self._background_extraction(ctx, response))
        
        return response
    
    async def process_request_stream(
        self,
        user_id: str,
        username: str = "unknown",
        message: str = "",
        session_id: str = None,
        persona: str = "friendly",
        style_profile: Optional[Any] = None, # StyleProfile
        message_id: Optional[int] = None, # SQL Persistent ID
        images: Optional[List[str]] = None # Vision Support
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming request işleme - Ana akış.
        """
        logger.info(f"[DEBUG_STREAM] Called with: user_id={user_id} username={username}")
        log.section(f"Brain Request: {username} ({user_id})")
        log.step("🧠", "Brain Engine Başlatılıyor", f"Mesaj: {message[:50]}...")
        
        ctx = self._init_request_context(
            user_id, 
            username, 
            message, 
            session_id, 
            persona, 
            style_profile=style_profile,
            assistant_message_id=message_id,
            images=images # Vision Support
        )
        
        # 0a. Safety Check (Input)
        is_safe, sanitized_input, issues, safety_model = await self.safety_gate.check_input_safety(ctx.message)
        if not is_safe:
            logger.warning(f"[Brain] Stream input blocked by safety gate: {issues}")
            yield {"type": "error", "content": "Güvenlik Engeli: Bu mesaj işlenemez.", "trace_id": ctx.trace_id}
            return
            
        ctx.message = sanitized_input
        
        # 0b. Proactive Due Scanning (Prospective)
        due_tasks = []
        try:
            due_tasks = await self.prospective_service.scan_due_tasks(ctx.user_id)
            if due_tasks:
                 # Yield notification status
                yield {"type": "status", "content": f"🔔 {len(due_tasks)} hatırlatma bulundu!", "trace_id": ctx.trace_id}
        except Exception as e:
            logger.warning(f"[Brain] Due scan failed: {e}")
        ctx.due_tasks = due_tasks

        # 1. Trace Start
        try:
            await counter_store.incr_request_try()
        except Exception as e:
            logger.warning(f"[Counters] stream_request_try failed: {e}")
        telemetry.emit(
            EventType.ROUTING,
            {"op": "stream_start", "trace_id": ctx.trace_id, "user_id": ctx.user_id},
            component="brain_engine"
        )
        
        # 1. Trace Start -- POINT 6: Proactive Pre-analysis Thought
        try:
            from app.services.brain.context_enricher import context_enricher
            from app.services.brain.thought_generator import thought_generator
            u_ctx = await context_enricher.get_user_context(ctx.user_id, ctx.message, [])
            pre_thought = await thought_generator.generate_thought(
                task_type="intent_planning",
                user_context=u_ctx,
                action_params={"message": ctx.message[:50]},
                personality_mode="friendly"
            )
            yield {"type": "thought", "cat": "ROUTER", "content": pre_thought, "trace_id": ctx.trace_id}
        except Exception:
            pass
        
        
        try:
            # 2a. Memory Context (Basic)
            log.step("📂", "Hafıza Bağlamı Yükleniyor", "Kısa ve Uzun Vadeli Hafıza")
            # OLD: Manual thought removed - using thought_generator instead
            
            ctx.memory_context = await self.memory_manager.get_user_context(ctx.user_id, ctx.message)

            # 2b. High-Speed Memory Retrieval (Unified Gateway)
            _, mem_thoughts = await self._memory_retrieval(ctx)
            
            # Inject due tasks into context if any
            if due_tasks:
                task_notes = "\n".join([f"- HATIRLATMA: {t.get('text')} (Zamanı geldi!)" for t in due_tasks])
                ctx.append_context(f"[SİSTEM BİLDİRİMLERİ]\n{task_notes}\n")
            
            # 3. Conversation History
            from app.core.constants import HISTORY_LIMITS
            synth_limit = HISTORY_LIMITS.get("synthesizer", 15)
            history_list = await self._get_history_from_sql(ctx.session_id, limit=synth_limit)
            ctx.set_history(history_list)
            history_dicts = ctx.history_list

            # 3. Conversation History
            
            # 4. Intent Analysis & Planning
            log.step("🤔", "Niyet Analizi ve Planlama", "Kullanıcı amacı çözümleniyor...")
            plan = await self.intent_manager.analyze_with_context(ctx)
            ctx.plan = plan
            log.info(f"Tespit Edilen Niyet: {plan.intent}")
            
            # [POINT 6] Yield Orchestrator Planning Thought (LLM-generated)
            # We prioritize user_thought for the UI, fallback to reasoning
            orc_thought = getattr(plan, 'user_thought', '') or getattr(plan, 'reasoning', '')
            if orc_thought:
                yield {
                    "type": "thought",
                    "cat": "ROUTER",
                    "content": orc_thought,
                    "task_id": "orchestrator_planning"
                }
            
            # 4.5 Proactive Hydration (Streaming)
            if plan.proactive_hints:
                yield {"type": "thought", "cat": "MEMORY", "content": "Önemli olabileceğini düşündüğüm detaylar için hafızamı biraz daha derinlemesine tarıyorum..."}
                extra_msg = await self._proactive_memory_hydration(ctx, plan.proactive_hints)
                if extra_msg:
                    ctx.append_context(extra_msg)
                    logger.info("[Brain] Context enriched proactively in stream.")
                    # OLD: Manual thought removed - using thought_generator instead
            
            yield {
                "type": "metadata",
                "intent": plan.intent,
                "reasoning": plan.reasoning,
                "model": plan.orchestrator_model,
                "trace_id": ctx.trace_id
            }
            
            # 5. Task Execution (Stream thoughts)
            task_results = []
            if plan.tasks:
                log.step("⚡", "Görev Yürütme", f"Planlanan: {len(plan.tasks)} görev")
            
            async for event in self.task_runner.execute_plan_stream_with_context(plan, ctx):
                if event["type"] == "thought":
                    # Map generic thought to categorized thought
                    cat = "TOOL" # Default category for task runner output
                    if event.get("task_id", "").startswith("t_gen"): cat = "SYNTHESIS"
                    yield {"type": "thought", "cat": cat, "content": event["thought"], "task_id": event.get("task_id")}
                
                elif event["type"] == "task_result":
                    res = event["result"]
                    task_results.append(res)
                    
                    # [NEW] Yield task result for downstream (API/UI)
                    yield {"type": "task_result", "task_id": event.get("task_id"), "result": res}

                    # Collect Sources from Task Result
                    # Collect Sources from Task Result (Robust Strategy)
                    found_sources = []
                    if "unified_sources" in res and res["unified_sources"]:
                        found_sources.extend(res["unified_sources"])
                    # Fallback: Check inside 'output' if it didn't bubble up
                    elif isinstance(res.get("output"), dict) and "unified_sources" in res["output"]:
                        found_sources.extend(res["output"]["unified_sources"])
                    
                    if found_sources:
                         if "unified_sources" not in ctx.metadata:
                             ctx.metadata["unified_sources"] = []
                         ctx.metadata["unified_sources"].extend(found_sources)

            
            # 6. Format tool outputs
            ctx.task_results = task_results
            ctx.tool_outputs = self._format_task_results(task_results)
            
            # Yield Unified Sources BEFORE starting generation (if any)
            if "unified_sources" in ctx.metadata and ctx.metadata["unified_sources"]:
                 srcs = ctx.metadata["unified_sources"]
                 yield {"type": "sources", "data": srcs}
            
            # 6. Final Synthesis (Streaming)
            current_model_id = style_profile.model_config.get('model_id', 'default-v4') if style_profile else 'llama-3.3-70b-versatile'
            log.step("💬", "Yanıt Sentezleniyor", f"Model: {current_model_id}")
            # 6. Final Synthesis (Streaming)
            
            async for chunk in self.synthesizer.synthesize_stream_with_context(
                ctx,
                tool_outputs=ctx.tool_outputs,
                history=history_dicts, # Pass list of dicts
                current_topic=plan.detected_topic,
                style_profile=style_profile
            ):
                yield chunk

            # --- RAG CITATION FOOTER ---
            # NOTE: RAG sources are now handled via unified_sources in ContextCards (v4.4+)
            # Legacy rag_sources footer removed - unified_sources already yielded above (line 583)
            
            # 7. Telemetry - End
            log.success("İşlem Başarıyla Tamamlandı")
            telemetry.emit(
                EventType.ROUTING,
                {"op": "stream_end", "trace_id": ctx.trace_id, "intent": plan.intent, "tasks": len(task_results)},
                component="brain_engine"
            )
            try:
                asyncio.create_task(counter_store.incr_request_returned())
            except Exception as e:
                logger.warning(f"[Counters] stream_request_returned failed: {e}")
            
            # 8. Background Learning (Fact + Vector Upsert)
            asyncio.create_task(self._background_extraction(ctx))
            
        except Exception as e:
            logger.error(f"[BrainEngine] Stream error: {e}")
            yield {"type": "error", "content": f"İşlem hatası: {str(e)}"}
            telemetry.emit(
                EventType.SYSTEM,
                {"op": "stream_error", "trace_id": ctx.trace_id, "error": str(e)},
                component="brain_engine"
            )
            try:
                asyncio.create_task(counter_store.incr_fallback("stream_error"))
            except Exception as ce:
                logger.warning(f"[Counters] fallback stream_error failed: {ce}")
    
    async def _background_extraction(self, ctx: RequestContext, response: str = None):
        """Arka planda bilgi çıkarımı, vektör kaydı ve Redis önbellek güncellemesi."""
        try:
            # A. Redis Cache Update (Push User Msg & AI Response)
            if ctx.session_id:
                try:
                    redis_client = await get_redis()
                    if redis_client:
                        key = f"session:{ctx.session_id}:history"
                        # User Msg (Old -> New order for LPUSH means we push in reverse, OR push individually to HEAD)
                        # We want HEAD (index 0) to be NEWEST.
                        # So if we push User then AI, AI is at 0, User at 1. This is correct for reverse chronological retrieval.
                        
                        await redis_client.lpush(key, json.dumps({"role": "user", "content": ctx.message}))
                        
                        if response:
                             await redis_client.lpush(key, json.dumps({"role": "assistant", "content": response}))
                        
                        await redis_client.ltrim(key, 0, 19) # Keep 20 items (10 turns)
                        await redis_client.expire(key, 3600) # 1 hour
                except Exception as re:
                     logger.warning(f"[BrainEngine] Redis cache update failed: {re}")

            # B. Vector Memory Upsert
            try:
                # Only upsert User Query for retrieval (Active Memory)
                vector = await self.embedder.embed(ctx.message)
                point_id = str(uuid.uuid4())
                await self.vector_repo.upsert(
                    point_id=point_id,
                    vector=vector,
                    payload={"text": ctx.message, "user_id": ctx.user_id, "type": "chat_history", "role": "user", "timestamp": datetime.now().isoformat()}
                )
            except Exception as ve:
                logger.warning(f"[BrainEngine] Vector upsert failed: {ve}")

            # C. Knowledge Extraction (Facts & Tasks) via CENTRAL LLM
            from app.core.llm.generator import LLMRequest
            request = LLMRequest(
                role="knowledge_extraction",
                prompt=f"Kullanıcı mesajı: {ctx.message}",
                temperature=0.1,
                metadata={"system_prompt": EXTRACTOR_SYSTEM_PROMPT}
            )
            
            result = await self.llm.generate(request)
            if not result.ok:
                 logger.warning(f"[BrainEngine] Background extraction failed: {result.text}")
                 return

            raw_extraction = result.text
            
            # Parse JSON
            if raw_extraction.strip().startswith("["):
                items = json.loads(raw_extraction)
                for item in items:
                    item_type = item.get("type", "fact")
                    
                    if item_type == "fact":
                        if item.get("subject") and item.get("predicate"):
                            # Phase 4: Fast Path for High Confidence Knowledge
                            conf = item.get("confidence", 0.0)
                            if conf > 0.8:
                                # Instant Ingestion (Direct to Graph)
                                await self.memory_manager.save_fact(ctx.user_id, item)
                                logger.info(f"[BrainEngine] Instant Ingestion: Highly confident fact stored.")
                            else:
                                # Normal buffer path (already handled by memory manager if called)
                                await self.memory_manager.save_fact(ctx.user_id, item)
                    
                    elif item_type == "task":
                        content = item.get("content")
                        due_at = item.get("due_at")
                        if content:
                            task_id = await self.prospective_service.create_task(ctx.user_id, content, due_at)
                            logger.info(f"[BrainEngine] Created Task: {task_id} - {content}")

        except json.JSONDecodeError:
            pass  # No valid JSON, skip
        except Exception as e:
            logger.warning(f"[BrainEngine] Background extraction failed: {e}")

    async def _auto_register_providers(self) -> None:
        """Auto-register providers based on ModelGovernance requirements."""
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        # Get all unique providers needed for specialist roles and background extraction
        providers_needed = set()
        roles = ["knowledge_extraction", "synthesizer", "orchestrator", "safety"]
        
        for role in roles:
            chain = governance.get_model_chain(role)
            for model_id in chain:
                provider_name = governance.detect_provider(model_id)
                providers_needed.add(provider_name)
        
        provider_adapters = {
            "groq": groq_adapter,
            "gemini": gemini_adapter
        }
        
        for provider in providers_needed:
            if provider in provider_adapters and provider not in self.llm.providers:
                self.llm.register_provider(provider, provider_adapters[provider])
                logger.info(f"[BrainEngine] Auto-registered provider: {provider}")

    def _format_task_results(self, results: List[Dict]) -> str:
        """Task sonuçlarını synthesizer için formatlar."""
        if not results:
            return ""
        
        formatted = []
        for res in results:
            if res.get("status") == "success":
                task_type = res.get("type", "unknown")
                output = res.get("output", "")
                
                if task_type == "tool":
                    tool_name = res.get("tool_name", "tool")
                    formatted.append(f"[{tool_name.upper()}_RESULT]: {output}")
                elif task_type == "generation":
                    model = res.get("model", "unknown")
                    formatted.append(f"[EXPERT_{model}]: {output}")
                else:
                    formatted.append(f"[{task_type.upper()}]: {output}")
            elif res.get("error"):
                formatted.append(f"[ERROR]: {res.get('error')}")
        
        return "\n\n".join(formatted)


# Global Singleton Instance
brain_engine = BrainEngine()
