"""
Integration Tests for Beautiful Response Plugin (Parser + Enhancer)
"""

import sys
import unittest
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


# Imports are delayed until after sys.path update
class TestIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        from app.plugins.beautiful_response.enhancer import enhance_response
        from app.plugins.beautiful_response.parser import parse_response

        # Raw noisy input
        raw_input = """Merhaba!

```js
function test() {
  return true;
}
```

> Bu bir alıntı
> Devamı

Sonuç.
"""

        # 1. Parse
        structured = parse_response(raw_input)
        self.assertTrue(len(structured.blocks) >= 4)  # Whitespace blocks might be included

        # 2. Enhance
        clean_markdown = enhance_response(structured)

        # Validate output
        # Should contain parsed elements formatted correctly
        self.assertIn("```javascript", clean_markdown)  # js aliased to javascript
        self.assertIn("> Bu bir alıntı", clean_markdown)
        self.assertIn("Merhaba!", clean_markdown)

        # Check balanced backticks
        self.assertEqual(clean_markdown.count("```") % 2, 0)

    def test_unbalanced_input_handling(self):
        from app.plugins.beautiful_response.enhancer import enhance_response
        from app.plugins.beautiful_response.parser import parse_response

        # Unbalanced input (missing closing backtick)
        raw_input = "Code star:\n```python\nprint(1)"

        structured = parse_response(raw_input)
        # Parser might capture it aggressively or fail to close it.
        # Actually parser regex typically looks for closed blocks.
        # If regex doesn't match, it might treat as text.
        # But if we want to support auto-closing, parser needs to be robust.
        # Our current parser regex `re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)` requires closing tag.
        # So it will likely treat unclosed block as Text.

        # Let's assume parser returns it as TextBlock with backticks.
        clean_markdown = enhance_response(structured)

        # If it's text, enhancer cleanups might leave it.
        # If parser fails to detect code block, it's just text.
        # The enhancer's `_final_cleanup` checks for balanced backticks and appends if needed.

        # In this case: count of ``` is 1. Enhancer should add closing ```.
        self.assertTrue(clean_markdown.strip().endswith("```"))


if __name__ == "__main__":
    unittest.main()
