# app/orchestrator_v42/feature_flags.py

import os
import logging
from typing import List
from pydantic import BaseModel, Field

# Logger kurulumu
logger = logging.getLogger("orchestrator.feature_flags")

class OrchestratorFeatureFlags(BaseModel):
    """
    Orchestrator v4.2 için Merkezi Özellik Bayrakları (Feature Flags).
    Tüm kritik özellikler bu model üzerinden yönetilir.
    
    Varsayılan değerler her zaman GÜVENLİ (SAFE) olmalıdır.
    """
    
    # 1. Ana Kontroller
    production_enabled: bool = False   # Gerçek Production modu (False = Test/Dev)
    
    # 2. Yetenekler
    streaming_enabled: bool = False    # Akışkan yanıt (Streaming)
    
    # 3. Güvenlik ve Dry-Run
    llm_dry_run: bool = True           # True = LLM'e gitme, mock dön
    rag_dry_run: bool = True           # True = Vector DB'ye gitme, mock dön
    
    # 4. İleri Seviye Doğrulama
    verify_enabled: bool = False       # Verify (Self-Correction) döngüsü
    jury_enabled: bool = False         # Jury (Human/AI Jury) döngüsü
    
    # 5. Kademeli Geçiş (Rollout)
    rollout_percent: int = 0           # %0 - %100 arası aktivasyon oranı
    rollout_allowlist: List[str] = Field(default_factory=list) # İzinli kullanıcı ID'leri

    # 6. Araçlar ve Eylemler (FAZ 14.0)
    tools_enabled: bool = False        # Araç kullanımı aktif mi?
    tools_dry_run: bool = True         # Gerçek eylem yapma, simüle et
    tools_max_calls: int = 1           # Maksimum ardışık araç çağrısı (0-3)

    # 7. Hafıza (FAZ 14.1) - Blueprint v1 Section 8
    memory_enabled: bool = True         # Hafıza erişimi aktif mi? (Açık for testing)
    memory_dry_run: bool = False        # Gerçek hafıza servisleri kullan
    memory_max_items: int = 5           # Bağlama eklenecek max hafıza sayısı (0-20)
    
    # 8. Hafıza Yazma (FAZ 14.4) - Memory Write aktif
    memory_write_enabled: bool = True  # Hafızaya yazma aktif (testing için)
    memory_write_dry_run: bool = False  # Gerçek yazma yap
    memory_write_timeout_s: float = 0.25 # Yazma işlemi için timeout (sn)

    # 9. Working Memory - Redis (Phase 1.1 - Blueprint v1 Section 8)
    working_memory_enabled: bool = True   # Redis Working Memory aktif
    working_memory_ttl: int = 172800      # TTL saniye (48 saat)
    working_memory_max_messages: int = 10 # Session'da tutulacak max mesaj

    @staticmethod
    def _parse_float(value: str | None, default: float, min_val: float, max_val: float) -> float:
        """Environment değişkenini güvenli aralıkta float'a çevirir."""
        if value is None:
            return default
        try:
            val = float(value)
            if min_val <= val <= max_val:
                return val
            return default
        except ValueError:
            return default

    @staticmethod
    def _parse_bool(value: str | None, default: bool) -> bool:
        """Environment değişkenini güvenli bool'a çevirir."""
        if not value:
            return default
            
        val_lower = str(value).lower().strip()
        if val_lower in ["true", "1", "yes", "on", "aktif"]:
            return True
        if val_lower in ["false", "0", "no", "off", "pasif"]:
            return False
            
        # Geçersiz değer
        logger.warning(f"[FEATURE_FLAGS] Geçersiz bool değeri: '{value}'. Varsayılan ({default}) kullanılıyor.")
        return default

    @staticmethod
    def _parse_int(value: str | None, default: int, min_val: int, max_val: int) -> int:
        """Environment değişkenini güvenli aralıkta int'e çevirir."""
        if value is None:
            return default
        try:
            val = int(value)
            if min_val <= val <= max_val:
                return val
            else:
                logger.warning(f"[FEATURE_FLAGS] Değer aralık dışı ({value}). {min_val}-{max_val} bekleniyor. Varsayılan ({default}) kullanılıyor.")
                return default
        except ValueError:
            logger.warning(f"[FEATURE_FLAGS] Geçersiz int değeri: '{value}'. Varsayılan ({default}) kullanılıyor.")
            return default

    @staticmethod
    def _parse_list(value: str | None) -> List[str]:
        """CSV formatındaki stringi güvenli listeye çevirir."""
        if not value:
            return []
        try:
            # Virgülle ayır, boşlukları temizle, boş elemanları at
            return [item.strip() for item in value.split(",") if item.strip()]
        except Exception as e:
            logger.warning(f"[FEATURE_FLAGS] Liste ayrıştırma hatası: {e}. Boş liste dönülüyor.")
            return []

    @classmethod
    def load_from_env(cls) -> "OrchestratorFeatureFlags":
        """
        Bayrakları merkezi Settings yapısından (config.py) okur.
        Hata durumunda güvenli varsayılan değerleri (Safe Defaults) kullanır.
        """
        try:
            from app.config import get_settings
            s = get_settings()
            
            return cls(
                production_enabled=s.ORCH_PRODUCTION_ENABLED,
                streaming_enabled=s.ORCH_STREAMING_ENABLED,
                llm_dry_run=s.ORCH_LLM_DRY_RUN,
                rag_dry_run=s.ORCH_RAG_DRY_RUN,
                rollout_percent=s.ORCH_ROLLOUT_PERCENT,
                rollout_allowlist=cls._parse_list(s.ORCH_ROLLOUT_ALLOWLIST),
                tools_enabled=s.ORCH_TOOLS_ENABLED,
                tools_dry_run=s.ORCH_TOOLS_DRY_RUN,
                memory_enabled=s.ORCH_MEMORY_ENABLED,
                memory_dry_run=s.ORCH_MEMORY_DRY_RUN,
                # Working Memory (Phase 1.1)
                working_memory_enabled=s.ORCH_WORKING_MEMORY_ENABLED,
                working_memory_ttl=s.ORCH_WORKING_MEMORY_TTL,
                working_memory_max_messages=s.ORCH_WORKING_MEMORY_MAX_MESSAGES,
            )
        except Exception as e:
            logger.error(f"[FEATURE_FLAGS] Ayar yükleme hatası: {e}. TAM GÜVENLİ mod devrede.")
            return cls()
