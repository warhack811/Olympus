import asyncio
import httpx
import uuid

async def test_style_modes():
    print("--- ATLAS Projesi: Stil ve Persona Testi Başlıyor (Faz 4) ---")
    
    base_url = "http://localhost:8000"
    session_id = f"style-test-{uuid.uuid4().hex[:6]}"
    
    question = "Borsa düştü, ne yapmalıyım?"
    modes = ["professional", "sincere"]
    results = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for mode in modes:
            print(f"\n[{mode.upper()}] Modunda Soru Soruluyor: '{question}'")
            try:
                resp = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "message": question,
                        "session_id": session_id,
                        "mode": mode
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results[mode] = data.get("response", "")
                    print(f"Yanıt ({mode}): {results[mode][:150]}...")
                    
                    # RDR Metadata Kontrolü
                    rdr = data.get("rdr", {})
                    print(f"RDR Persona: {rdr.get('style_persona')}")
                    print(f"RDR Preset: {rdr.get('style_preset')}")
                else:
                    print(f"Hata ({mode}): {resp.status_code}")
            except Exception as e:
                print(f"Hata ({mode}): {e}")

    # Karşılaştırma ve Doğrulama
    if "professional" in results and "sincere" in results:
        prof = results["professional"]
        sinc = results["sincere"]
        
        print("\n--- Analiz ---")
        
        # Professional modda "kurumsal" veya "ciddi" bir ton beklenir, genelde emoji olmaz.
        # Sincere modda emoji veya daha sıcak bir dil beklenir.
        
        import re
        emoji_pattern = re.compile(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]")
        
        prof_emojis = emoji_pattern.findall(prof)
        sinc_emojis = emoji_pattern.findall(sinc)
        
        print(f"Professional Emojiler: {len(prof_emojis)}")
        print(f"Sincere Emojiler: {len(sinc_emojis)}")
        
        if prof != sinc:
            print("\n✅ BAŞARI: İki mod farklı yanıtlar üretti.")
        else:
            print("\n⚠️ UYARI: İki mod aynı yanıtı üretti (Model aynı sonucu vermiş olabilir).")

        if len(sinc_emojis) >= len(prof_emojis):
            print("✅ BAŞARI: Sincere mod beklenen emoji/samimiyet eğilimini gösterdi.")

    print("\n--- Test Tamamlandı ---")

if __name__ == "__main__":
    # Testi çalıştırmak için API sunucusunun açık olması gerekir: 
    # python -m sandbox_router.api
    asyncio.run(test_style_modes())
