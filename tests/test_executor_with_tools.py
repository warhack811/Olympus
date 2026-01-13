import asyncio
import os
import sys
import json

# Proje kök dizinini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandbox_router.dag_executor import DAGExecutor
from sandbox_router.schemas import OrchestrationPlan

async def test_dag_with_tools():
    print("--- DAG Executor Tool ve Bağımlılık Testi Başlıyor ---")
    executor = DAGExecutor()
    
    # Test planı: 1 tool + ona bağımlı 1 generation
    plan_dict = {
        "intent": "weather_inquiry",
        "rewritten_query": "Ankara'da hava nasıl ve ne giymeliyim?",
        "tasks": [
            {
                "id": "t1",
                "type": "tool",
                "tool_name": "mock_weather",
                "params": {"city": "Ankara"}
            },
            {
                "id": "t2",
                "type": "generation",
                "specialist": "logic",
                "prompt": "Ankara havası şu an '{t1.output}' ise dışarı çıkarken ne giymeliyim? Kısa tavsiye ver.",
                "dependencies": ["t1"]
            }
        ]
    }
    
    # Planı Pydantic modele çevir (dag_executor zaten kabul ediyor ama temizlik için)
    plan = OrchestrationPlan(**plan_dict)
    
    print(f"Plan yüklendi: {len(plan.tasks)} görev var.")
    
    results = await executor.execute_plan(plan, session_id="test_session", original_message="Ankara'da hava nasıl?")
    
    print("\n--- Test Sonuçları ---")
    for res in results:
        t_id = res["task_id"]
        t_type = res["type"]
        output = str(res.get("output", ""))[:100]
        print(f"[{t_id}] Type: {t_type} | Output: {output}...")
        
        if t_id == "t2":
            prompt_sent = res.get("prompt", "")
            print(f" - T2'ye gönderilen gerçek prompt: {prompt_sent}")
            
            # Doğrulama: t1 çıktısı t2 promptu içinde mi?
            if "hava durumu" in prompt_sent and "°C" in prompt_sent:
                print(" -> BAŞARI: Tool çıktısı prompt içine başarıyla enjekte edildi.")
            else:
                print(" -> HATA: Tool çıktısı enjeksiyonu başarısız!")

    print("\n--- Test Tamamlandı ---")
    
    # Sonuçları dosyaya yaz (Doğrulama için)
    test_data = {
        "success": any("BAŞARI" in str(res) for res in results), # Basit kontrol
        "results": results
    }
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(test_dag_with_tools())
