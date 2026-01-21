"""
Mami AI - Deletion Intent Parser
---------------------------------
LLM-based parser that converts natural language deletion requests
into structured JSON commands.

Example:
    User: "Yaşımı ve görevleri sil ama anılar kalsın"
    Output: {
        "deletion_scope": "selective",
        "categories_to_delete": ["tasks"],
        "categories_to_keep": ["memories"],
        "entities": [{"type": "attribute", "name": "age", ...}],
        "confidence": 0.95
    }
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger("app.service.memory.deletion_parser")

PARSER_PROMPT = """Sen bir deletion intent parser'sın. Kullanıcının silme talebi için JSON döndür.

CATEGORIES (Kategoriler):
- tasks: Görevler, hatırlatmalar, yapılacaklar
- preferences: Tercihler, beğeniler, sevmediği şeyler, favori
- memories: Anılar, deneyimler, ziyaret edilen yerler
- attributes: Yaş, isim, lokasyon, doğum tarihi, kişisel bilgiler
- relationships: Aile, arkadaşlar, iş arkadaşları gibi ilişkiler

DELETION_SCOPE:
- single: Tek bir entity (örn: "ismimi unut")
- multi: Birden fazla entity (örn: "yaşımı ve ismimi sil")
- category: Bir kategori (örn: "tüm görevleri sil")
- selective: Kombinasyon (örn: "görevleri sil ama anılar kalsın")
- full: Tam silme (örn: "beni tamamen unut", "her şeyi sil")

Kullanıcı: {user_input}

JSON Format (sadece JSON döndür, başka açıklama yazma):
{{
  "deletion_scope": "single|multi|category|selective|full",
  "categories_to_delete": ["tasks", "preferences"],
  "categories_to_keep": ["memories"],
  "entities": [
    {{"type": "attribute", "name": "age", "search_terms": ["yaş", "age", "32"]}},
    {{"type": "preference", "name": "color_blue", "search_terms": ["mavi", "blue"]}}
  ],
  "require_confirmation": true,
  "confidence": 0.95
}}

ÖRNEKLER:
Kullanıcı: "ismimi unut"
{{"deletion_scope": "single", "entities": [{{"type": "attribute", "name": "name", "search_terms": ["isim", "name"]}}], "confidence": 0.95}}

Kullanıcı: "yaşımı ve mavi rengi sil"
{{"deletion_scope": "multi", "entities": [{{"type": "attribute", "name": "age", "search_terms": ["yaş", "age"]}}, {{"type": "preference", "name": "color_blue", "search_terms": ["mavi", "blue", "color"]}}], "confidence": 0.90}}

Kullanıcı: "tüm görevleri sil"
{{"deletion_scope": "category", "categories_to_delete": ["tasks"], "confidence": 0.95}}

Kullanıcı: "görevleri ve tercihlerimi sil ama anılar kalsın"
{{"deletion_scope": "selective", "categories_to_delete": ["tasks", "preferences"], "categories_to_keep": ["memories"], "confidence": 0.90}}

Kullanıcı: "beni tamamen unut"
{{"deletion_scope": "full", "categories_to_delete": ["all"], "confidence": 0.95}}

Kullanıcı: "sadece anılarımı sil"
{{"deletion_scope": "category", "categories_to_delete": ["memories"], "confidence": 0.90}}

Kullanıcı: "her şeyi unut"
{{"deletion_scope": "full", "categories_to_delete": ["all"], "confidence": 0.95}}

Kullanıcı: "ekranı temizle"
{{"deletion_scope": "unknown", "confidence": 0.2}}

Şimdi yukarıdaki kullanıcı girdisi için JSON döndür:
"""


class DeletionParser:
    """
    Parses natural language deletion requests into structured intent.
    Uses LLM for flexible understanding.
    """
    
    def __init__(self):
        self.llm = None
    
    async def parse(self, user_input: str) -> Dict:
        """
        Parse user deletion request into structured intent.
        
        Args:
            user_input: Natural language deletion request
                       e.g. "Yaşımı ve görevleri sil ama anılar kalsın"
        
        Returns:
            Dict with structure:
            {
              "deletion_scope": str,
              "categories_to_delete": List[str],
              "categories_to_keep": List[str],
              "entities": List[Dict],
              "confidence": float,
              "require_confirmation": bool
            }
        """
        # Lazy load LLM provider
        if self.llm is None:
            from app.providers.llm.groq import GroqProvider
            self.llm = GroqProvider()
        
        prompt = PARSER_PROMPT.format(user_input=user_input)
        
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are a precise JSON parser. Return only valid JSON, no explanations.",
                temperature=0.1,
                max_tokens=500
            )
            
            # Clean response (remove markdown if present)
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            # Parse JSON
            intent = json.loads(clean_response)
            
            # Validate required fields
            if "deletion_scope" not in intent:
                intent["deletion_scope"] = "full"
            if "confidence" not in intent:
                intent["confidence"] = 0.5
            if "require_confirmation" not in intent:
                intent["require_confirmation"] = True
            
            logger.info(f"[DeletionParser] Parsed: {user_input} -> {intent['deletion_scope']} (confidence: {intent['confidence']})")
            
            return intent
            
        except json.JSONDecodeError as e:
            logger.error(f"[DeletionParser] JSON parse failed for input '{user_input}': {e}")
            logger.error(f"[DeletionParser] LLM Response: {response}")
            
            # Fallback: Assume full delete with low confidence
            return {
                "deletion_scope": "full",
                "categories_to_delete": ["all"],
                "require_confirmation": True,
                "confidence": 0.3,
                "error": "Failed to parse LLM response"
            }
        
        except Exception as e:
            logger.error(f"[DeletionParser] Unexpected error: {e}")
            
            # Fallback
            return {
                "deletion_scope": "full",
                "categories_to_delete": ["all"],
                "require_confirmation": True,
                "confidence": 0.2,
                "error": str(e)
            }


# Singleton export
deletion_parser = DeletionParser()
