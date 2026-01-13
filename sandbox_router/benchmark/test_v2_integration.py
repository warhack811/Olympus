import asyncio
import httpx
import json

async def test_v2_flow():
    url = "http://localhost:8080/api/chat"
    payload = {
        "message": "Python'da bir API yaz ve bana bu kodun neden güvenli olduğunu açıkla.",
        "session_id": "test_v2_1",
        "use_mock": False
    }
    
    print("\n--- TEST 1: Çoklu Görev (Kod + Analiz) ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()['response'][:300]}...")
            
    print("\n--- TEST 2: Niyet Sürekliliği (Follow-up) ---")
    payload_2 = {
        "message": "Bunu asenkron yap.",
        "session_id": "test_v2_1",
        "use_mock": False
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload_2)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()['response'][:300]}...")

if __name__ == "__main__":
    asyncio.run(test_v2_flow())
