import asyncio
import logging
from sandbox_router.observer import observer
from sandbox_router.memory.neo4j_manager import neo4j_manager

# Logging ayarı
logging.basicConfig(level=logging.INFO)

async def test_observer_flow():
    print("--- ATLAS Projesi: Proaktif Observer Testi Başlıyor (Faz 5) ---")
    
    user_id = "test_user"
    
    # 1. Neo4j'ye Test Bilgisi Ekle
    print(f"\n[1] Neo4j'ye test planı ekleniyor for {user_id}...")
    test_triplets = [
        {"subject": "Muhammet", "predicate": "planlar", "object": "Yarın Ankara gezisi"}
    ]
    await neo4j_manager.store_triplets(test_triplets, user_id)
    
    # Neo4j işleminin tamamlanması için kısa bir bekleme
    await asyncio.sleep(1)

    # 2. Observer Tetikleme
    print(f"\n[2] Observer tetikleniyor (check_triggers)...")
    # Not: Daha önce çalıştırıldıysa 10 dk kuralına takılmaması için 
    # observer._last_check[user_id] = None yapılabilir (test amaçlı).
    observer._last_check[user_id] = None 
    
    await observer.check_triggers(user_id)
    
    # 3. Sonuçları Kontrol Et
    print(f"\n[3] Bildirimler alınıyor...")
    notifications = observer.get_notifications(user_id)
    
    if notifications:
        print(f"\n✅ BAŞARI: {len(notifications)} adet bildirim üretildi!")
        for n in notifications:
            print(f"- Bildirim: {n['message']}")
            
        # Doğrulama: Bildirim beklenen 'Ankara' ve 'fırtına' (mock verisi) kelimelerini içeriyor mu?
        msg = notifications[0]['message'].lower()
        if "ankara" in msg:
            print("✅ BAŞARI: Bildirim doğru lokasyonu içeriyor.")
    else:
        print("\n❌ HATA: Bildirim üretilemedi. LLM bir risk görmemiş olabilir veya bir hata oluştu.")

    print("\n--- Test Tamamlandı ---")

if __name__ == "__main__":
    asyncio.run(test_observer_flow())
