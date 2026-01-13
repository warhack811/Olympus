import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Proje kök dizinini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandbox_router.memory.extractor import extract_and_save

async def test_extraction_flow():
    print("--- Graph Memory (Neo4j) Entegrasyon Testi Başlıyor (Faz 2) ---")
    
    user_id = "test_user_123"
    message = "Benim adım Can, Berlin'de yaşıyorum. En sevdiğim film ise Inception."
    
    print(f"Test Mesajı: '{message}'")
    
    # Not: Gerçek bir Neo4j ve Groq bağlantısı yoksa bu test hata verebilir veya soft-fail olur.
    # Bu yüzden burada bir mock mekanizması veya sadece yükleme testi yapılabilir.
    
    print(" extraction_and_save çağrılıyor...")
    # Gerçek API çağrısı yapılacağı için (eğer env setse) veya hata alacağı için try-except
    results = await extract_and_save(message, user_id)
    
    if results:
        print(f"Başarılı! Çıkarılan Triplet Sayısı: {len(results)}")
        for i, t in enumerate(results):
            print(f" {i+1}. {t.get('subject')} --({t.get('predicate')})--> {t.get('object')}")
    else:
        print("Bilgi çıkarılamadı veya bir hata oluştu (Soft-fail kontrolü).")
        print("Not: Bu test gerçek bir NEO4J_URI ve GROQ_API_KEY gerektirir.")

    print("\n--- Test Tamamlandı ---")

if __name__ == "__main__":
    asyncio.run(test_extraction_flow())
