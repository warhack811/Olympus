# app/orchestrator_v42/quality_control.py
from typing import Dict, Any
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags

def decide_quality_control(
    flags: OrchestratorFeatureFlags,
    safety_report: Any | None,
    intent_report: Any | None = None
) -> Dict[str, Any]:
    """
    Orchestrator kalite kontrol adımları (Verify & Jury) için karar mekanizması.
    
    Karar Faktörleri:
    1. Feature Flags (verify_enabled, jury_enabled, streaming_enabled)
    2. Güvenlik Riski (safety_report.risk)
    
    Dönüş (Dict):
        run_verify: bool
        run_jury: bool
        risk_level: str
        reason: str
        jury_forced_off_by_streaming: bool
    """
    
    # 1. Varsayılanlar
    decision = {
        "run_verify": False,
        "run_jury": False,
        "risk_level": "unknown",
        "reason": "Varsayılan kapalı",
        "jury_forced_off_by_streaming": False
    }
    
    # 2. Risk Analizi
    risk = "unknown"
    if safety_report and hasattr(safety_report, "risk"):
        risk = str(safety_report.risk).lower().strip()
    elif isinstance(safety_report, dict):
        risk = str(safety_report.get("risk", "unknown")).lower().strip()
        
    decision["risk_level"] = risk

    # 3. Gating Mantığı
    
    # Kural 4a: Safety report yoksa veya risk bilinmiyorsa -> Güvenli mod (Her şey kapalı)
    if not safety_report or risk == "unknown":
        decision["reason"] = "Risk analiz edilemedi veya rapor yok"
        return decision
        
    # Kural 4b: Risk düşükse -> Her şey kapalı (Gerek yok)
    if risk == "low":
        decision["reason"] = "Risk düşük, ek kontrol gerekmiyor"
        return decision
        
    # Kural 4c: Risk Orta/Yüksek ise -> Kontrollü Açılış
    if risk in ["medium", "high", "critical"]:
        reason_parts = [f"Risk seviyesi: {risk}"]
        
        # Verify Kontrolü
        if flags.verify_enabled:
            decision["run_verify"] = True
            reason_parts.append("Doğrulama aktif")
        else:
            reason_parts.append("Doğrulama flag kapalı")
            
        # Jury Kontrolü
        if flags.jury_enabled:
            if flags.streaming_enabled:
                # Kural 3: Streaming açıksa Jury her zaman kapalı
                decision["run_jury"] = False
                decision["jury_forced_off_by_streaming"] = True
                reason_parts.append("Jüri streaming nedeniyle iptal")
            else:
                decision["run_jury"] = True
                reason_parts.append("Jüri aktif")
        else:
            reason_parts.append("Jüri flag kapalı")
            
        decision["reason"] = ", ".join(reason_parts)
        return decision

    # Kural Dışı Durum
    decision["reason"] = f"Tanımlanmamış risk seviyesi: {risk}"
    return decision
