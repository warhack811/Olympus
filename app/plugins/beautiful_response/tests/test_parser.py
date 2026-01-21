"""
Tests for Beautiful Response Parser
"""

import sys
import unittest
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.plugins.beautiful_response.models.blocks import CitationBlock, CodeBlock, StructuredResponse, TextBlock
from app.plugins.beautiful_response.parser import parse_response


class TestParser(unittest.TestCase):
    def test_parse_plain_text(self):
        text = "Merhaba dünya"
        result = parse_response(text)

        self.assertIsInstance(result, StructuredResponse)
        self.assertEqual(len(result.blocks), 1)
        self.assertIsInstance(result.blocks[0], TextBlock)
        self.assertEqual(result.blocks[0].content, "Merhaba dünya")

    def test_parse_single_code_block(self):
        text = "```python\nprint('hello')\n```"
        result = parse_response(text)

        self.assertEqual(len(result.blocks), 1)
        self.assertIsInstance(result.blocks[0], CodeBlock)
        self.assertEqual(result.blocks[0].language, "python")
        self.assertEqual(result.blocks[0].content.strip(), "print('hello')")

    def test_parse_multiple_code_blocks(self):
        text = "Block 1\n```js\nconsole.log(1)\n```\nSep\n```py\nprint(2)\n```"
        result = parse_response(text)

        self.assertEqual(len(result.blocks), 4)  # Text, Code, Text, Code
        self.assertIsInstance(result.blocks[1], CodeBlock)
        self.assertEqual(result.blocks[1].language, "js")
        self.assertIsInstance(result.blocks[3], CodeBlock)
        self.assertEqual(result.blocks[3].language, "py")

    def test_parse_citation(self):
        text = "> Bu bir alıntıdır\n> İkinci satır"
        result = parse_response(text)

        self.assertEqual(len(result.blocks), 1)
        self.assertIsInstance(result.blocks[0], CitationBlock)
        self.assertIn("Bu bir alıntıdır", result.blocks[0].text)

    def test_parse_mixed_content(self):
        text = """
Merhaba

```python
code
```

> Alıntı

Son
"""
        result = parse_response(text)

        # Beklenen: Text(\nMerhaba\n\n), Code, Text(\n\n), Citation, Text(\n\nSon\n)
        # Regex ve stripping detaylarına göre boşluk blokları değişebilir.
        # Parser mantığında strip() kontrolü yaptık, boşluklar atlanıyor mu bakalım.
        # Sadece whitespace olan text blokları atlanabilir veya tutulabilir.

        blocks = result.blocks
        self.assertTrue(len(blocks) >= 3)

        # Tipleri kontrol et
        has_code = any(isinstance(b, CodeBlock) for b in blocks)
        has_cite = any(isinstance(b, CitationBlock) for b in blocks)
        has_text = any(isinstance(b, TextBlock) for b in blocks)

        self.assertTrue(has_code)
        self.assertTrue(has_cite)
        self.assertTrue(has_text)

    def test_parse_empty_text(self):
        result = parse_response("")
        self.assertEqual(len(result.blocks), 0)

    def test_parse_no_lang_code_block(self):
        text = "```\nplain code\n```"
        result = parse_response(text)
        self.assertEqual(result.blocks[0].language, "plaintext")


if __name__ == "__main__":
    unittest.main()
