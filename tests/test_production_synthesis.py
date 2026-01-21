"""
PRODUCTION LIVE TEST - Embedded Thought System
-----------------------------------------------
Real Groq API call with embedded synthesis thought.
"""

import sys
sys.path.insert(0, 'd:/ai/mami_ai_v4')

import asyncio


async def test_synthesis_embedded_thought():
    """Test synthesis task with embedded thought."""
    print("\n" + "="*70)
    print("🧪 PRODUCTION LIVE TEST - SYNTHESIS EMBEDDED THOUGHT")
    print("="*70)
    
    from app.services.brain.task_runner import task_runner
    from app.services.brain.intent import TaskSpec
    
    # Simulate synthesis task
    task = TaskSpec(
        id="t1",
        type="generation",
        specialist="logic",
        instruction="Python nedir basit bir şekilde açıkla",
        dependencies=[]
    )
    
    executed_tasks = {}  # No prior tools
    
    print("\n📋 Test Scenario:")
    print("   Task: Synthesis (generation)")
    print("   User ID: test_user_123")
    print("   Message: 'Python nedir?'")
    print("   Expected: Embedded <thought> in response")
    
    print("\n⏳ Calling Groq API...")
    
    try:
        result = await task_runner._execute_generation(
            task=task,
            intent="general",
            executed_tasks=executed_tasks,
            original_message="Python nedir?",
            session_id="test_session",
            user_id="test_user_123"
        )
        
        print("\n✅ SUCCESS! Groq API Response:")
        print("-" * 70)
        
        print(f"\n📝 Thought:")
        print(f"   \"{result.get('thought', 'NO THOUGHT')[:200]}...\"")
        
        print(f"\n💬 Clean Output (first 300 chars):")
        output = result.get('output', 'NO OUTPUT')
        print(f"   \"{output[:300]}...\"")
        
        print(f"\n📊 Metrics:")
        print(f"   - Model: {result.get('model')}")
        print(f"   - Status: {result.get('status')}")
        print(f"   - Duration: {result.get('duration_ms')}ms")
        
        # Verify thought exists
        assert result.get('thought'), "❌ NO THOUGHT GENERATED"
        assert len(result.get('thought', '')) > 10, "❌ THOUGHT TOO SHORT"
        
        # Verify output is clean (no <thought> tags)
        assert '<thought>' not in output, "❌ OUTPUT NOT CLEANED"
        
        print("\n" + "="*70)
        print("✅ ALL CHECKS PASSED - PRODUCTION READY")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_synthesis_embedded_thought())
