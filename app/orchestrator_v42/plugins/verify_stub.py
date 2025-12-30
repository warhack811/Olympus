# app/orchestrator_v42/plugins/verify_stub.py

from typing import Dict, Any, List

def should_verify(safety_res: Dict[str, Any] | Any, claims: List[str]) -> bool:
    """
    Doğrulama (Verify) gerekli mi kontrol eder.
    
    Kural:
    - Güvenlik 'input_safe' False ise VEYA
    - İddia (claims) sayısı 3 veya daha fazlaysa doğrula.
    """
    is_safe = True
    
    # Dict veya Object desteği
    if isinstance(safety_res, dict):
        is_safe = safety_res.get("input_safe", True)
    elif hasattr(safety_res, "input_safe"):
        is_safe = safety_res.input_safe
        
    if not is_safe:
        return True
        
    if len(claims) >= 3:
        return True
        
    return False

def verify(contracted_output: Dict[str, Any] | Any) -> Dict[str, Any]:
    """
    Doğrulama işlemini simüle eder.
    """
    claims = []
    if isinstance(contracted_output, dict):
        claims = contracted_output.get("claims", [])
    elif hasattr(contracted_output, "claims"):
        claims = contracted_output.claims
        
    # Simülasyon: Çok fazla iddia varsa riskli ve başarısız
    if len(claims) >= 3:
        return {
            "passed": False,
            "risk_level": "medium",
            "notes": "Çok fazla iddia var, insan doğrulaması önerilir."
        }
    
    return {
        "passed": True,
        "risk_level": "low",
        "notes": "Otomatik doğrulama başarılı."
    }
