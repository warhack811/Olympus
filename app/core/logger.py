"""
Mami AI - Merkezi Loglama Sistemi
=================================

Bu modül, uygulama genelinde tutarlı loglama sağlar.

Özellikler:
    - Console çıktısı (geliştirme için)
    - Dönen log dosyası (production için)
    - Maksimum 5MB dosya boyutu, 3 yedek dosya
    - JSON formatında yapılandırılmış logging
    - Request ID tracking (correlation ID)
    - Tutarlı format: timestamp - modül - seviye - mesaj

Kullanım:
    from app.core.logger import get_logger, set_request_id, log_request, log_response, log_error

    logger = get_logger(__name__)
    set_request_id("req-123")
    logger.info("İşlem başladı")
    log_request(logger, "GET", "/api/users", user="admin")
    log_response(logger, 200, 45.5)
    log_error(logger, "Hata oluştu", exc_info=True)

Log Dosyası:
    logs/mami.log (ve mami.log.1, mami.log.2, mami.log.3 yedekleri)

Log Seviyeleri:
    - DEBUG: Detaylı debug bilgisi
    - INFO: Genel bilgi mesajları
    - WARNING: Uyarılar
    - ERROR: Hata mesajları
    - CRITICAL: Kritik hatalar
"""

import logging
import json
import traceback
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional, Dict
import asyncio
from queue import Queue
from threading import Thread

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Log dizini
LOG_DIR = Path("logs")

# Dosya boyutu limitleri
MAX_LOG_FILE_SIZE = 5_000_000  # 5 MB
BACKUP_COUNT = 3  # 3 yedek dosya (toplam ~20 MB)

# Log formatı
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Request ID storage (thread-local)
_request_id_storage = threading.local()

# =============================================================================
# REQUEST ID YÖNETİMİ
# =============================================================================


def set_request_id(request_id: str) -> None:
    """
    Geçerli thread için request ID'sini ayarla.
    
    Args:
        request_id: Correlation ID (örn: "req-123-abc")
    """
    _request_id_storage.request_id = request_id


def get_request_id() -> Optional[str]:
    """
    Geçerli thread için request ID'sini al.
    
    Returns:
        Request ID veya None
    """
    return getattr(_request_id_storage, "request_id", None)


def clear_request_id() -> None:
    """Geçerli thread için request ID'sini temizle."""
    if hasattr(_request_id_storage, "request_id"):
        delattr(_request_id_storage, "request_id")


# =============================================================================
# JSON FORMATTER
# =============================================================================


class JSONFormatter(logging.Formatter):
    """
    JSON formatında yapılandırılmış log mesajları üreten formatter.
    
    Her log mesajı şu alanları içerir:
    - timestamp: ISO 8601 formatında zaman
    - level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - module: Logger adı (örn: app.core.logger)
    - message: Log mesajı
    - request_id: Correlation ID (varsa)
    - context: Ek context bilgisi (varsa)
    - exception: Stack trace (hata varsa)
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        LogRecord'u JSON formatına dönüştür.
        
        Args:
            record: Logging LogRecord nesnesi
            
        Returns:
            JSON formatında log mesajı
        """
        # Temel log bilgileri
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Request ID ekle (varsa)
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        # Extra context ekle (varsa)
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        # Exception bilgisi ekle (varsa)
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # JSON olarak döndür
        try:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        except Exception as e:
            # JSON serialization hatası durumunda fallback
            log_data["message"] = f"JSON serialization error: {e} | Original: {record.getMessage()}"
            return json.dumps(log_data, ensure_ascii=False, default=str)

# =============================================================================
# LOGGER FONKSİYONLARI
# =============================================================================


def _ensure_log_directory() -> None:
    """Log dizininin var olduğundan emin ol."""
    LOG_DIR.mkdir(exist_ok=True)


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    Windows [WinError 32] PermissionError hatasını engelleyen handler.
    Çoklu işlem (multiprocessing) veya uvicorn reloader çalışırken,
    log dosyası döndürme (rotation) sırasında oluşan dosya kilitleme
    hatalarını yakalar ve uygulamanın çökmesini engeller.
    """

    def doRollover(self):
        """Dosya döndürme işlemini güvenli bir şekilde yap."""
        try:
            super().doRollover()
        except (PermissionError, OSError):
            # Windows dosya kilitlenme hatası - yoksay ve devam et
            # Bu durumda dosya boyutu limiti aşılabilir ama uygulama çökmez
            pass
        except Exception:
            # Diğer hataları da yut ki app çalışmaya devam etsin
            pass

    def emit(self, record):
        """Log mesajını emit et, yazma hatalarını yakala."""
        try:
            super().emit(record)
        except (PermissionError, OSError):
            # Yazma hatası olursa (nadiren) yoksay
            pass


class FlushStreamHandler(logging.StreamHandler):
    """
    Her log mesajından sonra stdout/stderr'i flush eden handler.
    Windows'ta uvicorn --reload ile çalışırken logların anında görünmesini sağlar.
    """

    def emit(self, record):
        """Log mesajını emit et ve flush et."""
        try:
            super().emit(record)
            self.flush()  # Her mesajdan sonra flush
        except Exception:
            self.handleError(record)


# =============================================================================
# ELASTICSEARCH HANDLER
# =============================================================================


class ElasticsearchHandler(logging.Handler):
    """
    Log mesajlarını Elasticsearch'e gönderen handler.
    
    Batch işleme ve async gönderim için queue kullanır.
    """

    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        """
        Handler'ı initialize et.
        
        Args:
            batch_size: Batch'te kaç log toplanacak
            batch_timeout: Batch timeout (saniye)
        """
        super().__init__()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.queue: Queue = Queue()
        self.batch: list = []
        self.last_flush_time = 0
        
        # Background thread'i başlat
        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Log mesajını queue'ya ekle.
        
        Args:
            record: LogRecord nesnesi
        """
        try:
            # LogRecord'u JSON'a dönüştür
            log_data = self._format_record(record)
            self.queue.put(log_data)
        except Exception:
            self.handleError(record)
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """LogRecord'u dict'e dönüştür."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        # Request ID ekle (varsa)
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        # Extra context ekle (varsa)
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context
        
        # Exception bilgisi ekle (varsa)
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        return log_data
    
    def _worker(self) -> None:
        """Background worker thread - log'ları batch halinde gönder."""
        import time
        from app.core.elasticsearch_client import get_elasticsearch_client, send_logs_batch
        
        while True:
            try:
                # Queue'dan log al (timeout ile)
                try:
                    log_data = self.queue.get(timeout=self.batch_timeout)
                    self.batch.append(log_data)
                except:
                    # Timeout - batch'i gönder
                    if self.batch:
                        self._flush_batch()
                    continue
                
                # Batch dolu mu kontrol et
                if len(self.batch) >= self.batch_size:
                    self._flush_batch()
                
                # Timeout kontrol et
                current_time = time.time()
                if current_time - self.last_flush_time >= self.batch_timeout and self.batch:
                    self._flush_batch()
            
            except Exception as e:
                # Worker thread'de hata - devam et
                pass
    
    def _flush_batch(self) -> None:
        """Batch'i Elasticsearch'e gönder."""
        if not self.batch:
            return
        
        try:
            from app.core.elasticsearch_client import get_elasticsearch_client, send_logs_batch
            
            es_client = get_elasticsearch_client()
            send_logs_batch(es_client, self.batch)
            self.batch = []
            self.last_flush_time = __import__("time").time()
        except Exception:
            # Elasticsearch'e gönderim başarısız - batch'i temizle
            self.batch = []
    
    def flush(self) -> None:
        """Kalan batch'i gönder."""
        self._flush_batch()
        super().flush()


# =============================================================================
# DATETIME IMPORT
# =============================================================================

from datetime import datetime


def get_logger(
    name: str = "mami",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_to_elasticsearch: bool = False,
    use_json: bool = True,
) -> logging.Logger:
    """
    Yapılandırılmış logger döndürür.

    Her modül için ayrı bir logger oluşturulur, ancak tüm loglar
    aynı dosyaya ve console'a yazılır. Handler'ların tekrar
    eklenmesini önlemek için kontrol yapılır.

    Args:
        name: Logger adı (genellikle __name__ kullanılır)
        level: Log seviyesi (varsayılan: INFO)
        log_to_file: Dosyaya log yaz (varsayılan: True)
        log_to_console: Console'a log yaz (varsayılan: True)
        log_to_elasticsearch: Elasticsearch'e log gönder (varsayılan: False)
        use_json: JSON formatı kullan (varsayılan: True)

    Returns:
        logging.Logger: Yapılandırılmış logger nesnesi

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Uygulama başlatıldı")
        {"timestamp": "2024-01-01 12:00:00", "level": "INFO", "module": "app.main", "message": "Uygulama başlatıldı"}

        >>> logger.error("Hata!", exc_info=True)  # Stack trace ile
    """
    logger = logging.getLogger(name)

    # Handler tekrar eklemeyi önle, ama eksik handler varsa ekle
    has_console = False
    has_file = False
    has_elasticsearch = False
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler):
            has_console = True
        if isinstance(h, RotatingFileHandler):
            try:
                if Path(getattr(h, "baseFilename", "")) == (LOG_DIR / "mami.log"):
                    has_file = True
            except Exception:
                pass
        if isinstance(h, ElasticsearchHandler):
            has_elasticsearch = True

    logger.setLevel(level)

    # Formatter oluştur (JSON veya text)
    if use_json:
        formatter = JSONFormatter(datefmt=DATE_FORMAT)
    else:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console Handler (with immediate flush for Windows compatibility)
    if log_to_console and not has_console:
        console_handler = FlushStreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File Handler (Safe Rotating)
    if log_to_file and not has_file:
        _ensure_log_directory()
        log_file = LOG_DIR / "mami.log"

        # Standart RotatingFileHandler yerine SafeRotatingFileHandler kullan
        file_handler = SafeRotatingFileHandler(
            filename=log_file, maxBytes=MAX_LOG_FILE_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Elasticsearch Handler
    if log_to_elasticsearch and not has_elasticsearch:
        try:
            es_handler = ElasticsearchHandler()
            es_handler.setLevel(level)
            logger.addHandler(es_handler)
        except Exception as e:
            # Elasticsearch handler'ı eklenemezse yoksay
            pass

    return logger


def configure_root_logger(level: int = logging.INFO) -> None:
    """
    Root logger'ı yapılandırır.

    Tüm kütüphanelerin loglarını kontrol etmek için kullanılır.
    Genellikle main.py'de bir kere çağrılır.

    Args:
        level: Log seviyesi
    """
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)


# =============================================================================
# LOG YARDIMCI FONKSİYONLARI (STRUCTURED LOGGING)
# =============================================================================


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    HTTP isteğini yapılandırılmış şekilde loglar.

    Args:
        logger: Logger nesnesi
        method: HTTP metodu (GET, POST vb.)
        path: İstek yolu
        user: Kullanıcı adı (varsa)
        headers: İstek header'ları (varsa)
        query_params: Query parametreleri (varsa)
        extra: Ek bilgiler (varsa)
    """
    context = {
        "type": "request",
        "method": method,
        "path": path,
    }

    if user:
        context["user"] = user

    if headers:
        context["headers"] = headers

    if query_params:
        context["query_params"] = query_params

    if extra:
        context.update(extra)

    # Context'i LogRecord'a ekle
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(request)",
        0,
        f"[REQUEST] {method} {path}",
        (),
        None,
    )
    record.context = context
    logger.handle(record)


def log_response(
    logger: logging.Logger,
    status_code: int,
    duration_ms: float,
    user: Optional[str] = None,
    path: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    HTTP yanıtını yapılandırılmış şekilde loglar.

    Args:
        logger: Logger nesnesi
        status_code: HTTP durum kodu
        duration_ms: İşlem süresi (milisaniye)
        user: Kullanıcı adı (varsa)
        path: İstek yolu (varsa)
        extra: Ek bilgiler (varsa)
    """
    context = {
        "type": "response",
        "status_code": status_code,
        "duration_ms": duration_ms,
    }

    if user:
        context["user"] = user

    if path:
        context["path"] = path

    if extra:
        context.update(extra)

    # Context'i LogRecord'a ekle
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(response)",
        0,
        f"[RESPONSE] status={status_code} duration={duration_ms:.2f}ms",
        (),
        None,
    )
    record.context = context
    logger.handle(record)


def log_error(
    logger: logging.Logger,
    message: str,
    error_type: Optional[str] = None,
    user: Optional[str] = None,
    path: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """
    Hatayı yapılandırılmış şekilde loglar.

    Args:
        logger: Logger nesnesi
        message: Hata mesajı
        error_type: Hata türü (varsa)
        user: Kullanıcı adı (varsa)
        path: İstek yolu (varsa)
        extra: Ek bilgiler (varsa)
        exc_info: Exception bilgisini ekle (varsa)
    """
    context = {
        "type": "error",
        "message": message,
    }

    if error_type:
        context["error_type"] = error_type

    if user:
        context["user"] = user

    if path:
        context["path"] = path

    if extra:
        context.update(extra)

    # Context'i LogRecord'a ekle
    record = logger.makeRecord(
        logger.name,
        logging.ERROR,
        "(error)",
        0,
        f"[ERROR] {message}",
        (),
        None,
    )
    record.context = context
    
    # Exception bilgisini ekle (varsa)
    if exc_info:
        import sys
        record.exc_info = sys.exc_info()
    
    logger.handle(record)


def log_event(
    logger: logging.Logger,
    event_type: str,
    event_name: str,
    user: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Sistem olayını yapılandırılmış şekilde loglar.

    Args:
        logger: Logger nesnesi
        event_type: Olay türü (system, user, api vb.)
        event_name: Olay adı (startup, shutdown, login vb.)
        user: Kullanıcı adı (varsa)
        data: Olay verisi (varsa)
        extra: Ek bilgiler (varsa)
    """
    context = {
        "type": "event",
        "event_type": event_type,
        "event_name": event_name,
    }

    if user:
        context["user"] = user

    if data:
        context["data"] = data

    if extra:
        context.update(extra)

    # Context'i LogRecord'a ekle
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(event)",
        0,
        f"[EVENT] {event_type}.{event_name}",
        (),
        None,
    )
    record.context = context
    logger.handle(record)
