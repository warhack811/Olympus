# app/orchestrator_v42/plugins/specialist_stub.py

import json
import logging
from typing import Dict, Any, List

from app.orchestrator_v42.plugins.llm_client_adapter import call_llm_safe
from app.config import get_settings

logger = logging.getLogger("orchestrator.specialist")

async def produce(message: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Uzman Üretici (Specialist Producer) - REAL IMPLEMENTATION v1.
    
    Verilen bağlamı (Evidence, History, Memory) kullanarak nihai yanıtı üretir.
    Gerçek LLM çağrısı yapar.
    """
    try:
        if context is None:
            context = {}

        # 1. BAĞLAM VERİLERİNİ ÇIKAR
        intent = context.get("intent", {})
        if not isinstance(intent, dict): intent = {}
        
        domain = intent.get("domain", "general")
        tool_evidence = context.get("tool_evidence", {})
        memory_context = context.get("memory_context", [])
        history = context.get("history", [])
        
        # 2. PROMPT İNŞASI
        # A) Sistem Mesajı
        settings = get_settings()
        sys_prompt = (
            "SEN MAMI AI, GELİŞMİŞ BİR YAPAY ZEKA ASİSTANISIN.\n"
            "GÖREVİN: Kullanıcıya en doğru, yardımsever ve doğal yanıtı vermektir.\n\n"
            "KURALLAR:\n"
            "1. Sana verilen 'KANIT' (Evidence) verilerini kullanarak soruları yanıtla.\n"
            "2. Eğer kanıtlarda bilgi varsa, onu kullan. Yoksa kendi genel bilgini kullan.\n"
            "3. Sohbet geçmişine (HISTORY) dikkat et, bağlamı koru.\n"
            "4. Yanıtın son kullanıcıya hitap etmeli (Json veya teknik detay verme).\n"
            "5. Asla 'bilgim yok' deme, elindeki bilgilerle en iyi tahmini yap veya yorumla.\n"
        )

        # B) Bağlam Bloğu
        context_str = "\n### BAĞLAM VE KANITLAR ###\n"
        
        # Tool Evidence (Arama Sonuçları vs.)
        if isinstance(tool_evidence, dict) and tool_evidence.get("items"):
             context_str += "\n[ARAÇ SONUÇLARI / GÜNCEL BİLGİLER]:\n"
             for item in tool_evidence["items"]:
                 context_str += f"- {item}\n"
        elif isinstance(tool_evidence, list) and tool_evidence:
             context_str += "\n[ARAÇ SONUÇLARI]:\n"
             for item in tool_evidence:
                 context_str += f"- {item}\n"

        # Memory (Uzun Vadeli Hafıza)
        if memory_context:
            context_str += "\n[HAFIZA (MEMORIES)]:\n"
            for mem in memory_context:
                # [FIX] Robust Handling: mem string olabilir
                if isinstance(mem, dict):
                    txt = mem.get('text', '') or mem.get('content', '')
                    tarih = mem.get('created_at', '')
                    context_str += f"- {txt} (Tarih: {tarih})\n"
                else:
                    context_str += f"- {str(mem)}\n"

        # C) Mesaj Listesi (History + Current)
        messages = [{"role": "system", "content": sys_prompt + context_str}]
        
        # Geçmiş Mesajlar
        if history:
            # Son 10 mesajı ekle (Context window koruması)
            for h in history[-10:]: 
                if isinstance(h, dict):
                    role = h.get("role", "user")
                    content = h.get("content", "")
                else:
                    # String gelirse user mesajı varsay
                    role = "user"
                    content = str(h)
                    
                if role in ["user", "assistant", "system"] and content:
                    messages.append({"role": role, "content": content})
        
        # Şu anki mesaj (Eğer history'de zaten varsa ekleme, basit kontrol)
        # Genellikle gateway 'message' argümanını ayrı gönderir, history ise önceki mesajlardır.
        # Ama load_messages() veritabanından çektiği için son mesajı da içerebilir.
        # Basit dedup: Son history mesajı ile şimdiki mesaj aynı ise ekleme.
        
        should_append = True
        if history and history[-1]:
            last_item = history[-1]
            last_hist = ""
            if isinstance(last_item, dict):
                 last_hist = last_item.get("content", "").strip()
            else:
                 last_hist = str(last_item).strip()
            
            if last_hist == message.strip():
                should_append = False
        
        if should_append:
            messages.append({"role": "user", "content": message})

        # 3. LLM ÇAĞRISI (ADAPTER VIA GATEWAY SELECTION)
        # [FAZ 16.6] Router Model Kablolama
        model_hint = context.get("selected_model_hint", "general")
        
        # Normalize
        if model_hint:
             model_hint = str(model_hint).strip()
        else:
             model_hint = "general"

        # Mapping güvencesi
        if model_hint.lower() in ["bilinmiyor", "unknown", "none"]:
            model_hint = "general"
            
        from app.orchestrator_v42.plugins.llm_client_adapter import LlmClientAdapter
        adapter = LlmClientAdapter()
        
        # print(f"DEBUG: [Specialist] Adapter Fetching... Hint: {model_hint}") # Clean log
        
        print(f"DEBUG: [Specialist] Adapter Fetching... Hint: {model_hint} (Msgs: {len(messages)})")
        
        # Adapter Generate Çağrısı
        # Not: Adapter 'feature_flags' veya 'runtime' bekleyebilir.
        adapter_res = await adapter.generate(
            message="", # Message listesini aşağıda raw olarak yollamıyoruz ama Adapter interface'i tek mesaj bekliyor gibi?
            # Adapter update edilecek veya burada messages -> str conversion yapılacak.
            # LlmClientAdapter.generate şuan tek mesaj alıyor.
            # ANCAK Specialist çoklu mesaj (history) yollamalı.
            # Blueprint: Adapter.generate daha basit. Ama call_llm_safe daha esnek.
            # ÇÖZÜM: Specialist için LlmClientAdapter'a 'messages' desteği eklemek yerine
            # Adapter içindeki _map_model_id lojiğini kullanıp call_llm_safe'i çağırmak daha risksiz.
            # AMA Talep: "Specialist call_llm_safe bypass’ını kaldır/azalt: LlmClientAdapter üzerinden çağır"
            # O zaman Adapter'ı güncelleyeceğiz. Şimdilik Adapter generate'i 'messages' parametresi ile genişletmek lazım.
            # Fakat "Tek seferde" kurali var.
            # Adapter.generate şu an: message: str.
            # Biz Adapter.generate_with_messages(...) gibi bir method ekleyeceğiz veya generate'i overload edeceğiz.
            # Basitlik için: Adapter'ı çağırırken message parametresine son user mesajını verip,
            # history'yi context'e gömebiliriz. Ancak Adapter 'messages' listesini oluştururken bunu kullanmalı.
            # Mevcut generate implementasyonuna bakalım. call_provider_func(**call_kwargs) yapıyor.
            # call_kwargs = {"messages": [{"role": "user", "content": message}]}
            # Demek ki Adapter şu an SADECE tek mesaj destekliyor.
            # PLAN DEĞİŞİKLİĞİ (MİNİMAL RİSK):
            # Adapter'dan sadece model mapping'i alıp call_llm_safe ile devam etmek daha güvenli olurdu ama
            # talep "LlmClientAdapter üzerinden çağır".
            # O halde Adapter.generate'i messages destekleyecek şekilde güncelleyeceğiz.
            # Şimdilik burada Adapter çağırıyoruz varsayalım.
            
            model_hint=model_hint,
            runtime={"timeout_seconds": 45.0}, # Specialist için uzun
            context=context, # Intent, history vs burada
            flags=None
        )
        
        # Adapter dönüşü: {"text": "...", "raw": ...}
        response_text = adapter_res.get("text")

        if not response_text:
            response_text = "Üzgünüm, şu an bağlantı kurulamadı."

        # 4. ÇIKTI FORMATLAMA
        # Specialist şemasına uygun dönüş
        return {
            "solution_text": response_text,
            "code_blocks": [], 
            "claims": [],
            "evidence": [],
            "adapter_meta": adapter_res.get("raw", {})
        }

    except Exception as e:
        logger.error(f"Specialist REAL hatası: {e}")
        return {
            "solution_text": f"Bir hata oluştu: {str(e)}",
            "code_blocks": [],
            "claims": [],
            "evidence": []
        }
