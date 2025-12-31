from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
from .states import PlanExecute, AgentState

# Placeholder functions for nodes (to be implemented strictly in agents/)
from core_v2.agents.gatekeeper import gatekeeper

async def gatekeeper_node(state: PlanExecute):
    return await gatekeeper.analyze(state)

from core_v2.agents.coder import coder

async def planner_node(state: PlanExecute):
    # Pass-through for now, as Gatekeeper creates the plan
    return {}

async def executor_node(state: PlanExecute):
    plan = state.get("plan", [])
    results = []
    
    for step in plan:
        if step == "respond_directly":
            continue
        # Execute each step with Coder
        res = await coder.execute(step)
        results.append((step, res))
        
    return {"past_steps": results}

async def responder_node(state: PlanExecute):
    return {"response": "This is a placeholder response."}

def create_graph():
    workflow = StateGraph(PlanExecute)

    # Add nodes
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("responder", responder_node)

    # Define edges
    workflow.set_entry_point("gatekeeper")
    workflow.add_edge("gatekeeper", "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "responder")
    workflow.add_edge("responder", END)

    return workflow.compile()
