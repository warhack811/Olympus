"""
Mami AI - API Key Manager
=========================

Bu modül, API anahtarlarının rotasyonundan, sağlık durumundan ve yük dağılımından sorumludur.
ApiMonitor servisinden veri alarak en uygun anahtarı seçer.

Sorumluluklar:
    - Round-robin veya Least-used stratejisi ile anahtar seçimi
    - 429 (Rate Limit) alan anahtarları geçici olarak soğumaya alma (Cooldown)
    - Geçersiz anahtarları devre dışı bırakma
"""

import logging
import random
import time
from typing import Dict, List, Optional, Any, Tuple

from app.core.env_manager import env_manager
from app.services.api_monitor import api_monitor

logger = logging.getLogger(__name__)

class KeyManager:
    _instance = None
    
    # Cooldown memory: {key: timestamp_when_available}
    _cooldowns: Dict[str, float] = {}
    
    # Circuit breaker state: {model: failure_count}
    _model_failures: Dict[str, int] = {}
    
    # Circuit breaker recovery: {model: timestamp_when_active_again}
    _model_cooldowns: Dict[str, float] = {}
    
    # Constants
    MAX_MODEL_FAILURES = 3
    MODEL_COOLDOWN_SECONDS = 60 # 1 minute block for broken models

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _cleanup_cooldowns(self):
        """Süresi dolmuş cooldown kayıtlarını temizler."""
        now = time.time()
        # Key cooldowns
        expired_keys = [k for k, t in self._cooldowns.items() if now >= t]
        for k in expired_keys:
            del self._cooldowns[k]
            
        # Model cooldowns (Auto-recovery)
        expired_models = [m for m, t in self._model_cooldowns.items() if now >= t]
        for m in expired_models:
            del self._model_cooldowns[m]
            if m in self._model_failures:
                del self._model_failures[m] # Reset failure count on recovery
            logger.info(f"[KeyManager] Model {m} circuit breaker reset (Recovered).")

    def _is_in_cooldown(self, key: str) -> bool:
        """Anahtar şu an cooldown'da mı?"""
        if key not in self._cooldowns:
            return False
            
        if time.time() >= self._cooldowns[key]:
            del self._cooldowns[key]
            return False
            
        return True
        
    def _is_model_broken(self, model: str) -> bool:
        """Model şu an devre dışı mı?"""
        if not model: return False
        
        # Cooldown check
        if model in self._model_cooldowns:
            return True # Still in penalty box
            
        # Limit check
        if self._model_failures.get(model, 0) >= self.MAX_MODEL_FAILURES:
            # Trigger cooldown if not already (should handle in report_failure but extra safety)
            return True
            
        return False

    def report_failure(self, key: str, status_code: int, model: str | None = None):
        """
        API hatası bildirir.
        429 -> Key Cooldown (Random)
        5xx -> Model Failure Count++
        401 -> Key Invalid
        """
        if status_code == 429:
            # Random jitter ile cooldown (10-30sn)
            cooldown_duration = random.uniform(10, 30)
            self._cooldowns[key] = time.time() + cooldown_duration
            logger.warning(f"[KeyManager] Key 429 Rate Limit. Cooldown for {cooldown_duration:.1f}s")
        
        elif status_code == 401:
            logger.error(f"[KeyManager] Key 401 Unauthorized. Marking invalid.")
            api_monitor.mark_invalid(key)
        
        # Model circuit breaker logic
        if model and status_code >= 500:
             count = self._model_failures.get(model, 0) + 1
             self._model_failures[model] = count
             
             if count >= self.MAX_MODEL_FAILURES:
                 # Trip the breaker
                 self._model_cooldowns[model] = time.time() + self.MODEL_COOLDOWN_SECONDS
                 logger.error(f"[KeyManager] CIRCUIT TRIP! Model {model} failed {count} times. Blocked for {self.MODEL_COOLDOWN_SECONDS}s.")

    def report_success(self, key: str, model: str | None = None):
        """Başarılı çağrı bildirimi."""
        # Reset model failures if needed
        if model and model in self._model_failures:
            self._model_failures[model] = 0

    def get_next_key(self, model: str | None = None) -> str | None:
        """
        Kullanılabilecek en iyi anahtarı seçer.
        Strategy: Least Used (Requests Today) + Cooldown Check
        """
        self._cleanup_cooldowns()
        
        # 0. Circuit Breaker Check
        if model and self._is_model_broken(model):
            logger.error(f"[KeyManager] Model {model} is broken (Circuit Breaker Active). Skipping.")
            return None
        
        # 1. Tüm anahtarları env_manager'dan al
        # Bu call hafiftir, env_manager bellekte tutar sonucu
        all_keys_conf = env_manager.get_groq_keys() 
        
        # Tuple: (key_value, usage_count)
        candidate_keys: List[Tuple[str, int]] = []
        
        for k_conf in all_keys_conf:
            raw_key = k_conf["value"]
            if not raw_key: 
                continue
                
            # 2. Cooldown kontrolü
            if self._is_in_cooldown(raw_key):
                continue
                
            # 3. ApiMonitor'dan sağlık ve kullanım durumunu al
            stats = api_monitor.get_stats_for_key(raw_key)
            if stats:
                if stats.get("status") == "invalid":
                    continue
                    
                # Kalan limit kontrolü (Eğer header bilgisi varsa ve çok düşükse)
                rem_req = stats.get("remaining_requests")
                if rem_req is not None and rem_req < 5:
                     # Çok az kalmış, riske atma
                     logger.debug(f"[KeyManager] Key skipping low limit: req={rem_req}")
                     continue
                
                daily = stats.get("daily_usage", {})
                req_today = daily.get("requests_today", 0)
                candidate_keys.append((raw_key, req_today))
            else:
                # Stats yoksa (hiç kullanılmamış), öncelikli aday (-1)
                candidate_keys.append((raw_key, -1))

        if not candidate_keys:
            logger.error("[KeyManager] No available keys found (all exhausted or in cooldown)!")
            return None
            
        # 4. Sıralama: 
        # En az kullanılan (req_today) en başa.
        # -1 (hiç kullanılmamış) en başa gelir.
        candidate_keys.sort(key=lambda x: x[1])
        
        best_key = candidate_keys[0][0]
        
        return best_key

# Singleton instance
key_manager = KeyManager()
