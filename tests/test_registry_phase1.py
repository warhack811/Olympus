import asyncio
import os
import sys

# Proje kök dizinini path'e ekle (eğer gerekirse)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandbox_router.tools.registry import ToolRegistry

async def main():
    print("--- Tool Registry Testi Başlıyor (Faz 1) ---")
    
    registry = ToolRegistry()
    
    # Dizinleri belirle
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    definitions_path = os.path.join(base_dir, "sandbox_router", "tools", "definitions")
    
    print(f"Tanımlar taranıyor: {definitions_path}")
    registry.load_tools(definitions_path)
    
    # 1. Yüklü tool'ları listele
    tools = registry.list_tools()
    print(f"Yüklenen Toplam Tool Sayısı: {len(tools)}")
    for name in tools:
        print(f" - Tool: {name}")

    # 2. Mock Weather Tool'u al ve çalıştır
    weather_tool = registry.get_tool("mock_weather")
    if weather_tool:
        print("\n'mock_weather' tool'u bulundu, çalıştırılıyor...")
        result = await weather_tool.execute(city="İstanbul")
        print(f"Çalıştırma Sonucu: {result}")
    else:
        print("\nHata: 'mock_weather' tool'u yüklenemedi!")

    # 3. Gerçek Tool'ları sadece yükleme bazlı kontrol et (API çağrısı yapmadan)
    for tool_name in ["search_tool", "flux_tool"]:
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"\n'{tool_name}' başarıyla yüklendi.")
            schema = tool.to_openai_function()
            print(f" - OpenAI Şeması: {schema['function']['name']} OK")
            print(f" - Açıklama: {schema['function']['description'][:50]}...")
        else:
            print(f"\nHata: '{tool_name}' yüklenemedi!")

    print("\n--- Test Tamamlandı ---")

if __name__ == "__main__":
    asyncio.run(main())
