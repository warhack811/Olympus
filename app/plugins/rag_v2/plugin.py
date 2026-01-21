import logging
from typing import Any

from app.core.feature_flags import feature_enabled

logger = logging.getLogger(__name__)


class RagV2Plugin:
    """
    RAG v2 Plugin Skeleton.

    Controlled by 'rag_v2' feature flag.
    Default: Disabled.
    """

    name: str = "rag_v2"
    version: str = "0.1.0"

    def is_enabled(self) -> bool:
        """Check if plugin is enabled via feature flag."""
        # Check both keys for compatibility
        res = feature_enabled("rag_v2", default=False) or feature_enabled("rag_v2_enabled", default=False)
        logger.info(f"[RAG v2 Eklentisi] is_enabled kontrolü yapıldı. Sonuç: {res}")
        return res

    def process_response(
        self, text: str, context: dict[str, Any] | None = None, options: dict[str, Any] | None = None
    ) -> str:
        """
        Metni (bağlamı) işler ve gerekirse değiştirilmiş sürümünü döndürür.
        """
        logger.info(
            f"[RAG v2 Eklentisi] process_response çağrıldı. Bağlam anahtarları: {list(context.keys()) if context else 'Yok'}"
        )
        try:
            if not context:
                logger.warning("[RAG v2 Eklentisi] Bağlam sağlanmadı. İşlem durduruluyor.")
                return text

            query = context.get("query")
            owner = context.get("owner")
            scope = context.get("scope")
            conversation_id = context.get("conversation_id")
            mode = context.get("rag_v2_mode", "fast")
            continue_mode = context.get("continue_mode", False)

            if not (query and owner and scope):
                logger.warning(
                    f"[RAG v2 Eklentisi] Gerekli bağlam bilgileri eksik. query={bool(query)}, owner={bool(owner)}, scope={bool(scope)}"
                )
                return text

            from app.memory import rag_v2

            # 0. BYPASS check for code/programming intent
            if self.should_bypass(query):
                # Telemetry: bypass used
                self._log_plugin_stats(
                    query,
                    owner,
                    scope,
                    gating_result="bypass",
                    bypass_used=True,
                    lexical_sanity_pass=False,
                    marker_written=False,
                )
                return text

            # 1. Retrieve results + stats from memory (do not log telemetry here)
            results_and_stats = rag_v2.search_documents_v2(
                query=query,
                owner=owner,
                scope=scope,
                top_k=60,
                mode=mode,
                conversation_id=conversation_id,
                continue_mode=continue_mode,
                return_stats=True,
            )

            # results_and_stats is (results, stats)
            if isinstance(results_and_stats, tuple):
                candidates, stats = results_and_stats
            else:
                candidates = results_and_stats or []

            # Sort by score (lower is better)
            candidates = candidates or []
            candidates.sort(key=lambda x: x.get("hybrid_score", x.get("score", 1.0)))

            # Lexical sanity check will only be applied when we have candidates
            lexical_ok = True

            # Gating decision based on retrieval scores
            gating_fail = False
            if not candidates:
                gating_reason = "empty"
                gating_fail = True

            else:
                top = candidates[0]
                # Treat candidate as hybrid if explicit score_type set OR hybrid_score present
                is_hybrid = top.get("score_type") == "hybrid_distance" or (top.get("hybrid_score") is not None)
                best_score = top.get("hybrid_score") if is_hybrid else top.get("score")

                # Now apply lexical sanity check since we have a top candidate
                lexical_ok = self.lexical_sanity_check(query, candidates)

                if is_hybrid:
                    threshold = 0.75
                    margin_limit = 0.05
                else:
                    threshold = 0.50
                    margin_limit = 0.08

                if best_score is None:
                    gating_fail = True
                    gating_reason = "no_score"
                elif best_score > threshold:
                    gating_fail = True
                    gating_reason = "threshold"
                elif len(candidates) >= 2:
                    second = candidates[1]
                    second_score = second.get("hybrid_score") if is_hybrid else second.get("score")
                    margin = abs(best_score - (second_score or 0))
                    if margin < margin_limit:
                        gating_fail = True
                        gating_reason = "margin"

            # Combine with lexical sanity
            if not lexical_ok:
                gating_fail = True
                gating_reason = "lexical_sanity"

            # Finalize outputs and write a single telemetry record
            if gating_fail:
                # Only marker — do NOT inject evidence
                # CHANGE: Allow fallback to General Knowledge by NOT writing the strict marker
                # marker = "\n\nRAG_V2_STATUS: NO_EVIDENCE_FOUND\n"

                self._log_plugin_stats(
                    query,
                    owner,
                    scope,
                    gating_result=gating_reason,
                    bypass_used=False,
                    lexical_sanity_pass=lexical_ok,
                    marker_written=False,
                )
                return text  # + marker (Disabled to allow LLM answer)

            # PASS: attach evidence only (no marker)
            # Build evidence block from top candidates (limit chars/items)
            MAX_TOTAL_CHARS = 2500
            MAX_CHUNK_CHARS = 650
            GUARD_TEXT = "⚠️ Aşağıdaki bilgiler BELGE KANITIDIR. Bu kanıtlar dışında cevap üretme."

            final_pool = []
            for i, cand in enumerate(candidates):
                final_pool.append(cand)
                if i < 2:
                    c_idx = cand.get("chunk_index")
                    if c_idx is not None:
                        try:
                            neighbors = rag_v2.expand_neighbors(
                                owner=owner,
                                scope=scope,
                                filename=cand.get("filename", ""),
                                page_number=cand.get("page_number", 0),
                                chunk_index=c_idx,
                                radius=1,
                            )
                            if neighbors:
                                final_pool.extend(neighbors)
                        except Exception:
                            pass

            evidence_lines = []
            seen = set()
            total_chars = 0
            for doc in final_pool:
                content = (doc.get("text") or "").strip()
                if not content or content in seen:
                    continue
                seen.add(content)

                fname = doc.get("filename", "unknown")
                page = doc.get("page_number", "?")
                trimmed = content[:MAX_CHUNK_CHARS] + "..." if len(content) > MAX_CHUNK_CHARS else content
                line = f"[{fname} | p.{page}] {trimmed}"
                if total_chars + len(line) > MAX_TOTAL_CHARS:
                    continue
                evidence_lines.append(line)
                total_chars += len(line)
                if len(evidence_lines) >= 8:
                    break

            v2_block = (
                "\n\n=== İLGİLİ BELGELER (RAG v2) ===\n" + GUARD_TEXT + "\n" + "\n".join(evidence_lines)
                if evidence_lines
                else ""
            )

            # Telemetry write once with final decision
            self._log_plugin_stats(
                query,
                owner,
                scope,
                gating_result="pass",
                bypass_used=False,
                lexical_sanity_pass=lexical_ok,
                marker_written=bool(not evidence_lines),
            )

            # PASS requires evidence and NO marker
            if v2_block:
                return text + v2_block

            return text

        except Exception as e:
            logger.exception(f"[RAG v2] Eklenti process_response başarısız oldu: {e}")
            try:
                self._log_plugin_stats(
                    context.get("query", "") if context else "",
                    context.get("owner", "") if context else "",
                    context.get("scope", "") if context else "",
                    "exception",
                    bypass_used=False,
                    lexical_sanity_pass=False,
                    marker_written=False,
                )
            except:
                pass
            return text

    def _log_plugin_stats(
        self,
        query,
        owner,
        scope,
        gating_result,
        bypass_used: bool = False,
        lexical_sanity_pass: bool = False,
        marker_written: bool = False,
        deep_fallback: bool = False,
        expansion: bool = False,
        best_score=None,
        second_score=None,
        best_score_type=None,
    ):
        try:
            from app.memory.rag_v2_telemetry import RAGV2Stats, calculate_query_hash, log_stats

            # Ensure query is string
            if query is None:
                query = ""

            stats = RAGV2Stats(
                query_hash=calculate_query_hash(str(query)),
                owner=owner,
                scope=str(scope),
                mode_used="plugin_decision",
                used_lexical=False,
                dense_count=0,
                lexical_count=0,
                merged_count=0,
                best_score=best_score,
                second_score=second_score,
                best_score_type=best_score_type,
                gating_result=gating_result,
                marker_written=marker_written,
                bypass_used=bypass_used,
                lexical_sanity_pass=lexical_sanity_pass,
                deep_fallback_triggered=deep_fallback,
                expansion_used=expansion,
            )
            log_stats(stats)
        except Exception as e:
            logger.exception(f"[RAG v2] _log_plugin_stats başarısız oldu: {e}")

    def should_bypass(self, query: str) -> bool:
        """Return True if query appears to be code/programming intent and RAG should be bypassed."""
        try:
            import re

            q = (query or "").lower()

            # Quick indicators: 'kod', 'örnek kod', 'programlama', language names
            keywords = [
                r"\bkod\b",
                r"örnek kod",
                r"programlama",
                r"python",
                r"javascript",
                r"java",
                r"c\+\+",
                r"c#",
                r"go\b",
                r"rust\b",
                r"php\b",
            ]

            for kw in keywords:
                if re.search(kw, q):
                    return True

            # If query explicitly asks for code with a question mark near 'kod' or language
            if re.search(r"(kod|örnek kod|python|java|javascript).{0,20}\?", q):
                return True

            # Heuristic: presence of code-like snippets (=>, :=, print(), def )
            if re.search(r"\bdef\s+\w+\(|print\(|console\.log\(|=>|<-|:=", q):
                return True

            return False
        except Exception:
            return False

    def lexical_sanity_check(self, query: str, candidates: list) -> bool:
        """Remove stopwords from query and require at least one remaining keyword to appear in best evidence."""
        try:
            import re

            q = (query or "").lower()
            # Basic Turkish+English stopwords (small set)
            stopwords = {
                "ve",
                "ile",
                "bir",
                "bu",
                "da",
                "de",
                "için",
                "nasıl",
                "mi",
                "mı",
                "mu",
                "mü",
                "ne",
                "kadar",
                "kaç",
                "lütfen",
                "kod",
                "yapılır",
                "yapmak",
                "sadece",
                "sor",
                "the",
                "is",
                "in",
                "on",
                "a",
                "an",
                "how",
                "to",
            }

            # Tokenize
            tokens = re.findall(r"[a-z0-9öçşığü]+", q)
            keywords = [t for t in tokens if t not in stopwords and len(t) > 1]

            if not keywords:
                return False

            # Check top evidence (first candidate text) for any keyword
            if not candidates:
                return False

            top_text = (candidates[0].get("text") or "").lower()
            for k in keywords:
                if k in top_text:
                    return True

            return False
        except Exception:
            return False
