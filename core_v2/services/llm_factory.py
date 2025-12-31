from typing import Optional, List
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
from core_v2.config.settings import settings
from core_v2.services.key_manager import KeyManager

class LLMFactory:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMFactory, cls).__new__(cls)
            cls._instance.key_manager = KeyManager()
        return cls._instance

    def create_model(self, model_name: str = "llama3-70b-8192", temperature: float = 0.7) -> BaseChatModel:
        """
        Create a LangChain Chat Model (Groq default).
        Uses KeyManager for rotation.
        """
        api_key = self.key_manager.get_next_key()
        
        return ChatGroq(
            temperature=temperature,
            model_name=model_name,
            api_key=api_key,
            max_retries=2
        )

# Global factory instance
llm_factory = LLMFactory()
