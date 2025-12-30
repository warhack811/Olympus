# app/orchestrator_v42/plugins/contract_guard.py

import hashlib
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.contract")

def _compute_integrity_hash(data: Dict[str, Any]) -> str:
    """
    Contract (Sözleşme) bütünlüğü için hash hesaplar.
    Code blocks, claims ve evidence alanlarını içerir.
    Deterministic olması için JSON sort_keys=True kullanılır.
    """
    # Sadece immutable alanları al
    subset = {
        "code_blocks": data.get("code_blocks", []),
        "claims": data.get("claims", []),
        "evidence": data.get("evidence", [])
    }
    dumped = json.dumps(subset, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

def enforce_contract(original: Dict[str, Any], rewritten_solution_text: str) -> Dict[str, Any]:
    """
    Sözleşme Muhafızı - Enforce.
    Orijinal verinin yapısal bütünlüğünü (code, claims) korur,
    metin kısmını (solution_text) stilistten gelen ile günceller.
    Immutable alanlar için hash hesaplar.
    """
    try:
        # Yeni çıktı oluştur
        contracted = {
            "solution_text": rewritten_solution_text,
            "code_blocks": original.get("code_blocks", []),
            "claims": original.get("claims", []),
            "evidence": original.get("evidence", [])
        }
        
        # Hash hesapla ve ekle
        integrity_hash = _compute_integrity_hash(contracted)
        contracted["immutable_hash"] = integrity_hash
        
        return contracted
    
    except Exception as e:
        logger.error(f"Contract enforce hatası: {e}")
        # Fail-safe: Orijinali döndürmeye çalış, hash boş olsun
        return original.copy()

def verify_integrity(contracted_output: Dict[str, Any]) -> bool:
    """
    Sözleşme Bütünlük Doğrulama.
    Verilen çıktının 'immutable_hash' değeri, içeriğiyle eşleşiyor mu kontrol eder.
    """
    try:
        stored_hash = contracted_output.get("immutable_hash")
        if not stored_hash:
            return False
            
        computed_hash = _compute_integrity_hash(contracted_output)
        return computed_hash == stored_hash
        
    except Exception as e:
        logger.error(f"Contract verify hatası: {e}")
        return False
