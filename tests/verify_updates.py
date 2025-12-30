import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock modules that might cause import errors or side effects
sys.modules["app.core.database"] = MagicMock()
sys.modules["chromadb"] = MagicMock()

from app.ai.prompts.compiler import _get_user_prefs_prompt
from app.memory.store import add_memory


async def test_style_compilation():
    print("\n=== TESTING STYLE COMPILATION ===")

    scenarios = [
        {
            "name": "Professional + Low Emoji",
            "profile": {"tone": "professional", "emoji_level": "low"},
            "checks": ["Profesyonel, iş odaklı", "Çok nadir kullan"],
        },
        {
            "name": "Formal + None Emoji",
            "profile": {"tone": "formal", "emoji_level": "none"},
            "checks": ["Resmi, mesafeli", "ASLA emoji kullanma"],
        },
        {
            "name": "Playful + High Emoji",
            "profile": {"tone": "playful", "emoji_level": "high"},
            "checks": ["Eğlenceli, enerjik", "Canlı ve renkli"],
        },
    ]

    for sc in scenarios:
        print(f"Testing: {sc['name']}...", end=" ")
        # We assume _get_user_prefs_prompt takes (user, style_profile, persona_metadata)
        # passing None for user/persona as we test raw style mapping
        try:
            prompt = _get_user_prefs_prompt(None, sc["profile"], None) or ""

            all_passed = True
            for check in sc["checks"]:
                if check not in prompt:
                    print(f"\n[FAIL] Missing phrase: '{check}'")
                    print(f"Generated Prompt:\n{prompt}")
                    all_passed = False

            if all_passed:
                print("[PASS]")
        except Exception as e:
            print(f"\n[ERROR] {e}")


async def test_memory_layer():
    print("\n=== TESTING MEMORY LAYER PIPELINE ===")

    # We want to verify that add_memory correctly passes 'memory_type' and 'topic'
    # to the underlying MemoryService.

    with patch("app.memory.store._get_memory_service") as mock_get_service:
        # User resolver mock
        with patch("app.memory.store._resolve_user_id", return_value=123):
            # Setup the mock service
            MagicMock()
            mock_service_class = MagicMock()
            mock_get_service.return_value = (mock_service_class, None)

            # Setup async add_memory return on the service class
            # Since MemoryService.add_memory is async, we need the mock to return a future or be awaitable?
            # Actually typically calls directly if mocked cleanly, but let's see.
            # If the code does `await MemoryService.add_memory(...)`, output matches return value.

            # Since `MemoryService` is a class with static/class methods or instance methods?
            # In store.py: `MemoryService, _ = _get_memory_service()` then `await MemoryService.add_memory(...)`
            # So MemoryService is the class/obj.

            async def mock_add_memory(**kwargs):
                return MagicMock(id="mem_123", text=kwargs.get("text"))

            mock_service_class.add_memory = MagicMock(side_effect=mock_add_memory)

            # TEST CASE: Event Memory
            print("Testing add_memory(type='event')...", end=" ")
            await add_memory(username="test_user", text="Meeting tomorrow", memory_type="event", topic="schedule")

            # Verify call args
            calls = mock_service_class.add_memory.call_args_list
            if not calls:
                print("[FAIL] MemoryService.add_memory was not called.")
                return

            args, kwargs = calls[0]

            if kwargs.get("memory_type") == "event" and kwargs.get("topic") == "schedule":
                print("[PASS]")
            else:
                print(f"[FAIL] Called with: {kwargs}")

            # TEST CASE: Default (Fact)
            print("Testing add_memory(defaults)...", end=" ")
            mock_service_class.add_memory.reset_mock()
            await add_memory(username="test_user", text="I like cats")

            args, kwargs = mock_service_class.add_memory.call_args_list[0]
            # Default in store.py signature logic
            # memory_type default="fact", topic default derived from tags or "general"
            if kwargs.get("memory_type") == "fact" and kwargs.get("topic") == "general":
                print("[PASS]")
            else:
                print(f"[FAIL] Defaults incorrect. Called with: {kwargs}")


async def main():
    await test_style_compilation()
    await test_memory_layer()


if __name__ == "__main__":
    asyncio.run(main())
