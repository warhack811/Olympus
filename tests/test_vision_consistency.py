
from sandbox_router.memory.context import ContextBuilder
from sandbox_router.prompts import ORCHESTRATOR_PROMPT, VISION_INJECTION_PROMPT

def test_imports():
    print("Testing imports...")
    try:
        cb = ContextBuilder("test-session")
        print("ContextBuilder imported successfully.")
        print(f"VISION_INJECTION_PROMPT length: {len(VISION_INJECTION_PROMPT)}")
        if "[SİSTEM ANALİZİ - GÖRSEL" in ORCHESTRATOR_PROMPT:
            print("Orchestrator prompt contains vision rule.")
        else:
            print("CRITICAL: Orchestrator prompt is MISSING the vision rule!")
    except Exception as e:
        print(f"Import Error: {e}")

if __name__ == "__main__":
    test_imports()
