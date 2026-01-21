"""
COMPREHENSIVE PRODUCTION TEST
------------------------------
Test: Model Governance + Thought System
Goal: Verify ModelGovernance usage, no fallback, detailed logging
"""

import sys
sys.path.insert(0, 'd:/ai/mami_ai_v4')

import asyncio
import json
from typing import Dict, Any


class ProductionTestLogger:
    """Detailed test logger for production verification."""
    
    def __init__(self):
        self.steps = []
    
    def log_step(self, step_name: str, data: Dict[str, Any]):
        """Log a test step with detailed data."""
        self.steps.append({
            "step": step_name,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        for idx, step in enumerate(self.steps, 1):
            print(f"\n{'─'*80}")
            print(f"STEP {idx}: {step['step']}")
            print(f"{'─'*80}")
            
            for key, value in step['data'].items():
                if isinstance(value, str) and len(value) > 200:
                    print(f"  {key}: {value[:200]}...")
                elif isinstance(value, list):
                    print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"  {key}: {value}")


logger = ProductionTestLogger()


async def test_model_governance():
    """Test 1: Verify ModelGovernance is used correctly."""
    print("\n" + "="*80)
    print("🧪 TEST 1: MODEL GOVERNANCE VERIFICATION")
    print("="*80)
    
    from app.core.llm.governance import governance
    
    # Test logic chain
    logic_chain = governance.get_model_chain("logic")
    
    logger.log_step("ModelGovernance - Logic Chain", {
        "role": "logic",
        "chain": logic_chain,
        "primary": logic_chain[0] if logic_chain else None,
        "fallbacks": logic_chain[1:] if len(logic_chain) > 1 else []
    })
    
    print(f"\n✅ Logic Chain Retrieved:")
    print(f"   PRIMARY: {logic_chain[0]}")
    for idx, fallback in enumerate(logic_chain[1:], 1):
        print(f"   FALLBACK {idx}: {fallback}")
    
    # Test provider detection
    primary_provider = governance.detect_provider(logic_chain[0])
    
    logger.log_step("Provider Detection", {
        "model": logic_chain[0],
        "provider": primary_provider
    })
    
    print(f"\n✅ Provider Detected: {primary_provider}")
    
    assert len(logic_chain) > 0, "❌ Logic chain is empty!"
    assert logic_chain[0] == "llama-3.3-70b-versatile", f"❌ Wrong primary model: {logic_chain[0]}"
    assert primary_provider == "groq", f"❌ Wrong provider: {primary_provider}"
    
    print("\n✅ MODEL GOVERNANCE TEST PASSED")
    return logic_chain


async def test_synthesis_with_thought():
    """Test 2: Synthesis task with embedded thought (REAL Groq call)."""
    print("\n" + "="*80)
    print("🧪 TEST 2: SYNTHESIS + EMBEDDED THOUGHT (REAL API)")
    print("="*80)
    
    from app.services.brain.task_runner import task_runner
    from app.services.brain.intent import TaskSpec
    
    # Create synthesis task
    task = TaskSpec(
        id="t1",
        type="generation",
        specialist="logic",  # Will use MODEL_GOVERNANCE["logic"]
        instruction="Python programlama dilini 2 cümlede açıkla",
        dependencies=[]
    )
    
    user_input = "Python nedir?"
    
    logger.log_step("Synthesis Input", {
        "task_id": task.id,
        "task_type": task.type,
        "specialist": task.specialist,
        "instruction": task.instruction,
        "user_message": user_input
    })
    
    print(f"\n📝 Input:")
    print(f"   User: '{user_input}'")
    print(f"   Task: {task.type}")
    print(f"   Specialist: {task.specialist}")
    
    print(f"\n⏳ Calling Groq API (ModelGovernance chain)...")
    
    try:
        result = await task_runner._execute_generation(
            task=task,
            intent="general",
            executed_tasks={},
            original_message=user_input,
            session_id="test_session_001",
            user_id="test_user_123"
        )
        
        # Extract details
        thought = result.get('thought', '')
        output = result.get('output', '')
        model_used = result.get('model', 'UNKNOWN')
        status = result.get('status', 'UNKNOWN')
        
        logger.log_step("Synthesis Output", {
            "model_used": model_used,
            "status": status,
            "thought_exists": bool(thought),
            "thought_length": len(thought),
            "thought_preview": thought[:100] if thought else "NO THOUGHT",
            "output_length": len(output),
            "output_preview": output[:200] if output else "NO OUTPUT"
        })
        
        print(f"\n✅ SUCCESS - Groq API Response:")
        print(f"   Model Used: {model_used}")
        print(f"   Status: {status}")
        
        print(f"\n💭 Thought (Embedded):")
        print(f"   Length: {len(thought)} chars")
        print(f"   Content: \"{thought[:150]}...\"" if len(thought) > 150 else f"   Content: \"{thought}\"")
        
        print(f"\n💬 Output (Clean):")
        print(f"   Length: {len(output)} chars")
        print(f"   Content: \"{output[:250]}...\"" if len(output) > 250 else f"   Content: \"{output}\"")
        
        # Verification
        print(f"\n🔍 Verification:")
        
        # Check model used
        from app.core.constants import MODEL_GOVERNANCE
        expected_models = MODEL_GOVERNANCE.get("logic", [])
        is_correct_model = model_used in expected_models
        print(f"   Model in governance chain: {'✅ YES' if is_correct_model else f'❌ NO (used {model_used})'}")
        
        # Check thought exists
        has_thought = len(thought) > 10
        print(f"   Thought generated: {'✅ YES' if has_thought else '❌ NO'}")
        
        # Check output is clean
        is_clean = '<thought>' not in output
        print(f"   Output cleaned: {'✅ YES' if is_clean else '❌ NO'}")
        
        # Check not fallback
        is_primary = model_used == expected_models[0]
        print(f"   Used PRIMARY model: {'✅ YES' if is_primary else f'⚠️ NO (fallback: {model_used})'}")
        
        assert is_correct_model, f"❌ Model not in governance: {model_used}"
        assert has_thought, "❌ No thought generated"
        assert is_clean, "❌ Output not cleaned"
        
        print("\n✅ SYNTHESIS + THOUGHT TEST PASSED")
        
        return result
        
    except Exception as e:
        logger.log_step("Synthesis Error", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


async def test_context_enrichment():
    """Test 3: Context enricher for thought personalization."""
    print("\n" + "="*80)
    print("🧪 TEST 3: CONTEXT ENRICHMENT")
    print("="*80)
    
    from app.services.brain.context_enricher import context_enricher
    
    test_message = "Python çalışmıyor hata veriyor yardım"
    
    logger.log_step("Context Enrichment Input", {
        "user_id": "test_user_123",
        "message": test_message
    })
    
    print(f"\n📝 Input:")
    print(f"   Message: '{test_message}'")
    
    context = await context_enricher.get_user_context(
        user_id="test_user_123",
        message=test_message,
        history=[]
    )
    
    logger.log_step("Context Enrichment Output", {
        "mood": context.get('mood'),
        "expertise_level": context.get('expertise_level'),
        "recent_topic": context.get('recent_topic'),
        "follow_up_count": context.get('follow_up_count')
    })
    
    print(f"\n✅ Context Extracted:")
    print(f"   Mood: {context.get('mood')}")
    print(f"   Expertise: {context.get('expertise_level')}")
    print(f"   Topic: {context.get('recent_topic')}")
    
    assert context.get('mood') in ['frustrated', 'neutral', 'curious', 'excited'], f"Invalid mood: {context.get('mood')}"
    assert context.get('expertise_level') in ['beginner', 'intermediate', 'expert'], f"Invalid expertise: {context.get('expertise_level')}"
    
    print("\n✅ CONTEXT ENRICHMENT TEST PASSED")
    
    return context


async def test_fallback_templates():
    """Test 4: Verify fallback templates for non-LLM tools."""
    print("\n" + "="*80)
    print("🧪 TEST 4: FALLBACK TEMPLATES (Search/Document/Image)")
    print("="*80)
    
    from app.services.brain.thought_generator import ThoughtGenerator
    
    # Test search fallback
    search_thought = ThoughtGenerator._fallback_template("search", {"query": "Bitcoin"})
    
    logger.log_step("Fallback Template - Search", {
        "task_type": "search",
        "params": {"query": "Bitcoin"},
        "thought": search_thought
    })
    
    print(f"\n✅ Search Fallback:")
    print(f"   \"{search_thought}\"")
    
    # Test document fallback
    doc_thought = ThoughtGenerator._fallback_template("document_query", {"query": "Python"})
    
    logger.log_step("Fallback Template - Document", {
        "task_type": "document_query",
        "params": {"query": "Python"},
        "thought": doc_thought
    })
    
    print(f"\n✅ Document Fallback:")
    print(f"   \"{doc_thought}\"")
    
    assert "Bitcoin" in search_thought, "Search thought doesn't contain query"
    assert len(doc_thought) > 5, "Document thought too short"
    
    print("\n✅ FALLBACK TEMPLATES TEST PASSED")


async def run_all_tests():
    """Run all production tests."""
    print("\n" + "🚀"*40)
    print("PRODUCTION TEST SUITE - MODEL GOVERNANCE & THOUGHT SYSTEM")
    print("🚀"*40)
    
    try:
        # Test 1: Model Governance
        logic_chain = await test_model_governance()
        
        # Test 2: Synthesis + Thought (REAL API)
        synthesis_result = await test_synthesis_with_thought()
        
        # Test 3: Context Enrichment
        context = await test_context_enrichment()
        
        # Test 4: Fallback Templates
        await test_fallback_templates()
        
        # Print summary
        logger.print_summary()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - PRODUCTION READY")
        print("="*80)
        
        # Next steps
        print("\n📋 NEXT STEPS:")
        print("   1. End-to-end user flow test (full router → DAG → synthesis)")
        print("   2. Test fallback model (moonshotai/kimi-k2-instruct)")
        print("   3. A/B test: embedded thoughts vs templates")
        print("   4. Monitor thought extraction success rate")
        print("   5. Production deployment")
        
    except Exception as e:
        logger.print_summary()
        print(f"\n❌ TESTS FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
