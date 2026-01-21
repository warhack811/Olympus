import asyncio
import sys
import json
from pathlib import Path

# Fix python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.brain.intent import analyze
from app.services.brain.request_context import RequestContext

async def test_planning():
    print("--- INTENT PLANNING TEST ---")
    user_id = "test_user"
    msg = "Bugünkü Bitcoin fiyatı nedir ve Trump hakkında son haberler neler?"
    
    print(f"Message: {msg}")
    
    # Analyze with LLM
    plan = await analyze(user_id, msg, use_llm=True)
    
    print(f"\nPlan Intent: {plan.intent}")
    print(f"Plan Reasoning: {plan.reasoning}")
    print(f"Orchestrator Model: {plan.orchestrator_model}")
    print(f"Tasks Count: {len(plan.tasks)}")
    
    for i, task in enumerate(plan.tasks):
        print(f"\nTask {i+1} [{task.id}]:")
        print(f"  Type: {task.type}")
        print(f"  Tool: {task.tool_name}")
        print(f"  Instruction: {task.instruction}")
        print(f"  Params: {task.params}")
        print(f"  Deps: {task.dependencies}")

if __name__ == "__main__":
    asyncio.run(test_planning())
