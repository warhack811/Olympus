import asyncio
import httpx
import json
import uuid

async def test_full_flow():
    print("--- ATLAS Projesi: Tam Akış (Memory + Retrieval) Testi Başlıyor ---")
    
    base_url = "http://localhost:8000"
    session_id = f"test-session-{uuid.uuid4().hex[:6]}"
    
    # 1. Bilgi Verme (Extraction Testi)
    msg1 = "Benim adım Muhammet ve en sevdiğim programlama dili Python'dır."
    print(f"\n[1] Mesaj Gönderiliyor: '{msg1}'")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp1 = await client.post(
                f"{base_url}/api/chat",
                json={
                    "message": msg1,
                    "session_id": session_id
                }
            )
            print(f"Yanıt 1 Durumu: {resp1.status_code}")
            if resp1.status_code == 200:
                print(f"Cevap: {resp1.json().get('response')}")
        except Exception as e:
            print(f"Hata (Mesaj 1): {e}")
            return

    # Arka plandaki extraction işleminin bitmesi için biraz bekle
    print("\nExtraction işlemi için 5 saniye bekleniyor...")
    await asyncio.sleep(5)

    # 2. Bilgi Sorgulama (Retrieval Testi)
    msg2 = "Benim en sevdiğim yazılım dili hangisiydi? Hatırlıyor musun?"
    print(f"\n[2] Mesaj Gönderiliyor: '{msg2}'")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp2 = await client.post(
                f"{base_url}/api/chat",
                json={
                    "message": msg2,
                    "session_id": session_id
                }
            )
            print(f"Yanıt 2 Durumu: {resp2.status_code}")
            if resp2.status_code == 200:
                data = resp2.json()
                answer = data.get('response')
                print(f"Cevap: {answer}")
                
                # Doğrulama: Yanıtta Python geçiyor mu?
                if "python" in answer.lower():
                    print("\n✅ BAŞARI: Sistem geçmiş bilgiyi (Python) hatırladı!")
                else:
                    print("\n❌ HATA: Sistem bilgiyi hatırlayamadı veya yanıta yansıtmadı.")
                    
                # RDR kontrolü
                rdr_data = data.get('rdr', {})
                if rdr_data.get('full_context_injection'):
                    print("RDR: Context injection görünüyor.")
        except Exception as e:
            print(f"Hata (Mesaj 2): {e}")

    print("\n--- Test Tamamlandı ---")

if __name__ == "__main__":
    # Testi çalıştırmak için API sunucusunun açık olması gerekir: 
    # python -m sandbox_router.api
    asyncio.run(test_full_flow())
