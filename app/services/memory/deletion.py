"""
Mami AI - Core Deletion Service
--------------------------------
Handles all memory deletion operations with multi-system coordination.

Features:
- Preview generation (show what will be deleted)
- 2-step confirmation with token validation
- Neo4j deletion with orphan cleanup
- Qdrant deletion (placeholder for Phase 2)
- Redis session cleanup
- Audit logging
"""

import logging
import secrets
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

from app.repositories.graph_db import graph_repo
from app.repositories.vector_db import vector_repo
from app.core.redis_client import get_redis
from app.services.memory.deletion_parser import deletion_parser

logger = logging.getLogger("app.service.memory.deletion")

# Category to Neo4j relationship type mapping
CATEGORY_PREDICATES = {
    "tasks": ["HAS_TASK", "REMINDER", "TODO"],
    "preferences": ["LIKES", "PREFERS", "DISLIKES", "FAVORITE", "HATES"],
    "memories": ["EXPERIENCED", "REMEMBERS", "VISITED", "DID"],
    "attributes": ["AGE", "NAME", "LOCATION", "BORN_AT", "EMAIL", "PHONE"],
    "relationships": ["HAS_MOTHER", "HAS_FATHER", "FRIEND_OF", "WORKS_WITH", "SIBLING_OF"]
}

# Entity to predicate mapping (for specific entity extraction)
ENTITY_PREDICATE_MAP = {
    "name": ["NAME"],
    "age": ["AGE", "BORN_AT"],
    "location": ["LOCATION"],
    "color": ["LIKES", "PREFERS"],  # Colors are preferences
    "color_blue": ["LIKES", "PREFERS"],
    "color_red": ["LIKES", "PREFERS"],
    "color_green": ["LIKES", "PREFERS"],
    "mother": ["HAS_MOTHER"],
    "father": ["HAS_FATHER"],
    "friend": ["FRIEND_OF"],
    "email": ["EMAIL"],
    "phone": ["PHONE"],
}


class DeletionService:
    """
    Core service for handling memory deletion operations.
    Coordinates action across Neo4j, Qdrant, Redis, and SQL.
    """
    
    async def process_deletion_request(self, user_id: str, user_input: str) -> Dict:
        """
        Main entry point for deletion requests.
        Parses intent, generates preview, and creates confirmation token.
        
        Args:
            user_id: User ID
            user_input: Natural language deletion request
                       e.g. "İsmimi unut", "Tüm görevleri sil"
        
        Returns:
            {
              "status": "preview|clarification_needed",
              "token": "abc123...",
              "preview": {...},
              "message": "User-facing message"
            }
        """
        logger.info(f"[Deletion] Processing request from user {user_id}: '{user_input}'")
        
        # Step 1: Parse intent
        intent = await deletion_parser.parse(user_input)
        
        # Check confidence
        if intent.get("confidence", 0) < 0.7:
            # Try to give specific hints based on keywords
            possible_intents = []
            user_input_lower = user_input.lower()
            
            if "görev" in user_input_lower:
                possible_intents.append("• 'Tüm görevleri sil' (tüm görevler)")
            if "tercih" in user_input_lower or "beğen" in user_input_lower:
                possible_intents.append("• 'Tercihlerimi sil' (beğeniler/sevmediği şeyler)")
            if "anı" in user_input_lower or "hatıra" in user_input_lower:
                possible_intents.append("• 'Anılarımı sil' (deneyimler)")
            if ("unut" in user_input_lower or "sil" in user_input_lower) and "ben" in user_input_lower:
                possible_intents.append("• 'Beni tamamen unut' (tüm bilgiler)")
            
            hints = "\n".join(possible_intents) if possible_intents else "\nÖrnekler:\n- İsmimi unut\n- Tüm görevleri sil\n- Beni tamamen unut"
            
            return {
                "status": "clarification_needed",
                "message": f"Tam olarak neyi silmek istediğinizi anlamadım. Lütfen daha spesifik olun.{hints}"
            }
        
        # Step 2: Generate preview
        preview = await self._generate_preview(user_id, intent)
        
        # Check if anything found to delete
        total_items = preview.get('neo4j_facts', 0)
        try:
            qdrant_count = int(preview.get('qdrant_vectors', '0')) if preview.get('qdrant_vectors', '0').replace('~', '').isdigit() else 0
            total_items += qdrant_count
        except:
            pass
        
        if total_items == 0:
            return {
                "status": "nothing_to_delete",
                "message": "Bu kategoride silinecek bilgi bulunamadı. Belki zaten silinmiş veya hiç kaydedilmemiş olabilir."
            }
        
        # Step 3: Generate and store confirmation token
        token = await self._store_deletion_intent(user_id, intent, preview)
        
        # Step 4: Build confirmation message
        message = self._build_confirmation_message(preview, intent)
        
        return {
            "status": "preview",
            "token": token,
            "preview": preview,
            "message": message
        }
    
    async def confirm_deletion(self, user_id: str, token: str, confirmation_text: str) -> Dict:
        """
        Execute deletion if token is valid and confirmation matches.
        
        Args:
            user_id: User ID
            token: Confirmation token from preview step
            confirmation_text: User's confirmation ("EVET", "ONAYLIYORUM", etc.)
        
        Returns:
            {
              "status": "success|error",
              "deleted_counts": {...},
              "message": "User-facing message"
            }
        """
        logger.info(f"[Deletion] Confirm request from user {user_id}, token: {token[:8]}...")
        
        # Validate token
        redis = await get_redis()
        if not redis:
            return {
                "status": "error",
                "message": "⚠️ Sistem hatası: Redis bağlantısı yok. Lütfen tekrar deneyin."
            }
        
        stored_data = await redis.get(f"deletion_token:{user_id}:{token}")
        if not stored_data:
            return {
                "status": "error",
                "message": "❌ Onay süresi doldu veya geçersiz token. Lütfen silme talebini tekrar yapın."
            }
        
        # Validate confirmation text
        valid_confirmations = ["EVET", "ONAYLIYORUM", "YES", "CONFIRM"]
        if confirmation_text.upper().strip() not in valid_confirmations:
            return {
                "status": "error",
                "message": f"❌ Onay metni hatalı. Lütfen tam olarak şunlardan birini yazın: {', '.join(valid_confirmations)}"
            }
        
        # Parse stored intent
        try:
            intent = json.loads(stored_data)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "⚠️ Sistem hatası: Intent verisi bozuk."
            }
        
        # Execute deletion
        result = await self._execute_deletion(user_id, intent)
        
        # Clean up token
        await redis.delete(f"deletion_token:{user_id}:{token}")
        
        logger.info(f"[Deletion] Completed for user {user_id}: {result.get('deleted_counts')}")
        
        return result
    
    async def _generate_preview(self, user_id: str, intent: Dict) -> Dict:
        """
        Query all systems to show what will be deleted.
        
        Returns:
            {
              "neo4j_facts": int,
              "neo4j_nodes": int,
              "qdrant_vectors": str,  # "~100" (approximate for now)
              "tasks": int,
              "details": List[str]
            }
        """
        preview = {
            "neo4j_facts": 0,
            "neo4j_nodes": 0,
            "qdrant_vectors": "~0",
            "tasks": 0,
            "details": []
        }
        
        # Get predicates from intent
        predicates = self._get_predicates_from_intent(intent)
        
        # Count Neo4j items
        if intent["deletion_scope"] == "full":
            # Full wipe: count all user relationships
            cypher = """
            MATCH (u:User {id: $uid})-[r]-()
            RETURN count(DISTINCT r) as rels
            """
            params = {"uid": user_id}
        else:
            # Selective: count specific relationships
            cypher = """
            MATCH (u:User {id: $uid})-[r]-()
            WHERE type(r) IN $predicates
            RETURN count(DISTINCT r) as rels
            """
            params = {"uid": user_id, "predicates": predicates}
        
        try:
            result = await graph_repo.query(cypher, params)
            if result and len(result) > 0:
                preview["neo4j_facts"] = result[0].get("rels", 0)
        except Exception as e:
            logger.error(f"[Deletion] Preview error (Neo4j): {e}")
            preview["details"].append(f"Neo4j preview failed: {e}")
        
        # Count Qdrant vectors
        try:
            vector_count = await vector_repo.count_by_filter({"user_id": user_id})
            preview["qdrant_vectors"] = str(vector_count)
            logger.info(f"[Deletion] Qdrant count: {vector_count}")
        except Exception as e:
            logger.error(f"[Deletion] Qdrant count failed: {e}")
            preview["qdrant_vectors"] = "~unknown"
            preview["details"].append(f"Qdrant count failed: {e}")
        
        return preview
    
    async def _store_deletion_intent(self, user_id: str, intent: Dict, preview: Dict) -> str:
        """
        Store deletion intent in Redis with 5-minute expiry.
        
        Returns:
            token: Confirmation token string
        """
        token = secrets.token_hex(16)  # 128-bit secure token
        
        redis = await get_redis()
        if not redis:
            logger.warning("[Deletion] Redis unavailable, token storage skipped")
            return token
        
        try:
            await redis.setex(
                f"deletion_token:{user_id}:{token}",
                300,  # 5 minutes
                json.dumps(intent)
            )
            logger.info(f"[Deletion] Token stored for user {user_id}: {token[:8]}...")
        except Exception as e:
            logger.error(f"[Deletion] Token storage failed: {e}")
        
        return token
    
    def _build_confirmation_message(self, preview: Dict, intent: Dict) -> str:
        """
        Build user-facing confirmation message.
        """
        msg = "⚠️ DİKKAT - GERİ ALINAMAZ İŞLEM\n\n"
        
        # Show what will be deleted
        msg += "Silinecekler:\n"
        if preview["neo4j_facts"] > 0:
            msg += f"• {preview['neo4j_facts']} gerçek ve ilişki (Neo4j)\n"
        if preview.get("qdrant_vectors") and preview["qdrant_vectors"] != "~0":
            msg += f"• {preview['qdrant_vectors']} anı (Semantic Memory)\n"
        if preview.get("tasks", 0) > 0:
            msg += f"• {preview['tasks']} görev\n"
        
        if preview["neo4j_facts"] == 0:
            msg += "• (Silinecek bilgi bulunamadı)\n"
        
        msg += "\n❗ KORUNACAKLAR:\n"
        msg += "• Sohbet geçmişiniz (mesajlar korunur)\n"
        
        # Show what will be kept if selective
        if intent.get("categories_to_keep"):
            kept_categories = ", ".join(intent["categories_to_keep"])
            msg += f"• {kept_categories} (talep üzerine korunur)\n"
        
        msg += "\nBu işlem geri alınamaz. Emin misiniz?\n"
        msg += "Onaylamak için tam olarak şunu yazın: ONAYLIYORUM"
        
        return msg
    
    async def _execute_deletion(self, user_id: str, intent: Dict) -> Dict:
        """
        Execute multi-system deletion.
        
        Returns:
            {
              "status": "success",
              "deleted_counts": {...},
              "message": "User-facing message"
            }
        """
        deleted_counts = {
            "neo4j_rels": 0,
            "neo4j_nodes": 0,
            "qdrant": 0,
            "redis": 0
        }
        
        # Get predicates from intent
        predicates = self._get_predicates_from_intent(intent)
        
        # 1. Delete from Neo4j with orphan cleanup
        if intent["deletion_scope"] == "full":
            # Full wipe: Delete all user relationships
            cypher = """
            MATCH (u:User {id: $uid})
            OPTIONAL MATCH (u)-[r]-()
            DELETE r
            RETURN count(r) as deleted_rels
            """
            params = {"uid": user_id}
        else:
            # Selective: Delete specific relationships and orphan nodes
            cypher = """
            MATCH (u:User {id: $uid})-[r]-(n)
            WHERE type(r) IN $predicates
            DELETE r
            WITH n
            WHERE NOT EXISTS((n)-[]-()) AND NOT EXISTS(()-[]->(n))
            DELETE n
            RETURN count(n) as deleted_nodes
            """
            params = {"uid": user_id, "predicates": predicates}
        
        try:
            result = await graph_repo.query(cypher, params)
            if result and len(result) > 0:
                if intent["deletion_scope"] == "full":
                    deleted_counts["neo4j_rels"] = result[0].get("deleted_rels", 0)
                else:
                    deleted_counts["neo4j_nodes"] = result[0].get("deleted_nodes", 0)
            logger.info(f"[Deletion] Neo4j deletion complete: {deleted_counts}")
        except Exception as e:
            logger.error(f"[Deletion] Neo4j deletion failed: {e}")
            return {
                "status": "error",
                "message": f"❌ Silme işlemi başarısız: {str(e)}"
            }
        
        # 2. Delete from Qdrant (Vector Memory)
        if intent["deletion_scope"] == "full" or "memories" in intent.get("categories_to_delete", []):
            try:
                await vector_repo.delete_by_filter({"user_id": user_id})
                deleted_counts["qdrant"] = "deleted"  # Qdrant doesn't return exact count
                logger.info(f"[Deletion] Qdrant deletion executed for user {user_id}")
            except Exception as e:
                logger.error(f"[Deletion] Qdrant deletion failed: {e}")
                deleted_counts["qdrant_error"] = str(e)
        
        # 3. Delete from Redis (session cache - all keys)
        redis = await get_redis()
        if redis:
            try:
                # Find all session keys for this user
                # Pattern: session:{user_id}:*
                pattern = f"session:{user_id}:*"
                cursor = 0
                deleted_total = 0
                
                # Use SCAN to find keys (safer than KEYS *)
                while True:
                    cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted = await redis.delete(*keys)
                        deleted_total += deleted
                    if cursor == 0:
                        break
                
                deleted_counts["redis"] = deleted_total
                logger.info(f"[Deletion] Redis deletion: {deleted_total} keys")
            except Exception as e:
                logger.error(f"[Deletion] Redis deletion failed: {e}")
        
        # 4. Audit log (enhanced - file export for GDPR)
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "deletion_scope": intent['deletion_scope'],
            "deleted_counts": deleted_counts,
            "intent_summary": {
                "categories_deleted": intent.get('categories_to_delete', []),
                "categories_kept": intent.get('categories_to_keep', [])
            }
        }
        
        logger.info(f"[DELETION AUDIT] {json.dumps(audit_entry)}")
        
        # Write to audit file (GDPR compliance)
        try:
            audit_file = "logs/deletion_audit.jsonl"
            os.makedirs("logs", exist_ok=True)
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
            logger.info(f"[Deletion] Audit entry written to {audit_file}")
        except Exception as e:
            logger.warning(f"[Deletion] Audit file write failed: {e}")
        # Build success message
        total_deleted = deleted_counts.get("neo4j_rels", 0) + deleted_counts.get("neo4j_nodes", 0)
        
        if total_deleted == 0 and not deleted_counts.get("qdrant"):
            message = "⚠️  Beklenmedik durum: Hiçbir şey silinemedi. Lütfen tekrar deneyin veya destek ekibine başvurun."
        else:
            message = f"✅ {total_deleted} bilgi başarıyla silindi."
        
        if deleted_counts.get("qdrant") == "deleted":
            message += "\n✅ Semantic hafıza temizlendi."
        
        if deleted_counts.get("redis", 0) > 0:
            message += f"\n✅ {deleted_counts['redis']} session cache temizlendi."
        
        # Report partial failures
        if deleted_counts.get("qdrant_error"):
            message += f"\n⚠️  Qdrant temizliği kısmen başarısız: {deleted_counts['qdrant_error']}"
        
        return {
            "status": "success",
            "deleted_counts": deleted_counts,
            "message": message
        }
    
    def _get_predicates_from_intent(self, intent: Dict) -> List[str]:
        """
        Convert intent categories and entities to Neo4j relationship predicates.
        
        Args:
            intent: Parsed deletion intent
        
        Returns:
            List of relationship type strings (e.g. ["NAME", "AGE", "LIKES"])
        """
        predicates = []
        
        categories_to_delete = intent.get("categories_to_delete", [])
        
        for category in categories_to_delete:
            if category == "all":
                # Return all known predicates
                for preds in CATEGORY_PREDICATES.values():
                    predicates.extend(preds)
            elif category in CATEGORY_PREDICATES:
                predicates.extend(CATEGORY_PREDICATES[category])
            else:
                logger.warning(f"[Deletion] Unknown category: {category}")
        
        # If entities exist, use entity-to-predicate mapping
        if intent.get("entities"):
            for entity in intent.get("entities", []):
                entity_name = entity.get("name", "").lower()
                
                if entity_name in ENTITY_PREDICATE_MAP:
                    predicates.extend(ENTITY_PREDICATE_MAP[entity_name])
                    logger.info(f"[Deletion] Mapped entity '{entity_name}' to predicates: {ENTITY_PREDICATE_MAP[entity_name]}")
                else:
                    # Fallback: use entity name as predicate
                    fallback_predicate = entity_name.upper()
                    predicates.append(fallback_predicate)
                    logger.warning(f"[Deletion] Unknown entity '{entity_name}', using as predicate: {fallback_predicate}")
        
        # Remove duplicates
        predicates = list(set(predicates))
        
        logger.info(f"[Deletion] Final mapped predicates: {predicates}")
        
        return predicates


# Singleton export
deletion_service = DeletionService()
