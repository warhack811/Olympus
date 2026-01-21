from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator

class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Ensures a consistent interface across different backends (Groq, Gemini, Ollama).
    """
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> str:
        """
        Generates a text completion.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generates a streaming text completion.
        """
        yield ""
