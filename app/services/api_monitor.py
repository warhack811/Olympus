"""
Mami AI - API Usage Monitor Service
===================================

Bu servis, Groq API çağrılarından dönen rate limit headerlarını izler
ve anlık kullanım istatistiklerini bellekte tutar.

Header Örnekleri:
x-ratelimit-limit-requests: 14400
x-ratelimit-limit-tokens: 6000
x-ratelimit-remaining-requests: 14399
x-ratelimit-remaining-tokens: 5990
x-ratelimit-reset-requests: 2s
x-ratelimit-reset-tokens: 0.8s
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

import hashlib
import json
from datetime import timezone
from pathlib import Path


class ApiMonitorService:
    _instance = None
    _stats: dict[str, dict[str, Any]] = {}
    _daily_usage: dict[str, dict[str, Any]] = {}  # Daily usage tracking
    _storage_file = Path("data/api_stats.json")
    _daily_file = Path("data/api_daily_usage.json")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_stats()
            cls._instance._load_daily_usage()
        return cls._instance

    def _load_stats(self):
        """Diskten istatistikleri yükler."""
        if self._storage_file.exists():
            try:
                data = self._storage_file.read_text(encoding="utf-8")
                self._stats = json.loads(data)
            except Exception as e:
                logger.error(f"[API_MONITOR] Load error: {e}")
                self._stats = {}
        else:
            self._stats = {}

    def _load_daily_usage(self):
        """Günlük kullanım verilerini yükler."""
        if self._daily_file.exists():
            try:
                data = self._daily_file.read_text(encoding="utf-8")
                self._daily_usage = json.loads(data)
                self._check_daily_reset()
            except Exception as e:
                logger.error(f"[API_MONITOR] Daily load error: {e}")
                self._daily_usage = {}
        else:
            self._daily_usage = {}

    def _save_stats(self):
        """İstatistikleri diske kaydeder."""
        try:
            self._storage_file.parent.mkdir(parents=True, exist_ok=True)
            self._storage_file.write_text(json.dumps(self._stats, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[API_MONITOR] Save error: {e}")

    def _save_daily_usage(self):
        """Günlük kullanım verilerini kaydeder."""
        try:
            self._daily_file.parent.mkdir(parents=True, exist_ok=True)
            self._daily_file.write_text(json.dumps(self._daily_usage, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[API_MONITOR] Daily save error: {e}")

    def _get_today_key(self) -> str:
        """
        Bugünün tarihini UTC'ye göre YYYY-MM-DD formatında döndürür.
        Groq limitleri UTC gece yarısı (TR 03:00) sıfırlanır.
        """
        from datetime import datetime

        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _check_daily_reset(self):
        """
        UTC gece yarısı (TR 03:00) sıfırlama kontrolü.
        Groq'un resmi sıfırlama zamanıyla senkron.
        """
        today = self._get_today_key()
        for key_hash in list(self._daily_usage.keys()):
            usage = self._daily_usage[key_hash]
            if usage.get("date") != today:
                # Yeni gün (UTC) - sıfırla
                self._daily_usage[key_hash] = {"date": today, "requests_today": 0, "tokens_today": 0, "models": {}}
        self._save_daily_usage()

    def _get_storage_key(self, api_key: str) -> str:
        """API anahtarı için güvenli/benzersiz bir hash üretir."""
        if not api_key:
            return "unknown"
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _mask_key(self, api_key: str) -> str:
        """API anahtarını gizler (örn: gsk_...1234)."""
        if not api_key or len(api_key) < 10:
            return "UNKNOWN"
        return f"{api_key[:4]}...{api_key[-4:]}"

    def _parse_duration(self, duration_str: str) -> float:
        """Groq süre stringini (2s, 14m, 100ms) saniyeye çevirir."""
        if not duration_str:
            return 0.0

        try:
            val = duration_str.lower()
            if val.endswith("ms"):
                return float(val[:-2]) / 1000
            elif val.endswith("s"):
                return float(val[:-1])
            elif val.endswith("m"):
                return float(val[:-1]) * 60
            elif val.endswith("h"):
                return float(val[:-1]) * 3600
            return float(val)
        except:
            return 0.0

    def increment_usage(self, api_key: str, model: str, tokens_used: int = 0):
        """Bir API çağrısı yapıldığında günlük kullanımı artırır."""
        storage_key = self._get_storage_key(api_key)
        today = self._get_today_key()

        if storage_key not in self._daily_usage or self._daily_usage[storage_key].get("date") != today:
            self._daily_usage[storage_key] = {"date": today, "requests_today": 0, "tokens_today": 0, "models": {}}

        usage = self._daily_usage[storage_key]
        usage["requests_today"] += 1
        usage["tokens_today"] += tokens_used

        # Model bazlı tracking
        if model not in usage["models"]:
            usage["models"][model] = {"requests": 0, "tokens": 0}
        usage["models"][model]["requests"] += 1
        usage["models"][model]["tokens"] += tokens_used

        self._save_daily_usage()

    def update_usage(self, api_key: str, headers: Any):
        """Headerlardan limit bilgisini günceller."""
        if not headers:
            return

        storage_key = self._get_storage_key(api_key)
        masked_key = self._mask_key(api_key)

        # Header isimleri
        limit_req = headers.get("x-ratelimit-limit-requests")
        limit_tok = headers.get("x-ratelimit-limit-tokens")
        rem_req = headers.get("x-ratelimit-remaining-requests")
        rem_tok = headers.get("x-ratelimit-remaining-tokens")
        reset_time_str = headers.get("x-ratelimit-reset-tokens")  # örn: 2s, 14m

        # Eğer headerlar yoksa işlem yapma
        if not all([limit_req, limit_tok, rem_req, rem_tok]):
            return

        try:
            now = time.time()
            reset_seconds = self._parse_duration(reset_time_str)
            reset_timestamp = now + reset_seconds

            current_stat = {
                "key_masked": masked_key,
                "limit_requests": int(limit_req),
                "limit_tokens": int(limit_tok),
                "remaining_requests": int(rem_req),
                "remaining_tokens": int(rem_tok),
                "reset_time_str": reset_time_str,
                "reset_timestamp": reset_timestamp,
                "last_updated": now,
                "status": "active",
            }

            # Yüzdeleri hesapla
            current_stat["percent_requests"] = (
                current_stat["remaining_requests"] / current_stat["limit_requests"]
            ) * 100
            current_stat["percent_tokens"] = (current_stat["remaining_tokens"] / current_stat["limit_tokens"]) * 100

            self._stats[storage_key] = current_stat
            self._save_stats()

        except ValueError as e:
            logger.error(f"[API_MONITOR] Parse error: {e}")

    def mark_invalid(self, api_key: str):
        """Anahtarı geçersiz olarak işaretler (401 durumunda)."""
        storage_key = self._get_storage_key(api_key)
        masked_key = self._mask_key(api_key)

        # Mevcut stats varsa üzerine yaz veya güncelle
        current = self._stats.get(storage_key, {})
        current.update({"key_masked": masked_key, "status": "invalid", "last_updated": time.time()})
        self._stats[storage_key] = current
        self._save_stats()

    def get_all_stats(self) -> list:
        """Tüm istatistikleri liste olarak döndürür."""
        return list(self._stats.values())

    def get_stats_for_key(self, api_key: str) -> dict[str, Any] | None:
        storage_key = self._get_storage_key(api_key)
        stats = self._stats.get(storage_key, {}).copy()

        # Günlük kullanımı da ekle
        daily = self._daily_usage.get(storage_key, {})
        if daily:
            stats["daily_usage"] = {
                "date": daily.get("date"),
                "requests_today": daily.get("requests_today", 0),
                "tokens_today": daily.get("tokens_today", 0),
                "models": daily.get("models", {}),
            }

        return stats if stats else None


# Singleton Export
api_monitor = ApiMonitorService()
