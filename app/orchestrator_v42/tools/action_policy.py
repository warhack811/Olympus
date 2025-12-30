from typing import Dict, Any
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags
from app.orchestrator_v42.types import SafetyReport, IntentReport

def decide_tools_run(
    flags: OrchestratorFeatureFlags,
    safety_report: SafetyReport | None,
    intent_report: IntentReport | None
) -> Dict[str, Any]:
    """
    Araçların çalıştırılıp çalıştırılmayacağına karar verir.
    
    Returns:
        {
            "run_tools": bool,
            "reason": str,
            "risk_level": str
        }
    """
    
    # Varsayılanlar
    risk_level = "unknown"
    if safety_report:
        risk_level = safety_report.risk
        
    # 1. Flag Kontrolü
    if not flags.tools_enabled:
        return {
            "run_tools": False,
            "reason": "Araçlar kapalı (Flag)",
            "risk_level": risk_level
        }
        
    # 2. Risk Kontrolü
    # Medium ve High riskli sorgularda araç çalıştırma (Injection riski vb.)
    if risk_level in ["medium", "high"]:
        return {
            "run_tools": False,
            "reason": "Risk nedeniyle araçlar kapalı",
            "risk_level": risk_level
        }

    # 3. Onay
    return {
        "run_tools": True,
        "reason": "Araçlar çalıştırılabilir",
        "risk_level": risk_level
    }
