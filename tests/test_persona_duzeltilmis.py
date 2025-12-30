"""
Mami AI - Persona Seçim Sistemi Testleri
=========================================

Bu dosya, kullanıcının aktif personasını değiştirdiği API endpoint'ini test eder.

Test Senaryoları:
    - Başarılı persona seçimi.
    - Kimlik doğrulaması olmadan deneme (başarısız olmalı).
    - Geçersiz persona adı gönderme (başarısız olmalı).
    - Eksik parametre ile istek gönderme (başarısız olmalı).
"""

import pytest
from httpx import AsyncClient
from sqlmodel import Session, SQLModel

from app.auth.session import create_session
from app.auth.user_manager import create_user, get_user_by_username
from app.core.database import engine
from app.core.database import get_session as app_get_session

# Testler çalışmadan önce ana uygulama ve veritabanı motorunun ayarlanması gerekir.
# Bu genellikle conftest.py dosyasında yapılır. Şimdilik burada basitleştirilmiş bir
# versiyonunu kullanacağız.
from app.main import app


# Test oturumu için uygulama bağımlılığını override et
def get_test_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[app_get_session] = get_test_session


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Tüm testlerden önce veritabanını oluşturur ve sonra temizler."""
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_user_session():
    """Her test için temiz bir test kullanıcısı ve oturum oluşturur."""
    with Session(engine) as session:
        # Eski test verilerini temizle
        existing_user = get_user_by_username("test_kullanici")
        if existing_user:
            session.delete(existing_user)
            session.commit()

        # Yeni kullanıcı ve oturum oluştur
        user = create_user("test_kullanici", "testsifre123", role="user")
        user_session = create_session(user)

        session.add(user)
        session.add(user_session)
        session.commit()
        session.refresh(user)
        session.refresh(user_session)

        yield user, user_session.id

        # Test sonrası temizlik
        session.delete(user)
        session.delete(user_session)
        session.commit()


@pytest.mark.asyncio
async def test_persona_secimi_basarili(test_user_session):
    """
    Başarılı bir şekilde persona seçimi yapıldığında API'nin doğru yanıt
    verdiğini ve veritabanını güncellediğini test eder.
    """
    user, session_id = test_user_session
    hedef_persona = "romantik"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/user/personas/select", json={"persona": hedef_persona}, cookies={"session-id": session_id}
        )

    # Yanıt kodunu ve mesajını kontrol et
    assert response.status_code == 200
    assert response.json()["message"] == f"Persona '{hedef_persona}' başarıyla seçildi."

    # Veritabanında kullanıcının personasının güncellendiğini doğrula
    with Session(engine) as session:
        guncel_kullanici = session.get(type(user), user.id)
        assert guncel_kullanici.active_persona == hedef_persona


@pytest.mark.asyncio
async def test_persona_secimi_kimlik_dogrulama_hatasi(test_user_session):
    """
    Geçersiz veya eksik session token ile yapılan isteğin 401 hatası
    döndürdüğünü test eder.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/user/personas/select",
            json={"persona": "bilge"},
            cookies={"session-id": "gecersiz_token"},  # Geçersiz token
        )

    assert response.status_code == 401
    assert "Kimlik doğrulama başarısız" in response.json()["detail"]


@pytest.mark.asyncio
async def test_persona_secimi_eksik_parametre(test_user_session):
    """
    İstekte 'persona' parametresi olmadığında 422 Unprocessable Entity
    hatası alındığını test eder.
    """
    _, session_id = test_user_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/user/personas/select",
            json={},  # Boş JSON gövdesi
            cookies={"session-id": session_id},
        )

    assert response.status_code == 422  # FastAPI'nin doğrulama hatası
