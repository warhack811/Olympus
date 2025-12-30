# app/orchestrator_v42/plugins/model_selector.py

import logging
from typing import List, Dict, Any

logger = logging.getLogger("orchestrator.selector")

def select(required_capabilities: List[str], catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gerekli yeteneklere göre katalogdan en uygun modeli seçer.
    Puanlama (Scoring) tabanlı, deterministik bir algoritma kullanır.
    
    Çıktı Şeması:
    {
        "selected_model_id": str,
        "score": int,
        "candidates_considered": int,
        "reason": str,
        "missing_capabilities": List[str],
        "matched_capabilities": List[str],
        "matched_rules": List[str]
    }
    """
    
    # [FAZ 16.7] Blueprint Model Catalog
    MODEL_CATALOG = [
        {
            "model_id": "fast",
            "capabilities": ["tr_natural", "short_chat", "extraction"],
            "tier": "hizli",
            "latency_class": "fast", 
            "cost_class": "low",
            "role_flags": {"can_rewrite": False, "can_judge": False}
        },
        {
            "model_id": "general",
            "capabilities": ["tr_natural", "tool_use", "search", "reasoning", "tool_planning"],
            "tier": "dengeli",
            "latency_class": "med",
            "cost_class": "med",
            "role_flags": {"can_rewrite": True, "can_judge": False}
        },
        {
            "model_id": "heavy",
            "capabilities": ["tr_natural", "coding", "analysis", "high_risk", "creative", "math"],
            "tier": "uzman",
            "latency_class": "slow",
            "cost_class": "high",
            "role_flags": {"can_rewrite": True, "can_judge": True}
        }
    ]
    
    # Katalog override edilmemişse Blueprint kataloğu kullan
    if not catalog:
        catalog = MODEL_CATALOG
        
    # Fail-safe ve Varsayılanlar
    default_model = "general" # Fallback daha güçlü olmalı
    
    if not catalog or not isinstance(catalog, list):
        return {
            "selected_model_id": default_model,
            "score": 0,
            "candidates_considered": 0,
            "reason": "Katalog boş, varsayılan seçildi.",
            "missing_capabilities": [],
            "matched_capabilities": [],
            "matched_rules": ["failsafe_empty_catalog"],
            "role_flags": {"can_rewrite": True, "can_judge": False}
        }
        
    candidates = []
    required_caps_set = set(required_capabilities) if required_capabilities else set()
    
    # --- PUANLAMA PARAMETRELERİ ---
    TIER_BONUS = {
        "hizli": 1,
        "dengeli": 2,
        "uzman": 3
    }
    
    LATENCY_PENALTY = {
        "fast": 0,
        "med": -1,
        "slow": -2
    }
    
    COST_PENALTY = {
        "low": 0,
        "med": -1,
        "high": -2
    }
    
    for model in catalog:
        model_id = model.get("model_id", "bilinmeyen")
        if not model_id: continue
        
        score = 0
        matched_rules = []
        
        model_caps = set(model.get("capabilities", []))
        matched_caps = required_caps_set.intersection(model_caps)
        missing_caps = required_caps_set.difference(model_caps)
        
        # 1. Yetenek Puanı (Ağırlıklı)
        score += len(matched_caps) * 10 # Eşleşme çok önemli
        score -= len(missing_caps) * 5  # Eksiklik ceza puanı
        
        # 2. Tier Bonusu
        tier = model.get("tier", "bilinmiyor")
        bonus = TIER_BONUS.get(tier, 0)
        score += bonus
        if bonus > 0: matched_rules.append(f"tier_bonus_{tier}")
        
        # 3. Latency Cezası
        latency = model.get("latency_tier") or model.get("latency_class", "slow")
        lat_pen = LATENCY_PENALTY.get(latency, -2)
        score += lat_pen
        if lat_pen < 0: matched_rules.append(f"latency_penalty_{latency}")

        # 4. Cost Cezası
        cost = model.get("cost_tier") or model.get("cost_class", "high")
        cost_pen = COST_PENALTY.get(cost, -2)
        score += cost_pen
        if cost_pen < 0: matched_rules.append(f"cost_penalty_{cost}")
        
        candidates.append({
            "model_id": model_id,
            "score": score,
            "missing_caps": sorted(list(missing_caps)),
            "matched_caps": sorted(list(matched_caps)),
            "matched_rules": matched_rules,
            "latency_val": lat_pen,
            "missing_count": len(missing_caps),
            "role_flags": model.get("role_flags", {})
        })
        
    if not candidates:
        return {
            "selected_model_id": default_model,
            "score": 0,
            "candidates_considered": 0,
            "reason": "Uygun aday bulunamadı, varsayılan seçildi.",
            "missing_capabilities": [],
            "matched_capabilities": [],
            "matched_rules": ["failsafe_no_candidates"],
            "role_flags": {"can_rewrite": True, "can_judge": False}
        }
        
    # --- SIRALAMA (TIE-BREAK) ---
    # 1) Score (Yüksek)
    # 2) Eksik Yetenek Sayısı (Düşük)
    # 3) Latency (Hızlı)
    # 4) Alfabetik
    
    candidates.sort(key=lambda x: (
        -x["score"], 
        x["missing_count"], 
        -x["latency_val"], 
        x["model_id"]
    ))
    
    winner = candidates[0]
    
    return {
        "selected_model_id": winner["model_id"],
        "score": winner["score"],
        "candidates_considered": len(candidates),
        "reason": f"Puan: {winner['score']}, Caps: {len(winner['matched_caps'])}/{len(required_caps_set)}",
        "missing_capabilities": winner["missing_caps"],
        "matched_capabilities": winner["matched_caps"],
        "matched_rules": winner["matched_rules"],
        "role_flags": winner["role_flags"]
    }
