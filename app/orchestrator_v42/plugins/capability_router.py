# app/orchestrator_v42/plugins/capability_router.py

import logging
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.capability")

async def derive(intent: Dict[str, Any] | object, safety: Dict[str, Any] | object) -> Dict[str, Any]:
    """
    Yetenek Yönlendirici (Capability Router) - Kural Tabanlı Motor.
    
    Niyet (Intent) ve Güvenlik (Safety) raporlarına dayanarak gerekli yetenekleri belirler.
    Deterministik ve güvenli (fail-safe) çalışır.
    
    Çıktı Şeması:
    {
        "required_capabilities": List[str],
        "domain": str,
        "complexity": str,
        "rag_decision": str,
        "notes": str,
        "matched_rules": List[str]
    }
    """
    # Fail-safe varsayılanları
    default_caps = {"sohbet", "akil_yurutme"}
    
    try:
        # --- VERİ HAZIRLIĞI ---
        # intent ve safety dict veya object olabilir, normalize edelim.
        
        intent_data = {}
        if isinstance(intent, dict):
            intent_data = intent
        elif hasattr(intent, "dict"):
            intent_data = intent.dict()
        elif hasattr(intent, "model_dump"):
            intent_data = intent.model_dump()
        elif hasattr(intent, "__dict__"):
            intent_data = intent.__dict__

        safety_data = {}
        if isinstance(safety, dict):
            safety_data = safety
        elif hasattr(safety, "dict"):
            safety_data = safety.dict()
        elif hasattr(safety, "model_dump"):
            safety_data = safety.model_dump()
        elif hasattr(safety, "__dict__"):
            safety_data = safety.__dict__
            
        # Değişkenleri al
        domain = intent_data.get("domain", "general")
        complexity = intent_data.get("complexity", "low")
        rag_decision = intent_data.get("rag_decision", "off")
        tasks = intent_data.get("tasks", [])
        
        input_safe = safety_data.get("input_safe", True)
        
        required_caps = set(default_caps)
        matched_rules = []
        notes = []

        # --- KURAL SETLERİ ---

        # 1. Domain Bazlı Yetenekler
        if domain == "coding":
            required_caps.update(["coding", "analysis", "high_precision"])
            matched_rules.append("domain_coding")
        elif domain == "search":
            required_caps.update(["analysis", "tool_planning", "tr_natural"])
            matched_rules.append("domain_search")
        elif domain == "social":
            required_caps.update(["social_chat", "tr_natural", "creative"])
            matched_rules.append("domain_social")
        elif domain == "math" or domain == "logic":
            required_caps.update(["analysis", "akil_yurutme", "high_precision"])
            matched_rules.append("domain_logic")
        elif domain == "productivity":
            required_caps.update(["planlama", "tool_planning"])
            matched_rules.append("domain_productivity")
            
        # 2. Görev (Task) Bazlı Yetenekler
        if isinstance(tasks, list):
            for t in tasks:
                if not isinstance(t, dict): 
                    if hasattr(t, "dict"): t = t.dict()
                    elif hasattr(t, "model_dump"): t = t.model_dump()
                    else: continue
                
                t_type = t.get("type")
                if t_type == "web_search":
                    required_caps.update(["analysis", "tool_planning"])
                    matched_rules.append("task_web_search")
                elif t_type == "code":
                    required_caps.update(["coding", "analysis"])
                    matched_rules.append("task_code")
                elif t_type == "image_generate":
                    required_caps.add("creative")
                    matched_rules.append("task_image")
                elif t_type == "social":
                    required_caps.update(["social_chat", "tr_natural"])
                    matched_rules.append("task_social")

        # 3. RAG Kararı
        if rag_decision == "on":
            required_caps.add("analysis") # RAG genelde analiz gerektirir
            matched_rules.append("rag_on")

        # 4. Karmaşıklık (Complexity) & Dil
        if complexity == "high":
            required_caps.add("analysis")
            matched_rules.append("complexity_high")
        
        # Türkçe her zaman öncelik
        required_caps.add("tr_natural")

        # --- ÇIKTI FORMATLAMA ---
        # Dedup ve Sıralama
        sorted_caps = sorted(list(required_caps))
        matched_rules = sorted(list(set(matched_rules)))
        
        final_notes = " | ".join(notes) if notes else "Blueprint v1.0 yetenek analizi tamamlandı."

        return {
            "required_capabilities": sorted_caps,
            "domain": domain,
            "complexity": complexity,
            "rag_decision": rag_decision,
            "notes": final_notes,
            "matched_rules": matched_rules
        }

    except Exception as e:
        logger.error(f"Yetenek türetme hatası: {e}")
        # Fail-safe dönüş
        return {
            "required_capabilities": sorted(list(default_caps)),
            "domain": "general",
            "complexity": "low",
            "rag_decision": "off",
            "notes": f"failsafe: {str(e)}",
            "matched_rules": ["hata_failsafe"]
        }
