import asyncio
import httpx
import json

async def test_greeting():
    url = "http://localhost:8086/api/chat"
    
    # First, a message about 404 to prime the history
    payload_1 = {
        "message": "404 hatası nedir?",
        "session_id": "hallucination_test_1",
        "use_mock": False
    }
    
    print("\n--- Priming history with 404 question ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp1 = await client.post(url, json=payload_1)
        print(f"Status: {resp1.status_code}")
        # print(f"Response: {resp1.json()['response'][:100]}...")

    # Now, the "selam" message
    payload_2 = {
        "message": "selam",
        "session_id": "hallucination_test_1",
        "use_mock": False
    }
    
    print("\n--- Sending GREETING ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp2 = await client.post(url, json=payload_2)
        print(f"Status: {resp2.status_code}")
        print(f"Response: {resp2.json()['response']}")

if __name__ == "__main__":
    asyncio.run(test_greeting())
