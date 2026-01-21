"""
JSON Logger ve Structured Logging Test'leri

Bu test dosyası, app/core/logger.py modülünün JSON formatter ve
structured logging helper fonksiyonlarını test eder.

Test Kapsamı:
    - JSON formatter'ın doğru format üretip üretmediği
    - Structured logging helper'larının doğru çalışıp çalışmadığı
    - Request ID tracking'in doğru çalışıp çalışmadığı
    - Exception handling'in doğru çalışıp çalışmadığı
"""

import json
import logging
import pytest
from pathlib import Path
from io import StringIO

from app.core.logger import (
    get_logger,
    set_request_id,
    get_request_id,
    clear_request_id,
    log_request,
    log_response,
    log_error,
    log_event,
    JSONFormatter,
)


class TestJSONFormatter:
    """JSON Formatter test'leri."""

    def test_json_formatter_basic_structure(self):
        """
        JSON formatter'ın temel yapıyı doğru üretip üretmediğini test et.
        
        Property 1: Log Entry Yapısı
        Validates: Requirements 1.6
        
        For any log message, the JSON formatter should produce a valid JSON
        object containing timestamp, level, module, and message fields.
        """
        # Logger oluştur ve StringIO handler ekle
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)
        
        # Mevcut handler'ları temizle
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Log mesajı yaz
        logger.info("Test mesajı")
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Temel alanları kontrol et
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "module" in log_data
        assert "message" in log_data
        
        # Değerleri kontrol et
        assert log_data["level"] == "INFO"
        assert log_data["module"] == "test_logger"
        assert log_data["message"] == "Test mesajı"

    def test_json_formatter_with_request_id(self):
        """
        JSON formatter'ın request ID'sini doğru ekleyip eklemediğini test et.
        
        For any log message with a request ID set, the JSON formatter should
        include the request_id field in the output.
        """
        # Request ID ayarla
        set_request_id("req-123-abc")
        
        try:
            # Logger oluştur
            logger = logging.getLogger("test_logger_req_id")
            logger.setLevel(logging.INFO)
            logger.handlers.clear()
            
            # StringIO handler ekle
            stream = StringIO()
            handler = logging.StreamHandler(stream)
            formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Log mesajı yaz
            logger.info("Test mesajı")
            
            # Çıktıyı al ve JSON olarak parse et
            output = stream.getvalue().strip()
            log_data = json.loads(output)
            
            # Request ID'sini kontrol et
            assert "request_id" in log_data
            assert log_data["request_id"] == "req-123-abc"
        finally:
            clear_request_id()

    def test_json_formatter_with_context(self):
        """
        JSON formatter'ın context bilgisini doğru ekleyip eklemediğini test et.
        
        For any log message with context data, the JSON formatter should
        include the context field in the output.
        """
        # Logger oluştur
        logger = logging.getLogger("test_logger_context")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Context ile log mesajı yaz
        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            "(test)",
            0,
            "Test mesajı",
            (),
            None,
        )
        record.context = {"user": "admin", "action": "login"}
        logger.handle(record)
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Context'i kontrol et
        assert "context" in log_data
        assert log_data["context"]["user"] == "admin"
        assert log_data["context"]["action"] == "login"

    def test_json_formatter_with_exception(self):
        """
        JSON formatter'ın exception bilgisini doğru ekleyip eklemediğini test et.
        
        For any log message with exception info, the JSON formatter should
        include the exception field with type, message, and traceback.
        """
        # Logger oluştur
        logger = logging.getLogger("test_logger_exception")
        logger.setLevel(logging.ERROR)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Exception ile log mesajı yaz
        try:
            raise ValueError("Test hatası")
        except ValueError:
            logger.error("Hata oluştu", exc_info=True)
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Exception bilgisini kontrol et
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test hatası"
        assert "traceback" in log_data["exception"]


class TestRequestIDTracking:
    """Request ID tracking test'leri."""

    def test_set_and_get_request_id(self):
        """
        Request ID'sini ayarla ve al.
        
        For any request ID set, get_request_id should return the same value.
        """
        set_request_id("req-456-def")
        
        try:
            assert get_request_id() == "req-456-def"
        finally:
            clear_request_id()

    def test_clear_request_id(self):
        """
        Request ID'sini temizle.
        
        For any request ID that is cleared, get_request_id should return None.
        """
        set_request_id("req-789-ghi")
        clear_request_id()
        
        assert get_request_id() is None

    def test_request_id_thread_isolation(self):
        """
        Request ID'sinin thread'ler arasında izole olduğunu test et.
        
        For any request ID set in one thread, it should not affect other threads.
        """
        import threading
        
        set_request_id("main-thread-id")
        
        result = {}
        
        def thread_func():
            # Bu thread'de request ID ayarla
            set_request_id("worker-thread-id")
            result["worker"] = get_request_id()
        
        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()
        
        # Main thread'in request ID'si değişmemiş olmalı
        assert get_request_id() == "main-thread-id"
        # Worker thread'in request ID'si farklı olmalı
        assert result["worker"] == "worker-thread-id"
        
        clear_request_id()


class TestStructuredLoggingHelpers:
    """Structured logging helper fonksiyonları test'leri."""

    def test_log_request_structure(self):
        """
        log_request fonksiyonunun doğru yapıyı üretip üretmediğini test et.
        
        For any request logged with log_request, the output should contain
        type, method, and path in the context.
        """
        # Logger oluştur
        logger = logging.getLogger("test_log_request")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # log_request çağır
        log_request(logger, "GET", "/api/users", user="admin")
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Context'i kontrol et
        assert "context" in log_data
        assert log_data["context"]["type"] == "request"
        assert log_data["context"]["method"] == "GET"
        assert log_data["context"]["path"] == "/api/users"
        assert log_data["context"]["user"] == "admin"

    def test_log_response_structure(self):
        """
        log_response fonksiyonunun doğru yapıyı üretip üretmediğini test et.
        
        For any response logged with log_response, the output should contain
        type, status_code, and duration_ms in the context.
        """
        # Logger oluştur
        logger = logging.getLogger("test_log_response")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # log_response çağır
        log_response(logger, 200, 45.5, user="admin", path="/api/users")
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Context'i kontrol et
        assert "context" in log_data
        assert log_data["context"]["type"] == "response"
        assert log_data["context"]["status_code"] == 200
        assert log_data["context"]["duration_ms"] == 45.5
        assert log_data["context"]["user"] == "admin"
        assert log_data["context"]["path"] == "/api/users"

    def test_log_error_structure(self):
        """
        log_error fonksiyonunun doğru yapıyı üretip üretmediğini test et.
        
        For any error logged with log_error, the output should contain
        type, message, and error_type in the context.
        """
        # Logger oluştur
        logger = logging.getLogger("test_log_error")
        logger.setLevel(logging.ERROR)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # log_error çağır
        log_error(logger, "Veritabanı bağlantısı başarısız", error_type="DatabaseError", user="admin")
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Context'i kontrol et
        assert "context" in log_data
        assert log_data["context"]["type"] == "error"
        assert log_data["context"]["message"] == "Veritabanı bağlantısı başarısız"
        assert log_data["context"]["error_type"] == "DatabaseError"
        assert log_data["context"]["user"] == "admin"

    def test_log_event_structure(self):
        """
        log_event fonksiyonunun doğru yapıyı üretip üretmediğini test et.
        
        For any event logged with log_event, the output should contain
        type, event_type, and event_name in the context.
        """
        # Logger oluştur
        logger = logging.getLogger("test_log_event")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # log_event çağır
        log_event(logger, "system", "startup", data={"version": "4.2.0"})
        
        # Çıktıyı al ve JSON olarak parse et
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Context'i kontrol et
        assert "context" in log_data
        assert log_data["context"]["type"] == "event"
        assert log_data["context"]["event_type"] == "system"
        assert log_data["context"]["event_name"] == "startup"
        assert log_data["context"]["data"]["version"] == "4.2.0"


class TestGetLogger:
    """get_logger fonksiyonu test'leri."""

    def test_get_logger_with_json_format(self):
        """
        get_logger'ın JSON formatında logger döndürüp döndürmediğini test et.
        
        For any logger created with use_json=True, the output should be in JSON format.
        """
        # Geçici log dosyası için
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Logger oluştur (dosyaya yazma devre dışı)
            logger = get_logger("test_json_logger", use_json=True, log_to_file=False)
            
            # StringIO handler ekle
            stream = StringIO()
            handler = logging.StreamHandler(stream)
            
            # Mevcut formatter'ı al
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler):
                    formatter = h.formatter
                    break
            
            handler.setFormatter(formatter)
            logger.handlers.clear()
            logger.addHandler(handler)
            
            # Log mesajı yaz
            logger.info("Test mesajı")
            
            # Çıktıyı al ve JSON olarak parse et
            output = stream.getvalue().strip()
            log_data = json.loads(output)
            
            # JSON formatında olduğunu kontrol et
            assert isinstance(log_data, dict)
            assert "timestamp" in log_data
            assert "level" in log_data
            assert "module" in log_data
            assert "message" in log_data

    def test_get_logger_with_text_format(self):
        """
        get_logger'ın text formatında logger döndürüp döndürmediğini test et.
        
        For any logger created with use_json=False, the output should be in text format.
        """
        # Logger oluştur (dosyaya yazma devre dışı)
        logger = get_logger("test_text_logger", use_json=False, log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        # Mevcut formatter'ı al
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                formatter = h.formatter
                break
        
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Log mesajı yaz
        logger.info("Test mesajı")
        
        # Çıktıyı al
        output = stream.getvalue().strip()
        
        # Text formatında olduğunu kontrol et (JSON değil)
        try:
            json.loads(output)
            # JSON parse edildiyse, bu test başarısız
            assert False, "Output should not be JSON"
        except json.JSONDecodeError:
            # Beklenen davranış - JSON değil
            assert "Test mesajı" in output
            assert "INFO" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
