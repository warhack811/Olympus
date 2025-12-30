# app/orchestrator_v42/rollout.py

import hashlib
from app.orchestrator_v42.feature_flags import OrchestratorFeatureFlags

def compute_bucket(user_id: str) -> int:
    """
    Kullanıcı ID'sine göre deterministik bir bucket (0-99) hesaplar.
    Algoritma: SHA256(user_id) -> Hex First 8 -> Int -> Mod 100
    """
    if not user_id:
        return -1
        
    hash_obj = hashlib.sha256(user_id.encode("utf-8"))
    hex_digest = hash_obj.hexdigest()
    # İlk 8 karakter (32-bit int için yeterli)
    hash_int = int(hex_digest[:8], 16)
    return hash_int % 100

def should_use_orchestrator(user_id: str | None, flags: OrchestratorFeatureFlags) -> bool:
    """
    DEBUG: Zorunlu ON. Normalde rollout mantığı çalışır.
    """
    return True
