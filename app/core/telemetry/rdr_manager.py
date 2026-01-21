"""
Mami AI - RDR Data Manager (Atlas Sovereign Edition)
----------------------------------------------------
Yönlendirme Karar Kaydı (Routing Decision Record) veri katmanı.

Temel Sorumluluklar:
1. RDR Oluşturma: Her istek için kara kutu kaydı
2. Depolama: Redis veya bellek içi FIFO
3. Sorgulama: Son kayıtları getirme
"""

import uuid
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RDR:
    """Sistemdeki her bir işlemin 'kara kutu' kaydını tutan veri sınıfı."""
    
    # Kimlik ve Zaman
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Girdi
    message: str = ""
    message_length: int = 0
    rewritten_query: str = ""
    
    # Niyet Sınıflandırma
    intent: str = "unknown"
    confidence: float = 0.0
    tier_used: int = -1
    
    # Model Seçimi
    model_category: str = ""
    model_id: str = ""
    model_reason: str = ""
    
    # Performans (ms)
    safety_ms: int = 0
    classification_ms: int = 0
    dag_execution_ms: int = 0
    synthesis_ms: int = 0
    quality_ms: int = 0
    total_ms: int = 0
    
    # Yanıt
    response_length: int = 0
    response_preview: str = ""
    
    # Güvenlik
    safety_passed: bool = True
    safety_issues: list = field(default_factory=list)
    pii_redacted: bool = False
    injection_blocked: bool = False
    
    # Kalite
    quality_passed: bool = True
    quality_issues: list = field(default_factory=list)
    
    # Görev Detayları
    is_multi_task: bool = False
    tasks_count: int = 1
    tasks_completed: int = 0
    tasks_failed: int = 0
    task_details: list = field(default_factory=list)
    
    # Model Detayları
    safety_model: str = ""
    orchestrator_model: str = ""
    synthesizer_model: str = ""
    
    # Bağlam
    time_context: str = ""
    user_facts_dump: list = field(default_factory=list)
    
    # Reasoning
    orchestrator_reasoning: str = ""
    reasoning_steps: list = field(default_factory=list)
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    technical_errors: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def create(cls, message: str) -> "RDR":
        """Belirli bir mesaj için yeni RDR kaydı oluşturur."""
        return cls(message=message, message_length=len(message))


# Bellek içi depolama (FIFO)
_rdr_storage: Dict[str, RDR] = {}
_RDR_MAX_SIZE = 1000


class RDRManager:
    """RDR yönetim sınıfı."""
    
    def __init__(self):
        self._redis = None
        self._settings = get_settings()
    
    def _get_redis(self):
        """Redis bağlantısı al (lazy)."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(
                    host=self._settings.REDIS_HOST,
                    port=self._settings.REDIS_PORT,
                    password=getattr(self._settings, 'REDIS_PASSWORD', None),
                    db=getattr(self._settings, 'REDIS_DB_RDR', 2),
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"[RDRManager] Redis not available: {e}")
        return self._redis
    
    def save_rdr(self, rdr: RDR) -> None:
        """RDR'yi depolamaya kaydet."""
        global _rdr_storage
        
        # Redis varsa kullan
        redis_client = self._get_redis()
        if redis_client:
            try:
                key = f"rdr:{rdr.request_id}"
                redis_client.setex(key, 86400, rdr.to_json())  # 24h TTL
                redis_client.lpush("rdr:recent", rdr.request_id)
                redis_client.ltrim("rdr:recent", 0, _RDR_MAX_SIZE - 1)
                return
            except Exception as e:
                logger.warning(f"[RDRManager] Redis save failed: {e}")
        
        # Fallback: Bellek içi
        if len(_rdr_storage) >= _RDR_MAX_SIZE:
            oldest_id = min(_rdr_storage.keys(), key=lambda k: _rdr_storage[k].timestamp)
            del _rdr_storage[oldest_id]
        
        _rdr_storage[rdr.request_id] = rdr
    
    def get_rdr(self, request_id: str) -> Optional[RDR]:
        """Request ID ile RDR getir."""
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                data = redis_client.get(f"rdr:{request_id}")
                if data:
                    return RDR(**json.loads(data))
            except Exception as e:
                logger.warning(f"[RDRManager] Redis get failed: {e}")
        
        return _rdr_storage.get(request_id)
    
    def get_recent_rdrs(self, limit: int = 10) -> List[RDR]:
        """En son RDR'leri getir."""
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                ids = redis_client.lrange("rdr:recent", 0, limit - 1)
                rdrs = []
                for rid in ids:
                    rdr = self.get_rdr(rid)
                    if rdr:
                        rdrs.append(rdr)
                return rdrs
            except Exception as e:
                logger.warning(f"[RDRManager] Redis list failed: {e}")
        
        # Fallback: Bellek içi
        sorted_rdrs = sorted(
            _rdr_storage.values(),
            key=lambda r: r.timestamp,
            reverse=True
        )
        return sorted_rdrs[:limit]


# Singleton
rdr_manager = RDRManager()


# Helper functions
def save_rdr(rdr: RDR) -> None:
    rdr_manager.save_rdr(rdr)

def get_rdr(request_id: str) -> Optional[RDR]:
    return rdr_manager.get_rdr(request_id)

def get_recent_rdrs(limit: int = 10) -> List[RDR]:
    return rdr_manager.get_recent_rdrs(limit)
