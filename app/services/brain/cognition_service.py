
"""
Mami AI - Cognition Service (Atlas Sovereign Edition)
------------------------------------------------------
Episodik hafıza yönetimi, hiyerarşik özetleme ve kognitif analiz servisi.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.core.logger import get_logger
from app.core.llm.generator import LLMGenerator, LLMRequest
from app.core.llm.governance import governance
from sqlmodel import select
from app.core.database import get_session
from app.core.models import Message, Conversation, ConversationSummary

logger = get_logger(__name__)

EPISODE_PROMPT = """
Aşağıdaki sohbet dökümünü analiz et ve bir "Episodik Hafıza Bloğu" oluştur.

### TALİMATLAR:
1. Sohbetin ana temasını ve önemli olayları kısa ve öz bir şekilde özetle.
2. Kullanıcının paylaştığı özel bilgileri (isim, tercihler, hedefler) ayıkla.
3. Önem Puanı (Importance Score) ver (1-10):
   - 1-3: Genel sohbet, günlük konuşmalar.
   - 4-7: Bilgi paylaşımı, teknik konular, spesifik sorular.
   - 8-10: Çok kritik kişisel veriler, kullanıcı tercihleri, önemli kararlar.

### FORMAT (JSON):
{{
  "summary": "Sohbetin özeti...",
  "importance": 8,
  "entities": ["Mami", "Python", "Yazılım Geliştirme"],
  "mood_detected": "meraklı"
}}

Döküm:
{transcript}
"""

class CognitionService:
    """Yapay zeka için kognitif süreçleri (hafıza konsolidasyonu vb.) yönetir."""
    
    def __init__(self):
        self._generator = LLMGenerator()
        # Not: Generator içindeki _auto_register_providers sonradan çağrılacak

    async def generate_episode_summary(self, transcript: str) -> Dict[str, Any]:
        """Konuşma dökümünden akıllı bir episod özeti oluşturur."""
        import json
        
        request = LLMRequest(
            role="episodic_summary",
            prompt=EPISODE_PROMPT.format(transcript=transcript),
            temperature=0.3
        )
        
        try:
            # Sağlayıcıları otomatik kaydet (lazy context)
            from app.core.llm.adapters import groq_adapter, gemini_adapter
            if "gemini" not in self._generator.providers:
                self._generator.register_provider("gemini", gemini_adapter)
            if "groq" not in self._generator.providers:
                self._generator.register_provider("groq", groq_adapter)

            result = await self._generator.generate(request)
            if not result.ok:
                raise Exception(result.text)
                
            # JSON temizleme ve parse
            raw_text = result.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(raw_text)
            return data
        except Exception as e:
            logger.error(f"[Cognition] Episode generation failed: {e}")
            return {
                "summary": transcript[:200] + "...",
                "importance": 1,
                "entities": [],
                "mood_detected": "unknown"
            }

    async def process_pending_sessions(self, lookback_hours: int = 24):
        """Henüz özetlenmemiş veya güncellenmesi gereken oturumları işler."""
        from sqlalchemy import text
        
        logger.info(f"[Cognition] Bekleyen oturumlar taranıyor (Son {lookback_hours} saat)...")
        
        with get_session() as session:
            # Basit mantık: Son 24 saatte aktif olan ve özetlenmemiş oturumlar
            # (Gerçek üretimde daha karmaşık bir PENDING tablosu kullanılır)
            stmt = select(Conversation).where(
                Conversation.updated_at >= datetime.utcnow() - timedelta(hours=lookback_hours)
            )
            sessions = session.exec(stmt).all()
            
            processed_count = 0
            for conv in sessions:
                # Özet gerekli mi kontrol et? (Örn: 8 mesajda bir)
                msg_stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
                messages = session.exec(msg_stmt).all()
                
                if len(messages) < 5: continue # Yeterli derinlik yok
                
                # Mevcut özeti kontrol et
                summary_stmt = select(ConversationSummary).where(ConversationSummary.conversation_id == conv.id)
                existing = session.exec(summary_stmt).first()
                
                if existing and existing.message_count_at_update >= len(messages):
                    continue # Zaten güncel
                
                # Özet üret
                transcript = "\n".join([f"{'User' if m.role == 'user' else 'AI'}: {m.content}" for m in messages[-20:]])
                episode_data = await self.generate_episode_summary(transcript)
                
                # Kaydet
                if existing:
                    existing.summary = episode_data.get("summary", "")
                    existing.importance = episode_data.get("importance", 1)
                    existing.entities = episode_data.get("entities", [])
                    existing.mood = episode_data.get("mood_detected")
                    existing.message_count_at_update = len(messages)
                    existing.updated_at = datetime.utcnow()
                else:
                    new_summary = ConversationSummary(
                        conversation_id=conv.id,
                        summary=episode_data.get("summary", ""),
                        importance=episode_data.get("importance", 1),
                        entities=episode_data.get("entities", []),
                        mood=episode_data.get("mood_detected"),
                        message_count_at_update=len(messages),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_summary)
                
                # Graf ve Vektör Veritabanı Güncelleme (Geçit/Placeholder)
                # await self._sync_to_longterm_memory(conv.user_id, conv.id, episode_data)
                
                processed_count += 1
                
                # Rate limiting: Her özetleme sonrası 2 saniye bekle (Kotaları koru)
                await asyncio.sleep(2)
                
                if processed_count % 5 == 0:
                    session.commit()
            
            session.commit()
            logger.info(f"[Cognition] {processed_count} oturum özetlendi.")
            return processed_count

# Singleton
cognition_service = CognitionService()
