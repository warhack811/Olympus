"""
Mami AI - Sentezleyici (Synthesizer / The Stylist - Atlas Sovereign Edition)
---------------------------------------------------------------------------
Ham uzman verilerini ve araç çıktılarını alır, kullanıcının istediği persona
ve üslup ile harmanlayarak akıcı ve tutarlı bir nihai yanıt oluşturur.

Temel Sorumluluklar:
1. Veri Harmanlama: Çoklu uzman çıktılarını birleştirme.
2. Üslup Enjeksiyonu: Persona kurallarına göre şekillendirme.
3. Memory Voice: "Hatırladığım kadarıyla..." gibi doğal ifadeler.
4. Mirroring: Kullanıcının duygu durumuna göre ton ayarlama.
5. Akış Desteği: Stream halinde parça parça iletim.
"""

import re
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.core.llm.generator import LLMGenerator, LLMRequest
from app.core import prompts
from app.core.constants import STYLE_TEMPERATURE_MAP
from .vocalizer import vocalizer
from app.schemas.chat import StyleProfile

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.brain.request_context import RequestContext

class Synthesizer:
    """Uzman çıktılarını nihai yanıta dönüştüren sentez katmanı."""
    
    def __init__(self, llm_generator: Optional[LLMGenerator] = None):
        """
        Args:
            llm_generator: Optional LLMGenerator instance. If None, will be created.
        """
        self.llm = llm_generator
    
    async def synthesize(
        self,
        user_id: str,
        message: str,
        context: str = "",
        persona: str = "friendly",
        current_topic: str = None,
        images: Optional[List[str]] = None
    ) -> str:
        """
        Çoklu uzman sonuçlarını birleştirir ve tekil yanıt oluşturur.
        """
        # Mirroring logic
        mirroring = self._detect_mirroring(message, context)
        
        # Build prompt
        formatted_data = self._format_tool_outputs(tool_outputs, message)
        history_text = self._format_history(history, message)
        
        prompt = prompts.SYNTHESIZER_PROMPT.format(
            history=history_text or "[Henüz konuşma geçmişi yok]",
            raw_data=formatted_data,
            user_message=message,
            context=context or "[Hafıza kaydı yok]"
        )
        
        # System instruction with persona and mirroring
        system_instruction = prompts.get_persona_prompt(persona)
        if mirroring:
            system_instruction += f"\n{mirroring}"
        
        # Memory voice injection
        if "GRAF" in formatted_data or context:
            system_instruction += "\n[MEMORY_VOICE]: 'Hatırladığım kadarıyla...' gibi doğal ifadeler kullan. Teknik etiketleri gizle."
        
        # Temperature based on persona
        temperature = STYLE_TEMPERATURE_MAP.get(persona, 0.5)
        
        # 2. Call LLM via central generator (Manual Fallback handled internally)
        if not self.llm:
            self.llm = LLMGenerator()
            await self._auto_register_providers()

        request = LLMRequest(
            role="synthesizer",
            prompt=prompt,
            temperature=temperature,
            metadata={
                "system_prompt": system_instruction,
                "images": images
            }
        )
        
        try:
            result = await self.llm.generate(request)
            if result.ok:
                return self._sanitize_response(result.text)
            else:
                logger.error(f"[Synthesizer] LLM generation failed: {result.text}")
                return "Üzgünüm, şu an yanıt üretemiyorum. Lütfen tekrar dene."
        except Exception as e:
            logger.error(f"[Synthesizer] Synthesis failed: {e}")
            return "Üzgünüm, şu an yanıt üretemiyorum. Lütfen tekrar dene."
    
    async def synthesize_with_context(
        self,
        ctx: "RequestContext",
        tool_outputs: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        current_topic: Optional[str] = None
    ) -> str:
        resolved_tool_outputs = tool_outputs or ctx.tool_outputs
        resolved_history = history if history is not None else ctx.history_list
        return await self.synthesize(
            user_id=ctx.user_id,
            message=ctx.message,
            context=ctx.memory_context,
            tool_outputs=resolved_tool_outputs,
            history=resolved_history,
            persona=ctx.persona,
            current_topic=current_topic,
            images=ctx.images # Pass images from context
        )

    async def synthesize_stream(
        self,
        user_id: str,
        message: str,
        context: str,
        history: List[Dict[str, str]],
        tool_outputs: str,
        persona: str = "friendly",
        current_topic: Optional[str] = None,
        style_profile: Optional[StyleProfile] = None,
        images: Optional[List[str]] = None # Vision Support
    ):
        """
        Final yanıtı stream (akış) olarak üretir.
        
        Yields:
            dict: {"type": "metadata" | "chunk", ...}
        """
        # 1. Uzman ve Geçmiş Verilerini Formatla
        formatted_data = self._format_tool_outputs(tool_outputs, message)
        history_text = self._format_history(history, message)
        
        # 2. Nihai Kullanıcı Mesajını İnşa Et (Context Injection)
        prompt = prompts.SYNTHESIZER_PROMPT.format(
            history=history_text or "[Henüz konuşma geçmişi yok]",
            raw_data=formatted_data,
            user_message=message,
            context=context or "[Hafıza kaydı yok]"
        )
        
        # 3. Sovereign Style Enjeksiyonu (Vocalizer)
        normalized_persona = vocalizer._normalize_persona_name(persona)
        
        system_instruction = vocalizer.build_instruction(
            persona_name=persona, 
            style=style_profile,
            context=context,
            message=message
        )
        
        # --- ATLAS RICH DIRECTIVES PORT (ENHANCED) ---
        atlas_extras = []
        
        # 1.5: Memory Meta-Cognition Enhancement
        if context:
            memory_voice_inst = self._build_memory_voice_instruction(context)
            atlas_extras.append(memory_voice_inst)
        
        # 1.7: Conflict Resolution Enhancement
        if "[ÇÖZÜLMESİ GEREKEN DURUM]" in tool_outputs or "status: CONFLICTED" in context:
            conflict_inst = """[CONFLICT_RESOLUTION]: Bağlamda bir çelişki (conflict) tespit edildi.
- Cevabını verdikten sonra, nazikçe ve MERAKLI bir tonla bu durumu netleştirecek bir soru sor.
- ASLA suçlayıcı olma, sadece anlamaya çalış.
- Örnek: 'Bu arada, kayıtlarımda iki farklı bilgi var... hangisi doğru acaba?' (casual ton)
- Örnek: 'Bir şeyi merak ettim: önceden X demiştin, şimdi Y diyorsun. Değişti mi?' (friendly)"""
            atlas_extras.append(conflict_inst)
        
        # 1.8: Topic Transition Enhancement
        if current_topic and current_topic not in ("SAME", "CHITCHAT"):
            topic_inst = f"""[KONU DEĞİŞİMİ]: Konuşmanın ana konusu '{current_topic}' olarak güncellendi.
- Eğer önceki konudan KESKIN bir geçiş varsa, doğal bir geçiş cümlesiyle başla.
- Örnekler:
  * 'O konudan buna geçersek...'
  * 'Şimdi {current_topic} konusuna dönelim...'
  * 'Tamam, o konuyu kapatalım. {current_topic} için...'
- Eğer geçiş doğal ise (related topics), geçiş cümlesi gereksiz."""
            atlas_extras.append(topic_inst)
        
        # 1.6: Emotional Continuity Enhancement
        emotional_inst = self._build_emotional_continuity_instruction(context)
        if emotional_inst:
            atlas_extras.append(emotional_inst)

        if atlas_extras:
            system_instruction += "\n\n### [ATLAS ÖZEL TALİMATLAR]\n" + "\n".join(atlas_extras)
        
        temperature = STYLE_TEMPERATURE_MAP.get(normalized_persona, STYLE_TEMPERATURE_MAP.get("default", 0.5))
        
        # POINT 6: Synthesis Thought (Thinking aloud while merging data)
        try:
            from app.services.brain.thought_generator import thought_generator
            from app.services.brain.context_enricher import context_enricher
            u_ctx = {"mood": "neutral", "expertise_level": "intermediate"} # Fallback context
            try:
                u_ctx = await context_enricher.get_user_context(user_id, message, history)
            except: pass
            
            synth_thought = await thought_generator.generate_thought(
                task_type="synthesis",
                user_context=u_ctx,
                action_params={"tool_count": tool_outputs.count('[')},
                personality_mode=persona,
                allow_fallback=True
            )
            yield {"type": "thought", "cat": "SYNTHESIS", "content": synth_thought}
        except Exception:
            pass

        # --- CENTRALIZED LLM GENERATION (REFACTORED) ---
        if not self.llm:
            self.llm = LLMGenerator()
            await self._auto_register_providers()

        request = LLMRequest(
            role="synthesizer",
            prompt=prompt,
            temperature=temperature,
            metadata={
                "system_prompt": system_instruction,
                "images": images
            }
        )

        try:
            tail_buffer = ""
            async for chunk in self.llm.generate_stream(request):
                # Central generator signals errors with "error:" prefix in stream
                if isinstance(chunk, str) and chunk.startswith("error:"):
                    logger.error(f"[Synthesizer] Stream error: {chunk}")
                    yield {"type": "error", "content": "Yanıt oluşturulurken bir hata oluştu."}
                    continue
                
                if isinstance(chunk, str) and chunk.startswith("budget_exceeded:"):
                    yield {"type": "error", "content": "Günlük limit aşıldı."}
                    return

                current_text = tail_buffer + (chunk or "")
                
                # Tag protection logic: buffer partial brackets
                if '[' in current_text:
                    last_open = current_text.rfind('[')
                    if ']' not in current_text[last_open:] and len(current_text) - last_open < 50:
                        to_send = current_text[:last_open]
                        tail_buffer = current_text[last_open:]
                    else:
                        to_send = current_text
                        tail_buffer = ""
                else:
                    to_send = current_text
                    tail_buffer = ""

                if to_send:
                    clean_chunk = self._sanitize_response(to_send, strip_all=False)
                    if clean_chunk:
                        yield {"type": "chunk", "content": clean_chunk}
            
            if tail_buffer:
                clean_chunk = self._sanitize_response(tail_buffer, strip_all=False)
                if clean_chunk:
                    yield {"type": "chunk", "content": clean_chunk}
            
        except Exception as e:
            logger.error(f"[Synthesizer] Stream synthesis failed: {e}")
            yield {"type": "error", "content": "Sentezleme sırasında beklenmedik bir hata oluştu."}
    
    async def synthesize_stream_with_context(
        self,
        ctx: "RequestContext",
        tool_outputs: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        current_topic: Optional[str] = None,
        style_profile: Optional[StyleProfile] = None
    ):
        resolved_tool_outputs = tool_outputs or ctx.tool_outputs
        resolved_history = history if history is not None else ctx.history_list
        async for chunk in self.synthesize_stream(
            user_id=ctx.user_id,
            message=ctx.message,
            context=ctx.memory_context,
            history=resolved_history,
            tool_outputs=resolved_tool_outputs,
            persona=ctx.persona,
            current_topic=current_topic,
            style_profile=style_profile or ctx.style_profile
        ):
            yield chunk

    def _detect_mirroring(self, message: str, context: str) -> str:
        """1.9: Mirroring Granularity Enhancement"""
        combined = (message + " " + context).lower()
        # Note: Using partial word matching (no spaces) to catch "yorgunum", "heyecanlıyım" etc.
        if any(w.lower() in combined for w in ["yorgun", "gergin", "üzgün", "stres", "yoğun"]):
            return """[MIRRORING]: Kullanıcı yorgun/gergin görünüyor.
- Cevabını KISA tut (2-3 paragraf max)
- Empatik ve çözüm odaklı ol
- TEKNİK DETAYLARA BOĞMA (jargon kullanma, step-by-step basit tut)"""
        
        elif any(w.lower() in combined for w in ["mutlu", "neşeli", "heyecan", "enerjik"]):
            return """[MIRRORING]: Kullanıcı enerjik ve neşeli.
- Cevabını daha CANLI ve DETAYLI hazırla
- EŞLİKÇİ bir ton kullan (beraber keşfedelim, heyecan paylaşalım)
- İlginç detaylar, yan bilgiler ekleyebilirsin"""
        
        return ""
    
    def _format_tool_outputs(self, tool_outputs: str, message: str) -> str:
        if not tool_outputs:
            return f"[DİKKAT: Uzman raporu yok.]\nKullanıcı: {message}"
        return tool_outputs
    
    def _format_history(self, history: List[Dict[str, str]], current_message: str) -> str:
        if not history:
            return ""
        filtered = [m for m in history if m.get("content") != current_message]
        return "\n".join([f"{m['role']}: {m['content']}" for m in filtered])
    
    def _build_memory_voice_instruction(self, context: str) -> str:
        """
        1.5: Memory Meta-Cognition Enhancement
        Analyzes confidence and timestamp from context, generates meta-cognitive instructions.
        """
        instruction = "[MEMORY_VOICE]: Hafızadan gelen bilgileri kullanırken 'Hatırladığım kadarıyla...', 'Daha önce belirttiğin gibi...' gibi doğal girişler yap. Teknik etiketleri asla kullanıcıya gösterme."
        
        # Check for low confidence facts
        if "confidence" in context.lower():
            import re
            confidence_matches = re.findall(r'confidence["\s:]+([0-9.]+)', context.lower())
            if confidence_matches:
                avg_confidence = sum(float(c) for c in confidence_matches) / len(confidence_matches)
                if avg_confidence < 0.6:
                    instruction += "\n- Kullanılan bilgilerin güven skoru düşük. 'Yanlış hatırlamıyorsam...', 'Emin olmamakla birlikte...' gibi ifadelerle başla."
        
        # Check for old facts (6+ months)
        if "created_at" in context or "timestamp" in context:
            from datetime import datetime, timedelta
            import re
            
            timestamp_pattern = r'(\d{4}-\d{2}-\d{2}|\d{10,13})'
            timestamps = re.findall(timestamp_pattern, context)
            
            if timestamps:
                oldest_date = None
                for ts in timestamps:
                    try:
                        if len(ts) > 10:  # Epoch timestamp
                            date = datetime.fromtimestamp(int(ts) / 1000)
                        else:  # ISO date
                            date = datetime.fromisoformat(ts)
                        
                        if oldest_date is None or date < oldest_date:
                            oldest_date = date
                    except:
                        continue
                
                if oldest_date:
                    age_months = (datetime.now() - oldest_date).days / 30
                    if age_months > 6:
                        instruction += "\n- Kullanılan bilgiler 6 aydan eski. 'Bir süre önceki kayıtlara göre...', 'Eskiden bahsettiğin gibi...' diye başla."
        
        return instruction
    
    def _build_emotional_continuity_instruction(self, context: str) -> str:
        """
        1.6: Emotional Continuity Enhancement
        Extracts previous mood from context, generates concrete greeting instructions.
        """
        if "[ÖNCEKİ DUYGU DURUMU]" not in context:
            return ""
        
        import re
        mood_match = re.search(r"ÖNCEKİ DUYGU DURUMU.*?'([^']+)'", context)
        if not mood_match:
            return ""
        
        mood = mood_match.group(1).lower()
        
        # Mood categorization
        negative_moods = ["üzgün", "kızgın", "sinirli", "depresif", "mutsuz", 
                          "hasta", "yorgun", "stresli", "gergin"]
        positive_moods = ["mutlu", "neşeli", "heyecanlı", "enerjik", 
                          "motive", "rahat", "iyi"]
        
        if any(neg in mood for neg in negative_moods):
            return """[EMOTIONAL_CONTINUITY]: Kullanıcının önceki duygu durumu negatif idi.
- Selamlaşırken 'Umarım daha iyisindir', 'Nasıl gidiyor?' gibi empatik bir giriş yap.
- Çok nazik ol, ısrarcı sorular sorma.
- Ana cevabı bu durum etkilememeli, SADECE selamlaşma kısmında kullan."""
        
        elif any(pos in mood for pos in positive_moods):
            return """[EMOTIONAL_CONTINUITY]: Kullanıcının önceki duygu durumu pozitif idi.
- 'Enerjin harika görünüyordu!', 'O ruh halini koruyorsun!' gibi olumlu bir giriş yap.
- Enerjik ve destekleyici ol.
- Ana cevabı bu durum etkilememeli, SADECE selamlaşma kısmında kullan."""
        
        return ""
    
    def _sanitize_response(self, text: str, strip_all: bool = False) -> str:
        if not text:
            return ""
            
        code_blocks = []
        def preserve_code(match):
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            return placeholder
            
        protected_text = re.sub(r'```[\s\S]*?```', preserve_code, text)
        
        # [PROD-FIX] Protect LaTeX Math Blocks
        # Handles $$, $, \[, \], \(, \)
        protected_text = re.sub(r'\$\$[\s\S]*?\$\$', preserve_code, protected_text)
        protected_text = re.sub(r'\\{1,2}\[[\s\S]*?\\{1,2}\]', preserve_code, protected_text)
        protected_text = re.sub(r'\$[^\$\n]+?\$', preserve_code, protected_text)
        protected_text = re.sub(r'\\{1,2}\([\s\S]*?\\{1,2}\)', preserve_code, protected_text)
        
        cjk_pattern = r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]'
        sanitized = re.sub(cjk_pattern, '', protected_text)
        
        meta_patterns = [
            r'\[THOUGHT\].*?\[/THOUGHT\]',
            r'\[ANALYSIS\].*?\[/ANALYSIS\]',
            r'Thinking\.\.\.',
            r'Loading\.\.\.'
        ]
        for pattern in meta_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.DOTALL | re.IGNORECASE)
        
        sanitized = re.sub(r'\[GRAF \| Skor: \d+\.\d+\][:\s]*', '', sanitized)
        sanitized = re.sub(r'\[HIB_GRAF \| Skor: \d+\.\d+\][:\s]*', '', sanitized)
        sanitized = re.sub(r'\[VECTOR \| Skor: \d+\.\d+\][:\s]*', '', sanitized)
        sanitized = re.sub(r'\[(GRAPH|VECTOR|HIB_GRAF|GRAF)\][:\s]*', '', sanitized)
        
        for i, block in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            sanitized = sanitized.replace(placeholder, block)
            
        if strip_all:
            return sanitized.strip()
        return sanitized


    async def _auto_register_providers(self) -> None:
        """Auto-register providers based on ModelGovernance requirements."""
        from app.core.llm.governance import governance
        from app.core.llm.adapters import groq_adapter, gemini_adapter
        
        synth_chain = governance.get_model_chain("synthesizer")
        providers_needed = set()
        for model_id in synth_chain:
            provider_name = governance.detect_provider(model_id)
            providers_needed.add(provider_name)
        
        provider_adapters = {
            "groq": groq_adapter,
            "gemini": gemini_adapter
        }
        
        for provider in providers_needed:
            if provider in provider_adapters and provider not in self.llm.providers:
                self.llm.register_provider(provider, provider_adapters[provider])
                logger.info(f"[Synthesizer] Auto-registered provider: {provider}")

# Singleton
synthesizer = Synthesizer()
