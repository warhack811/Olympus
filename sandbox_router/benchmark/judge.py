"""
ATLAS Router - Arena Judge
Yanıtları puanlayan AI Hakem (Gemini Pro/Flash - Modern SDK v1.0).
"""

import json
import logging
import asyncio
from typing import Dict, Any, List
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions
from sandbox_router.config import API_CONFIG, get_gemini_api_key

logger = logging.getLogger(__name__)

# Default Judge Provider
DEFAULT_PROVIDER = "gemini" 

# Models
GROQ_JUDGE_MODEL = "llama-3.3-70b-versatile"
GEMINI_JUDGE_MODEL = "gemini-2.0-flash"

class ArenaJudge:
    def __init__(self, api_key: str = None, provider: str = DEFAULT_PROVIDER):
        self.provider = provider
        self.api_key = api_key
        self._gemini_client = None
        
        if provider == "gemini":
            gemini_key = get_gemini_api_key()
            if not gemini_key:
                logger.warning("Gemini API Key missing! Fallback to Groq.")
                self.provider = "groq"
            else:
                self.api_key = gemini_key
                # Initialize Google GenAI Client
                self._gemini_client = genai.Client(api_key=self.api_key)
        else:
            self.api_key = api_key

    async def grade_response(self, question: str, response: str, category: str) -> Dict[str, Any]:
        """Bir yanıtı puanla."""
        
        prompt = f"""
Sen uzman bir AI değerlendiricisin. Aşağıdaki soruya verilen yanıtı 1 ile 10 arasında puanla.

SORU: {question}
KATEGORİ: {category}

MODEL YANITI:
{response}

DEĞERLENDİRME KRİTERLERİ:
1. Doğruluk: Bilgi doğru mu?
2. Format: İstenen formatta mı?
3. Dil: Türkçe akıcı ve hatasız mı?
4. Kapsam: Soru tam olarak cevaplanmış mı?

ÖNEMLİ: Yanıtı SADECE geçerli bir JSON objesi olarak döndür. Markdown backticks kullanma.
ÇIKTI FORMATI:
{{
    "score": 8,
    "reason": "Genel olarak akıcı ancak X detayı eksik olduğu için 2 puan kırıldı."
}}
"""
        if self.provider == "gemini":
            return await self._grade_with_gemini(prompt)
        else:
            return await self._grade_with_groq(prompt)

    async def grade_batch(self, question: str, responses: List[Dict[str, Any]], category: str) -> Dict[str, Any]:
        """
        Birden fazla yanıtı aynı anda karşılaştırmalı puanla (Blind Test).
        """
        import random
        
        # Shuffle responses to prevent positional bias
        indexed_responses = [(i, res) for i, res in enumerate(responses)]
        random.shuffle(indexed_responses)
        
        formatted_responses = ""
        for shuffled_idx, (original_idx, res) in enumerate(indexed_responses):
            formatted_responses += f"--- MODEL {shuffled_idx+1} ---\n{res['response']}\n\n"

        prompt = f"""
Sen 'Adalet Divanı' adına çalışan tarafsız, uzman bir karşılaştırmalı değerlendirme AI'sısın.
Aşağıda bir soru ve buna farklı AI modelleri tarafından verilmiş {len(responses)} farklı yanıt var.

SORU: {question}
KATEGORİ: {category}

YANITLAR:
{formatted_responses}

GÖREVİN:
1. Her yanıtı 1-10 arasında puanla (Ondalıklı puan verebilirsin, örn: 8.5).
2. En iyi yanıtı ve en kötü yanıtı belirle.
3. GEREKÇE FORMATI:
   - Eğer puan 10 değilse, MUTLAKA "Neden X puan kırdığını" belirt.
   - Sadece övgü yazma, eksikleri net söyle.
4. DİL: SADECE VE SADECE TÜRKÇE.

ÇIKTI FORMATI (SADECE JSON):
{{
    "rankings": [
        {{ "model_index": 1, "score": 9.0, "reason": "Başarılı ancak X eksik." }},
        {{ "model_index": 2, "score": 6.5, "reason": "Halüsinasyon mevcut." }}
    ],
    "best_model_index": 1
}}
"""
        try:
            if self.provider == "gemini":
                result = await self._grade_with_gemini(prompt)
            else:
                result = await self._grade_with_groq(prompt)
            
            final_scores = {}
            if "rankings" in result:
                for rank in result["rankings"]:
                    shuffled_idx = rank["model_index"] - 1
                    if 0 <= shuffled_idx < len(indexed_responses):
                        original_idx, original_res = indexed_responses[shuffled_idx]
                        original_model_id = responses[original_idx]["model_id"]
                        final_scores[original_model_id] = {
                            "score": rank.get("score", 5),
                            "reason": rank.get("reason", "Değerlendirme tamamlandı.")
                        }
            return final_scores
        except Exception as e:
            logger.error(f"Batch Judge Error: {e}")
            return {}

    async def _grade_with_groq(self, prompt: str) -> Dict[str, Any]:
        import httpx
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": GROQ_JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                logger.error(f"Groq Judge Error: {str(e)}")
                return {"score": 5, "reason": "Yargıç hatası (Groq)."}

    async def _grade_with_gemini(self, prompt: str) -> Dict[str, Any]:
        """Using modern google-genai SDK with Retry (Faz 12)"""
        max_retries = 3
        base_delay = 5 
        
        if not self._gemini_client:
            return {"score": 5, "reason": "Gemini istemcisi başlatılamadı."}

        for attempt in range(max_retries):
            try:
                # Async generate content with specific config
                response = await self._gemini_client.aio.models.generate_content(
                    model=GEMINI_JUDGE_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                result_text = response.text
                return json.loads(result_text)
                
            except google_exceptions.ResourceExhausted as e:
                logger.warning(f"Gemini Judge 429 (Attempt {attempt+1}/{max_retries}). Waiting...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (attempt + 1))
                    continue
            except Exception as e:
                logger.error(f"Gemini Judge Error: {e}")
                if attempt == max_retries - 1:
                    return {"score": 5, "reason": f"Yargıç hatası (Gemini): {str(e)[:50]}"}
        
        return {"score": 5, "reason": "Yargıç hatası: Başarısız."}
