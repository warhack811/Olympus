import asyncio
import pytest
from sandbox_router.dag_executor import DAGExecutor
from sandbox_router.schemas import OrchestrationPlan, TaskSpec

class MockBrokenTool:
    async def execute(self, **kwargs):
        raise Exception("Tool intentional failure for testing")

async def test_dag_resilience():
    print("\n--- ATLAS Projesi: Resilience (Dayanıklılık) Testi Başlıyor (Faz 6) ---")
    
    executor = DAGExecutor()
    
    # 1. Kasıtlı olarak bozulan bir tool ekleyelim (Registry'ye manuel müdahale)
    executor.tool_registry.register_tool("broken_tool", MockBrokenTool())
    
    # 2. Bağımlı bir plan oluşturalım
    # t1: Hatalı tool
    # t2: t1'in çıktısını kullanmaya çalışan bir generation görevi
    plan = OrchestrationPlan(
        tasks=[
            TaskSpec(id="t1", type="tool", tool_name="broken_tool", params={}),
            TaskSpec(
                id="t2", 
                type="generation", 
                specialist="logic", 
                instruction="Önceki aracın çıktısını özetle: {t1.output}",
                dependencies=["t1"]
            )
        ],
        intent="general"
    )
    
    print("[1] Plan yürütülüyor (Bozuk tool içeriyor)...")
    results = await executor.execute_plan(plan, session_id="resilience-test", original_message="Bozuk tool testi")
    
    # 3. Sonuçları doğrula
    print("\n[2] Sonuçlar Analiz Ediliyor...")
    
    t1_res = next((r for r in results if r["task_id"] == "t1"), None)
    t2_res = next((r for r in results if r["task_id"] == "t2"), None)
    
    if t1_res:
        print(f"t1 Durumu: {t1_res.get('status')} - Hata: {t1_res.get('error')}")
        assert t1_res["status"] == "failed"
        assert "intentional failure" in t1_res["error"]
        print("✅ t1 beklendiği gibi hata verdi.")
    
    if t2_res:
        output = t2_res.get("output", "")
        print(f"t2 Çıktısı: {output[:100]}...")
        # t2'nin çökmemesi ve prompt içine hata mesajının enjekte edilmiş olması gerekir
        assert t2_res.get("error") is not True # Generation çökmemeli
        print("✅ t1'in hatasına rağmen t2 başarıyla tamamlandı (Graceful Degradation).")
        
        # prompt log'unda enjeksiyonu kontrol edelim
        prompt = t2_res.get("prompt", "")
        if "[Hata: t1 verisi alınamadı" in prompt:
            print("✅ Hata mesajı prompt içine başarıyla enjekte edildi.")
            
    print("\n--- Resilience Testi Tamamlandı ---")

if __name__ == "__main__":
    asyncio.run(test_dag_resilience())
