# app/orchestrator_v42/gateway.py

import asyncio
from typing import Any
import logging
import os
import time
from app.orchestrator_v42.types import (
    RoutingDecision, 
    GatewayResult, 
    dump_model, 
    IntentReport, 
    SafetyReport,
    CapabilityReport,
    ModelSelectionReport,
    RuntimePolicyReport,
    SpecialistOutput,
    ContractedOutput,
    OutputSanitizerReport,
    StreamingRewriteReport,
    VerifyReport,
    JuryReport,
    LlmAdapterReport,
    RagGateReport,    # NEW
    RagAdapterReport   # NEW
)
from app.orchestrator_v42.observability import generate_trace_id, log_event
from app.orchestrator_v42 import telemetry # FAZ 13.6
from app.orchestrator_v42.plugins import (
    intent_classifier, 
    safety_guard,
    capability_router,
    model_catalog,
    model_selector,
    runtime_state,
    runtime_policy,
    specialist_stub,
    stylist_stub,
    contract_guard,
    output_sanitizer,
    streaming_rewriter,
    verify_stub,
    jury_stub,
    llm_client_adapter,
    task_graph,
    # Phase 12 (NEW)
    rag_gate,
    rag_adapter
)
from app.orchestrator_v42.auto_circuit import OrchestratorAutoCircuit # FAZ 13.9

# --- LIVE TRACE ---
try:
    from app.core.live_tracer import LiveTracer
except ImportError:
    class LiveTracer:
        @staticmethod
        def request_in(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def routing_decision(*args, **kwargs): pass
        @staticmethod
        def model_select(*args, **kwargs): pass
# ------------------

# --- GLOBAL SINGLETON STATE (FAZ 3.0) ---
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags # NEW Import

# --- GLOBAL SINGLETON STATE (FAZ 3.0) ---
_RUNTIME_STATE = runtime_state.RuntimeState()
_AUTO_CIRCUIT = OrchestratorAutoCircuit() # FAZ 13.9

class LegacyFallbackRequired(Exception):
    """
    Orchestrator, açıkça eski işlem hattına geri dönülmesine karar verdiğinde
    bu istisna fırlatılır. Çekirdek (Core) sistemi bunu yakalar.
    """
    pass

def _budget_remaining(start_ts: float, limit: float = 3.0) -> float:
    return max(0.0, limit - (time.time() - start_ts))

async def try_handle(*args, **kwargs) -> GatewayResult | None:
    """
    İsteği Orchestrator üzerinden işlemeyi dener.
    
    Akış:
    1. Mesaj ve Trace ID
    2. Niyet & Güvenlik
    3. Yetenek (Faz 8.0) & Model (Faz 9.0)
    4. Çalışma Zamanı Politikası
    5. Yanıt Sözleşmesi
    6. Akışkan Rewrite & Verify/Jury
    7. LLM Adaptörü
    8. Legacy Fallback
    """
    trace_id = generate_trace_id()
    start_ts = time.time()
    
    # 0. Feature Flags Yükleme (Faz 13.0)
    flags = OrchestratorFeatureFlags.load_from_env()
    print(f"!!! GATEWAY ENTRY DOĞRULANDI !!! Trace: {trace_id} Flags: {flags}")
    log_event(trace_id, "Gateway isteği aldı", {"flags": dump_model(flags)})
    
    # KÜRESEL KILLSWITCH (FAZ 13.7)
    if not flags.production_enabled:
        print(f"DEBUG: Orchestrator Fallback - Production Disabled (flags.production_enabled={flags.production_enabled})")
        log_event(trace_id, "Production Kapalı (Killswitch) - Legacy Fallback")
        await telemetry.count("orch_fallback", labels={"reason": "production_off"})
        raise LegacyFallbackRequired("Production kapalı")
    
    # OTOMATİK DEVRE KESİCİ (FAZ 13.9)
    now = time.time()
    if _AUTO_CIRCUIT.is_open(now):
        print(f"DEBUG: Orchestrator Fallback - Auto Circuit Open")
        log_event(trace_id, "Otomatik devre kesici açık - Legacy Fallback", _AUTO_CIRCUIT.snapshot(now))
        await telemetry.count("orch_fallback", labels={"reason": "auto_circuit_open"})
        raise LegacyFallbackRequired("Otomatik devre kesici açık")
    
    # Telemetry: Deneme
    await telemetry.count("orch_try")
    
    # 1. Güvenli Mesaj Ayrıştırma
    payload = kwargs.get("payload")
    message = ""
    if payload and hasattr(payload, "message"):
        message = payload.message
    elif kwargs.get("message"):
        message = kwargs.get("message")
    
    username = kwargs.get("username", "bilinmiyor")
    conversation_id = kwargs.get("conversation_id")  # History loading için gerekli
    
    # Debug: conversation_id kontrolü
    print(f"DEBUG: [Gateway] conversation_id={conversation_id}, username={username}")

    # [GATEWAY DEBUG] Request Recv | User: {user_id} | ConvID: {conversation_id}")
    
    # History Loading
    # history_items = await self._safe_load_history(user_id, conversation_id) # This line requires `self` and `_safe_load_history`
    # print(f"[GATEWAY DEBUG] Loaded History Items: {len(history_items)}")
    # if history_items:
    #      print(f"[GATEWAY DEBUG] Last message in history: {history_items[-1]['content'][:50]}...")
    # else:
    #      print("[GATEWAY DEBUG] No history found (or empty).")

    # Context (User Profile, etc)
    # memory_context = await self.memory_adapter.get_memory_context(...)
    # Şimdilik dry_run=False ile gerçek veri
    try:
         # FLagleri al
         # ...
         pass
    except:
         pass

    # 2. Paralel İşleme (Taslak Pluginler)
    log_event(trace_id, "Paralel Analiz Başlatılıyor (Niyet + Güvenlik)")
    
    intent_report = None
    safety_report = None
    
    intent_res = {}
    safety_res = {}
    
    try:
        results = await asyncio.gather(
            intent_classifier.classify(message, username),
            safety_guard.check(message, username),
            return_exceptions=True
        )
        
        raw_intent, raw_safety = results
        
        # --- NİYET RAPORU İŞLEME (Faz 7.1 Fix) ---
        if isinstance(raw_intent, Exception):
            log_event(trace_id, "Niyet Sınıflandırıcı Hatası", {"hata": str(raw_intent)})
        else:
            intent_res = raw_intent
            try:
                if isinstance(intent_res, dict):
                    intent_report = IntentReport(**intent_res)
                else:
                    intent_report = intent_res 
                
                # Niyet Raporu Loglama
                log_event(trace_id, "Niyet Raporu", dump_model(intent_report))
                
                # Görev Grafiği Sıralaması (Topo Sort)
                raw_tasks = []
                if isinstance(intent_res, dict):
                    raw_tasks = intent_res.get("tasks", [])
                elif intent_report:
                    raw_tasks = [t.model_dump() if hasattr(t, "model_dump") else t.dict() for t in intent_report.tasks]
                
                sorted_tasks = task_graph.topo_sort(raw_tasks)
                sorted_ids = [t.get("id") for t in sorted_tasks]
                
                # Graf Uyarılarını Kontrol Et
                unknown_dep_count = 0
                cycle_count = 0
                for t in sorted_tasks:
                    meta = t.get("meta", {})
                    if meta.get("unknown_dep_ignored"):
                        unknown_dep_count += 1
                    if meta.get("cycle_suspected"):
                        cycle_count += 1
                
                if unknown_dep_count > 0 or cycle_count > 0:
                    log_event(trace_id, "Görev Grafiği Uyarısı", {
                        "unknown_dep": unknown_dep_count, 
                        "cycle": cycle_count
                    })

                log_event(trace_id, "Görev Grafiği Sıralaması", {
                    "sirali_task_idler": sorted_ids, 
                    "task_sayisi": len(sorted_tasks)
                })
                
                # Multi-Intent Loglama
                matched_rules = intent_report.matched_rules
                if len(intent_report.tasks) > 1:
                     log_event(trace_id, "Çoklu Niyet Tespit Edildi", {"matched_rules": matched_rules})
                     
            except Exception as e:
                log_event(trace_id, "Niyet Raporu Ayrıştırma Hatası", {"hata": str(e), "ham_veri": str(intent_res)})

        # --- GÜVENLİK RAPORU İŞLEME (Faz 7.0) ---
        if isinstance(raw_safety, Exception):
            log_event(trace_id, "Güvenlik Modeli Hatası", {"hata": str(raw_safety)})
        else:
            safety_res = raw_safety
            try:
                if isinstance(safety_res, dict):
                    safety_report = SafetyReport(**safety_res)
                else:
                    safety_report = safety_res
                log_event(trace_id, "Güvenlik Raporu", dump_model(safety_report))
            except Exception as e:
                 log_event(trace_id, "Güvenlik Raporu Ayrıştırma Hatası", {"hata": str(e), "ham_veri": str(safety_res)})
            
            if safety_report:
                safe_val = safety_report.input_safe
                risk_val = safety_report.risk
            else:
                safe_val = safety_res.get("input_safe", True)
                risk_val = safety_res.get("risk", "none")

            if not safe_val:
                log_event(trace_id, "Güvenlik Engeli (Politika): Bu istek orchestrator tarafında reddedilirdi", {"sebep": "Yasaklı İçerik"})
            elif risk_val in ["medium", "high"]:
                log_event(trace_id, "Güvenlik Uyarısı (Riskli İçerik)", {"risk": risk_val})

    except Exception as e:
        log_event(trace_id, "Paralel İşleme Kritik Hatası", {"hata": str(e)})

    selected_model_id = "bilinmiyor"

    # 3. Yetenek Yönlendirme ve Model Seçimi (FAZ 8.0 & 9.0)
    try:
        log_event(trace_id, "Yetenek ve Model Analizi Başlatılıyor")
        
        cap_input_intent = intent_report if intent_report else intent_res
        cap_input_safety = safety_report if safety_report else safety_res
        
        cap_res = await capability_router.derive(cap_input_intent, cap_input_safety)
        capability_report = None
        
        try:
            capability_report = CapabilityReport(**cap_res)
            log_event(trace_id, "Yetenek Raporu", dump_model(capability_report))
            
            log_event(trace_id, "Yetenek Türetilen Liste", {
                "required_capabilities": capability_report.required_capabilities, 
                "cap_sayisi": len(capability_report.required_capabilities)
            })
            
            if "guvenlik_engeli_sinyali" in capability_report.matched_rules:
                log_event(trace_id, "Güvenlik Engeli Sinyali (Yetenek)", {
                    "risk": "high", 
                    "not": capability_report.notes
                })
                
        except Exception as e:
            log_event(trace_id, "Yetenek Raporu Hatası", {"hata": str(e), "ham_veri": str(cap_res)})
        # 6. Çalışma Zamanı Politikası Kontrolü (Yer tutucu)
        # NOT: Bu bölüm önceki bir fazdan kalan taslak/yer tutucu görünüyor.
        # Asıl çalışma zamanı politikası aşağıdaki "4. Çalışma Zamanı Politikası" bölümünde uygulanıyor.
        # Şimdilik kullanıcı talebi gereği korunuyor; final temizlikte kaldırılabilir.
        # state = runtime_state.RuntimeState() # Gerçek uygulamada dependency injection ile gelir
        # policy_res = runtime_policy.choose_key_and_limits(state, available_keys, model_res["selected_model_id"])
        
        # runtime_report = {
        #     "selected_key_id": policy_res["selected_key_id"],
        #     "cooldown_active": policy_res["cooldown_active"],
        #     "rate_limit_remaining": policy_res["remaining_requests"],
        #     "status": "approved" if policy_res["selected_key_id"] else "rejected"
        # }
        # # Log: Policy
        # await log_event("Runtime Policy Kontrolü", level="info", details={"key": runtime_report["selected_key_id"]})

        # --- FAZ 12.0: RAG INTELLIGENT GATE & ADAPTER ---
        
        # A. RAG Kararı (Gate) - (FAZ 12.0 Fix Pack)
        rag_gate_report = None
        try:
            # rag_gate.decide returns a Dict
            gate_res = rag_gate.decide(
                intent_report=intent_report if intent_report else intent_res, 
                capability_report=capability_report if capability_report else cap_res, 
                message=message
            )
            rag_gate_report = RagGateReport(**gate_res)
            log_event(trace_id, "RAG Kapısı Kararı", {"decision": rag_gate_report.decision, "reasons": rag_gate_report.signal_reasons})
        except Exception as e:
             log_event(trace_id, "RAG Gate Hatası (Fail-Closed)", {"hata": str(e)})
             # Fallback
             rag_gate_report = RagGateReport(
                 decision="off", signal_reasons=[], quick_check={}, notes="Gate hatası, kapalı."
             )
             await telemetry.count("orch_warning", labels={"type": "rag_gate_fail"})

        # B. RAG Çalıştırma (Adapter) 
        rag_context = [] # Default empty list
        rag_adapter_report = None
        
        if rag_gate_report.decision == "on":
            # 13.11 RAG ROLLOUT & BÜTÇE
            # Orchestrator kullanacak mıyız? (Henüz karar verilmedi ama ön kontrol)
            # Rollout check'i erkene almak lazım ama akışı bozamıyoruz.
            # Varsayım: Herkese açık ama dry-run ile korunuyor.
            
            try:
                log_event(trace_id, "RAG Adaptör Çalıştırılıyor", {"mode": "adapter_active"})
                await telemetry.count("rag_attempt")
                
                # Bütçe Kontrolü
                rem_budget = _budget_remaining(start_ts)
                rag_timeout = min(0.6, rem_budget) # Max 0.6s veya kalan
                
                # Bütçe çok azsa hiç deneme (Event loop'u meşgul etme)
                if rem_budget < 0.1:
                    log_event(trace_id, "RAG Bütçesi Yetersiz - Atlanıyor")
                    await telemetry.count("rag_budget_exceeded")
                    
                    rag_adapter_report = RagAdapterReport(
                        ran=False, 
                        dry_run=flags.rag_dry_run if flags else True, 
                        doc_count=0, 
                        docs=[], 
                        notes="RAG bütçesi yetersiz, atlandı."
                    )
                else:
                    # Adaptörü Çağır (Thread içinde çalıştır ki event loop bloklanmasın)
                    # Böylece wait_for gerçekten zaman aşımını yakalayabilir.
                    try:
                        adapter_res = await asyncio.wait_for(
                            asyncio.to_thread(
                                rag_adapter.fetch_context,
                                query=message,
                                user_id=username,
                                extra={"scope": "user"},
                                flags=flags
                            ),
                            timeout=rag_timeout
                        )
                        
                        rag_adapter_report = RagAdapterReport(**adapter_res)
                        
                        if rag_adapter_report.dry_run:
                            await telemetry.count("rag_skipped_dry_run")
                        elif rag_adapter_report.doc_count > 0:
                            await telemetry.count("rag_used", labels={"type": "legacy_v2"})
                        
                        # Context için dokümanları al
                        rag_context = [
                            d.model_dump() if hasattr(d, "model_dump") else d 
                            for d in rag_adapter_report.docs
                        ]
                        
                        log_event(trace_id, "RAG Bağlamı Alındı", {
                            "doc_count": rag_adapter_report.doc_count,
                            "dry_run": rag_adapter_report.dry_run,
                            "notes": rag_adapter_report.notes
                        })

                    except asyncio.TimeoutError:
                         log_event(trace_id, "RAG Zaman Aşımı (Budget Exceeded)")
                         await telemetry.count("rag_budget_exceeded")
                         # Fail-soft: Boş rapor dön, exception fırlatma
                         rag_adapter_report = RagAdapterReport(
                            ran=False, 
                            dry_run=True, # Timeout olduysa güvenli mod varsay
                            doc_count=0, 
                            docs=[], 
                            notes="RAG zaman aşımı, atlandı."
                         )
                         
            except Exception as e:
                # Diğer bilinmeyen hatalar (Adapter içi crash vb.)
                log_event(trace_id, "RAG Adaptör Hatası (Fallback)", {"hata": str(e)})
                await telemetry.count("rag_error", labels={"type": "adapter_fail"})
                # Fail-soft Rapor
                rag_adapter_report = RagAdapterReport(
                    ran=True, 
                    dry_run=True, 
                    doc_count=0, 
                    docs=[], 
                    notes=f"Adaptör hatası: {e}"
                )
        else:
             # RAG Kapalı ise boş rapor
             rag_adapter_report = RagAdapterReport(
                ran=False, 
                dry_run=False, 
                doc_count=0, 
                docs=[], 
                notes="Kapı kapalı"
             )
        
        # Log RAG Gate and Adapter reports (Safe dump)
        try:
            log_event(trace_id, "RAG Gate Raporu", dump_model(rag_gate_report))
            log_event(trace_id, "RAG Adaptör Raporu", dump_model(rag_adapter_report))
        except:
            pass

        catalog = model_catalog.get_catalog()
        
        req_caps = ["sohbet"] 
        if capability_report:
            req_caps = capability_report.required_capabilities
        elif isinstance(cap_res, dict):
            req_caps = cap_res.get("required_capabilities", ["sohbet"])
            
        sel_res = model_selector.select(req_caps, catalog)
        selected_role_flags = sel_res.get("role_flags", {}) # [FAZ 16.7]
        
        
        try:
            selection_report = ModelSelectionReport(**sel_res)
            log_event(trace_id, "Model Seçim Raporu", dump_model(selection_report))
            selected_model_id = selection_report.selected_model_id
            
            # FAZ 9.0 Log Güçlendirme
            log_event(trace_id, "Model Seçim Özeti", {
                "selected_model_id": selected_model_id,
                "score": selection_report.score,
                "eksik_yetenek_sayisi": len(selection_report.missing_capabilities),
                "matched_rules": selection_report.matched_rules
            })
            
        except Exception as e:
            log_event(trace_id, "Model Seçim Raporu Hatası", {"hata": str(e), "ham_veri": str(sel_res)})
            if isinstance(sel_res, dict):
                selected_model_id = sel_res.get("selected_model_id", "bilinmiyor")

    except Exception as e:
         log_event(trace_id, "Yetenek/Model Akışı Hatası", {"hata": str(e)})

    # --- FAZ 14.0: ARAÇLAR ve EYLEMLER (MVP) ---
    tool_evidence = {"ran": False, "ok_count": 0, "items": []}
    try:
        from app.orchestrator_v42.tools import action_policy, action_compiler, action_host
        
        # 1. Karar (Policy)
        # Niyet ve güvenliğe göre araç çalıştırma kararı
        print(f"DEBUG: [Gate] Action Policy Calling... Flags: {flags.tools_enabled}")
        tools_decision = action_policy.decide_tools_run(flags, safety_report, intent_report)
        print(f"DEBUG: [Gate] Tool Decision: {tools_decision}")
        
        log_event(trace_id, "Araç Kullanım Kararı", tools_decision)
        
        if not tools_decision["run_tools"]:
            print(f"DEBUG: [Gate] Tools SKIPPED via Policy: {tools_decision['reason']}")
            # Kapalıysa nedenine göre telemetri bas
            reason_lbl = "disabled"
            if tools_decision["reason"].startswith("Risk"):
                reason_lbl = "risk_high"
                await telemetry.count("tool_skipped_risk", labels={"risk": tools_decision.get("risk_level", "unknown")})
            else:
                await telemetry.count("tool_skipped_disabled")
        else:
            print("DEBUG: [Gate] PROCEEDING to Tool Compile")
            # 2. Planlama (Compiler)
            tool_plan = None
            
            # A) Task-Based Plan (FAZ 14.6)
            tasks_source = []
            if intent_report and hasattr(intent_report, "tasks"):
                tasks_source = [t.model_dump() if hasattr(t, "model_dump") else t.__dict__ for t in intent_report.tasks]
            elif isinstance(intent_res, dict):
                 tasks_source = intent_res.get("tasks", [])
                 
            if tasks_source:
                print(f"DEBUG: [Gate] TASKS SOURCE: {tasks_source}")
                print(f"DEBUG: [Gate] Compiling from TASKS: {len(tasks_source)}")
                tool_plan = action_compiler.compile_tool_plan_from_tasks(tasks_source, flags)
            
            # B) Legacy / Fallback Plan
            if not tool_plan or not tool_plan.calls:
                 print(f"DEBUG: [Gate] Compiling Legacy Plan (Fallback)")
                 caps_for_tools = ["sohbet"]
                 if capability_report:
                     caps_for_tools = capability_report.required_capabilities
                 elif isinstance(cap_res, dict):
                     caps_for_tools = cap_res.get("required_capabilities", ["sohbet"])
                     
                 tool_plan = action_compiler.compile_tool_plan(message, caps_for_tools, flags)
            
            if tool_plan.calls:
                print(f"DEBUG: [Gate] Tool Plan READY: {[c.name for c in tool_plan.calls]}")
                log_event(trace_id, "Araç Planı Oluşturuldu", {"calls": len(tool_plan.calls), "names": [c.name for c in tool_plan.calls]})
                
                # 3. Yürütme (Host) - Bütçe ve Timeout Kontrolü (FAZ 14.2)
                rem_budget = _budget_remaining(start_ts)
                
                # Eğer bütçe çok azsa hiç deneme
                if rem_budget < 0.15:
                    log_event(trace_id, "Araç bütçesi yetersiz, atlandı")
                    # Bu bir hata değil, operasyonel karar
                else:
                    # Timeout hesapla: Max 7.0s (Web Arama için)
                    tool_timeout = min(7.0, max(0.1, rem_budget - 0.2))
                    print(f"DEBUG: [Gate] Tool Timeout set to: {tool_timeout}s")
                    
                    tool_results = await action_host.execute_plan(
                        tool_plan, 
                        flags, 
                        trace_id, 
                        telemetry,
                        timeout_s=tool_timeout
                    )
                    
                    # 4. Kanıt Toplama (Evidence) for Specialist
                    try:
                        from app.orchestrator_v42.tools import evidence_builder
                        
                        # Artık liste değil, structured dict
                        tool_evidence_data = evidence_builder.build_tool_evidence(tool_results)
                        
                        # Mevcut tool_evidence değişkeni liste olarak başladı ([])
                        # Bunu override ediyoruz. 
                        # execution_context içinde bu değer gidecek.
                        tool_evidence = tool_evidence_data
                        
                    except ImportError:
                        # Fallback (Eski usul liste)
                        tool_evidence = []
                        for res in tool_results:
                            if res.ok:
                                tool_evidence.append(f"Araç Sonucu ({res.name}): {str(res.output)}") 
                    except Exception as e:
                        log_event(trace_id, "Evidence Builder Hatası", {"hata": str(e)})
                        # tool_evidence boş kalsın veya []
                        tool_evidence = {"error": "Evidence build failed", "items": []}
            else:
                print("DEBUG: [Gate] No tools to run (Plan empty).")
    
    except Exception as e:
        # Araç hatası akışı bozmamalı
        print(f"DEBUG: [Gate] Tool Flow Exception: {e}")
        log_event(trace_id, "Araç Yürütme Akış Hatası (Fail-Soft)", {"hata": str(e)})
        # await telemetry.count("tool_flow_error")


        
    # --- ARAÇLAR BLOĞU (Mevcut kod korunuyor, sadece referans için) ---
    # Bu blok replace edilmiyor çünkü start line aşağıda.
    
    print("DEBUG: [Gate] Breadcrumb 1 - Starting Memory Context")

    # --- FAZ 14.1: HAFIZA BAĞLAMI (Memory Context) ---
    memory_context_res = {"items": []}
    
    # Kullanıcı ID Temizliği (Tek Kaynak)
    # "bilinmiyor", "unknown" veya boş string ise None yap
    req_user_id = username if (username and username.lower() not in ["bilinmiyor", "unknown", "none"]) else None
    
    try:
        print("DEBUG: [Gate] Breadcrumb 2 - Importing Memory Adapter")
        from app.orchestrator_v42 import memory_adapter
        
        # Eğer kullanıcı yoksa hafızaya hiç gitme (ama hata da sayma)
        if req_user_id:
             print(f"DEBUG: [Gate] Breadcrumb 3 - Calling Memory Adapter for {req_user_id}")
             mem_ctx = await memory_adapter.get_memory_context(req_user_id, message, flags, trace_id)
             print("DEBUG: [Gate] Breadcrumb 4 - Memory Adapter Returned")
        else:
             # Kullanıcı yok -> Boş context
             mem_ctx = {"items": [], "ran": False, "dry_run": False, "item_count": 0, "notes": "Kullanıcı ID yok"}

        # Telemetri
        if not flags.memory_enabled:
             await telemetry.count("memory_skipped_disabled")
        elif not req_user_id:
             # Kullanıcı yok diye skip
             pass 
        else:
             await telemetry.count("memory_attempt", labels={"type": "read"})
             
             if mem_ctx["item_count"] > 0 and not mem_ctx["dry_run"]:
                 await telemetry.count("memory_used", labels={"type": "read"})
             
             # Hata durumu
             if "Hafıza hatası" in mem_ctx.get("notes", "") or "Hafıza servisi bulunamadı" in mem_ctx.get("notes", ""):
                 await telemetry.count("memory_error", labels={"type": "read"})
        
        if mem_ctx.get("ran") or mem_ctx.get("item_count", 0) > 0:
             log_event(trace_id, "Hafıza Bağlamı", {
                 "ran": mem_ctx.get("ran"),
                 "dry_run": mem_ctx.get("dry_run"),
                 "count": mem_ctx.get("item_count"),
                 "notes": mem_ctx.get("notes")
             })
             
        memory_context_res = mem_ctx

    except Exception as e:
        print(f"DEBUG: [Gate] Memory Flow Error: {e}")
        log_event(trace_id, "Hafıza Akış Hatası (Fail-Soft)", {"hata": str(e)})
        # await telemetry.count("memory_flow_error")

    # 4. Çalışma Zamanı Politikası (DEPRECATED)
    # ... (Silindi) ...

    # 5. Yanıt Sözleşmesi ve Çıktı Üretimi (FAZ 4.0)
    # ...
    # FAZ 13.2: Bu mantık tamamen Bölüm 7 (Managed Call) içine taşındı.
    # Eski kod temizlendi.

    print("DEBUG: [Gate] Breadcrumb 5 (Fixed) - Starting Specialist Block", flush=True)
    
    # 5. Yanıt Sözleşmesi ve Çıktı Üretimi (FAZ 4.0)
    final_solution_text = ""
    contracted_out = None
    
    # TRY START
    try:
        print("DEBUG: [Gate] Breadcrumb 5.1 (Fixed) - Inside Try", flush=True)
        log_event(trace_id, "Uzman Üretim Başlatılıyor")
        
        # Context Hazırlığı
        safe_rag_context = locals().get("rag_context", [])
        safe_indices = locals().get("capability_report", None)
        cap_dump = dump_model(safe_indices) if safe_indices else {}

        
        import sys
        
        # HISTORY YÜKLEME (sys.stdout kullanımı)
        sys.stdout.write(f"DEBUG: [Gate] Calling _safe_load_history [User:{req_user_id}]\n")
        sys.stdout.flush()
        
        history_items = _safe_load_history(req_user_id, conversation_id)
        
        sys.stdout.write(f"DEBUG: [Gate] History Result Size: {len(history_items)}\n")
        if history_items:
             sys.stdout.write(f"DEBUG: [Gate] First Item: {str(history_items[0])[:50]}...\n")
        sys.stdout.flush()

        execution_context = {
            "intent": dump_model(intent_report) if intent_report else intent_res,
            "capabilities": cap_dump,
            "rag_evidence": safe_rag_context,
            "tool_evidence": tool_evidence,
            "memory_context": memory_context_res.get("items", []),
            "history": history_items,
            # [FAZ 16.6] Router Model Kablolama
            "selected_model_hint": selected_model_id, 
            "selection_reason": selection_report.reason if 'selection_report' in locals() else "fallback"
        }
        
        # [FAZ 16.6] Telemetri: Model Seçimi
        await telemetry.increment("orch_model_selected", labels={"type": selected_model_id})
        
        sys.stdout.write("DEBUG: [Gate] Execution Context Keys: " + str(list(execution_context.keys())) + "\n")
        sys.stdout.flush()
        
        sys.stdout.write("DEBUG: [Gate] CALLING SPECIALIST STUB...\n")
        sys.stdout.flush()

        specialist_out = await specialist_stub.produce(message, context=execution_context)

        sys.stdout.write("DEBUG: [Gate] SPECIALIST STUB RETURNED\n")
        sys.stdout.write(f"DEBUG: [Gate] RAW OUT: {str(specialist_out)}\n")
        sys.stdout.flush()

        # [FAZ 16.7] Cascade Telemetry
        if isinstance(specialist_out, dict):
             meta = specialist_out.get("adapter_meta", {})
             if meta.get("cascade_used"):
                 orig = meta.get("original_hint", "unknown")
                 await telemetry.count("orch_cascade_fallback", labels={"acc": "1", "from": orig})
                 log_event(trace_id, "Model Cascade Triggered", meta)


        
        spec_report = None
        try:
            spec_report = SpecialistOutput(**specialist_out)
            log_event(trace_id, "Uzman Çıktısı Doğrulandı", dump_model(spec_report))
        except Exception as e:
            log_event(trace_id, "Uzman Çıktısı Doğrulama Hatası", {"hata": str(e)})
            sys.stdout.write(f"DEBUG: [Gate] Validation Failed: {e}\n")
            sys.stdout.flush()
            # FALLBACK: Doğrulama başarısız olsa bile metni kurtar
            if isinstance(specialist_out, dict) and "solution_text" in specialist_out:
                 final_solution_text = specialist_out["solution_text"]
            elif not specialist_out:
                 final_solution_text = ""
            else:
                 final_solution_text = str(specialist_out) # En kötü ihtimal stringe çevir
            
        if spec_report:
            # [FIX] Failsafe: En başta ham metni ata, alt adımlar (stylist/contract) patlarsa bu kalsın.
            final_solution_text = spec_report.solution_text
            sys.stdout.write(f"DEBUG: [Gate] After Spec Failsafe: len={len(final_solution_text)}\n"); sys.stdout.flush()
            
            log_event(trace_id, "Stil Düzenleme Başlatılıyor")
            rewritten_text = await stylist_stub.rewrite(
                spec_report.solution_text, 
                style_profile={"mode": "taslak"}
            )
            log_event(trace_id, "Stilist Çıktısı Alındı", {"uzunluk": len(rewritten_text)})
            
            log_event(trace_id, "Kontrat Uygulanıyor (Koruma Kalkanı)")
            contracted = contract_guard.enforce_contract(
                original=dump_model(spec_report), 
                rewritten_solution_text=rewritten_text
            )
            contracted_out = contracted
            
            cont_report = None
            try:
                cont_report = ContractedOutput(**contracted)
                log_event(trace_id, "Kontratlı Çıktı İmzalandı", {
                    "immutable_hash": cont_report.immutable_hash,
                    "code_count": len(cont_report.code_blocks)
                })
            except Exception as e:
                 log_event(trace_id, "Kontrat Verisi Hatası", {"hata": str(e)})

            if cont_report:
                log_event(trace_id, "Çıktı Temizleyici Çalıştırılıyor")
                sanitized_text = output_sanitizer.sanitize(cont_report.solution_text)
                
                was_modified = sanitized_text != cont_report.solution_text
                san_report = OutputSanitizerReport(
                    was_modified=was_modified, 
                    reason="Format bozukluğu giderildi" if was_modified else "Temiz"
                )
                log_event(trace_id, "Temizleyici Raporu", dump_model(san_report))
                final_solution_text = sanitized_text
                sys.stdout.write(f"DEBUG: [Gate] After Sanitizer: len={len(final_solution_text)}\n"); sys.stdout.flush() 

    except Exception as e:
        log_event(trace_id, "Yanıt Sözleşmesi Akış Hatası", {"hata": str(e)})



    # 6. Akışkan Yeniden Yazım & Verify/Jury (FAZ 5.0 + 13.4 QC Gating)
    try:
        # QC Karar Mekanizması
        from app.orchestrator_v42.quality_control import decide_quality_control
        
        # safety_report ve intent_report context'ten alınmalı
        # safety_report yukarıda 'safety_report' değişkeninde, yoksa 'safety_res' içinde olabilir
        qc_safety = safety_report if safety_report else SafetyReport(**safety_res) if safety_res else None
        
        qc = decide_quality_control(flags, qc_safety, intent_report)
        
        
        # [FAZ 16.7] Pipeline Role Override
        # 1. Verify Override
        has_tools = False
        if isinstance(tool_evidence, list) and tool_evidence: has_tools = True
        if isinstance(tool_evidence, dict) and tool_evidence.get("items"): has_tools = True
        
        force_verify = (
             selected_role_flags.get("can_judge", False) 
             or has_tools
             or (qc_safety and qc_safety.risk_level == "high")
        )
        if force_verify:
            qc["run_verify"] = True
            qc["reason"] += "+ForceVerify"
            
        # 2. Jury Override (Streaming -> Off)
        if flags.streaming_enabled:
            qc["run_jury"] = False

        log_event(trace_id, "Kalite Kontrol Kararı", {
            "run_verify": qc["run_verify"],
            "run_jury": qc["run_jury"],
            "risk": qc["risk_level"],
            "jury_off_by_stream": qc["jury_forced_off_by_streaming"],
            "reason": qc["reason"]
        })

        # Telemetry: QC Kararı
        qc_labels = {
            "verify": "1" if qc["run_verify"] else "0",
            "jury": "1" if qc["run_jury"] else "0", 
            "risk": qc["risk_level"]
        }
        await telemetry.count("orch_qc_decision", labels=qc_labels)
        
        if qc["jury_forced_off_by_streaming"]:
            log_event(trace_id, "Streaming açık olduğu için jüri devre dışı bırakıldı")
            await telemetry.count("orch_qc_jury_bypass_stream")

        # Rewrite İşlemi (Simülasyon) - Artık Flag Kontrollü
        # Eğer streaming kapalıysa bu simülasyonu yapma (Gerçekçi değil)
        if flags.streaming_enabled and final_solution_text:
            log_event(trace_id, "Akışkan Yeniden Yazım (Simülasyon) Başlatılıyor")
            chunk_size = 30
            chunks = [final_solution_text[i:i+chunk_size] for i in range(0, len(final_solution_text), chunk_size)]
            
            rewriter = streaming_rewriter.StreamingRewriter()
            _, stream_rep = await rewriter.rewrite_chunks(chunks)
            
            try:
                stream_report_model = StreamingRewriteReport(**stream_rep)
                log_event(trace_id, "Akışkan Rewrite Raporu", dump_model(stream_report_model))
            except Exception as e:
                 log_event(trace_id, "Stream Rapor Hatası", {"hata": str(e)})
        elif not flags.streaming_enabled:
             # Log kirliliği olmaması için sadece debug seviyesinde olabilir ama burada açıkça belirtelim
             pass # Streaming kapalı, simülasyon atlandı

        # VERIFY ÇAĞRISI
        if qc["run_verify"]:
            if not contracted_out:
                log_event(trace_id, "Kontratlı veri yok, Verify atlanıyor - Legacy Fallback")
                await telemetry.count("orch_fallback", labels={"reason": "qc_no_contract"})
                raise LegacyFallbackRequired("Doğrulanacak veri yok")

            log_event(trace_id, "Doğrulama (Verify) Başlatılıyor...")
            
            # Verify Stub Çağrısı
            v_out = verify_stub.verify(contracted_out)
            
            # Sonuç Analizi
            # VerifyStub basit dict dönüyor: {passed: bool, notes: str, ...}
            is_passed = v_out.get("passed", False) if isinstance(v_out, dict) else False
            notes = v_out.get("notes", "Bilinmiyor") if isinstance(v_out, dict) else "Geçersiz çıktı"

            if not is_passed:
                 log_event(trace_id, "Doğrulama Başarısız - Legacy Fallback", {"not": notes})
                 await telemetry.count("orch_fallback", labels={"reason": "qc_verify_fail"})
                 raise LegacyFallbackRequired(f"Doğrulama başarısız: {notes}")
                 

            log_event(trace_id, "Doğrulama Başarılı", dump_model(v_out))
            
            # JURY ÇAĞRISI
            if qc["run_jury"]:
                log_event(trace_id, "Jüri (Jury) Başlatılıyor...")
                # Jury Stub Çağrısı 
                # (Mevcut stub.should_jury sadece boolean dönüyor. Eğer True dönerse bu bir 'istek'tir.)
                # Ancak burada güvenlik için varsayılan stub davranışını kontrol ediyoruz.
                jury_verdict = jury_stub.should_jury(None) 
                
                # NOT: Bu fazda should_jury=True olması, jürinin devreye girmesi gerektiğini söyler.
                # Ancak henüz gerçek bir insan jürisi olmadığı için, bu bir "risk" işaretidir.
                # Bu yüzden şimdilik should_jury=True -> Legacy Fallback (Güvenli Liman) olarak ele alıyoruz.
                # İleride Jury sonucu beklenecek.
                
                if jury_verdict: 
                   log_event(trace_id, "Jüri İncelemesi Gerekli - Legacy Fallback")
                   await telemetry.count("orch_fallback", labels={"reason": "qc_jury_req"})
                   raise LegacyFallbackRequired("Jüri incelemesi gerekli")
                   
                log_event(trace_id, "Jüri Onayı (Otomatik)", {"ran": True, "verdict": "passed"})

    except LegacyFallbackRequired:
        raise # Zaten istenen bu, ellemeyin yukarı çıksın
    except Exception as e:
        log_event(trace_id, "Kalite Kontrol Akış Hatası - Legacy Fallback", {"hata": str(e)})
        await telemetry.count("orch_fallback", labels={"reason": "qc_exception"})
        _AUTO_CIRCUIT.record_failure("qc_exception", time.time())
        raise LegacyFallbackRequired(f"Kalite kontrol hatası: {e}")

    # 7. LLM İstemci Adaptörü (FAZ 6.0 + 13.1 + 13.2 - Yönetilen Çağrı)
    try:
        log_event(trace_id, "Uyarlayıcı (Adapter) Hazırlanıyor")
        
        # A. Anahtarları Getir (Decider veya Env)
        available_keys = []
        
        # 1. Decider (Varsa)
        try:
            from app.chat.decider import get_available_keys
            keys_from_decider = get_available_keys()
            if keys_from_decider:
                available_keys.extend(keys_from_decider)
        except ImportError:
            pass

        # [FIX] Specialist Bypass: Eğer specialist zaten bir yanıt ürettiyse, Adapter'a gerek yok.
        # Bu değişken (final_solution_text) specialist bloğunda doluyordu.
        use_adapter = True
        if final_solution_text:
             log_event(trace_id, "Specialist Yanıtı Mevcut - Adapter Atlanıyor")
             sys.stdout.write(f"DEBUG: [Gate] use_adapter=False because final_solution_text len={len(final_solution_text)}\n")
             sys.stdout.flush()
             use_adapter = False
             # Adapter sonucunu boş bir başarı yapısı gibi kuralım ki aşağıda patlamasın
             final_adapter_res = {"used_model_hint": "specialist-v1", "raw": {}}
             
        # 2. Env ORCH_KEY_POOL (Eğer Decider boşsa veya ek kaynak olarak)
        # Karar: Tek kaynak ilkesi -> Decider varsa onu kullan, yoksa Env.
        if not available_keys:
            pool_str = os.environ.get("ORCH_KEY_POOL", "")
            if pool_str:
                env_keys = [k.strip() for k in pool_str.split(",") if k.strip()]
                available_keys.extend(env_keys)

        # 3. Fail-Safe (Boş liste kalsın, sahte key YOK)
        if not available_keys:
             available_keys = [] 

        # B. Failover Döngüsü (Yönetilen Çağrı)

        # B. Failover Döngüsü (Yönetilen Çağrı)
        # Policy'den max deneme sayısını öğrenmek için dummy call veya varsayılan 2
        # Döngü içinde her turda yeniden policy çağıracağız (çünkü state değişiyor)
        
        adapter = llm_client_adapter.LlmClientAdapter()
        # final_adapter_res yukarıda tanımlandı veya burada tanımlanmalı
        if use_adapter:
             final_adapter_res = {} # Reset only if using adapter
        
        last_exception = None
        max_loop_attempts = 2 # Toplam deneme hakkı (Key 1 -> Key 2)
        
        # Eğer adapter kullanmayacaksak range(0) yapalım ki döngüye girmesin
        loop_range = range(max_loop_attempts) if use_adapter else range(0)
        
        for attempt in loop_range:
            loop_start_ts = time.time()
            
            # 1. Policy Kararı (Hangi Key?)
            policy_res = runtime_policy.choose_key_and_limits(
                state=_RUNTIME_STATE,
                available_keys=available_keys,
                selected_model_id=selected_model_id or "genel",
                now_ts=loop_start_ts
            )
            
            selected_key = policy_res.get("selected_key_id")
            
            # Log Policy (sadece ilk deneme veya key değişince)
            log_event(trace_id, f"Kaynak Politikası Kararı (Deneme {attempt+1})", dump_model(policy_res))
            
            adapter_runtime = dump_model(policy_res)
            
            # Operasyonel Limit: Retry Clamp (FAZ 13.7)
            # Adapter retry 1'i geçemez
            raw_retries = adapter_runtime.get("max_retries", 1)
            clamped_retries = min(int(raw_retries), 1)
            
            # Clamp Telemetry Tekilleştirme
            did_count_clamp = locals().get("did_count_clamp", False)
            
            if clamped_retries != raw_retries:
                 adapter_runtime["max_retries"] = clamped_retries
                 if not did_count_clamp:
                     await telemetry.count("orch_fallback", labels={"reason": "attempts_clamped"})
                     did_count_clamp = True
                 log_event(trace_id, "Adapter Retry Sınırlandı (Clamp)", {"eski": raw_retries, "yeni": clamped_retries})

            adapter_context = {
                "intent": dump_model(intent_report) if intent_report else intent_res,
                "capabilities": dump_model(capability_report) if capability_report else {}
            }
            
            try:
                # FAZ 14.5: Prompt Builder ile Zenginleştir
                from app.orchestrator_v42 import llm_prompt_builder
                
                # Context bileşenlerini topla (Güvenli Erişim)
                mem_items = locals().get("memory_context_res", {}).get("items", []) if locals().get("memory_context_res") else []
                rag_ev = locals().get("safe_rag_context", [])
                tool_ev = locals().get("tool_evidence", {})

                adapter_prompt = llm_prompt_builder.build_adapter_prompt(
                    user_message=message, 
                    rag_evidence=rag_ev,
                    tool_evidence=tool_ev,
                    memory_items=mem_items
                )

                # 2. Adapter Çağrısı (Bütçe Korumalı)
                rem_budget = _budget_remaining(start_ts)
                if rem_budget < 0.05: # Çok az kaldıysa hiç girme
                    raise asyncio.TimeoutError("Bütçe tükendi (Adapter öncesi)")
                    
                adapter_res = await asyncio.wait_for(
                    adapter.generate(
                        message=adapter_prompt, # Zenginleştirilmiş Prompt
                        model_hint=selected_model_id,
                        runtime=adapter_runtime,
                        context=adapter_context,
                        flags=flags 
                    ),
                    timeout=rem_budget
                )
                
                final_adapter_res = adapter_res
                raw_res = adapter_res.get("raw", {})
                
                # 3. Sonuç Analizi ve State Güncelleme
                if selected_key and selected_key != "yok":
                    if raw_res.get("trigger_cooldown") or raw_res.get("error_type") == "rate_limit":
                        # 429 -> Cooldown
                        log_event(trace_id, "Rate Limit Algılandı - Key Cooldown", {"key": selected_key[:5]})
                        _RUNTIME_STATE.record_failure(selected_key, error_type="429")
                        
                        # Eğer ilk denemeyse ve başka key varsa devam et (Failover)
                        if attempt < max_loop_attempts - 1:
                            log_event(trace_id, "Failover: Başka anahtara geçiliyor...")
                            continue # Döngüye devam (yeni key)
                            
                    elif raw_res.get("error"):
                        # Diğer Hatalar -> Error count artır, döngüyü kır (Failover yapma)
                        log_event(trace_id, "API Hatası - Key Hata Sayacı Artıyor", {"key": selected_key[:5]})
                        _RUNTIME_STATE.record_failure(selected_key, error_type="generic")
                        break # Diğer hatalarda inat etme
                    else:
                        # Başarı -> RPM Artır ve Çık
                        _RUNTIME_STATE.record_success(selected_key)
                        break
                else:
                    break # Key yoksa döngü anlamsız
                    
            except asyncio.TimeoutError:
                log_event(trace_id, "Adapter Zaman Aşımı (Budget Exceeded)")
                await telemetry.count("orch_fallback", labels={"reason": "budget_exceeded"})
                _AUTO_CIRCUIT.record_failure("budget_exceeded", time.time())
                raise LegacyFallbackRequired("Orchestrator süre bütçesi aşıldı (Adapter)")
                
            except Exception as e:
                last_exception = e
                log_event(trace_id, "Adapter Çağrı Hatası", {"hata": str(e)})
                # Adapter exception telemetry
                # await telemetry.count("orch_adapter_error") # İleride detaylandırılabilir
                break # Adapter crash edince döngü kırılır

    except Exception as e:
        log_event(trace_id, "LLM Adaptör Akışı Hatası", {"hata": str(e)})
        await telemetry.count("orch_fallback", labels={"reason": "adapter_flow_exception"})
        _AUTO_CIRCUIT.record_failure("adapter_flow_exception", time.time())
        # Bu exception altaki rollout bloğuna düşer, orada da legacy raise edilir.
        
    # [FIX] Adapter Sonucu İşleme ve Final Text Atama
    # Eğer adapter kullanıldıysa ve boş döndüyse hata ver
    if use_adapter and not final_adapter_res:
         log_event(trace_id, "Adaptör Sonuç Dönemedi - Legacy Fallback")
         msg = str(last_exception) if last_exception else "Adaptör boş döndü"
         try: await telemetry.count("orch_fallback", labels={"reason": "adapter_empty"})
         except: pass
         raise LegacyFallbackRequired(msg)
         
    # Eğer Adapter çalıştıysa, onun metnini ana metin yap
    if use_adapter and final_adapter_res:
         adapter_text = final_adapter_res.get("text")
         if adapter_text:
              final_solution_text = adapter_text

    # Faz Gecişi İçin Gerekli Import
    from app.orchestrator_v42 import rollout

    # ... (Önceki kodlar: failover loop bitti, adapter_report oluştu)
    
    # 8. Nihai Karar ve Yanıt (FAZ 13.3 - Rollout)
    try:
        # req_user_id yukarıda "Hafıza" bölümünde hesaplandı.
        
        # Karar Ver
        use_orch = rollout.should_use_orchestrator(req_user_id, flags)
        
        # Bucket hesapla (Log için)
        bucket_val = rollout.compute_bucket(req_user_id) if req_user_id else -1
        
        log_event(trace_id, "Rollout Kararı", {
            "use_orchestrator": use_orch,
            "production_enabled": flags.production_enabled,
            "llm_dry_run": flags.llm_dry_run,
            "rollout_percent": flags.rollout_percent,
            "user_id": req_user_id,
            "bucket": bucket_val,
            "allowlisted": (req_user_id in flags.rollout_allowlist) if req_user_id else False
        })
        
        if not use_orch:
            # Rollout dışı -> Legacy
            await telemetry.count("orch_rollout_out")
            LiveTracer.warning("GATEWAY", "Rollout Out -> Fallback to Legacy")
            raise LegacyFallbackRequired("Rollout kapsamı dışı")
        
        # İçindeyiz
        await telemetry.count("orch_rollout_in")
        LiveTracer.routing_decision("ORCHESTRATOR", 1.0, "Allowed by Rollout")
            
        # Eğer buraya geldiysek Orchestrator yanıtı dönmeli
        # [FIX] Specialist yanıtı varsa onu kullan, yoksa adapter yanıtını kullan
        raw_text_for_pp = final_solution_text or final_adapter_res.get("text", "")

        # Eğer hala metin yoksa o zaman hata ver
        if not raw_text_for_pp:
             log_event(trace_id, "Orchestrator Yanıtı Boş (Specialist & Adapter) - Güvenlik Ağı")
             await telemetry.count("orch_fallback", labels={"reason": "adapter_empty"})
             _AUTO_CIRCUIT.record_failure("adapter_empty", time.time())
             raise LegacyFallbackRequired("Adaptör ve Specialist boş döndü")

        # Post-Process (FAZ 13.5)
        # Sanitizer + Streaming Rewrite (Eğer açık ise)
        from app.orchestrator_v42.response_postprocess import postprocess_response_text
        
        # Await ediyoruz çünkü içinde rewriter async çalışabilir

        # Bütçe Korumalı Post-Process
        rem_budget_pp = _budget_remaining(start_ts)
        use_fail_open_pp = False
        pp_res = {} # Default
        
        # [FAZ 16.2] Fail-Open: Bütçe yoksa post-process atla, ham metni dön
        if rem_budget_pp < 0.05:
             use_fail_open_pp = True
             log_event(trace_id, "Post-process bütçesi yetersiz - Atlanıyor (Fail-Open)")
             try: await telemetry.count("orch_pp_skipped_budget")
             except: pass
        else:
             try:
                 pp_res = await asyncio.wait_for(
                     postprocess_response_text(raw_text_for_pp, flags, trace_id),
                     timeout=rem_budget_pp
                 )
             except asyncio.TimeoutError:
                 # [FAZ 16.2] Timeout olursa da Fail-Open
                 use_fail_open_pp = True
                 log_event(trace_id, "Post-Process Zaman Aşımı - Ham Metin Kullanılıyor (Fail-Open)")
                 try: await telemetry.count("orch_pp_skipped_timeout")
                 except: pass
                 _AUTO_CIRCUIT.record_failure("pp_timeout_failopen", time.time())
        
        if use_fail_open_pp:
             final_text = raw_text_for_pp
             pp_res = {
                 "was_sanitized": False, 
                 "was_stream_rewritten": False, 
                 "notes": "Fail-open (Budget/Timeout)"
             }
        else:
             final_text = pp_res["text"]
        
        log_event(trace_id, "Yanıt Son-İşleme", {
            "was_sanitized": pp_res["was_sanitized"],
            "was_stream_rewritten": pp_res["was_stream_rewritten"],
            "notes": pp_res["notes"]
        })
        
        final_text = pp_res.get("text", final_text) # Ensure fallback
        
        if not final_text:
             log_event(trace_id, "Son-işleme sonrası yanıt boş - Legacy Fallback")
             await telemetry.count("orch_fallback", labels={"reason": "postprocess_empty"})
             _AUTO_CIRCUIT.record_failure("postprocess_empty", time.time())
             raise LegacyFallbackRequired("Son-işleme sonrası yanıt boş")

        # [FAZ 16.2] Kaynak Başlıkları Ekle (Deterministik)
        final_text = _append_source_titles(final_text, tool_evidence)

        # 9. Hafıza Yazma (Writeback) - FAZ 14.4
        # Sadece Orchestrator başarılıysa ve final_text varsa
        if use_orch and final_text:
            rem_budget_write = _budget_remaining(start_ts)
            conv_id = kwargs.get("conversation_id")
            
            # Yazma şartları: Enabled + UserID + ConvID
            should_attempt = flags.memory_write_enabled and req_user_id and conv_id
            
            if should_attempt:
                if rem_budget_write < 0.12:
                    log_event(trace_id, "Hafıza yazma atlandı (Bütçe yetersiz)")
                else:
                    try:
                        await telemetry.count("memory_write_attempt", labels={"type": "write"})
                        from app.orchestrator_v42 import memory_writeback
                        
                        write_res = await memory_writeback.write_memory_turn(
                            user_id=req_user_id,
                            user_message=message,
                            assistant_message=final_text,
                            flags=flags,
                            trace_id=trace_id,
                            conversation_id=conv_id
                        )
                        
                        if write_res["ok"]:
                            await telemetry.count("memory_write_ok", labels={"type": "write"})
                        elif write_res["ran"]:
                            # Hata analizi
                            reason = "timeout" if "zaman aşımı" in write_res.get("notes", "") else "exception"
                            await telemetry.count("memory_write_error", labels={"type": "write", "reason": reason})
                            
                    except Exception as e:
                        # Kritik değil, logla geç
                        log_event(trace_id, "Hafıza Yazma Modülü Hatası", {"hata": str(e)})
            
            elif flags.memory_write_enabled and not conv_id:
                 log_event(trace_id, "Hafıza yazma atlandı (Conversation ID yok)")

        # Başarı Sayacı (Sadece return garantiyse)
        await telemetry.count("orch_returned")

        # GatewayResult Dönüşü
        return GatewayResult(
            trace_id=trace_id,
            response_text=final_text,
            model_name=final_adapter_res.get("used_model_hint", "bilinmiyor"),
            usage_stats={} # İleride dolarız
        )


    except LegacyFallbackRequired:
        raise # Zaten istenen bu
    except Exception as e:
        log_event(trace_id, "Nihai Karar Hatası", {"hata": str(e)})
        await telemetry.count("orch_fallback", labels={"reason": "decision_exception"})
        _AUTO_CIRCUIT.record_failure("decision_exception", time.time())
        raise LegacyFallbackRequired(f"Karar hatası: {e}")



    # 8. Son Karar ve Dönüş (Legacy)
    decision = RoutingDecision(
        mode="legacy_passthrough", 
        reason="Taslak Mod (Faz 9.0): Model seçimi aktif, sistem stabil, eski sisteme devrediliyor"
    )
    
    result = GatewayResult(
        decision=decision,
        trace_id=trace_id,
        payload=None
    )
    
    log_event(trace_id, "Gateway Sonucu Kesinleşti", dump_model(result))
    
    if decision.mode == "legacy_passthrough":
        log_event(trace_id, "İstisna ile Eski Sisteme Yönlendiriliyor")
        raise LegacyFallbackRequired("Orchestrator eski hattı kullanmaya karar verdi")
        
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _safe_load_history(user_id: Any, conv_id: Any) -> list[dict[str, Any]]:
    """
    Sohbet geçmişini güvenli bir şekilde yükler.
    Exception fırlatmaz (Fail-Safe).
    """
    import sys
    try:
        sys.stdout.write(f"DEBUG: [_safe_load_history] Start. User={user_id} Conv={conv_id}\\n")
        sys.stdout.flush()
        
        if not user_id or not conv_id:
            sys.stdout.write("DEBUG: [_safe_load_history] Missing ID\\n")
            sys.stdout.flush()
            return []
            
        from app.memory.conversation import load_messages
        
        # ID'leri string'e çevirmeyi dene (bazen UUID gelebilir)
        u_id_str = str(user_id) if user_id else None
        c_id_str = str(conv_id) if conv_id else None
        
        raw_msgs = load_messages(u_id_str, c_id_str)
        sys.stdout.write(f"DEBUG: [_safe_load_history] Raw Msgs Count: {len(raw_msgs) if raw_msgs else 0}\\n")
        sys.stdout.flush()
        
        if not raw_msgs:
            return []
            
        # Son 10 mesaj
        recent = raw_msgs[-10:]
        
        items = []
        for m in recent:
            # Message objesinden content alma
            content = getattr(m, "content", None) or getattr(m, "text", "")
            role = getattr(m, "role", "user")
            items.append({"role": role, "content": content})
            
        sys.stdout.write(f"DEBUG: [_safe_load_history] Processed {len(items)} items\\n")
        sys.stdout.flush()
        return items
        
    except Exception as e:
        sys.stdout.write(f"DEBUG: [_safe_load_history] ERROR: {e}\\n")
        if "traceback" in sys.modules:
            import traceback
            traceback.print_exc()
        sys.stdout.flush()
        return []


def _append_source_titles(text: str, evidence: dict) -> str:
    """FAZ 16.2: Kaynak başlıklarını metne ekler."""
    if not evidence or not evidence.get("items"):
        return text
    
    titles = []
    seen = set()
    
    for item in evidence.get("items", []):
        # Web Search sonucu: "results" key'i içerir (evidence_builder.py'a göre)
        if isinstance(item, dict) and "results" in item:
            for res in item["results"]:
                title = res.get("title")
                if title and title not in seen:
                    # Clamp: max 120 chars
                    clamped = title[:117] + "..." if len(title) > 120 else title
                    titles.append(clamped)
                    seen.add(title)
                    if len(titles) >= 2: break # Max 2 kaynak
        if len(titles) >= 2: break
            
    if titles:
        # Metin zaten varsa altına ekle
        parts = ["\n\nKaynak başlıkları:"]
        for t in titles:
            parts.append(f"- {t}")
        text += "\n".join(parts)
            
    return text
