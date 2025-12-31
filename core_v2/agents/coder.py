from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core_v2.services.llm_factory import llm_factory

class CoderAgent:
    def __init__(self):
        self.llm = llm_factory.create_model(model_name="llama3-70b-8192", temperature=0.1)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a senior python developer. Write clean, efficient code for the user's request."),
            ("user", "{input}")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def execute(self, task: str) -> str:
        return await self.chain.ainvoke({"input": task})

# Singleton
coder = CoderAgent()
