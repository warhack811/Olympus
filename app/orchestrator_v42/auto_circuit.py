from collections import deque
from typing import Dict, Any, Set
import time

class OrchestratorAutoCircuit:
    """
    Kendi Kendini Koruyan Otomatik Devre Kesici (Auto-Circuit Breaker).
    Belirli bir süre içinde çok sayıda kritik hata oluşursa, 
    Orchestrator'ı geçici olarak (20sn) kapatarak eski sisteme yönlendirir.
    """
    
    # Sabit Yapılandırma
    WINDOW_SECONDS = 10.0
    THRESHOLD = 5
    COOLOFF_SECONDS = 20.0
    
    # Kritik nedenler (sistem hatası sayılanlar)
    CRITICAL_REASONS: Set[str] = {
        "budget_exceeded",
        "adapter_flow_exception",
        "qc_exception",
        "decision_exception",
        "adapter_empty",
        "postprocess_empty"
    }

    def __init__(self):
        self.open_until_ts: float = 0.0
        self.recent_failures: deque[float] = deque()

    def is_open(self, now_ts: float) -> bool:
        """Devre kesicinin şu an açık olup olmadığını kontrol eder."""
        return now_ts < self.open_until_ts

    def record_failure(self, reason: str, now_ts: float) -> None:
        """
        Bir hata durumunu kaydeder.
        Eğer hata kritikse ve eşik aşılırsa devreyi açar.
        """
        if reason not in self.CRITICAL_REASONS:
            return

        # Pencere temizliği (eski hataları at)
        cutoff = now_ts - self.WINDOW_SECONDS
        while self.recent_failures and self.recent_failures[0] < cutoff:
            self.recent_failures.popleft()

        # Yeni hatayı ekle
        self.recent_failures.append(now_ts)

        # Eşik kontrolü
        if len(self.recent_failures) >= self.THRESHOLD:
            # Zaten açıksa süreyi uzatma kararı verebiliriz ama basitçe
            # sadece kapalıysa veya süresi dolmuşsa yeni süre set edelim.
            # Veya her tetiklendiğinde uzatabiliriz (rolling).
            # Basit & Güvenli: Eğer şu an kapalıysa aç. Açıksa elleme (cooloff bitene kadar bekle).
            if now_ts >= self.open_until_ts:
                self.open_until_ts = now_ts + self.COOLOFF_SECONDS
                # Devre açılınca kuyruğu temizle (reset) ki hemen tekrar tetiklenmesin?
                # Hayır, kuyruk kalsın, cooloff bitince tekrar bakılır.
                # Ama cooloff süresince yeni hata gelirse ne olur? 
                # Gateway zaten "circuit open" hatası fırlatır, o da critical değil.
                # Dolayısıyla loop olmaz.

    def snapshot(self, now_ts: float) -> Dict[str, Any]:
        """Devre durumu hakkında bilgi verir."""
        is_open = self.is_open(now_ts)
        # Pruning yapmadan sadece bilgi verelim, record_failure pruning yapar.
        # Ama doğru count için pruning gerekebilir. Snapshot read-only olsun,
        # count yaklaşık olabilir.
        
        return {
            "is_open": is_open,
            "open_until": self.open_until_ts,
            "recent_critical_failures": len(self.recent_failures),
            "window_seconds": self.WINDOW_SECONDS,
            "threshold": self.THRESHOLD
        }
