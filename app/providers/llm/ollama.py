"""
Ollama provider adapter for LLMGenerator.

Supports local Ollama models with automatic fallback handling.
"""
from __future__ import annotations

import logging
import aiohttp
import json
from typing import Any, AsyncGenerator, Dict, Optional

from app.core.llm.generator import LLMRequest

logger = logging.getLogger("app.providers.llm.ollama")


async def ollama_adapter(
    model_id: str,
    api_key: str,
    request: LLMRequest,
    stream: bool = False
) -> Any:
    """
    Ollama API adapter for LLMGenerator.
    
    Args:
        model_id: Ollama model name (e.g., "llama3.2", "mistral")
        api_key: Not used for Ollama (local deployment)
        request: LLMRequest object with prompt/messages
        stream: Whether to stream the response
        
    Returns:
        Response object with .text and .tokens attributes
    """
    
    # Ollama base URL (configurable via environment)
    base_url = "http://localhost:11434"
    
    # Prepare messages for chat completion
    messages = []
    
    if request.messages:
        messages = request.messages
    elif request.prompt:
        messages = [{"role": "user", "content": request.prompt}]
    else:
        raise ValueError("Either prompt or messages must be provided")
    
    # Prepare request payload
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": request.temperature or 0.7,
        "stream": stream
    }
    
    if not stream:
        # Non-streaming request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30.0)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Ollama API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # Extract response text
                    response_text = result.get("message", {}).get("content", "")
                    
                    # Create response object
                    class Response:
                        def __init__(self, text: str, tokens: int = 0):
                            self.text = text
                            self.tokens = tokens
                    
                    return Response(response_text, tokens=0)
                    
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise
    
    else:
        # Streaming request
        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{base_url}/api/chat",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30.0)
                    ) as response:
                        
                        if response.status != 200:
                            error_text = await response.text()
                            raise RuntimeError(f"Ollama API error {response.status}: {error_text}")
                        
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line.decode('utf-8'))
                                    if 'message' in chunk and 'content' in chunk['message']:
                                        yield chunk['message']['content']
                                except json.JSONDecodeError:
                                    continue
            
            except Exception as e:
                logger.error(f"Ollama streaming failed: {e}")
                raise
        
        return stream_generator()


async def ollama_adapter_stream(
    model_id: str,
    api_key: str,
    request: LLMRequest
) -> AsyncGenerator[str, None]:
    """Streaming version of ollama_adapter."""
    async for chunk in ollama_adapter(model_id, api_key, request, stream=True):
        yield chunk