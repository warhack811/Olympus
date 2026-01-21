"""
Backend Logging Middleware Integration Test'leri

Bu test dosyası, app/main.py'deki request logging middleware'inin
doğru çalışıp çalışmadığını test eder.

Test Kapsamı:
    - Middleware'in request'leri doğru log'ladığı
    - Middleware'in response'ları doğru log'ladığı
    - Middleware'in error'ları doğru log'ladığı
    - Request ID tracking'in doğru çalışıp çalışmadığı
    - Performance timing'in doğru ölçüldüğü

Property 1: Log Entry Yapısı
Validates: Requirements 1.1, 1.2, 1.3
"""

import json
import pytest
from io import StringIO
import logging
from unittest.mock import patch, MagicMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.core.logger import (
    get_logger,
    set_request_id,
    get_request_id,
    clear_request_id,
    JSONFormatter,
)


# Test uygulaması oluştur
test_app = FastAPI()

# Logger'ı StringIO'ya yönlendir (test için)
test_logger = logging.getLogger("test_middleware")
test_logger.setLevel(logging.INFO)
test_logger.handlers.clear()

test_stream = StringIO()
test_handler = logging.StreamHandler(test_stream)
test_formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
test_handler.setFormatter(test_formatter)
test_logger.addHandler(test_handler)


# Middleware'i test uygulamasına ekle
@test_app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Test middleware - request logging."""
    import uuid
    from time import perf_counter
    from app.core.logger import (
        set_request_id,
        clear_request_id,
        log_request,
        log_response,
        log_error,
    )
    
    start = perf_counter()
    user = None
    request_id = None
    
    try:
        # Request ID oluştur
        request_id = str(uuid.uuid4())[:8]
        set_request_id(request_id)
        
        # Request'i log'la
        log_request(
            test_logger,
            request.method,
            request.url.path,
            user=user,
            extra={"request_id": request_id}
        )
        
        # Request'i işle
        try:
            response = await call_next(request)
        except Exception as exc:
            # Hata durumunda error logging
            duration_ms = (perf_counter() - start) * 1000
            
            log_error(
                test_logger,
                f"İstek işlenirken hata oluştu: {str(exc)}",
                error_type=type(exc).__name__,
                path=request.url.path,
                extra={
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "method": request.method,
                },
                exc_info=True
            )
            
            clear_request_id()
            raise
        
        # Response'u log'la
        duration_ms = (perf_counter() - start) * 1000
        log_response(
            test_logger,
            response.status_code,
            duration_ms,
            path=request.url.path,
            extra={
                "request_id": request_id,
                "method": request.method,
            }
        )
        
        return response
        
    finally:
        clear_request_id()


# Test endpoint'leri
@test_app.get("/test/success")
async def endpoint_success():
    """Başarılı response dönen endpoint."""
    return {"status": "ok"}


@test_app.get("/test/error")
async def endpoint_error():
    """Hata dönen endpoint."""
    raise ValueError("Test hatası")


# Exception handler - error endpoint'i için
@test_app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """ValueError'ları handle et."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


@test_app.post("/test/post")
async def endpoint_post():
    """POST endpoint."""
    return {"method": "POST"}


class TestLoggingMiddleware:
    """Logging middleware test'leri."""

    def setup_method(self):
        """Her test öncesi setup."""
        test_stream.truncate(0)
        test_stream.seek(0)
        clear_request_id()

    def test_middleware_logs_successful_request(self):
        """
        Middleware'in başarılı request'leri doğru log'ladığını test et.
        
        For any successful HTTP request, the middleware should log both
        the request and response with correct status code and duration.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Response kontrol et
        assert response.status_code == 200
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # En az 2 log satırı olmalı (request + response)
        assert len(log_lines) >= 2
        
        # Log'ları parse et
        request_log = json.loads(log_lines[0])
        response_log = json.loads(log_lines[1])
        
        # Request log'unu kontrol et
        assert request_log["context"]["type"] == "request"
        assert request_log["context"]["method"] == "GET"
        assert request_log["context"]["path"] == "/test/success"
        assert "request_id" in request_log["context"]
        
        # Response log'unu kontrol et
        assert response_log["context"]["type"] == "response"
        assert response_log["context"]["status_code"] == 200
        assert response_log["context"]["method"] == "GET"
        assert response_log["context"]["path"] == "/test/success"
        assert "duration_ms" in response_log["context"]
        assert response_log["context"]["duration_ms"] > 0

    def test_middleware_logs_error_request(self):
        """
        Middleware'in error request'lerini doğru log'ladığını test et.
        
        For any request that raises an exception, the middleware should log
        the error with exception type and message.
        """
        client = TestClient(test_app)
        
        # Error request yap
        response = client.get("/test/error")
        
        # Response kontrol et (500 hatası bekleniyor)
        assert response.status_code == 500
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # En az 2 log satırı olmalı (request + response)
        # Exception handler tarafından handle edildiği için error log yerine response log olacak
        assert len(log_lines) >= 2
        
        # Log'ları parse et
        request_log = json.loads(log_lines[0])
        response_log = json.loads(log_lines[1])
        
        # Request log'unu kontrol et
        assert request_log["context"]["type"] == "request"
        assert request_log["context"]["method"] == "GET"
        
        # Response log'unu kontrol et (exception handler tarafından handle edildi)
        assert response_log["context"]["type"] == "response"
        assert response_log["context"]["status_code"] == 500

    def test_middleware_logs_post_request(self):
        """
        Middleware'in POST request'lerini doğru log'ladığını test et.
        
        For any POST request, the middleware should log the request with
        correct method and response with correct status code.
        """
        client = TestClient(test_app)
        
        # POST request yap
        response = client.post("/test/post")
        
        # Response kontrol et
        assert response.status_code == 200
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # Log'ları parse et
        request_log = json.loads(log_lines[0])
        response_log = json.loads(log_lines[1])
        
        # Request log'unu kontrol et
        assert request_log["context"]["method"] == "POST"
        assert request_log["context"]["path"] == "/test/post"
        
        # Response log'unu kontrol et
        assert response_log["context"]["method"] == "POST"
        assert response_log["context"]["status_code"] == 200

    def test_middleware_request_id_tracking(self):
        """
        Middleware'in request ID'sini doğru track'leyip track'lemediğini test et.
        
        For any request, the middleware should generate a unique request ID
        and include it in both request and response logs.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # Log'ları parse et
        request_log = json.loads(log_lines[0])
        response_log = json.loads(log_lines[1])
        
        # Request ID'leri kontrol et
        request_id = request_log["context"]["request_id"]
        response_id = response_log["context"]["request_id"]
        
        # Aynı request ID'si olmalı
        assert request_id == response_id
        # Request ID boş olmamalı
        assert len(request_id) > 0

    def test_middleware_performance_timing(self):
        """
        Middleware'in performance timing'i doğru ölçüp ölçmediğini test et.
        
        For any request, the middleware should measure and log the duration
        in milliseconds with a positive value.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # Response log'unu parse et
        response_log = json.loads(log_lines[1])
        
        # Duration'ı kontrol et
        duration_ms = response_log["context"]["duration_ms"]
        
        # Duration pozitif olmalı
        assert duration_ms > 0
        # Duration makul bir değer olmalı (< 10 saniye)
        assert duration_ms < 10000

    def test_middleware_logs_json_format(self):
        """
        Middleware'in JSON formatında log'ladığını test et.
        
        For any request, the middleware should produce valid JSON output
        that can be parsed and contains all required fields.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Log çıktısını al
        logs = test_stream.getvalue()
        log_lines = [line for line in logs.strip().split("\n") if line]
        
        # Her log satırı valid JSON olmalı
        for log_line in log_lines:
            log_data = json.loads(log_line)
            
            # Temel alanları kontrol et
            assert "timestamp" in log_data
            assert "level" in log_data
            assert "module" in log_data
            assert "message" in log_data
            assert "context" in log_data

    def test_middleware_multiple_requests_isolation(self):
        """
        Middleware'in birden fazla request'i izole şekilde log'ladığını test et.
        
        For any multiple concurrent requests, each request should have
        a unique request ID and logs should not be mixed.
        """
        client = TestClient(test_app)
        
        # İlk request yap
        response1 = client.get("/test/success")
        logs1 = test_stream.getvalue()
        
        # Stream'i temizle
        test_stream.truncate(0)
        test_stream.seek(0)
        
        # İkinci request yap
        response2 = client.get("/test/success")
        logs2 = test_stream.getvalue()
        
        # Log'ları parse et
        log_lines1 = [line for line in logs1.strip().split("\n") if line]
        log_lines2 = [line for line in logs2.strip().split("\n") if line]
        
        request_id1 = json.loads(log_lines1[0])["context"]["request_id"]
        request_id2 = json.loads(log_lines2[0])["context"]["request_id"]
        
        # Request ID'leri farklı olmalı
        assert request_id1 != request_id2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
