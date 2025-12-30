# app/orchestrator_v42/plugins/runtime_state.py

import time
from typing import Dict, Any, List, Optional

class RuntimeState:
    """
    Süreç İçi (In-Memory) Durum Yöneticisi.
    
    Erişim anahtarlarının (keys) anlık durumlarını takip eder.
    Hataları 5 dakikalık (300sn) kayan pencere içinde sayar.
    
    Bu sınıf bir Singleton olarak kullanılmalıdır.
    """
    
    def __init__(self):
        # keys yapısı: { 
        #   key_id: { 
        #     "rpm": int, 
        #     "tpm": int, 
        #     "error_count": int, 
        #     "error_timestamps": List[float],
        #     "cooldown_until": float, 
        #     "circuit_open_until": float 
        #   } 
        # }
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.last_selected_key: Optional[str] = None

    def _ensure_key(self, key_id: str):
        """Anahtar kaydı yoksa varsayılan değerlerle oluşturur."""
        if key_id not in self.keys:
            self.keys[key_id] = {
                "rpm": 0,
                "tpm": 0,
                "error_count": 0, 
                "error_timestamps": [],
                "cooldown_until": 0.0,
                "circuit_open_until": 0.0
            }

    def get_key_snapshot(self) -> Dict[str, Any]:
        """Tüm anahtarların anlık durumunun kopyasını döndürür."""
        # Yüzeysel kopya yeterlidir
        return {k: v.copy() for k, v in self.keys.items()}

    def record_success(self, key_id: str):
        """Başarılı bir kullanım kaydeder (RPM, TPM artırır)."""
        self._ensure_key(key_id)
        # Hata sayacını sıfırlamak yerine pencere mantığına dokunmuyoruz,
        # ancak RPM/TPM artırıyoruz.
        self.keys[key_id]["rpm"] += 1 
        self.keys[key_id]["tpm"] += 1

    def record_failure(self, key_id: str, error_type: str = "unknown"):
        """
        Hata durumunu kaydeder ve politikaları (Cooldown/Devre Kesici) tetikler.
        """
        self._ensure_key(key_id)
        now = time.time()
        
        # Hata ekle ve temizle
        self.prune_errors(key_id, now)
        
        entry = self.keys[key_id]
        entry["error_timestamps"].append(now)
        entry["error_count"] = len(entry["error_timestamps"])
        
        # 3. Özel Kurallar
        # 429 -> 20 sn Cooldown
        if error_type == "429":
            entry["cooldown_until"] = now + 20.0
            
        # 3+ Hata (5 dk içinde) -> 60 sn Devre Kesici
        if entry["error_count"] >= 3:
            entry["circuit_open_until"] = now + 60.0
            
    def prune_errors(self, key_id: str, now_ts: float) -> None:
        """
        Belirtilen anahtar için 5 dakikalık (300sn) pencere dışındaki hataları temizler.
        Bu sayede error_count her zaman güncel kalır.
        """
        self._ensure_key(key_id)
        entry = self.keys[key_id]
        cutoff = now_ts - 300.0
        
        # Filtreleme: cutoff'tan büyük olan timestamp'leri tut
        if entry["error_timestamps"]:
            entry["error_timestamps"] = [t for t in entry["error_timestamps"] if t > cutoff]
            entry["error_count"] = len(entry["error_timestamps"])

    def is_in_cooldown(self, key_id: str, now_ts: float) -> bool:
        """Anahtarın cooldown (soğuma) süresinde olup olmadığını kontrol eder."""
        if key_id not in self.keys:
            return False
        return self.keys[key_id]["cooldown_until"] > now_ts

    def is_circuit_open(self, key_id: str, now_ts: float) -> bool:
        """Anahtarın devre kesicisinin (circuit breaker) açık olup olmadığını kontrol eder."""
        if key_id not in self.keys:
            return False
        return self.keys[key_id]["circuit_open_until"] > now_ts
