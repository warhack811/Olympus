import asyncio
import uuid
import httpx
import json
from app.memory.rag_service import rag_service

async def test_document_rag():
    print("🚀 DOKÜMAN BAZLI RAG TESTİ BAŞLATILIYOR")
    
    # 1. Doküman Hazırla & Yükle
    # owner 'admin' olsun, test scriptleri genelde 'u_test_ok' veya 'admin' kullanır.
    # Ama API'den gelen user_id neyse o olmalı.
    user_id = "test_user_rag_live"
    filename = "sirket_politikasi.txt"
    content = "Mami AI Şirket Politikası: Cuma günleri ofis 15:00'da kapanır. Bu kural 2026 Ocak ayından itibaren geçerlidir."
    
    print(f"1. Doküman sisteme yükleniyor: {filename}")
    chunks = rag_service.add_text(content, filename, user_id)
    print(f"   {chunks} parça başarıyla RAG v2 sistemine eklendi.")
    
    # 2. BrainEngine üzerinden sorgula (API Çağrısı)
    print("\n2. BrainEngine üzerinden doküman bilgisi soruluyor...")
    
    API_URL = "http://localhost:8000/api/v1/user/atlas/stream"
    payload = {
        "message": "Şirket politikasına göre Cuma günleri ofis kaçta kapanıyor?",
        "user_id": user_id,
        "session_id": str(uuid.uuid4()),
        "persona": "professional"
    }
    AUTH_HEADER = {"Authorization": "Bearer mami-internal-secret-token"}

    found_doc_recall = False
    ai_response = ""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", API_URL, json=payload, headers=AUTH_HEADER) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "thought":
                            thought = data.get("thought", "")
                            print(f"[THOUGHT]: {thought}")
                            if "document fragments" in thought or "Kayit" in thought:
                                pass
                        if data.get("type") == "chunk":
                            ai_response += data.get("content", "")
    except Exception as e:
        print(f"Hata: {e}")

    print(f"\nAI YANITI: {ai_response}")
    
    if "15:00" in ai_response:
        print("\n✅ BAŞARILI: AI dokümandaki spesifik bilgiyi buldu.")
    else:
        print("\n❌ BAŞARISIZ: AI bilgiyi bulamadı.")

    # 3. Temizlik
    print("\n3. Test dokümanı temizleniyor...")
    rag_service.delete_document_by_filename(filename, user_id)
    print("   Temizlik tamamlandı.")

if __name__ == "__main__":
    asyncio.run(test_document_rag())
