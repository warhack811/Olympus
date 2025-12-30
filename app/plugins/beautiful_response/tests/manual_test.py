"""
Manual Test for Beautiful Response Plugin Integration via Response Processor
"""

import logging
import sys
from pathlib import Path

# Setup simple logging
logging.basicConfig(level=logging.INFO)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import processor after path setup
from app.plugins import load_plugins
from app.services.response_processor import full_post_process


def run_test():
    """Manual integration test"""
    print("Loading plugins...")
    load_plugins()

    test_input = """
Merhaba! İşte bir örnek:

```python
def test():
    print("Working")
```

> Alıntı yapıyorum.

Normal text.
    """

    print(f"\n[INPUT] Length: {len(test_input)}")
    print("-" * 50)
    print(test_input)
    print("-" * 50)

    # Process
    print("\nProcessing...")
    result = full_post_process(test_input)

    print(f"\n[OUTPUT] Length: {len(result)}")
    print("-" * 50)
    print(result)
    print("-" * 50)

    # Validation
    if "```python" in result:
        print("\n[PASS] Code block preserved/enhanced")
    else:
        print("\n[FAIL] Code block missing or malformed")

    if "> Alıntı" in result:
        print("[PASS] Citation block preserved/enhanced")
    else:
        print("[FAIL] Citation block missing")


if __name__ == "__main__":
    run_test()
