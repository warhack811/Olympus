"""
Sovereign Core - Vocalizer (Stil ve Persona Motoru)
---------------------------------------------------
AI'nın karakterini, tonunu ve sesini (voice) yöneten ana servis.
Tüm talimatlarını app.core.prompts üzerinden alır.
"""

import logging
from typing import Optional
from app.core import prompts
from app.schemas.chat import StyleProfile

logger = logging.getLogger(__name__)

class Vocalizer:
    """
    AI'nın 'sesini' (style/persona) inşa eden servis.
    """
    
    def build_instruction(
        self, 
        persona_name: str = "friendly", 
        style: Optional[StyleProfile] = None,
        context: str = "",
        message: str = ""
    ) -> str:
        """
        Karakter ve stil parametrelerine göre nihai sistem talimatını oluşturur.
        """
        from app.core.dynamic_config import config_service

        # 1. Persona (Karakter) Tanımı - DB Öncelikli
        persona_key = self._normalize_persona_name(persona_name)
        
        # Önce DB'den ara
        persona_cfg = config_service.get_persona(persona_key)
        if persona_cfg:
            persona_inst = persona_cfg.get("system_prompt", "")
        else:
            # Fallback to code definition
            persona_inst = prompts.PERSONA_PROMPTS.get(persona_key, prompts.PERSONA_PROMPTS["friendly"])
        
        # 2. Temel Kimlik (Mami/Atlas)
        identity_part = prompts.get_base_identity_instruction()
        
        # 3. Stil Direktifleri (Tone, Length, Emoji)
        tone_val = "casual"
        len_val = "normal"
        emoji_val = "medium"
        
        if style:
            tone_val = style.tone or tone_val
            len_val = style.length or len_val
            emoji_val = style.emoji_level or emoji_val
            
        tone_inst = prompts.TONE_DIRECTIVES.get(tone_val, prompts.TONE_DIRECTIVES["casual"])
        len_inst = prompts.LENGTH_DIRECTIVES.get(len_val, prompts.LENGTH_DIRECTIVES["normal"])
        emoji_inst = prompts.EMOJI_DIRECTIVES.get(emoji_val, prompts.EMOJI_DIRECTIVES["medium"])
        
        # 4. Aynalama (Mirroring)
        mirror_inst = self._get_mirroring_instruction(message, context)
        
        # 5. Parçaları Birleştir (Karakter Odaklı Hiyerarşi)
        construction = [
            f"### [SENİN KARAKTERİN VE KİMLİĞİN]\n{persona_inst}",
            f"\n{identity_part}",
            f"\n### [KONUŞMA DİSİPLİNLERİN]\n- TON: {tone_inst}",
            f"- UZUNLUK: {len_inst}",
            f"- EMOJİ: {emoji_inst}",
            f"\n{prompts.PURE_TURKISH_DIRECTIVE}",
            f"\n{prompts.get_time_context()}"
        ]
        
        if mirror_inst:
            construction.insert(2, f"\n{mirror_inst}")
            
        # 6. Atlas 'Standard' Special Flow
        if persona_key == "standard":
            construction.append(f"\n{prompts.STANDARD_MEMORY_VOICE_DIRECTIVE}")
            construction.append(f"\n{prompts.STANDARD_MIRRORING_DIRECTIVE}")
            
        final_instruction = "\n".join(construction)
        logger.info(f"[VOCALIZER] Built instruction for persona='{persona_name}' (Standalone Mode)")
        return final_instruction

    def _normalize_persona_name(self, name: str) -> str:
        """İsimleri normalize eder. Artık yönlendirme (mapping) yok, her isim kendisi."""
        if not name:
            return "standard"
            
        return name.lower().strip()

    def _get_mirroring_instruction(self, message: str, context: str) -> str:
        """Kullanıcının duygu durumuna ve hitap tarzına göre anlık tavır değişikliği."""
        combined = (message + " " + context).lower()
        mirror_parts = []
        
        # 1. Duygusal Aynalama (Emotional Mirroring)
        if any(w in combined for w in ["yorgun", "gergin", "üzgün", "stres", "yoğun"]):
            mirror_parts.append("DİKKAT: Kullanıcı yorgun veya gergin görünüyor. Daha empatik, destekleyici ve kısa cevaplar ver.")
        elif any(w in combined for w in ["mutlu", "neşeli", "süper", "harika", "enerjik"]):
            mirror_parts.append("DİKKAT: Kullanıcı pozitif/enerjik bir havada. Sen de bu enerjiyi yansıt, daha canlı ve detaylı ol.")
            
        # 2. Hitap Aynalaması (Address Mirroring - ATLAS Port)
        formal_hits = ["hocam", "bey", "hanım", "beyefendi", "hanımefendi", "siz", "mami bey", "atlas bey"]
        casual_hits = ["kanka", "dostum", "aga", "moruk", "bro", "selam mami", "selam atlas"]
        
        if any(w in combined for w in formal_hits):
            mirror_parts.append(prompts.MIRROR_HITAP_PROMPT)
            mirror_parts.append("- NOT: Kullanıcı sana mesafeli/saygılı hitap etti. Sen de bu çizgiyi bozma, saygılı kal.")
        elif any(w in combined for w in casual_hits):
            mirror_parts.append(prompts.MIRROR_HITAP_PROMPT)
            mirror_parts.append("- NOT: Kullanıcı sana çok samimi yaklaştı. Sen de 'kanka' moduna geçebilirsin.")
            
        return "\n".join(mirror_parts) if mirror_parts else ""

# Singleton
vocalizer = Vocalizer()
