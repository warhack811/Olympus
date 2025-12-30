# app/orchestrator_v42/plugins/jury_stub.py

from typing import Dict, Any, Optional

def should_jury(user_feedback: Dict[str, Any] | None) -> bool:
    """
    Jüri seçimi gerekli mi?
    Bu fazda kullanıcı geri bildirimi henüz olmadığı için varsayılan False.
    """
    if user_feedback:
        return True
    return False

def jury_pick(candidate_a: str, candidate_b: str) -> Dict[str, Any]:
    """
    İki aday arasından seçim yapar.
    Deterministik Kural: Daha kısa olanı seç, eşitse alfabetik.
    """
    len_a = len(candidate_a)
    len_b = len(candidate_b)
    
    chosen = "a"
    reason = "Daha kısa"
    
    if len_b < len_a:
        chosen = "b"
    elif len_b == len_a:
        if candidate_b < candidate_a:
            chosen = "b"
            reason = "Eşit uzunluk, alfabetik öncelik"
        else:
            chosen = "a"
            reason = "Eşit uzunluk, alfabetik öncelik"
            
    return {
        "chosen": chosen,
        "reason": reason
    }
