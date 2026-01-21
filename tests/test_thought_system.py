"""
Dynamic Thought System Unit Tests
----------------------------------
Simple tests without LLM dependencies.
"""

import sys
sys.path.insert(0, 'd:/ai/mami_ai_v4')

import asyncio


def test_context_enricher():
    """Test context enrichment (mood, expertise detection)."""
    from app.services.brain.context_enricher import ContextEnricher
    
    # Test frustrated mood
    mood = ContextEnricher._detect_mood("Python çalışmıyor hata veriyor yardım")
    assert mood == "frustrated", f"Expected frustrated, got {mood}"
    print("✅ Frustrated mood detected")
    
    # Test curious mood
    mood2 = ContextEnricher._detect_mood("Merak ediyorum Python nasıl çalışır")
    assert mood2 == "curious", f"Expected curious, got {mood2}"
    print("✅ Curious mood detected")
    
    # Test expertise detection
    expertise = ContextEnricher._detect_expertise("async await promise callback api")
    assert expertise == "expert", f"Expected expert, got {expertise}"
    print("✅ Expert level detected")
    
    # Test beginner
    expertise2 = ContextEnricher._detect_expertise("Merhaba")
    assert expertise2 == "beginner", f"Expected beginner, got {expertise2}"
    print("✅ Beginner level detected")


def test_thought_fallback():
    """Test thought fallback templates."""
    from app.services.brain.thought_generator import ThoughtGenerator
    
    # Test search fallback
    fallback = ThoughtGenerator._fallback_template("search", {"query": "Bitcoin"})
    assert "Bitcoin" in fallback
    print(f"✅ Search fallback: {fallback}")
    
    # Test image fallback
    fallback2 = ThoughtGenerator._fallback_template("image_gen", {"prompt": "ejderha"})
    assert len(fallback2) > 5
    print(f"✅ Image fallback: {fallback2}")
    
    # Test unknown type (should return default)
    fallback3 = ThoughtGenerator._fallback_template("unknown", {})
    assert "devam" in fallback3.lower()
    print(f"✅ Default fallback: {fallback3}")


def test_cache_key_generation():
    """Test cache key determinism."""
    from app.services.brain.thought_generator import ThoughtGenerator
    
    context1 = {"mood": "neutral", "expertise_level": "intermediate"}
    params1 = {"query": "test"}
    
    key1 = ThoughtGenerator._generate_cache_key("search", context1, params1)
    key2 = ThoughtGenerator._generate_cache_key("search", context1, params1)
    
    assert key1 == key2, "Cache keys should be deterministic"
    print(f"✅ Cache key generated: {key1}")
    
    # Different context = different key
    context2 = {"mood": "frustrated", "expertise_level": "beginner"}
    key3 = ThoughtGenerator._generate_cache_key("search", context2, params1)
    
    assert key3 != key1, "Different context should generate different key"
    print(f"✅ Different context → different key: {key3}")


def test_prompts_builder():
    """Test thought prompt builder."""
    from app.core.prompts import build_thought_prompt
    
    prompt = build_thought_prompt(
        task_type="search",
        user_context={"mood": "frustrated", "expertise_level": "beginner", "recent_topic": "Python"},
        action_params={"query": "Python hata"},
        personality_mode="friendly"
    )
    
    assert len(prompt) > 100
    assert "frustrated" in prompt or "Anlıyorum" in prompt
    assert "Python" in prompt
    print("✅ Prompt builder works")
    
    # Test different task types
    prompt2 = build_thought_prompt(
        task_type="synthesis",
        user_context={"mood": "neutral", "expertise_level": "expert", "recent_topic": "genel"},
        action_params={"tool_count": 2, "tools_used": ["search", "document"]},
        personality_mode="professional"
    )
    
    assert "sentez" in prompt2.lower() or "synthesis" in prompt2.lower()
    print("✅ Synthesis prompt works")


def test_task_runner_helper():
    """Test task runner helper method."""
    from app.services.brain.task_runner import task_runner
    
    # Test task summarizer
    executed_tasks = {
        "t1": {"tool_name": "search_tool", "type": "tool"},
        "t2": {"tool_name": "document_tool", "type": "tool"},
        "t3": {"tool_name": "flux_tool", "type": "tool"}
    }
    
    summary = task_runner._summarize_executed_tasks(executed_tasks)
    assert "web" in summary.lower()
    assert "belge" in summary.lower()
    assert "görsel" in summary.lower()
    print(f"✅ Task summary: {summary}")
    
    # Empty tasks
    summary2 = task_runner._summarize_executed_tasks({})
    assert "veri" in summary2.lower()
    print(f"✅ Empty task summary: {summary2}")


if __name__ == "__main__":
    print("\n🧪 Running Dynamic Thought System Tests (LLM-free)...\n")
    
    try:
        test_context_enricher()
        test_thought_fallback()
        test_cache_key_generation()
        test_prompts_builder()
        test_task_runner_helper()
        
        print("\n✅ ALL TESTS PASSED! Dynamic thought system foundations working.\n")
        print("💡 Note: LLM integration tests skipped (requires Groq API).\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
