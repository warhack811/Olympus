import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.prompts import compiler
from app.memory import rag_v2


class TestRagV2Continue(unittest.TestCase):
    def test_compiler_continue_contract(self):
        """Verify compiler injects CONTINUE CONTRACT."""
        prompt = compiler.build_system_prompt(user=MagicMock(), rag_v2_active=True, rag_v2_continue_mode=True)
        self.assertIn("CONTROLLED CONTINUE CONTRACT", prompt)
        self.assertIn("CONTINUE:", prompt)
        self.assertNotIn("ANSWER CONTRACT", prompt)
        self.assertNotIn("SUMMARY CONTRACT", prompt)

    def test_compiler_priority(self):
        """Verify Summary > Continue > Answer."""
        # Summary + Continue -> Summary
        p_sum = compiler.build_system_prompt(
            user=MagicMock(), rag_v2_active=True, rag_v2_summary_mode=True, rag_v2_continue_mode=True
        )
        self.assertIn("SUMMARY CONTRACT", p_sum)
        self.assertNotIn("CONTINUE CONTRACT", p_sum)

        # Continue -> Continue
        p_cont = compiler.build_system_prompt(
            user=MagicMock(), rag_v2_active=True, rag_v2_summary_mode=False, rag_v2_continue_mode=True
        )
        self.assertIn("CONTINUE CONTRACT", p_cont)

        # Normal -> Answer
        p_norm = compiler.build_system_prompt(
            user=MagicMock(), rag_v2_active=True, rag_v2_summary_mode=False, rag_v2_continue_mode=False
        )
        self.assertIn("ANSWER CONTRACT", p_norm)

    @patch("app.memory.rag_v2._get_rag_v2_collection")
    @patch("app.memory.rag_v2_conversation.get_active_page")
    @patch("app.memory.rag_v2_conversation.get_active_doc")
    def test_search_continue_logic(self, mock_get_doc, mock_get_page, mock_get_coll):
        """Verify search applies window filter (last_page + 1)."""
        mock_coll = MagicMock()
        mock_get_coll.return_value = mock_coll
        mock_coll.query.return_value = {"ids": [], "metadatas": [], "documents": [], "distances": []}

        mock_get_doc.return_value = "doc1"
        mock_get_page.return_value = 10

        try:
            rag_v2.search_documents_v2(
                query="devam?", owner="test", scope="user", conversation_id="conv1", continue_mode=True
            )

            args, kwargs = mock_coll.query.call_args
            where = kwargs["where"]

            and_list = where["$and"]

            # Find the page number filters
            # Looking for $gte: 11 (10+1) and $lte: 15 (10+5)
            # Structure: {"page_number": {"$gte": 11}}

            gte_filter = next((f for f in and_list if "page_number" in f and "$gte" in f["page_number"]), None)
            lte_filter = next((f for f in and_list if "page_number" in f and "$lte" in f["page_number"]), None)

            self.assertIsNotNone(gte_filter, "Missing min_page filter")
            self.assertIsNotNone(lte_filter, "Missing max_page filter")

            self.assertEqual(gte_filter["page_number"]["$gte"], 11, "Min page should be last_page + 1")
            self.assertEqual(lte_filter["page_number"]["$lte"], 15, "Max page should be last_page + 5")

        except Exception:
            import traceback

            traceback.print_exc()
            raise

    def test_processor_triggers_clean(self):
        """Verify processor triggers do not contain placeholders."""
        from app.chat import processor

        # We need to simulate the message processing to access triggers, or inspect the file content/variables if accessible.
        # Since triggers are local variables inside `process_chat_message`, we can't import them easily.
        # But we can inspect the file source for literal "..." in that list.
        # Or I can just trust the code modification I just did.
        # Or better: Test the behavior with "..." as an input message? No.
        # I'll modify the test to just Pass if compilation works? The user specifically asked:
        # "continue_triggers listesinde placeholder ("...") olmadığını doğrulayan test"

        # Since I can't access local variables of a function in python easily without analyzing bytecode or source.
        # I will read the file source and check string presence.

        with open(processor.__file__, encoding="utf-8") as f:
            content = f.read()

        # Find the continue_triggers line
        import re

        match = re.search(r"continue_triggers\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            list_content = match.group(1)
            self.assertNotIn("...", list_content, "Triggers should not contain literal '...'")
            print("Triggers clean.")
        else:
            self.fail("Could not find continue_triggers definition in processor.py")


if __name__ == "__main__":
    unittest.main()
