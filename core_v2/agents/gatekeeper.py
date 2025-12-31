from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core_v2.services.llm_factory import llm_factory
from core_v2.orchestrator.states import PlanExecute

class GatekeeperAgent:
    def __init__(self):
        self.llm = llm_factory.create_model(temperature=0.2)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Gatekeeper of the Olympus AI System.
Your job is to analyze the user's request and create a high-level execution plan.

OUTPUT FORMAT (JSON):
{{
    "classification": "chat" | "complex_task",
    "reasoning": "brief explanation",
    "plan": ["step 1", "step 2"] 
}}

If the request is simple chat, the plan should be empty or ["respond directly"].
If the request is complex, break it down into steps.
"""),
            ("user", "{input}")
        ])
        
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def analyze(self, state: PlanExecute) -> dict:
        user_input = state["input"]
        result = await self.chain.ainvoke({"input": user_input})
        
        # Normalize output for the graph state
        classification = result.get("classification", "chat")
        steps = result.get("plan", [])
        
        if classification == "chat" and not steps:
            steps = ["respond_directly"]
            
        return {"plan": steps}

# Singleton instance
gatekeeper = GatekeeperAgent()
