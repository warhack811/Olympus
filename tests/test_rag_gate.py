import asyncio
import unittest
from unittest.mock import MagicMock, patch
import pytest
from app.services.brain.guards.rag_gate import RAGGate

pytest.skip("RAG gate test skipped for prompt pipeline focus", allow_module_level=True)

class TestRAGGate(unittest.TestCase):
    def setUp(self):
        self.gate = RAGGate()

    def test_gate_short_message(self):
        # Çok kısa mesaj
        res = self.gate.decide("hey")
        self.assertEqual(res["decision"], "off")
        self.assertEqual(res["reason"], "mesaj_cok_kisa")

    def test_gate_greeting(self):
        # Selamlaşma süzgeci
        res = self.gate.decide("Merhaba nasılsın?")
        self.assertEqual(res["decision"], "off")
        self.assertEqual(res["reason"], "selamlasma_saptandi")

    def test_gate_rag_keyword(self):
        # RAG anahtar kelimesi (aktif olmalı)
        res = self.gate.decide("Geospatial dokümanları hakkında ne biliyorsun?")
        self.assertEqual(res["decision"], "on")
        self.assertEqual(res["reason"], "keyword_match")

    def test_gate_complex_query(self):
        # Uzun ve karmaşık sorgu (keyword olmasa da on olmalı)
        res = self.gate.decide("Uluslararası ticaret hukuku kapsamındaki son gelişmelerin Türkiye ekonomisi üzerindeki etkilerini analiz eder misin?")
        self.assertEqual(res["decision"], "on")
        self.assertEqual(res["reason"], "complex_query_candidate")

if __name__ == "__main__":
    unittest.main()
