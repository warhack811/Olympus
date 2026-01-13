import asyncio
import httpx
import time
import json
from typing import List, Dict

# Configuration
BASE_URL = "http://127.0.0.1:8080"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat"

# Scenarios
TEST_SCENARIOS = [
    {
        "name": "Coding (Heavy Logic)",
        "payload": {
            "user_id": "user_1",
            "message": "Python ile merge sort nasıl yapılır? Adım adım açıkla ve kod örneği ver.",
            "mode": "professional"
        }
    },
    {
        "name": "Creative (Lightweight)",
        "payload": {
            "user_id": "user_2",
            "message": "Deniz ve özgürlük hakkında kısa bir şiir yaz.",
            "mode": "creative"
        }
    },
    {
        "name": "Tool Use (Search)",
        "payload": {
            "user_id": "user_3",
            "message": "Şu an dolar kuru kaç TL? Güncel bilgiyi getir.",
            "mode": "standard"
        }
    },
    {
        "name": "General Greeting (Fast)",
        "payload": {
            "user_id": "user_4",
            "message": "Merhaba ATLAS, nasılsın bugün?",
            "mode": "friendly"
        }
    },
    {
        "name": "Image Generation (Flux Tool)",
        "payload": {
            "user_id": "user_5",
            "message": "Cyberpunk tarzında kırmızı bir araba resmi çiz.",
            "mode": "creative"
        }
    }
]

async def send_chat_request(client: httpx.AsyncClient, scenario: Dict) -> Dict:
    name = scenario["name"]
    payload = scenario["payload"]
    
    print(f"[START] Executing Scenario: {name}...")
    start_time = time.time()
    
    try:
        response = await client.post(CHAT_ENDPOINT, json=payload, timeout=60.0)
        duration = time.time() - start_time
        
        status = response.status_code
        if status == 200:
            result = response.json()
            is_success = "error" not in result
            # RDR Bilgilerini çek
            rdr = result.get("rdr", {})
            model = rdr.get("synthesizer_model", "unknown")
            print(f"[SUCCESS] {name} | Duration: {duration:.2f}s | Model: {model}")
            return {"name": name, "status": "OK", "duration": duration, "model": model}
        else:
            print(f"[FAILED] {name} | Status: {status} | Error: {response.text}")
            return {"name": name, "status": f"HTTP {status}", "duration": duration}
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"[ERROR] {name} | Exception: {str(e)}")
        return {"name": name, "status": "EXCEPTION", "duration": duration}

async def run_stress_test():
    print("=== ATLAS STRESS TEST (PHASE 8) ===")
    print(f"Target: {CHAT_ENDPOINT}")
    print(f"Concurrent Scenarios: {len(TEST_SCENARIOS)}\n")
    
    async with httpx.AsyncClient() as client:
        tasks = [send_chat_request(client, s) for s in TEST_SCENARIOS]
        results = await asyncio.gather(*tasks)
    
    print("\n" + "="*40)
    print("STRESS TEST RESULTS SUMMARY")
    print("="*40)
    
    total_time = 0
    success_count = 0
    
    for res in results:
        status_icon = "✅" if res["status"] == "OK" else "❌"
        print(f"{status_icon} {res['name']:<25} | {res['status']:<10} | {res['duration']:.2f}s")
        if res["status"] == "OK":
            success_count += 1
            total_time += res["duration"]
            
    if success_count > 0:
        avg_time = total_time / success_count
        print(f"\nAverage Success Latency: {avg_time:.2f}s")
        print(f"Success Rate: {success_count}/{len(TEST_SCENARIOS)} (%{success_count/len(TEST_SCENARIOS)*100:.1f})")
    
    print("="*40)

if __name__ == "__main__":
    try:
        asyncio.run(run_stress_test())
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
