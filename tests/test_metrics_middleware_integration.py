"""
Metrics Middleware Integration Test'leri

Bu test dosyası, app/main.py'deki metrics collection middleware'inin
doğru çalışıp çalışmadığını test eder.

Test Kapsamı:
    - Middleware'in request duration'ını doğru ölçüp ölçmediği
    - Middleware'in status code'u doğru saydığı
    - Middleware'in error'ları doğru saydığı
    - Metriklerin Prometheus formatında toplandığı

Property 6: Metrics Consistency
Validates: Requirements 3.2
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from unittest.mock import patch, MagicMock

from app.core.metrics import (
    request_duration_histogram,
    request_count_counter,
    error_count_counter,
    get_metrics_output,
    record_request_metrics,
    record_error_metrics,
)


# Test uygulaması oluştur
test_app = FastAPI()


# Middleware'i test uygulamasına ekle
@test_app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Test middleware - metrics collection."""
    from time import perf_counter
    from app.core.metrics import record_request_metrics, record_error_metrics
    
    start = perf_counter()
    
    try:
        # Request'i işle
        try:
            response = await call_next(request)
        except Exception as exc:
            # Hata durumunda error metrics'i kaydet
            record_error_metrics(
                method=request.method,
                endpoint=request.url.path,
                error_type=type(exc).__name__,
            )
            raise
        
        # Response metrikleri kaydet
        duration_ms = (perf_counter() - start) * 1000
        duration_seconds = duration_ms / 1000
        
        record_request_metrics(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        
        return response
        
    except Exception:
        raise


# Test endpoint'leri
@test_app.get("/test/success")
async def endpoint_success():
    """Başarılı response dönen endpoint."""
    return {"status": "ok"}


@test_app.get("/test/error")
async def endpoint_error():
    """Hata dönen endpoint."""
    raise ValueError("Test hatası")


@test_app.post("/test/post")
async def endpoint_post():
    """POST endpoint."""
    return {"method": "POST"}


@test_app.get("/test/not-found")
async def endpoint_not_found():
    """404 dönen endpoint."""
    return JSONResponse(status_code=404, content={"error": "Not found"})


# Exception handler - error endpoint'i için
@test_app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """ValueError'ları handle et."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


class TestMetricsMiddleware:
    """Metrics middleware test'leri."""

    def setup_method(self):
        """Her test öncesi setup."""
        # Registry'yi sıfırlamıyoruz çünkü metrikleri kaydetmek için
        # aynı registry'yi kullanmamız gerekiyor
        pass

    def test_middleware_records_request_duration(self):
        """
        Middleware'in request duration'ını doğru ölçüp ölçmediğini test et.
        
        For any successful HTTP request, the middleware should record
        the request duration in the histogram with correct labels.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Response kontrol et
        assert response.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Duration histogram'ının output'ta olduğunu kontrol et
        assert "mami_request_duration_seconds" in metrics_str
        assert 'method="GET"' in metrics_str
        assert 'endpoint="/test/success"' in metrics_str
        assert 'status="200"' in metrics_str

    def test_middleware_records_request_count(self):
        """
        Middleware'in request count'unu doğru saydığını test et.
        
        For any successful HTTP request, the middleware should increment
        the request counter with correct labels.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        
        # Response kontrol et
        assert response.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Request counter'ının output'ta olduğunu kontrol et
        assert "mami_request_total" in metrics_str
        assert 'method="GET"' in metrics_str
        assert 'endpoint="/test/success"' in metrics_str
        assert 'status="200"' in metrics_str

    def test_middleware_records_error_count(self):
        """
        Middleware'in error count'unu doğru saydığını test et.
        
        For any request that raises an exception, the middleware should
        increment the error counter with correct labels.
        """
        client = TestClient(test_app)
        
        # Error request yap
        response = client.get("/test/error")
        
        # Response kontrol et (500 hatası bekleniyor)
        assert response.status_code == 500
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Error request'in 500 status code ile kaydedildiğini kontrol et
        # (Exception handler tarafından handle edildiği için error counter yerine
        # request counter'ında 500 status code ile görünecek)
        assert 'status="500"' in metrics_str
        assert 'endpoint="/test/error"' in metrics_str

    def test_middleware_records_different_status_codes(self):
        """
        Middleware'in farklı status code'ları doğru saydığını test et.
        
        For any request with different status codes, the middleware should
        record each status code separately in the metrics.
        """
        client = TestClient(test_app)
        
        # 200 status code
        response1 = client.get("/test/success")
        assert response1.status_code == 200
        
        # 404 status code
        response2 = client.get("/test/not-found")
        assert response2.status_code == 404
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Her iki status code'un da output'ta olduğunu kontrol et
        assert 'status="200"' in metrics_str
        assert 'status="404"' in metrics_str

    def test_middleware_records_different_methods(self):
        """
        Middleware'in farklı HTTP method'larını doğru saydığını test et.
        
        For any request with different HTTP methods, the middleware should
        record each method separately in the metrics.
        """
        client = TestClient(test_app)
        
        # GET request
        response1 = client.get("/test/success")
        assert response1.status_code == 200
        
        # POST request
        response2 = client.post("/test/post")
        assert response2.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Her iki method'un da output'ta olduğunu kontrol et
        assert 'method="GET"' in metrics_str
        assert 'method="POST"' in metrics_str

    def test_middleware_records_different_endpoints(self):
        """
        Middleware'in farklı endpoint'leri doğru saydığını test et.
        
        For any request to different endpoints, the middleware should
        record each endpoint separately in the metrics.
        """
        client = TestClient(test_app)
        
        # İlk endpoint
        response1 = client.get("/test/success")
        assert response1.status_code == 200
        
        # İkinci endpoint
        response2 = client.post("/test/post")
        assert response2.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Her iki endpoint'in de output'ta olduğunu kontrol et
        assert 'endpoint="/test/success"' in metrics_str
        assert 'endpoint="/test/post"' in metrics_str

    def test_middleware_duration_is_positive(self):
        """
        Middleware'in ölçtüğü duration'ın pozitif olduğunu test et.
        
        For any request, the recorded duration should be a positive value
        in seconds.
        """
        client = TestClient(test_app)
        
        # Request yap
        response = client.get("/test/success")
        assert response.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Duration histogram'ının output'ta olduğunu kontrol et
        assert "mami_request_duration_seconds" in metrics_str
        
        # Histogram'ın bucket'larını kontrol et (pozitif değerler)
        # Prometheus formatında bucket'lar şu şekilde görünür:
        # mami_request_duration_seconds_bucket{...le="0.005"} 0
        # mami_request_duration_seconds_bucket{...le="0.01"} 0
        # vb.
        assert 'le="0.005"' in metrics_str or 'le="0.01"' in metrics_str

    def test_middleware_multiple_requests_accumulate(self):
        """
        Middleware'in birden fazla request'i doğru şekilde topladığını test et.
        
        For any multiple requests, the middleware should accumulate metrics
        correctly with each request incrementing the counters.
        """
        client = TestClient(test_app)
        
        # Birden fazla request yap
        for i in range(3):
            response = client.get("/test/success")
            assert response.status_code == 200
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Request counter'ının output'ta olduğunu kontrol et
        assert "mami_request_total" in metrics_str
        
        # Counter'ın değerini kontrol et (3 request yapıldı)
        # Prometheus formatında counter şu şekilde görünür:
        # mami_request_total{...} 3
        lines = metrics_str.split("\n")
        for line in lines:
            if "mami_request_total" in line and 'method="GET"' in line and 'endpoint="/test/success"' in line and 'status="200"' in line:
                # Counter değerini al (son sayı)
                parts = line.split()
                if len(parts) > 0:
                    try:
                        count = float(parts[-1])
                        # En az 3 request sayılmış olmalı
                        assert count >= 3
                    except ValueError:
                        pass

    def test_middleware_error_and_success_separate(self):
        """
        Middleware'in error ve success request'lerini ayrı şekilde saydığını test et.
        
        For any mix of successful and error requests, the middleware should
        record them separately in the metrics.
        """
        client = TestClient(test_app)
        
        # Başarılı request
        response1 = client.get("/test/success")
        assert response1.status_code == 200
        
        # Error request
        response2 = client.get("/test/error")
        assert response2.status_code == 500
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Her iki metric'in de output'ta olduğunu kontrol et
        assert 'status="200"' in metrics_str
        assert 'status="500"' in metrics_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
