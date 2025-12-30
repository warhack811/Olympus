"""
Mami AI - Uygulama Yapılandırması
=================================

Bu modül, uygulamanın tüm yapılandırma ayarlarını yönetir.
Ayarlar öncelikle .env dosyasından, yoksa varsayılan değerlerden okunur.

Kullanım:
    from app.config import get_settings

    settings = get_settings()
    print(settings.APP_NAME)

Ortam Değişkenleri:
    Tüm ayarlar .env dosyasından veya sistem ortam değişkenlerinden
    okunabilir. Örnek .env dosyası için .env.example'a bakın.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Uygulama yapılandırma sınıfı.

    Pydantic BaseSettings kullanarak .env dosyasından veya
    ortam değişkenlerinden otomatik değer okur.

    Attributes:
        APP_NAME: Uygulama adı
        DEBUG: Debug modu (True: geliştirme, False: production)
        SECRET_KEY: JWT ve session imzalama için gizli anahtar
    """

    # =========================================================================
    # GENEL UYGULAMA AYARLARI
    # =========================================================================
    APP_NAME: str = Field(default="Mami AI", description="Uygulama adı")
    DEBUG: bool = Field(default=True, description="Debug modu")

    # Sunucu Ayarları
    API_HOST: str = Field(default="0.0.0.0", description="API sunucu adresi")
    API_PORT: int = Field(default=8000, description="API sunucu portu")

    # Güvenlik - KRİTİK: Production'da mutlaka değiştirin!
    SECRET_KEY: str = Field(
        default="super-secret-dev-key-change-this", description="Oturum ve JWT imzalama için gizli anahtar"
    )

    # =========================================================================
    # ORCHESTRATOR AYARLARI (v4.2)
    # =========================================================================
    ORCH_ENABLED: bool = Field(default=True, description="Orchestrator Gateway aktif mi?")
    ORCH_PRODUCTION_ENABLED: bool = Field(default=True, description="Orchestrator Üretim Modu")
    ORCH_LLM_DRY_RUN: bool = Field(default=False, description="LLM Dry Run")
    ORCH_RAG_DRY_RUN: bool = Field(default=False, description="RAG Dry Run")
    ORCH_STREAMING_ENABLED: bool = Field(default=False, description="Orchestrator Streaming")
    ORCH_ROLLOUT_PERCENT: int = Field(default=100, description="Rollout Yüzdesi")
    ORCH_ROLLOUT_ALLOWLIST: str = Field(default="", description="İzinli Kullanıcılar (CSV)")
    ORCH_TOOLS_ENABLED: bool = Field(default=True, description="Araç Kullanımı") # ENABLED BY DEFAULT
    ORCH_TOOLS_DRY_RUN: bool = Field(default=False, description="Araç Isınma Turu") # DISABLED DRY RUN
    ORCH_MEMORY_ENABLED: bool = Field(default=True, description="Hafıza Erişimi") # ENABLED BY DEFAULT
    ORCH_MEMORY_DRY_RUN: bool = Field(default=False, description="Hafıza Isınma Turu") # DISABLED DRY RUN

    # =========================================================================
    # VERİTABANI AYARLARI
    # =========================================================================
    DATABASE_URL: str | None = Field(
        default=None, description="Veritabanı bağlantı URL'si. Boşsa sqlite:///data/app.db kullanılır"
    )
    CHROMA_PERSIST_DIR: str = Field(default="data/chroma_db", description="ChromaDB vektör veritabanı dizini")

    # =========================================================================
    # REDIS AYARLARI (Working Memory - Blueprint v1 Section 8)
    # =========================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/2",
        description="Redis bağlantı URL'si. DB 2 Working Memory için ayrılmış (DB 0-1 Celery)"
    )
    ORCH_WORKING_MEMORY_ENABLED: bool = Field(
        default=True, description="Working Memory (Redis) aktif mi? - ENABLED FOR TESTING"
    )
    ORCH_WORKING_MEMORY_TTL: int = Field(
        default=172800, description="Working Memory TTL (saniye). Varsayılan: 48 saat"
    )
    ORCH_WORKING_MEMORY_MAX_MESSAGES: int = Field(
        default=10, description="Session'da tutulacak maksimum mesaj sayısı"
    )

    # =========================================================================
    # GROQ API AYARLARI (Ana LLM Sağlayıcısı)
    # =========================================================================
    # Ana ve yedek API anahtarları - Rate limit durumunda otomatik geçiş
    GROQ_API_KEY: str = Field(default="", description="Groq API ana anahtar")
    GROQ_API_KEY_BACKUP: str = Field(default="", description="Groq API yedek anahtar 1")
    GROQ_API_KEY_3: str = Field(default="", description="Groq API yedek anahtar 2")
    GROQ_API_KEY_4: str = Field(default="", description="Groq API yedek anahtar 3")

    # Model Stratejisi: Farklı görevler için optimize edilmiş modeller
    # NOT: llama-3.1-70b-versatile Groq tarafından kullanımdan kaldırıldı (Aralık 2024)
    GROQ_DECIDER_MODEL: str = Field(
        default="llama-3.3-70b-versatile", description="Router/Decider için kullanılan model"
    )
    GROQ_ANSWER_MODEL: str = Field(
        default="llama-3.3-70b-versatile", description="Ana cevap üretimi için model (yüksek kalite)"
    )
    GROQ_FAST_MODEL: str = Field(
        default="llama-3.1-8b-instant", description="Hızlı işlemler için model (semantic, özet)"
    )
    GROQ_SEMANTIC_MODEL: str = Field(default="llama-3.1-8b-instant", description="Semantic classifier için model")

    # =========================================================================
    # İNTERNET ARAMA AYARLARI
    # =========================================================================
    # Bing Search API
    BING_API_KEY: str = Field(default="", description="Bing Search API anahtarı")
    BING_ENDPOINT: str = Field(
        default="https://api.bing.microsoft.com/v7.0/search", description="Bing Search API endpoint"
    )

    # Serper (Google Search) API
    SERPER_API_KEY: str = Field(default="", description="Serper (Google) API anahtarı")
    SERPER_ENDPOINT: str = Field(default="https://google.serper.dev/search", description="Serper API endpoint")

    # =========================================================================
    # OLLAMA AYARLARI (Yerel LLM)
    # =========================================================================
    OLLAMA_BASE_URL: str = Field(default="http://127.0.0.1:11434", description="Ollama sunucu adresi")
    OLLAMA_LOCAL_MODEL: str = Field(default="josiefied-qwen3-8b", description="Ollama'da kullanılacak model adı")

    # =========================================================================
    # GÖRSEL ÜRETİM AYARLARI (Forge/Flux)
    # =========================================================================
    FORGE_BASE_URL: str = Field(default="http://127.0.0.1:7860", description="Forge/Stable Diffusion WebUI adresi")
    FORGE_TXT2IMG_PATH: str = Field(default="/sdapi/v1/txt2img", description="Text-to-image API endpoint")
    FORGE_TIMEOUT: int = Field(default=1200, description="Görsel üretim zaman aşımı (saniye)")

    # =========================================================================
    # FALLBACK STRATEJİSİ
    # =========================================================================
    # Model başarısız olursa (Circuit Breaker veya Timeout) sırayla denenecek modeller
    FALLBACK_CHAINS: dict[str, list[str]] = Field(
        default={
            "llama-3.3-70b-versatile": ["llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
            "llama-3.1-8b-instant": ["gemma2-9b-it", "mixtral-8x7b-32768"],
            "default": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        },
        description="Model fallback zincirleri"
    )

    # Flux checkpoint seçimleri
    FLUX_STANDARD_CHECKPOINT: str = Field(
        default="flux1-dev-bnb-nf4-v2.safetensors", description="Standard (safe content) Flux checkpoint"
    )
    FLUX_NSFW_CHECKPOINT: str = Field(
        default="fluxedUpFluxNSFW_51FP8.safetensors", description="Uncensored (NSFW allowed) Flux checkpoint"
    )

    # Legacy - backward compatibility
    FORGE_FLUX_CHECKPOINT: str = Field(
        default="fluxedUpFluxNSFW_51FP8.safetensors",
        description="[DEPRECATED] Kullanılacak Flux model dosyası (fallback)",
    )

    # =========================================================================
    # CORS AYARLARI
    # =========================================================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000", description="İzin verilen origin'ler (virgülle ayrılmış)"
    )

    # =========================================================================
    # PYDANTIC YAPILANDIRMASI
    # =========================================================================
    class Config:
        """Pydantic model yapılandırması."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        # Extra alanları yoksay (geriye uyumluluk için)
        extra = "ignore"

    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    def get_cors_origins_list(self) -> list[str]:
        """
        CORS origin'lerini liste olarak döndürür.

        Returns:
            List[str]: İzin verilen origin URL'leri listesi
        """
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def get_groq_api_keys(self) -> list[str]:
        """
        Tüm geçerli Groq API anahtarlarını liste olarak döndürür.
        Rate limit durumunda sırayla denenmek üzere.

        Returns:
            List[str]: Boş olmayan API anahtarları listesi
        """
        keys = [
            self.GROQ_API_KEY,
            self.GROQ_API_KEY_BACKUP,
            self.GROQ_API_KEY_3,
            self.GROQ_API_KEY_4,
        ]
        return [k for k in keys if k]


@lru_cache
def get_settings() -> Settings:
    """
    Uygulama ayarlarını döndürür (Singleton pattern).

    lru_cache ile sarıldığından, ilk çağrıda Settings nesnesi
    oluşturulur ve sonraki çağrılarda aynı nesne döndürülür.

    Returns:
        Settings: Uygulama yapılandırma nesnesi

    Example:
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        Mami AI
    """
    return Settings()
