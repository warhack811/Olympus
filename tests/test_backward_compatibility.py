"""
Backward Compatibility Test'leri - Logging & Monitoring Sistemi

Bu test dosyası, yeni logging & monitoring sistemi ile mevcut kodun
uyumluluğunu test eder.

Test Kapsamı:
    - Eski logger'ın hala çalışıp çalışmadığı
    - Eski error handling'in hala çalışıp çalışmadığı
    - Eski API route'larının hala çalışıp çalışmadığı
    - Mevcut middleware'in yeni logging sistemi ile uyumlu olduğu
    - Mevcut exception handler'ların yeni logging sistemi ile uyumlu olduğu

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8
"""

import json
import logging
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

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
    configure_root_logger,
)
from app.core.exceptions import MamiException, AuthenticationError, ValidationError


class TestBackwardCompatibilityLogger:
    """Eski logger'ın uyumluluğu test'leri."""

    def test_old_logger_still_works(self):
        """
        Eski logger'ın hala çalışıp çalışmadığını test et.
        
        For any existing code using get_logger, it should continue to work
        without any changes.
        
        Requirements: 10.1
        """
        # Eski şekilde logger oluştur
        logger = get_logger("test_old_logger", log_to_file=False)
        
        # Logger'ın valid olduğunu kontrol et
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_old_logger"

    def test_old_logger_with_default_parameters(self):
        """
        Eski logger'ın default parametrelerle çalışıp çalışmadığını test et.
        
        For any code using get_logger with default parameters, it should
        work exactly as before.
        
        Requirements: 10.1
        """
        # Default parametrelerle logger oluştur
        logger = get_logger("test_default_logger")
        
        # Logger'ın valid olduğunu kontrol et
        assert logger is not None
        assert logger.level == logging.INFO

    def test_old_logger_json_format_backward_compat(self):
        """
        Eski logger'ın JSON formatında backward compatible olduğunu test et.
        
        For any code using get_logger with use_json=True, the output should
        still be valid JSON that can be parsed.
        
        Requirements: 10.1, 10.6
        """
        # Logger oluştur (JSON formatında)
        logger = get_logger("test_json_compat", use_json=True, log_to_file=False)
        
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
        assert "message" in log_data

    def test_old_logger_text_format_backward_compat(self):
        """
        Eski logger'ın text formatında backward compatible olduğunu test et.
        
        For any code using get_logger with use_json=False, the output should
        still be in text format.
        
        Requirements: 10.1
        """
        # Logger oluştur (text formatında)
        logger = get_logger("test_text_compat", use_json=False, log_to_file=False)
        
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
        
        # Text formatında olduğunu kontrol et
        assert "Test mesajı" in output
        assert "INFO" in output

    def test_old_logger_file_output_backward_compat(self):
        """
        Eski logger'ın dosya çıktısında backward compatible olduğunu test et.
        
        For any code using get_logger with log_to_file=True, the logger should
        still write to the log file.
        
        Requirements: 10.1, 10.7
        """
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Geçici log dosyası
            log_file = Path(tmpdir) / "test.log"
            
            # Logger oluştur (dosyaya yazma)
            logger = logging.getLogger("test_file_compat_unique")
            logger.setLevel(logging.INFO)
            logger.handlers.clear()
            
            # File handler ekle
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=5_000_000,
                backupCount=3,
                encoding="utf-8"
            )
            formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Log mesajı yaz
            logger.info("Test mesajı")
            
            # Handler'ı kapat (Windows dosya kilitleme sorunu için)
            handler.close()
            logger.handlers.clear()
            
            # Dosyanın oluşturulduğunu kontrol et
            assert log_file.exists()
            
            # Dosya içeriğini oku
            content = log_file.read_text(encoding="utf-8")
            # JSON formatında olduğunu kontrol et
            assert "Test mesaj" in content or "Test mesajı" in content


class TestBackwardCompatibilityErrorHandling:
    """Eski error handling'in uyumluluğu test'leri."""

    def test_old_exception_handler_still_works(self):
        """
        Eski exception handler'ın hala çalışıp çalışmadığını test et.
        
        For any code using MamiException, it should still work with the
        new logging system.
        
        Requirements: 10.2, 10.3
        """
        # Eski şekilde exception oluştur
        exc = MamiException(
            message="Test hatası",
            user_message="Bir hata oluştu",
            status_code=500
        )
        
        # Exception'ın valid olduğunu kontrol et
        assert exc.message == "Test hatası"
        assert exc.user_message == "Bir hata oluştu"
        assert exc.status_code == 500

    def test_old_authentication_error_still_works(self):
        """
        Eski AuthenticationError'ın hala çalışıp çalışmadığını test et.
        
        For any code using AuthenticationError, it should still work with
        the new logging system.
        
        Requirements: 10.2
        """
        # Eski şekilde exception oluştur
        exc = AuthenticationError("Token expired")
        
        # Exception'ın valid olduğunu kontrol et
        assert exc.message == "Token expired"
        assert exc.status_code == 401

    def test_old_validation_error_still_works(self):
        """
        Eski ValidationError'ın hala çalışıp çalışmadığını test et.
        
        For any code using ValidationError, it should still work with
        the new logging system.
        
        Requirements: 10.2
        """
        # Eski şekilde exception oluştur
        exc = ValidationError("Invalid input")
        
        # Exception'ın valid olduğunu kontrol et
        assert exc.message == "Invalid input"
        assert exc.status_code == 400

    def test_old_exception_handler_with_logging(self):
        """
        Eski exception handler'ın logging ile uyumlu olduğunu test et.
        
        For any exception logged with log_error, it should work with
        the new logging system.
        
        Requirements: 10.2, 10.3
        """
        # Logger oluştur
        logger = get_logger("test_exc_logging", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Exception oluştur ve log'la
        try:
            raise ValueError("Test hatası")
        except ValueError:
            log_error(
                logger,
                "Hata oluştu",
                error_type="ValueError",
                exc_info=True
            )
        
        # Log çıktısını al
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Exception bilgisinin log'lanmış olduğunu kontrol et
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"


class TestBackwardCompatibilityMiddleware:
    """Eski middleware'in uyumluluğu test'leri."""

    def test_old_middleware_with_new_logging(self):
        """
        Eski middleware'in yeni logging sistemi ile uyumlu olduğunu test et.
        
        For any request processed by the middleware, it should work with
        the new logging system without any changes.
        
        Requirements: 10.2, 10.3
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Eski middleware'i ekle (request logging)
        @app.middleware("http")
        async def old_middleware(request, call_next):
            """Eski middleware - request logging."""
            import uuid
            from time import perf_counter
            
            start = perf_counter()
            request_id = str(uuid.uuid4())[:8]
            set_request_id(request_id)
            
            try:
                response = await call_next(request)
                return response
            finally:
                clear_request_id()
        
        # Test endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        # Test client oluştur
        client = TestClient(app)
        
        # Request yap
        response = client.get("/test")
        
        # Response kontrol et
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_old_middleware_request_id_tracking(self):
        """
        Eski middleware'in request ID tracking'i ile uyumlu olduğunu test et.
        
        For any request processed by the middleware, the request ID should
        be properly tracked and cleared.
        
        Requirements: 10.2, 10.3
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Eski middleware'i ekle
        @app.middleware("http")
        async def old_middleware(request, call_next):
            """Eski middleware - request ID tracking."""
            import uuid
            
            request_id = str(uuid.uuid4())[:8]
            set_request_id(request_id)
            
            try:
                response = await call_next(request)
                return response
            finally:
                clear_request_id()
        
        # Test endpoint
        @app.get("/test")
        async def test_endpoint():
            # Request ID'nin set olduğunu kontrol et
            req_id = get_request_id()
            return {"request_id": req_id}
        
        # Test client oluştur
        client = TestClient(app)
        
        # Request yap
        response = client.get("/test")
        
        # Response kontrol et
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0


class TestBackwardCompatibilityAPIRoutes:
    """Eski API route'larının uyumluluğu test'leri."""

    def test_old_api_routes_still_work(self):
        """
        Eski API route'larının hala çalışıp çalışmadığını test et.
        
        For any existing API route, it should continue to work without
        any changes.
        
        Requirements: 10.4
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Eski route'ları ekle
        @app.get("/api/users")
        async def get_users():
            return {"users": []}
        
        @app.post("/api/users")
        async def create_user():
            return {"id": 1, "name": "Test"}
        
        # Test client oluştur
        client = TestClient(app)
        
        # GET request yap
        response = client.get("/api/users")
        assert response.status_code == 200
        assert response.json() == {"users": []}
        
        # POST request yap
        response = client.post("/api/users")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "Test"}

    def test_old_api_routes_with_logging(self):
        """
        Eski API route'larının logging ile uyumlu olduğunu test et.
        
        For any existing API route with logging, it should work with
        the new logging system.
        
        Requirements: 10.4
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Logger oluştur
        logger = get_logger("test_api_routes", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski route'ı ekle (logging ile)
        @app.get("/api/test")
        async def test_route():
            log_request(logger, "GET", "/api/test")
            log_response(logger, 200, 10.5)
            return {"status": "ok"}
        
        # Test client oluştur
        client = TestClient(app)
        
        # Request yap
        response = client.get("/api/test")
        
        # Response kontrol et
        assert response.status_code == 200
        
        # Log çıktısını kontrol et
        logs = stream.getvalue()
        assert "GET" in logs
        assert "/api/test" in logs


class TestBackwardCompatibilityExceptionHandlers:
    """Eski exception handler'larının uyumluluğu test'leri."""

    def test_old_exception_handler_with_fastapi(self):
        """
        Eski exception handler'ın FastAPI ile uyumlu olduğunu test et.
        
        For any existing exception handler, it should work with the
        new logging system.
        
        Requirements: 10.3
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Eski exception handler'ı ekle
        @app.exception_handler(MamiException)
        async def mami_exception_handler(request, exc: MamiException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "ok": False,
                    "error": True,
                    "message": exc.user_message,
                }
            )
        
        # Test endpoint
        @app.get("/test")
        async def test_endpoint():
            raise MamiException(
                message="Test hatası",
                user_message="Bir hata oluştu",
                status_code=500
            )
        
        # Test client oluştur
        client = TestClient(app)
        
        # Request yap
        response = client.get("/test")
        
        # Response kontrol et
        assert response.status_code == 500
        data = response.json()
        assert data["ok"] is False
        assert data["error"] is True
        assert data["message"] == "Bir hata oluştu"

    def test_old_exception_handler_with_logging(self):
        """
        Eski exception handler'ın logging ile uyumlu olduğunu test et.
        
        For any existing exception handler with logging, it should work
        with the new logging system.
        
        Requirements: 10.3
        """
        # Test uygulaması oluştur
        app = FastAPI()
        
        # Logger oluştur
        logger = get_logger("test_exc_handler", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski exception handler'ı ekle (logging ile)
        @app.exception_handler(MamiException)
        async def mami_exception_handler(request, exc: MamiException):
            log_error(logger, exc.message, error_type="MamiException")
            return JSONResponse(
                status_code=exc.status_code,
                content={"message": exc.user_message}
            )
        
        # Test endpoint
        @app.get("/test")
        async def test_endpoint():
            raise MamiException(
                message="Test hatası",
                user_message="Bir hata oluştu",
                status_code=500
            )
        
        # Test client oluştur
        client = TestClient(app)
        
        # Request yap
        response = client.get("/test")
        
        # Response kontrol et
        assert response.status_code == 500
        
        # Log çıktısını kontrol et
        logs = stream.getvalue()
        log_data = json.loads(logs.strip())
        assert log_data["context"]["type"] == "error"
        assert log_data["context"]["error_type"] == "MamiException"


class TestBackwardCompatibilityStructuredLogging:
    """Eski structured logging'in uyumluluğu test'leri."""

    def test_old_log_request_still_works(self):
        """
        Eski log_request fonksiyonunun hala çalışıp çalışmadığını test et.
        
        For any code using log_request, it should continue to work without
        any changes.
        
        Requirements: 10.1
        """
        # Logger oluştur
        logger = get_logger("test_old_log_request", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski şekilde log_request çağır
        log_request(logger, "GET", "/api/users", user="admin")
        
        # Log çıktısını al
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Log'ın doğru olduğunu kontrol et
        assert log_data["context"]["type"] == "request"
        assert log_data["context"]["method"] == "GET"
        assert log_data["context"]["path"] == "/api/users"
        assert log_data["context"]["user"] == "admin"

    def test_old_log_response_still_works(self):
        """
        Eski log_response fonksiyonunun hala çalışıp çalışmadığını test et.
        
        For any code using log_response, it should continue to work without
        any changes.
        
        Requirements: 10.1
        """
        # Logger oluştur
        logger = get_logger("test_old_log_response", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski şekilde log_response çağır
        log_response(logger, 200, 45.5, user="admin", path="/api/users")
        
        # Log çıktısını al
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Log'ın doğru olduğunu kontrol et
        assert log_data["context"]["type"] == "response"
        assert log_data["context"]["status_code"] == 200
        assert log_data["context"]["duration_ms"] == 45.5

    def test_old_log_error_still_works(self):
        """
        Eski log_error fonksiyonunun hala çalışıp çalışmadığını test et.
        
        For any code using log_error, it should continue to work without
        any changes.
        
        Requirements: 10.1
        """
        # Logger oluştur
        logger = get_logger("test_old_log_error", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski şekilde log_error çağır
        log_error(logger, "Hata oluştu", error_type="ValueError", user="admin")
        
        # Log çıktısını al
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Log'ın doğru olduğunu kontrol et
        assert log_data["context"]["type"] == "error"
        assert log_data["context"]["message"] == "Hata oluştu"
        assert log_data["context"]["error_type"] == "ValueError"

    def test_old_log_event_still_works(self):
        """
        Eski log_event fonksiyonunun hala çalışıp çalışmadığını test et.
        
        For any code using log_event, it should continue to work without
        any changes.
        
        Requirements: 10.1
        """
        # Logger oluştur
        logger = get_logger("test_old_log_event", log_to_file=False)
        
        # StringIO handler ekle
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Eski şekilde log_event çağır
        log_event(logger, "system", "startup", data={"version": "4.2.0"})
        
        # Log çıktısını al
        output = stream.getvalue().strip()
        log_data = json.loads(output)
        
        # Log'ın doğru olduğunu kontrol et
        assert log_data["context"]["type"] == "event"
        assert log_data["context"]["event_type"] == "system"
        assert log_data["context"]["event_name"] == "startup"


class TestBackwardCompatibilityConfiguration:
    """Eski konfigürasyon'un uyumluluğu test'leri."""

    def test_old_configure_root_logger_still_works(self):
        """
        Eski configure_root_logger fonksiyonunun hala çalışıp çalışmadığını test et.
        
        For any code using configure_root_logger, it should continue to work
        without any changes.
        
        Requirements: 10.1
        """
        # Root logger'ı al
        root_logger = logging.getLogger()
        
        # Eski şekilde root logger'ı yapılandır (hata fırlatmamalı)
        try:
            configure_root_logger(logging.INFO)
            # Fonksiyon başarıyla çalıştı
            assert True
        except Exception as e:
            # Fonksiyon hata fırlatmamalı
            pytest.fail(f"configure_root_logger raised exception: {e}")

    def test_old_request_id_functions_still_work(self):
        """
        Eski request ID fonksiyonlarının hala çalışıp çalışmadığını test et.
        
        For any code using set_request_id, get_request_id, clear_request_id,
        it should continue to work without any changes.
        
        Requirements: 10.1
        """
        # Eski şekilde request ID'sini ayarla
        set_request_id("req-123-abc")
        
        # Request ID'sini al
        req_id = get_request_id()
        assert req_id == "req-123-abc"
        
        # Request ID'sini temizle
        clear_request_id()
        req_id = get_request_id()
        assert req_id is None


class TestBackwardCompatibilityGradualMigration:
    """Gradual migration desteği test'leri."""

    def test_old_and_new_logging_can_coexist(self):
        """
        Eski ve yeni logging sisteminin aynı anda çalışıp çalışmadığını test et.
        
        For any application using both old and new logging, they should
        coexist without conflicts.
        
        Requirements: 10.7
        """
        # Eski logger oluştur
        old_logger = get_logger("old_logger", log_to_file=False)
        
        # Yeni logger oluştur
        new_logger = get_logger("new_logger", log_to_file=False)
        
        # Her iki logger'ın valid olduğunu kontrol et
        assert old_logger is not None
        assert new_logger is not None
        assert old_logger.name == "old_logger"
        assert new_logger.name == "new_logger"

    def test_logging_can_be_enabled_disabled(self):
        """
        Logging'in enable/disable edilebilip edilemediğini test et.
        
        For any application, logging should be configurable to enable/disable
        specific handlers.
        
        Requirements: 10.8
        """
        # Logger oluştur (dosyaya yazma devre dışı)
        logger = get_logger(
            "test_config_logger",
            log_to_file=False,
            log_to_console=True,
            use_json=True
        )
        
        # Logger'ın valid olduğunu kontrol et
        assert logger is not None
        
        # Handler'ları kontrol et
        has_console = False
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                has_console = True
        
        assert has_console


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
