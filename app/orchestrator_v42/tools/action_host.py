import asyncio
from typing import List, Dict, Any
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.tools.types import ToolPlan, ToolResult

ALLOWED_TOOLS = {"web_search"}

async def execute_plan(
    plan: ToolPlan, 
    flags: OrchestratorFeatureFlags, 
    trace_id: str,
    telemetry: Any,
    timeout_s: float | None = None
) -> List[ToolResult]:
    """
    Planlanan araç çağrılarını yürütür.
    
    Args:
        plan: Yürütülecek plan
        flags: Feature flags
        trace_id: Trace ID
        telemetry: Telemetri servisi
        timeout_s: Toplam zaman aşımı (saniye) - Opsiyonel, default 0.8
        
    Returns:
        List[ToolResult]: Sonuç listesi
    """
    results = []
    
    if not plan.calls:
        return results
        
    # Varsayılan timeout
    effective_timeout = timeout_s if timeout_s is not None else 0.8

    # GUARDRAIL: Max Calls enforcement (Host level defense)
    raw_max = getattr(flags, "tools_max_calls", 1)
    max_calls = max(0, min(int(raw_max), 3))
    
    calls_to_run = plan.calls
    if len(calls_to_run) > max_calls:
        # Fazlalıkları at ve telemetriye işle
        skipped_count = len(calls_to_run) - max_calls
        calls_to_run = calls_to_run[:max_calls]
        
        for _ in range(skipped_count):
             await telemetry.count("tool_skipped_clamped", labels={"reason": "max_calls"})
             
    for call in calls_to_run:
        # Telemetri: Call Attempt
        await telemetry.count("tool_attempt", labels={"type": call.name})
        
        # Güvenlik Kontrolü (Tekrar)
        if call.name not in ALLOWED_TOOLS:
            results.append(ToolResult(
                id=call.id,
                name=call.name,
                ok=False,
                output="İzin verilmeyen araç.",
                error="İzin verilmeyen araç"
            ))
            await telemetry.count("tool_error", labels={"type": "unauthorized"})
            continue
            
        try:
            # DRY RUN veya SAFE MODE
            if flags.tools_dry_run:
                # Simülasyon
                simulated_output = {
                    "source": "simulated",
                    "results": [
                        {"title": f"Simüle Sonuç {call.name}", "snippet": "Bu bir dry-run çıktısıdır."}
                    ]
                }
                results.append(ToolResult(
                    id=call.id,
                    name=call.name,
                    ok=True,
                    output=simulated_output
                ))
                # "mode" yerine "reason" kullanıyoruz (Whitelist uyumlu)
                await telemetry.count("tool_executed", labels={"type": call.name, "reason": "dry_run"})
                
            else:
                # GERÇEK ÇAĞRI (FAZ 14.2)
                # Şimdilik sadece web_search var
                if call.name == "web_search":
                    # Adapter import (Lazy)
                    from app.orchestrator_v42.tools import web_search_adapter
                    
                    # parametrelerden query'i al
                    query_val = call.arguments.get("query", "")
                    
                    # Adapter çağır (Timeout clamp: min 0.1)
                    safe_timeout = max(0.1, effective_timeout)
                    search_res = await web_search_adapter.web_search(query_val, safe_timeout)
                    
                    # Sonuç analizi
                    is_ok = True
                    err_msg = None
                    
                    if not search_res["results"] and "hatası" in search_res.get("notes", "").lower():
                        is_ok = False
                        err_msg = search_res["notes"]
                        
                    results.append(ToolResult(
                        id=call.id,
                        name=call.name,
                        ok=is_ok,
                        output=search_res,
                        error=err_msg
                    ))
                    
                    if is_ok:
                        await telemetry.count("tool_executed", labels={"type": call.name, "reason": "real"})
                    else:
                        await telemetry.count("tool_error", labels={"type": call.name})
                else:
                    # Bilinmeyen araç (Yukarıdaki kontrolden kaçarsa)
                    results.append(ToolResult(
                        id=call.id,
                        name=call.name,
                        ok=False,
                        output="Implementasyon eksik.",
                        error="Uygulanmadı"
                    ))
                    await telemetry.count("tool_error", labels={"type": "not_implemented"})

        except Exception as e:
            results.append(ToolResult(
                id=call.id,
                name=call.name,
                ok=False,
                output="Araç yürütme hatası.",
                error=str(e)
            ))
            await telemetry.count("tool_error", labels={"type": "runtime_exception"})

    return results
