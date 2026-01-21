"""
FALLBACK MODEL TEST
-------------------
Goal: Verify moonshotai/kimi-k2-instruct works when primary fails
Method: Force primary model failure, observe fallback
"""

import sys
sys.path.insert(0, 'd:/ai/mami_ai_v4')

import asyncio
from unittest.mock import patch, AsyncMock


async def test_fallback_model():
    """Test fallback to moonshotai when llama-3.3-70b fails."""
    print("\n" + "="*80)
    print("🧪 FALLBACK MODEL TEST - moonshotai/kimi-k2-instruct")
    print("="*80)
    
    from app.services.brain.task_runner import task_runner
    from app.services.brain.intent import TaskSpec
    from app.providers.llm.groq import GroqProvider
    
    # Create synthesis task
    task = TaskSpec(
        id="t1",
        type="generation",
        specialist="logic",
        instruction="Python nedir kısaca açıkla",
        dependencies=[]
    )
    
    print("\n📋 Test Scenario:")
    print("   1. PRIMARY model: llama-3.3-70b-versatile (WILL FAIL)")
    print("   2. FALLBACK model: moonshotai/kimi-k2-instruct (SHOULD WORK)")
    
    # Track which models were called
    call_log = []
    
    original_generate = GroqProvider.generate
    
    async def mock_generate(self, **kwargs):
        """Mock that fails on primary, succeeds on fallback."""
        model = kwargs.get('model', 'unknown')
        call_log.append(model)
        
        print(f"\n   🔄 Attempting model: {model}")
        
        # Simulate primary failure
        if model == "llama-3.3-70b-versatile":
            print(f"      ❌ Simulated failure (primary)")
            raise Exception("Simulated API rate limit")
        
        # Fallback succeeds
        elif "moonshotai" in model or "kimi" in model:
            print(f"      ✅ Fallback model working")
            return """<thought>Fallback model kullanarak Python'u açıklıyorum.</thought>
Python, yüksek seviyeli bir programlama dilidir."""
        
        # Other models
        else:
            print(f"      ⚠️ Unexpected model: {model}")
            return await original_generate(self, **kwargs)
    
    # Patch GroqProvider.generate
    with patch.object(GroqProvider, 'generate', mock_generate):
        print("\n⏳ Running synthesis with fallback simulation...")
        
        try:
            result = await task_runner._execute_generation(
                task=task,
                intent="general",
                executed_tasks={},
                original_message="Python nedir?",
                session_id="test_fallback",
                user_id="test_user"
            )
            
            print("\n" + "="*80)
            print("📊 TEST RESULTS")
            print("="*80)
            
            # Analyze call log
            print(f"\n📝 Model Call Sequence:")
            for idx, model in enumerate(call_log, 1):
                status = "❌ FAILED" if model == "llama-3.3-70b-versatile" else "✅ SUCCESS"
                print(f"   {idx}. {model}: {status}")
            
            # Verify results
            model_used = result.get('model', 'UNKNOWN')
            thought = result.get('thought', '')
            output = result.get('output', '')
            status = result.get('status', 'UNKNOWN')
            
            print(f"\n💬 Final Response:")
            print(f"   Model Used: {model_used}")
            print(f"   Status: {status}")
            print(f"   Thought: \"{thought[:80]}...\"" if len(thought) > 80 else f"   Thought: \"{thought}\"")
            print(f"   Output: \"{output[:80]}...\"" if len(output) > 80 else f"   Output: \"{output}\"")
            
            # Verification
            print(f"\n🔍 Verification:")
            
            # Check primary was attempted
            primary_attempted = "llama-3.3-70b-versatile" in call_log
            print(f"   PRIMARY attempted: {'✅ YES' if primary_attempted else '❌ NO'}")
            
            # Check fallback was used
            fallback_used = any("moonshotai" in m or "kimi" in m for m in call_log)
            print(f"   FALLBACK used: {'✅ YES' if fallback_used else '❌ NO'}")
            
            # Check final model is fallback
            is_fallback_model = "moonshotai" in model_used or "kimi" in model_used
            print(f"   Final model is FALLBACK: {'✅ YES' if is_fallback_model else f'❌ NO ({model_used})'}")
            
            # Check response exists
            has_response = len(output) > 10
            print(f"   Response generated: {'✅ YES' if has_response else '❌ NO'}")
            
            # Final verdict
            print("\n" + "="*80)
            if primary_attempted and fallback_used and is_fallback_model and has_response:
                print("✅ FALLBACK TEST PASSED")
                print("="*80)
                print("\n💡 Conclusion:")
                print("   - PRIMARY model failed (simulated)")
                print("   - FALLBACK model took over")
                print("   - Response generated successfully")
                print("   - ModelGovernance chain working correctly")
            else:
                print("❌ FALLBACK TEST FAILED")
                print("="*80)
                if not fallback_used:
                    print("\n⚠️ Issue: Fallback model was NOT used")
                if not is_fallback_model:
                    print(f"\n⚠️ Issue: Final model is not fallback: {model_used}")
            
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()


async def test_end_to_end_flow():
    """Test complete flow: Router → Orchestrator → DAG → Synthesis."""
    print("\n" + "="*80)
    print("🧪 END-TO-END USER FLOW TEST")
    print("="*80)
    
    print("\n📋 Test Scenario:")
    print("   User Input: 'Python programlama dili nedir?'")
    print("   Expected Flow:")
    print("      1. Smart Router (intent detection)")
    print("      2. Orchestrator (DAG planning)")
    print("      3. Task Runner (execute plan)")
    print("      4. Synthesis (embedded thought)")
    
    print("\n⚠️ Note: This requires full system integration")
    print("   Skipping for now - requires running backend")
    
    # TODO: Implement when backend is running
    # from app.chat.smart_router import smart_router
    # async for chunk in smart_router.route_stream(...):
    #     print(chunk)


if __name__ == "__main__":
    print("\n" + "🚀"*40)
    print("NEXT STEP: FALLBACK MODEL VERIFICATION")
    print("🚀"*40)
    
    # Run fallback test
    asyncio.run(test_fallback_model())
    
    # End-to-end test (placeholder)
    asyncio.run(test_end_to_end_flow())
