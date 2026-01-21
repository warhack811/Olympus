"""
Mami AI - Uygulama Yapılandırması (Hybrid Architecture & Atlas v4.4)
=====================================================================

Bu modül, uygulamanın tüm yapılandırma ayarlarını merkezi olarak yönetir.
Ayarlar .env dosyasından veya ortam değişkenlerinden otomatik olarak okunur.
Pydantic BaseSettings kullanarak tip güvenliği ve validasyon sağlar.

Mimarı:
  - Hybrid Cloud-Local: CORE (Oracle Cloud) ve WORKER (Local GPU) modları
  - Atlas Memory System: Neo4j (Graph), Qdrant (Vector), Redis (Cache)
  - Multi-Provider LLM: Groq, Gemini, Ollama fallback zincirleri
  - Görsel Üretim: Forge/Stable Diffusion entegrasyonu

Kullanım:
    from app.config import get_settings
    settings = get_settings()
    print(settings.APP_NAME)
    print(settings.get_redis_url(db=1))

Ortam Değişkenleri:
    .env dosyasında tanımlanan tüm ayarlar otomatik olarak yüklenir.
    Üretim ortamında .env yerine sistem ortam değişkenleri kullanılmalıdır.
"""

import re
import uuid
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Pydantic BaseSettings tabanlı yapılandırma sınıfı.
    
    Tüm uygulama ayarlarını merkezi olarak yönetir ve .env dosyasından
    otomatik olarak değerleri okur. Singleton pattern ile kullanılır.
    """

    # ═════════════════════════════════════════════════════════════════════════
    # 1. GENEL UYGULAMA AYARLARI
    # ═════════════════════════════════════════════════════════════════════════
    
    APP_NAME: str = Field(default="Mami AI", description="Uygulama adı")
    DEBUG: bool = Field(default=True, description="Debug modu (Swagger UI, verbose logging)")
    API_HOST: str = Field(default="0.0.0.0", description="API sunucu adresi")
    API_PORT: int = Field(default=8000, description="API sunucu portu")
    SECRET_KEY: str = Field(
        default="super-secret-dev-key-change-this",
        description="Oturum ve JWT imzalama için gizli anahtar (üretimde değiştirilmeli)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 2. GÜVENLİK AYARLARI (Atlas Sovereign)
    # ═════════════════════════════════════════════════════════════════════════
    
    SAFETY_PROMPT_GUARD_ENABLED: bool = Field(
        default=True,
        description="Prompt Injection koruması aktif mi?"
    )
    SAFETY_PROMPT_GUARD_MODEL: str = Field(
        default="meta-llama/llama-prompt-guard-2-86m",
        description="Prompt Injection tespiti için kullanılan model"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 2.1. YÖNETİCİ AYARLARI (Bootstrap)
    # ═════════════════════════════════════════════════════════════════════════
    
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Varsayılan yönetici kullanıcı adı (ilk kurulum için)"
    )
    ADMIN_PASSWORD: str = Field(
        default="admin",
        description="Varsayılan yönetici şifresi (ilk kurulum için)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 3. NODE KİMLİĞİ (Hybrid Architecture)
    # ═════════════════════════════════════════════════════════════════════════
    
    NODE_MODE: str = Field(
        default="CORE",
        description="Çalışma Modu: CORE (Oracle Cloud) veya WORKER (Local GPU Node)"
    )
    NODE_ID: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:8],
        description="Benzersiz Instance ID (otomatik oluşturulur)"
    )
    ATLAS_API_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Worker'ın veriyi yükleyeceği ana API adresi"
    )
    INTERNAL_UPLOAD_TOKEN: str = Field(
        default="mami-internal-secret-token",
        description="Cloud-Worker arası veri transferi için güvenli token"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 4. ATLAS CORE (Beyin & Hafıza Sistemi)
    # ═════════════════════════════════════════════════════════════════════════
    
    ATLAS_ENABLED: bool = Field(
        default=True,
        description="Atlas yetenekleri aktif mi?"
    )
    ATLAS_MEMORY_MODE: str = Field(
        default="STANDARD",
        description="Hafıza Modu: OFF, STANDARD (Graph+Vector), FULL (Deep Extraction)"
    )
    RDR_ENABLED: bool = Field(
        default=True,
        description="Routing Decision Record (Traceability) aktif mi?"
    )
    BRAIN_RAG_GATE_ENABLED: bool = Field(
        default=False,
        description="Akıllı RAG Kapısı (Intelligent RAG Gate) aktif mi?"
    )
    ATLAS_EMBED_DIM: int = Field(
        default=768,
        description="Hafıza vektör boyutu (Gemini=768, MiniLM=384)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 5. NEO4J (GRAPH MEMORY)
    # ═════════════════════════════════════════════════════════════════════════
    
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j bağlantı adresi"
    )
    NEO4J_USER: str = Field(
        default="neo4j",
        description="Neo4j kullanıcı adı"
    )
    NEO4J_PASSWORD: str = Field(
        default="password",
        description="Neo4j şifresi"
    )
    NEO4J_POOL_SIZE: int = Field(
        default=50,
        description="Neo4j bağlantı havuzu boyutu"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 6. QDRANT (VECTOR MEMORY)
    # ═════════════════════════════════════════════════════════════════════════
    
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant API adresi"
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API Key (opsiyonel)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 7. REDIS (CACHE & SESSION MEMORY)
    # ═════════════════════════════════════════════════════════════════════════
    
    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis sunucu adresi"
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="Redis portu"
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        description="Redis şifresi (opsiyonel)"
    )
    REDIS_DB_CELERY: int = Field(
        default=0,
        description="Celery Task Queue DB indeksi"
    )
    REDIS_DB_MEMORY: int = Field(
        default=0,
        description="Working Memory & Dynamic Context DB indeksi"
    )
    REDIS_DB_RDR: int = Field(
        default=0,
        description="RDR & Life Trace Events DB indeksi"
    )
    REDIS_DB_QUEUE: int = Field(
        default=0,
        description="Hybrid Worker Queue DB indeksi"
    )
    # Env'den okumak için (Property ile çakışmaması için farklı isim ama alias var)
    REDIS_DSN: Optional[str] = Field(
        default=None,
        alias="REDIS_URL",
        description="Redis bağlantı dizesi (Environment variable önceliği)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 8. SQL VERİTABANI (Legacy/Auth)
    # ═════════════════════════════════════════════════════════════════════════
    
    DATABASE_URL: str | None = Field(
        default=None,
        description="Veritabanı bağlantı URL'si (boşsa sqlite:///data/app.db kullanılır)"
    )
    CHROMA_PERSIST_DIR: str = Field(
        default="data/chroma_db",
        description="[DEPRECATED] ChromaDB dizini"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 9. GROQ API (Ana LLM Provider)
    # ═════════════════════════════════════════════════════════════════════════
    
    GROQ_API_KEY: str = Field(
        default="",
        description="Groq API ana anahtar"
    )
    GROQ_API_KEY_BACKUP: str = Field(
        default="",
        description="Groq API yedek anahtar 1"
    )
    GROQ_API_KEY_3: str = Field(
        default="",
        description="Groq API yedek anahtar 2"
    )
    GROQ_API_KEY_4: str = Field(
        default="",
        description="Groq API yedek anahtar 3"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 10. GEMINI API (Yedek LLM Provider)
    # ═════════════════════════════════════════════════════════════════════════
    
    GEMINI_API_KEY: str = Field(
        default="",
        description="Gemini API ana anahtar"
    )
    GEMINI_API_KEY_2: str = Field(
        default="",
        description="Gemini API yedek anahtar 1"
    )
    GEMINI_API_KEY_3: str = Field(
        default="",
        description="Gemini API yedek anahtar 2"
    )
    VISION_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Görsel analiz için kullanılacak Gemini modeli"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 11. MODEL STRATEJİSİ (Fallback & Governance)
    # ═════════════════════════════════════════════════════════════════════════
    
    ROLE_MODEL_CHAINS: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Rol bazlı model zincirleri (governance tarafından okunur)"
    )
    FALLBACK_CHAINS: dict[str, list[str]] = Field(
        default={
            "llama-3.3-70b-versatile": ["mixtral-8x7b-32768", "gemma2-9b-it"],
            "llama-3.1-8b-instant": ["gemma2-9b-it", "mixtral-8x7b-32768"],
            "default": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        },
        description="Model fallback zincirleri (hata durumunda sırasıyla denenir)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 12. OLLAMA (Yerel LLM)
    # ═════════════════════════════════════════════════════════════════════════
    
    OLLAMA_BASE_URL: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama sunucu adresi"
    )
    OLLAMA_LOCAL_MODEL: str = Field(
        default="josiefied-qwen3-8b",
        description="Ollama'da kullanılacak model adı"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 13. İNTERNET ARAMA (Serper/Google)
    # ═════════════════════════════════════════════════════════════════════════
    
    SERPER_API_KEY: str = Field(
        default="",
        description="Serper (Google) API anahtarı"
    )
    SERPER_ENDPOINT: str = Field(
        default="https://google.serper.dev/search",
        description="Serper API endpoint"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 14. GÖRSEL ÜRETİM (Forge/Stable Diffusion)
    # ═════════════════════════════════════════════════════════════════════════
    
    IMAGE_GENERATION_MODE: str = Field(
        default="LOCAL_QUEUE",
        description="Görsel üretim modu: API, LOCAL_QUEUE, MOCK"
    )
    WORKER_PUBLIC_URL: Optional[str] = Field(
        default=None,
        description="Dışarıdan erişilebilir Worker URL'i (opsiyonel)"
    )
    FORGE_BASE_URL: str = Field(
        default="http://127.0.0.1:7860",
        description="Forge/SD WebUI adresi"
    )
    FORGE_TXT2IMG_PATH: str = Field(
        default="/sdapi/v1/txt2img",
        description="Text-to-image API endpoint"
    )
    FORGE_TIMEOUT: int = Field(
        default=1200,
        description="Görsel üretim zaman aşımı (saniye)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 15. FLUX CHECKPOINTS (Görsel Modelleri)
    # ═════════════════════════════════════════════════════════════════════════
    
    FLUX_STANDARD_CHECKPOINT: str = Field(
        default="flux1-dev-bnb-nf4-v2.safetensors",
        description="Standard Flux checkpoint"
    )
    FLUX_NSFW_CHECKPOINT: str = Field(
        default="fluxedUpFluxNSFW_51FP8.safetensors",
        description="NSFW Flux checkpoint"
    )
    FORGE_FLUX_CHECKPOINT: str = Field(
        default="flux1-dev-bnb-nf4-v2.safetensors",
        description="Forge default Flux checkpoint"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # 16. CORS & NETWORK
    # ═════════════════════════════════════════════════════════════════════════
    
    CORS_ORIGINS: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        description="İzin verilen origin'ler (virgülle ayrılmış)"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # PYDANTIC CONFIGURATION
    # ═════════════════════════════════════════════════════════════════════════
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═════════════════════════════════════════════════════════════════════════
    
    @property
    def REDIS_URL(self) -> str:
        """
        Redis bağlantı URL'sini dinamik olarak oluşturur.
        
        Bireysel bileşenlerden (host, port, password, db) tam URL'i oluşturur.
        REDIS_DB_MEMORY varsayılan database indeksi olarak kullanılır.
        
        Returns:
            str: Redis connection URL (redis:// veya rediss://)
            
        Note:
            Farklı database için get_redis_url(db) metodunu kullanın.
        """
        if self.REDIS_DSN:
            return self.REDIS_DSN
            
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_MEMORY}"

    # ═════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═════════════════════════════════════════════════════════════════════════
    
    def get_redis_url(self, db: int) -> str:
        """
        Belirtilen database indeksi ile Redis URL'sini döndürür.
        
        Upstash gibi managed Redis servisleri için URL'i temizler ve
        yeni database indeksini ekler.
        
        Args:
            db: Redis database indeksi (0-15)
            
        Returns:
            str: Redis connection URL with specified database index
            
        Example:
            >>> settings = get_settings()
            >>> url = settings.get_redis_url(db=1)
            >>> print(url)
            redis://localhost:6379/1
        """
        base_url = self.REDIS_URL
        if base_url and (base_url.startswith("redis://") or base_url.startswith("rediss://")):
            # Mevcut DB indeksini temizle ve yenisini ekle
            clean_url = re.sub(r'/\d+$', '', base_url)
            return f"{clean_url}/{db}"
        
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{db}"

    def get_groq_api_keys(self) -> list[str]:
        """
        Tüm geçerli Groq API anahtarlarını liste olarak döndürür.
        
        Boş olmayan tüm Groq API anahtarlarını sırasıyla döner.
        Fallback stratejisi için kullanılır.
        
        Returns:
            list[str]: Geçerli Groq API anahtarları
        """
        keys = [self.GROQ_API_KEY, self.GROQ_API_KEY_BACKUP, self.GROQ_API_KEY_3, self.GROQ_API_KEY_4]
        return [k for k in keys if k]

    def get_gemini_api_keys(self) -> list[str]:
        """
        Tüm geçerli Gemini API anahtarlarını liste olarak döndürür.
        
        Boş olmayan tüm Gemini API anahtarlarını sırasıyla döner.
        Fallback stratejisi için kullanılır.
        
        Returns:
            list[str]: Geçerli Gemini API anahtarları
        """
        keys = [self.GEMINI_API_KEY, self.GEMINI_API_KEY_2, self.GEMINI_API_KEY_3]
        return [k for k in keys if k]

    def get_cors_origins_list(self) -> list[str]:
        """
        CORS origin'lerini liste olarak döndürür.
        
        CORS_ORIGINS string'ini virgülle ayrılmış liste olarak parse eder.
        Boşlukları temizler.
        
        Returns:
            list[str]: CORS origin'leri
            
        Example:
            >>> settings = get_settings()
            >>> origins = settings.get_cors_origins_list()
            >>> print(origins)
            ['http://localhost:8000', 'http://127.0.0.1:8000']
        """
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# ═════════════════════════════════════════════════════════════════════════════
# SINGLETON FACTORY
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache
def get_settings() -> Settings:
    """
    Singleton Settings nesnesi döndürür.
    
    @lru_cache dekoratörü sayesinde aynı Settings nesnesi her zaman döner.
    Uygulama başlangıcında bir kez oluşturulur ve yeniden kullanılır.
    
    Returns:
        Settings: Singleton Settings nesnesi
        
    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        Mami AI
    """
    return Settings()
