import json
import logging
from typing import Dict, Any, List

# Orchestrator modülleri
from app.config import get_settings
from app.chat.decider import call_groq_api_safe_async

logger = logging.getLogger("orchestrator.intent")

async def classify(message: str, username: str | None = None) -> Dict[str, Any]:
    """
    Niyet Sınıflandırıcı (Intent Classifier) - HİBRİT MOTOR (LLM + Kural).
    
    Blueprint v1.0 uyarınca:
    1. Önce Hızlı Model (Scout - llama-3.1-8b-instant) ile semantik analiz denenir.
    2. Hata durumunda (veya çok kısa sorgularda) Kural Tabanlı (Rule-Based) motor devreye girer.
    
    Yetenekler:
    - Semantik Anlama: "Covid durumu" -> Search, "Python scripti" -> Coding
    - Multi-tasking: Search + Coding vb.
    - JSON Output: Deterministik yapı.
    """
    # 1. GUARDS & PRE-CHECKS
    if not isinstance(message, str) or not message.strip():
        logger.warning("Boş mesaj, default dönülüyor.")
        return _get_default_response()
        
    msg_clean = message.strip()
    
    # Debug Print
    print(f"DEBUG: [Intent] Classify Start - Msg: '{msg_clean[:20]}...'")

    # Çok kısa mesajlar için LLM harcama (Rule-based'e düşsün)
    if len(msg_clean.split()) < 2 and len(msg_clean) < 10:
         print(f"DEBUG: [Intent] Mesaj çok kısa, rule-based.")
         return _rule_based_classify(msg_clean)

    # 2. LLM SEMANTIC ANALYSIS (SCOUT)
    try:
        settings = get_settings()
        semantic_model = settings.GROQ_SEMANTIC_MODEL or "llama-3.1-8b-instant"
        print(f"DEBUG: [Intent] LLM Call Start - Model: {semantic_model}")
        
        system_prompt = """SEN BİR 'INTENT CLASSIFIER' (NİYET SINIFLANDIRICI) AI AJANISIN.
GÖREVİN: Kullanıcı mesajını analiz edip, hangi uzmanlık alanına (domain) girdiğini ve hangi araçların (tools) gerektiğini belirlemek.

CEVAP FORMATI (SADECE JSON):
{
  "domain": "general" | "search" | "coding" | "image" | "productivity",
  "complexity": "low" | "medium" | "high",
  "rag_decision": "off" | "on" | "maybe",
  "tool_hints": ["internet_arama", "kod_yazma", "gorsel_uretim"],
  "tasks": [
    {"id": "t1", "type": "web_search", "priority": 1, "meta": {"desc": "X hakkında bilgi topla"}}
  ]
}

KURALLAR:
1. "search" (internet_arama): Güncel bilgi, hava durumu, borsa, haber, 'nedir', 'kimdir', 'fiyat' soruları için ZORUNLU.
   - ÖRNEK: "Bugün hava nasıl?", "Dolar ne kadar?", "Covid bitti mi?", "En son deprem", "Python nedir?"
2. "coding" (kod_yazma): Kod isteği, hata ayıklama, teknik soru.
3. "image" (gorsel_uretim): Resim, logo, çizim isteği.
4. "general": Selamlaşma, basit sohbet, felsefi soru, kişisel görüş.
5. Multi-Intent: Eğer hem arama hem kod gerekiyorsa görevleri sırala (önce search, sonra code).

BAĞLAM:
Kullanıcı mesajı: """
        
        # Message Listesi Oluştur
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": msg_clean}
        ]

        # LLM Çağrısı (Corrected Signature)
        llm_response, error = await call_groq_api_safe_async(
            model=semantic_model, # model_id -> model
            messages=messages,    # system_prompt/user_prompt -> messages list
            temperature=0.1,      # Deterministik
            # max_tokens=500      # Bu argüman decider.py'da yok (default Groq limit)
        )

        if error:
             print(f"DEBUG: [Intent] LLM Error: {error}")

        if llm_response and llm_response.strip().startswith("{"):
            # JSON Parsing
            try:
                # Markdown fence varsa temizle
                cleaned_json = llm_response.replace("```json", "").replace("```", "").strip()
                intent_data = json.loads(cleaned_json)
                
                # Validasyon: En azından domain alanı olmalı
                if "domain" in intent_data:
                    intent_data["matched_rules"] = ["llm_semantic_analysis"]
                    intent_data["composer"] = "sequential" # Default
                    print(f"DEBUG: [Intent] LLM Success: {intent_data.get('domain')} - Tasks: {len(intent_data.get('tasks', []))}")
                    return intent_data
                    
            except json.JSONDecodeError:
                print(f"DEBUG: [Intent] JSON Error: {llm_response[:50]}...")
        
    except Exception as e:
        print(f"DEBUG: [Intent] LLM Exception: {e}")
        
    # 3. FALLBACK: RULE-BASED ENGINE
    print("DEBUG: [Intent] Fallback Triggered")
    return _rule_based_classify(msg_clean)


def _rule_based_classify(message: str) -> Dict[str, Any]:
    """Eski Regex/Keyword tabanlı sınıflandırıcı (Yedek Güç)."""
    try:
        # Varsayılan Değerler
        domain = "general"
        complexity = "low"
        rag_decision = "off"
        composer = "sequential"
        tool_hints = []
        matched_rules = ["fallback_rule_engine"]
        tasks = []
        
        msg_lower = message.lower()
        
        # --- ANAHTAR KELİME ANALİZİ ---
        
        # Kod / Yazılım
        coding_keywords = ["python", "javascript", "hata", "bug", "stack trace", "kod", "refactor", "unit test", "regex"]
        is_coding = any(kw in msg_lower for kw in coding_keywords)
        if is_coding:
            tool_hints.append("kod_yazma")
        
        # İnternet Arama (Standart Liste)
        search_keywords = ["araştır", "google", "web", "internet", "kaynak", "link", "son haber", "güncel"]
        is_search = any(kw in msg_lower for kw in search_keywords)
        if is_search:
            tool_hints.append("internet_arama")

        # Görsel Üretim
        image_keywords = ["görsel", "resim", "logo", "afiş", "illustration", "tasarım", "image"]
        is_image = any(kw in msg_lower for kw in image_keywords)
        if is_image:
            tool_hints.append("gorsel_uretim")
            
        # ... (Diğer lojik benzer şekilde devam eder, ancak şuan sade tutuyoruz) ...
        # Basit Fallback Görev Ataması
        
        if is_search:
            domain = "search"
            tasks = [{"id": "t1", "type": "web_search", "priority": 1}]
        elif is_coding:
            domain = "coding"
            tasks = [{"id": "t1", "type": "code", "priority": 1}]
        elif is_image:
            domain = "image"
            tasks = [{"id": "t1", "type": "image_generate", "priority": 1}]
        else:
            domain = "general"
            tasks = [{"id": "t1", "type": "chat", "priority": 1}]
            
        return {
            "tasks": tasks,
            "composer": composer,
            "complexity": complexity,
            "domain": domain,
            "rag_decision": rag_decision,
            "tool_hints": tool_hints,
            "matched_rules": matched_rules
        }

    except Exception as e:
        logger.error(f"Rule-based sınıflandırma hatası: {e}")
        return _get_default_response()

def _get_default_response():
    return {
        "tasks": [{"id": "t1", "type": "chat", "depends_on": [], "priority": 1}],
        "composer": "sequential",
        "complexity": "low",
        "domain": "general",
        "rag_decision": "off",
        "tool_hints": [],
        "matched_rules": ["system_fail_default"]
    }
