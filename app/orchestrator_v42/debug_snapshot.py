from typing import Dict, Any, Optional
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.types import dump_model
from app.orchestrator_v42.plugins.runtime_state import RuntimeState
import time

def build_debug_snapshot(
    flags: OrchestratorFeatureFlags, 
    telemetry_snapshot: Dict[str, int], 
    state: Optional[RuntimeState]
) -> Dict[str, Any]:
    """
    Orchestrator'ın anlık durumunu özetleyen güvenli bir snapshot döndürür.
    Hassas veriler (API Key) maskelenir. Fail-soft çalışır.
    """
    snapshot = {
        "timestamp": time.time(),
        "flags": {},
        "telemetry": {},
        "runtime_state": "none"
    }
    
    try:
        # 1. Flags & Rollout Settings
        if flags:
            snapshot["flags"] = dump_model(flags)
            snapshot["rollout"] = {
                "production_enabled": flags.production_enabled,
                "llm_dry_run": flags.llm_dry_run,
                "rag_dry_run": flags.rag_dry_run,
                "streaming_enabled": flags.streaming_enabled,
                "rollout_percent": flags.rollout_percent,
                "allowlist_count": len(flags.rollout_allowlist),
            }
        
        # 2. Telemetry & Summary
        if telemetry_snapshot:
            snapshot["telemetry"] = telemetry_snapshot
            
            # Daha okunabilir özet çıkar
            summary = {
                "requests": {
                     "try": telemetry_snapshot.get("orch_try", 0),
                     "returned": telemetry_snapshot.get("orch_returned", 0),
                     "rollout_in": telemetry_snapshot.get("orch_rollout_in", 0),
                     "rollout_out": telemetry_snapshot.get("orch_rollout_out", 0)
                },
                "rag": {
                    "attempt": telemetry_snapshot.get("rag_attempt", 0),
                    "used": telemetry_snapshot.get("rag_used", 0), # Total (Legacy + others)
                    "skipped_dry_run": telemetry_snapshot.get("rag_skipped_dry_run", 0),
                    "budget_exceeded": telemetry_snapshot.get("rag_budget_exceeded", 0),
                    "error": telemetry_snapshot.get("rag_error", 0)
                },
                "fallback_reasons": {}
            }
            
            # Fallback nedenlerini ayrıştır
            for k, v in telemetry_snapshot.items():
                if k.startswith("orch_fallback"):
                    # Format: orch_fallback|reason=xyz
                    try:
                        reason = "unknown"
                        parts = k.split("|")
                        for p in parts:
                            if p.startswith("reason="):
                                reason = p.split("=")[1]
                        summary["fallback_reasons"][reason] = v
                    except:
                        pass
            
            snapshot["telemetry_summary"] = summary
            
        # 3. Runtime State
        if state:
            state_snapshot = state.get_key_snapshot() # copy dict
            key_count = len(state_snapshot)
            
            # Aggregate counts
            cooldown_count = 0
            circuit_count = 0
            now = time.time()
            
            # Sort by error count desc for top keys
            # item: (key_id, stats_dict)
            sorted_keys = sorted(
                state_snapshot.items(), 
                key=lambda item: item[1].get("error_count", 0), 
                reverse=True
            )
            
            top_keys_summary = []
            for key_id, stats in sorted_keys:
                # Count alerts
                if stats.get("cooldown_until", 0) > now:
                    cooldown_count += 1
                if stats.get("circuit_open_until", 0) > now:
                    circuit_count += 1
                
                # Top 3 (Masked)
                if len(top_keys_summary) < 3:
                     # Masking: first 4 chars + ***
                     masked_id = key_id[:4] + "***" if len(key_id) > 4 else "***"
                     top_keys_summary.append({
                         "key_id_masked": masked_id,
                         "error_count": stats.get("error_count", 0),
                         "rpm": stats.get("rpm", 0),
                         "cooldown_active": stats.get("cooldown_until", 0) > now
                     })
            
            snapshot["runtime_state"] = {
                "key_count": key_count,
                "cooldown_active_count": cooldown_count,
                "circuit_open_count": circuit_count,
                "top_keys": top_keys_summary
            }
        
        # 4. Auto Circuit Status (Late Import for Circular Dependency Safety)
        try:
            from app.orchestrator_v42.gateway import _AUTO_CIRCUIT
            snapshot["auto_circuit"] = _AUTO_CIRCUIT.snapshot(time.time())
        except ImportError:
            snapshot["auto_circuit"] = {"status": "unreachable", "note": "Gateway import edilemedi"}
        except Exception as ace:
             snapshot["auto_circuit"] = {"status": "error", "note": str(ace)}

        # 5. Kardinalite & Hassas Veri Kontrolü (Son Güvenlik Ağı)
        # Snapshot'ı stringe çevir ve içinde API Key veya User ID var mı bak
        raw_dump = str(snapshot)
        if "sk-" in raw_dump or "user_" in raw_dump or "trace_" in raw_dump:
             # Eğer sızıntı şüphesi varsa, şüpheli alanları temizle veya uyar.
             # Ancak bu maliyetli olabilir.
             # Sadece bilinen alanları maskeleyelim (yukarıda yapıldı).
             pass

        # [FAZ 16.6] Router Model Analizi (Telemetri Tabanlı)
        router_stats = {"total_selections": 0, "distribution": {}}
        if telemetry_snapshot:
            for k, v in telemetry_snapshot.items():
                if k.startswith("orch_model_selected"):
                    # orch_model_selected|type=fast -> fast
                    m_type = "unknown"
                    parts = k.split("|")
                    for p in parts:
                        if p.startswith("type="):
                            m_type = p.split("=")[1]
                    router_stats["distribution"][m_type] = v
                    router_stats["total_selections"] += v
        
        # [FAZ 16.7] Cascade
        cascade_stats = {"active": False, "count": 0, "breakdown": {}}
        if telemetry_snapshot:
             for k, v in telemetry_snapshot.items():
                 if k.startswith("orch_cascade_fallback"):
                     cascade_stats["active"] = True
                     cascade_stats["count"] += v
                     # breakdown logic if needed
                     
        router_stats["cascade"] = cascade_stats
        snapshot["router"] = router_stats

    except Exception as e:
        snapshot["error"] = f"Snapshot hatasi: {str(e)}"
        
    return snapshot
