# app/orchestrator_v42/plugins/model_catalog.py

from typing import List, Dict, Any

def get_catalog() -> List[Dict[str, Any]]:
    """
    Kullanılabilir modellerin kataloğu.
    Blueprint v1.0 (Consensus v5.2) standartlarına göre optimize edilmiştir.
    """
    return [
        {
            "model_id": "genel_hizli_v1",
            "tier": "hizli",
            "capabilities": ["sohbet", "akil_yurutme", "ozetleme", "tr_natural", "tool_planning"],
            "strengths": {"coding": 1, "analysis": 1, "creative": 2, "tr_natural": 2, "tool_planning": 1},
            "quality_tier": "med",
            "latency_tier": "fast",
            "cost_tier": "low",
            "can_judge": False,
            "can_rewrite": False,
            "notes": "Llama 3.1 8B Instant - Günlük hızlı görevler."
        },
        {
            "model_id": "genel_dengeli_v1",
            "tier": "dengeli",
            "capabilities": ["sohbet", "akil_yurutme", "planlama", "ozetleme", "tr_natural", "analysis", "coding"],
            "strengths": {"coding": 2, "analysis": 3, "creative": 2, "tr_natural": 3, "tool_planning": 3},
            "quality_tier": "high",
            "latency_tier": "med",
            "cost_tier": "med",
            "can_judge": True,
            "can_rewrite": True,
            "notes": "Qwen 3 32B - Zeki ve doğal Türkçe desteği."
        },
        {
            "model_id": "kod_uzman_v1",
            "tier": "uzman",
            "capabilities": ["sohbet", "akil_yurutme", "kod_yazma", "hata_ayiklama", "analysis", "high_precision"],
            "strengths": {"coding": 3, "analysis": 3, "creative": 2, "tr_natural": 2, "tool_planning": 3},
            "quality_tier": "high",
            "latency_tier": "slow",
            "cost_tier": "high",
            "can_judge": True,
            "can_rewrite": False,
            "notes": "GPT-OSS 120B - Teknik ve kodlama uzmanı."
        },
        {
            "model_id": "sosyal_uzman_v1",
            "tier": "yaratici",
            "capabilities": ["sohbet", "creative", "tr_natural", "social_chat", "social_intelligence"],
            "strengths": {"coding": 2, "analysis": 2, "creative": 3, "tr_natural": 3, "tool_planning": 2, "social_chat": 3},
            "quality_tier": "high",
            "latency_tier": "med",
            "cost_tier": "med",
            "can_judge": False,
            "can_rewrite": True,
            "notes": "Kimi-k2 - Doğal samimiyet ve uzun bağlam."
        },
        {
            "model_id": "derin_akil_v1",
            "tier": "derin",
            "capabilities": ["sohbet", "derin_akil_yurutme", "analiz", "matematik", "analysis"],
            "strengths": {"coding": 2, "analysis": 3, "creative": 2, "tr_natural": 2, "tool_planning": 2},
            "quality_tier": "high",
            "latency_tier": "slow",
            "cost_tier": "high",
            "can_judge": True,
            "can_rewrite": False,
            "notes": "Llama 70B (v3.3) - Karmaşık mantık yürütme."
        }
    ]
