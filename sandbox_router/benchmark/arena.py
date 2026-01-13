"""
ATLAS Router - Model Arena Engine
9 Modeli paralel çalıştıran benchmark motoru.
"""

import asyncio
import time
import uuid
import json
import httpx
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from sandbox_router.config import API_CONFIG

# Test edilecek 9 Model
ARENA_MODELS = [
    "groq/compound",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "moonshotai/kimi-k2-instruct",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b"
]


@dataclass
class ArenaResponse:
    model_id: str
    response: str
    latency_ms: float
    token_count: int
    tokens_per_sec: float
    error: Optional[str] = None
    
    # Skorlama
    ai_score: int = 0
    ai_reason: str = ""
    human_score: int = 0
    
    # Judge the Judge (Hakemi Değerlendirme)
    # 0: Yok, 1: Katılmıyorum (Kötü), 5: Katılıyorum (İyi)
    judge_verification: int = 0
    
    # Maliyet/Performans (örnek maliyet hesabı için)
    estimated_cost: float = 0.0

class ArenaEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _call_model(self, model_id: str, prompt: str, temperature: float = 0.5) -> ArenaResponse:
        """Tek bir modeli çağırır ve metrikleri ölçer."""
        start_time = time.time()
        try:
            # Kullanıcıdan gelen ID'yi olduğu gibi kullanıyoruz.
            # (Önceki split('/') mantığı bazı özel ID'leri (openai/gpt-oss...) bozduğu için kaldırıldı)
            
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 4096,
                "frequency_penalty": 0.1,  # Prevent word loops (Page Page Page...)
                "presence_penalty": 0.1,   # Encourage topic diversity
                "stop": ["<|header_end|>", "<|end_of_text|>", "<|eot_id|>", "assistant<|header_end|>"] # Block special tokens
            }
            
            # Qwen/DeepSeek: Show reasoning for visibility if requested
            if "qwen" in model_id.lower() or "deepseek" in model_id.lower():
                payload["reasoning_format"] = "hidden"

            response = await self.client.post(
                f"{API_CONFIG['groq_api_base']}/chat/completions",
                headers=self.headers,
                json=payload
            )
            
            duration = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return ArenaResponse(
                    model_id=model_id,
                    response="",
                    latency_ms=duration,
                    token_count=0,
                    tokens_per_sec=0,
                    error=f"API Error: {response.status_code} - {response.text}"
                )
                
            data = response.json()
            message = data["choices"][0]["message"]
            raw_content = message.get("content")
            
            # 1. Tool Call check
            if not raw_content and message.get("tool_calls"):
                raw_content = " ".join([tc.get("function", {}).get("arguments", "") for tc in message["tool_calls"]])

            # 2. Recursive Robust String Conversion
            def ensure_string(val):
                if val is None: return ""
                if isinstance(val, str): return val
                if isinstance(val, list):
                    return "\n".join([ensure_string(i) for i in val])
                if isinstance(val, dict):
                    # Try common text keys first
                    for key in ["text", "content", "input", "value", "thought"]:
                        if key in val: return ensure_string(val[key])
                    # Fallback: full JSON
                    return json.dumps(val, ensure_ascii=False)
                return str(val)

            content = ensure_string(raw_content).strip()
            
            # Fallback for empty
            if not content:
                content = "[HATA] Model boş veya işlenemeyen bir format döndürdü."
            
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Empty response check
            if not content or not content.strip():
                return ArenaResponse(
                    model_id=model_id,
                    response="",
                    latency_ms=duration,
                    token_count=0,
                    tokens_per_sec=0,
                    error="[EMPTY] Model boş cevap döndürdü."
                )
            
            # Token/sec hesabı
            tps = (completion_tokens / (duration / 1000)) if duration > 0 else 0
            
            return ArenaResponse(
                model_id=model_id,
                response=content,
                latency_ms=duration,
                token_count=completion_tokens,
                tokens_per_sec=tps
            )
            
        except Exception as e:
            return ArenaResponse(
                model_id=model_id,
                response="",
                latency_ms=(time.time() - start_time) * 1000,
                token_count=0,
                tokens_per_sec=0,
                error=str(e)
            )

    async def run_benchmark(self, prompt: str, category: str = "general") -> List[ArenaResponse]:
        """Tüm modelleri paralel çalıştırır (category-optimized temperature)."""
        from sandbox_router.config import ARENA_CATEGORY_TEMPERATURE
        
        # Lookup category-specific temperature
        temperature = ARENA_CATEGORY_TEMPERATURE.get(category, 0.5)
        
        tasks = [self._call_model(model, prompt, temperature) for model in ARENA_MODELS]
        return await asyncio.gather(*tasks)

    async def close(self):
        await self.client.aclose()
