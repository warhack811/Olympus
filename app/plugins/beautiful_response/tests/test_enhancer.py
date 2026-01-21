"""
Tests for Beautiful Response Enhancer
"""

import sys
import unittest
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.plugins.beautiful_response.enhancer import enhance_response
from app.plugins.beautiful_response.models.blocks import CitationBlock, CodeBlock, StructuredResponse, TextBlock


class TestEnhancer(unittest.TestCase):
    def test_enhance_code_block_with_language(self):
        # Normal python block
        block = CodeBlock(block_type="code", content='print("hello")', language="python")
        response = StructuredResponse(blocks=[block])
        result = enhance_response(response)

        expected = '```python\nprint("hello")\n```'
        self.assertEqual(result.strip(), expected)

    def test_enhance_code_block_normalize_language(self):
        # 'js' -> 'javascript' aliases
        block = CodeBlock(block_type="code", content="console.log(1)", language="js")
        response = StructuredResponse(blocks=[block])
        result = enhance_response(response)

        expected = "```javascript\nconsole.log(1)\n```"
        self.assertEqual(result.strip(), expected)

    def test_enhance_code_block_unknown_language(self):
        # Unknown -> plaintext
        block = CodeBlock(block_type="code", content="foo bar", language="unknown_lang")
        response = StructuredResponse(blocks=[block])
        result = enhance_response(response)

        expected = "```plaintext\nfoo bar\n```"
        self.assertEqual(result.strip(), expected)

    def test_enhance_text_block_cleanup(self):
        # Multiple newlines -> max 2
        content = "Line 1\n\n\nLine 2   "
        block = TextBlock(block_type="text", content=content)
        response = StructuredResponse(blocks=[block])
        result = enhance_response(response)

        # Expect trimmed lines and max 2 newlines
        expected = "Line 1\n\nLine 2"
        self.assertEqual(result, expected)

    def test_enhance_citation_block(self):
        content = "Source line 1\nSource line 2"
        block = CitationBlock(block_type="citation", source_id="1", text=content)
        response = StructuredResponse(blocks=[block])
        result = enhance_response(response)

        expected = "> Source line 1\n> Source line 2"
        self.assertEqual(result, expected)

    def test_enhance_mixed_response(self):
        # Text + Code + Citation
        b1 = TextBlock(block_type="text", content="Intro text")
        b2 = CodeBlock(block_type="code", content="x = 1", language="py")
        b3 = CitationBlock(block_type="citation", source_id="2", text="A quote")

        response = StructuredResponse(blocks=[b1, b2, b3])
        result = enhance_response(response)

        # Separation by double newlines expected
        # Intro text\n\n```python...```\n\n> A quote

        self.assertIn("Intro text", result)
        self.assertIn("```python", result)
        self.assertIn("x = 1", result)
        self.assertIn("> A quote", result)

    def test_enhance_empty_response(self):
        response = StructuredResponse(blocks=[])
        result = enhance_response(response)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
