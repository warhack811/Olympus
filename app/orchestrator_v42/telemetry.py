import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict

class TelemetryCounters:
    """
    Orchestrator için basit, in-memory ve async-safe sayaç sistemi.
    Rollout ve hata oranlarını anlık izlemek için kullanılır.
    """
    _instance = None
    
    _ALLOWED_KEYS = {'reason', 'type', 'verify', 'jury', 'risk'}

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def incr(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Bir sayacı artırır.
        Label verilirse, metrik ismi "name{label_key=label_val}" formatına dönüştürülür.
        Güvenlik: Sadece izin verilen label anahtarları işlenir.
        """
        key = name
        if labels:
            # Sadece izinli anahtarları al
            filtered_labels = {k: str(v) for k, v in labels.items() if k in self._ALLOWED_KEYS}
            
            if filtered_labels:
                # Basit, deterministik label formatı: name|key=val|key2=val2
                sorted_items = sorted(filtered_labels.items())
                label_str = "|".join([f"{k}={v}" for k, v in sorted_items])
                key = f"{name}|{label_str}"
            
        async with self._lock:
            self._counters[key] += 1

    async def snapshot(self) -> Dict[str, int]:
        """
        Mevcut sayaçların bir kopyasını döndürür.
        """
        async with self._lock:
            return dict(self._counters)

    async def reset(self):
        """
        Sayaçları sıfırlar (Test veya reset durumları için).
        """
        async with self._lock:
            self._counters.clear()

# Global nesne (Gateway bunu import edip kullanacak)
_TELEMETRY = TelemetryCounters.get_instance()

# Kolay erişim helper'ı (Gateway içinde await telemetry.incr(...) yerine await count(...) gibi kullanılabilir,
# veya direkt module üzerinden erişilebilir)
async def count(name: str, labels: Optional[Dict[str, str]] = None):
    await _TELEMETRY.incr(name, labels)

async def get_snapshot() -> Dict[str, int]:
    return await _TELEMETRY.snapshot()
