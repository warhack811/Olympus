"""
Expanded Parser Tests for Edge Cases
"""

import sys
import unittest
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.plugins.beautiful_response.parser import parse_response


class TestParserEdgeCases(unittest.TestCase):
    def test_parse_cpp_language(self):
        text = "```c++\nint main() {}\n```"
        result = parse_response(text)
        self.assertEqual(result.blocks[0].language, "c++")

    def test_parse_sharp_language(self):
        text = "```c#\nvar x = 1;\n```"
        result = parse_response(text)
        self.assertEqual(result.blocks[0].language, "c#")

    def test_parse_spaced_language(self):
        text = "``` python \nprint(1)\n```"
        result = parse_response(text)
        self.assertEqual(result.blocks[0].language, "python")

    def test_parse_no_lang(self):
        text = "```\ncode\n```"
        result = parse_response(text)
        self.assertEqual(result.blocks[0].language, "plaintext")


if __name__ == "__main__":
    unittest.main()
