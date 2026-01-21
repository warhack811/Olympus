"""
6-POINT COMPLETE LIVE TEST
---------------------------
Test ALL 6 integration points with REAL outputs
"""

import sys
sys.path.insert(0, 'd:/ai/mami_ai_v4')

import asyncio


async def test_all_6_points():
    """Test all 6 integration points and show REAL outputs."""
    
    print("\n" + "="*80)
    print("🧪 6-POINT COMPLETE LIVE TEST")
    print("="*80)
    
    results = {}
    
    # ========================================================================
    # POINT 1: SEARCH TOOL
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 1: SEARCH TOOL")
    print("─"*80)
    
    try:
        from app.services.brain.task_runner import task_runner
        from app.services.brain.context_enricher import context_enricher
        from app.services.brain.thought_generator import thought_generator
        
        # Context
        context1 = await context_enricher.get_user_context(
            "user_test",
            "Bitcoin fiyatı ne?",
            []
        )
        
        # Thought
        thought1 = await thought_generator.generate_thought(
            task_type="search",
            user_context=context1,
            action_params={"query": "Bitcoin fiyatı", "freshness": None},
            personality_mode="friendly"
        )
        
        results["point1_search"] = {
            "input": "Bitcoin fiyatı ne?",
            "context": context1,
            "thought": thought1
        }
        
        print(f"✅ INPUT: 'Bitcoin fiyatı ne?'")
        print(f"✅ CONTEXT: mood={context1['mood']}, expertise={context1['expertise_level']}")
        print(f"✅ THOUGHT: \"{thought1}\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point1_search"] = {"error": str(e)}
    
    # ========================================================================
    # POINT 2: DOCUMENT TOOL
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 2: DOCUMENT TOOL")
    print("─"*80)
    
    try:
        context2 = await context_enricher.get_user_context(
            "user_test",
            "Belgelerimde Python ara",
            []
        )
        
        thought2 = await thought_generator.generate_thought(
            task_type="document_query",
            user_context=context2,
            action_params={"query": "Python", "owner": "user_test"},
            personality_mode="friendly"
        )
        
        results["point2_document"] = {
            "input": "Belgelerimde Python ara",
            "context": context2,
            "thought": thought2
        }
        
        print(f"✅ INPUT: 'Belgelerimde Python ara'")
        print(f"✅ CONTEXT: mood={context2['mood']}, expertise={context2['expertise_level']}")
        print(f"✅ THOUGHT: \"{thought2}\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point2_document"] = {"error": str(e)}
    
    # ========================================================================
    # POINT 3: IMAGE GEN TOOL
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 3: IMAGE GEN TOOL")
    print("─"*80)
    
    try:
        context3 = await context_enricher.get_user_context(
            "user_test",
            "Kedi çiz",
            []
        )
        
        thought3 = await thought_generator.generate_thought(
            task_type="image_gen",
            user_context=context3,
            action_params={"prompt": "kedi", "style": "flux"},
            personality_mode="creative"
        )
        
        results["point3_image"] = {
            "input": "Kedi çiz",
            "context": context3,
            "thought": thought3
        }
        
        print(f"✅ INPUT: 'Kedi çiz'")
        print(f"✅ CONTEXT: mood={context3['mood']}, expertise={context3['expertise_level']}")
        print(f"✅ THOUGHT: \"{thought3}\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point3_image"] = {"error": str(e)}
    
    # ========================================================================
    # POINT 4: SYNTHESIS TASK (FULL TEST - REAL GROQ)
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 4: SYNTHESIS TASK (REAL GROQ API)")
    print("─"*80)
    
    try:
        from app.services.brain.intent import TaskSpec
        
        task4 = TaskSpec(
            id="t_synth",
            type="generation",
            specialist="logic",
            instruction="Python programlama dilini 2 cümlede açıkla",
            dependencies=[]
        )
        
        result4 = await task_runner._execute_generation(
            task=task4,
            intent="general",
            executed_tasks={},
            original_message="Python nedir?",
            session_id="test_sess_4",
            user_id="user_test"
        )
        
        results["point4_synthesis"] = {
            "input": "Python nedir?",
            "model_used": result4.get("model"),
            "thought": result4.get("thought"),
            "output": result4.get("output")
        }
        
        print(f"✅ INPUT: 'Python nedir?'")
        print(f"✅ MODEL USED: {result4.get('model')}")
        print(f"✅ THOUGHT: \"{result4.get('thought')[:100]}...\"")
        print(f"✅ OUTPUT: \"{result4.get('output')[:150]}...\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point4_synthesis"] = {"error": str(e)}
    
    # ========================================================================
    # POINT 5: MEMORY WRITE
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 5: MEMORY WRITE")
    print("─"*80)
    
    try:
        context5 = await context_enricher.get_user_context(
            "user_test",
            "Python'u seviyorum",
            []
        )
        
        thought5 = await thought_generator.generate_thought(
            task_type="memory_write",
            user_context=context5,
            action_params={
                "predicate": "SEVER",
                "object": "Python",
                "decision": "LONG_TERM"
            },
            personality_mode="friendly"
        )
        
        results["point5_memory"] = {
            "input": "Python'u seviyorum",
            "context": context5,
            "thought": thought5
        }
        
        print(f"✅ INPUT: 'Python'u seviyorum'")
        print(f"✅ CONTEXT: mood={context5['mood']}, expertise={context5['expertise_level']}")
        print(f"✅ THOUGHT: \"{thought5}\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point5_memory"] = {"error": str(e)}
    
    # ========================================================================
    # POINT 6: ORCHESTRATOR PLANNING
    # ========================================================================
    print("\n" + "─"*80)
    print("POINT 6: ORCHESTRATOR PLANNING")
    print("─"*80)
    
    try:
        context6 = await context_enricher.get_user_context(
            "user_test",
            "Bitcoin fiyatını öğrenmek istiyorum",
            []
        )
        
        thought6 = await thought_generator.generate_thought(
            task_type="intent_planning",
            user_context=context6,
            action_params={
                "message": "Bitcoin fiyatını öğrenmek istiyorum",
                "detected_intent": "search"
            },
            personality_mode="friendly"
        )
        
        results["point6_orchestrator"] = {
            "input": "Bitcoin fiyatını öğrenmek istiyorum",
            "context": context6,
            "thought": thought6
        }
        
        print(f"✅ INPUT: 'Bitcoin fiyatını öğrenmek istiyorum'")
        print(f"✅ CONTEXT: mood={context6['mood']}, expertise={context6['expertise_level']}")
        print(f"✅ THOUGHT: \"{thought6}\"")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results["point6_orchestrator"] = {"error": str(e)}
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("📊 6-POINT TEST SUMMARY")
    print("="*80)
    
    for point, data in results.items():
        status = "✅ PASS" if "error" not in data else f"❌ FAIL: {data['error']}"
        print(f"{point}: {status}")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_all_6_points())
    
    print("\n" + "="*80)
    print("✅ 6-POINT TEST COMPLETE")
    print("="*80)
