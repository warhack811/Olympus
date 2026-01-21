from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_admin_user  # Admin yetkisi gerektirir
from app.core.env_manager import env_manager
from app.services.api_monitor import api_monitor

router = APIRouter(prefix="/api-keys", tags=["admin_api_keys"])


class ApiKeyInfo(BaseModel):
    key_name: str
    masked_value: str
    stats: dict | None = None


class ApiKeyUpdate(BaseModel):
    key_name: str
    value: str


@router.get("", response_model=list[ApiKeyInfo])
async def get_api_keys(current_user: dict = Depends(get_current_admin_user)):
    """
    Sistemdeki Groq API anahtarlarını ve kullanım istatistiklerini döndürür.
    """
    groq_keys = env_manager.get_groq_keys()
    result = []

    for item in groq_keys:
        full_key = item["value"]
        masked = api_monitor._mask_key(full_key)
        stats = api_monitor.get_stats_for_key(full_key)

        result.append(ApiKeyInfo(key_name=item["key"], masked_value=masked, stats=stats))

    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_or_update_api_key(data: ApiKeyUpdate, current_user: dict = Depends(get_current_admin_user)):
    """
    Yeni bir API anahtarı ekler veya mevcut olanı günceller.
    .env dosyasına yazar.
    """
    if not data.key_name.upper().startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=400, detail="Anahtar ismi GROQ_API_KEY ile başlamalıdır.")

    env_manager.set_key(data.key_name, data.value)
    return {"message": f"{data.key_name} başarıyla güncellendi."}


@router.delete("/{key_name}")
async def delete_api_key(key_name: str, current_user: dict = Depends(get_current_admin_user)):
    """
    Bir API anahtarını siler.
    """
    if not key_name.upper().startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=400, detail="Sadece GROQ_API_KEY silinebilir.")

    env_manager.delete_key(key_name)
    return {"message": f"{key_name} silindi."}


@router.get("/{key_name}/reveal")
async def reveal_api_key(key_name: str, current_user: dict = Depends(get_current_admin_user)):
    """
    Tam API anahtarını açık şekilde döndürür (sadece admin).
    """
    groq_keys = env_manager.get_groq_keys()
    for k in groq_keys:
        if k["key"] == key_name:
            return {"key_name": key_name, "value": k["value"]}

    raise HTTPException(status_code=404, detail="Anahtar bulunamadı.")


@router.post("/{key_name}/refresh", response_model=ApiKeyInfo)
async def refresh_api_key(key_name: str, current_user: dict = Depends(get_current_admin_user)):
    """
    Belirtilen API anahtarı için Groq'a ufak bir istek atarak
    limit bilgilerini günceller ve son durumu döner.
    """
    import httpx

    # 1. Anahtarı bul
    groq_keys = env_manager.get_groq_keys()
    target_key_value = None
    for k in groq_keys:
        if k["key"] == key_name:
            target_key_value = k["value"]
            break

    if not target_key_value:
        raise HTTPException(status_code=404, detail="Anahtar bulunamadı.")

    # 2. İstek at (Groq Models Endpoint - ucuz/bedava)
    # 2. İstek at (Groq Chat Endpoint - Header almak için bu gerekli)
    URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {target_key_value}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",  # Ana Model (Gerçek limitleri görmek için)
        "messages": [{"role": "user", "content": "."}],
        "max_tokens": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(URL, headers=headers, json=payload)

            if resp.status_code == 401:
                api_monitor.mark_invalid(target_key_value)
                # Hata fırlatma, çünkü durumu "Invalid" olarak döndürmek istiyoruz

            # 3. İstatistikleri güncelle (Başarılı veya 429 olsa bile header gelir)
            elif resp.headers:
                api_monitor.update_usage(target_key_value, resp.headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq bağlantı hatası: {str(e)}")

    # 4. Güncel bilgiyi dön
    masked = api_monitor._mask_key(target_key_value)
    stats = api_monitor.get_stats_for_key(target_key_value)

    # Stats null ise boş obje dönelim ki frontend patlamasın?
    # Frontend stats? kontrolü yapıyor

    return ApiKeyInfo(key_name=key_name, masked_value=masked, stats=stats)
