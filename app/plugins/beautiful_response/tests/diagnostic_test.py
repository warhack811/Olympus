"""
Diagnostic Test for Language Tag Visibility
Simulates the flow from LLM output to Final Response
"""

import logging
import sys
from pathlib import Path

# Configure logging to show INFO
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("diagnostic_test")

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.plugins import load_plugins
from app.services.response_processor import full_post_process


def run_diagnostic():
    # Load plugins
    load_plugins()

    # Simulate LLM Output (this is what we expect from LLM)
    # Scenario: User asked "Python list example"
    llm_output = """Here is a Python list example:

``` python
my_list = [1, 2, 3]
print(my_list)
```

And here is some text.
"""

    logger.info("--- DIAGNOSTIC START ---")
    logger.info(f"[SIMULATED LLM OUTPUT] {llm_output}")

    # Run pipeline
    final_output = full_post_process(llm_output)

    logger.info("--- DIAGNOSTIC END ---")

    # Verification
    if "```python" in final_output:
        logger.info("✅ Code block has 'python' tag")
    elif "``` python" in final_output:
        logger.info("✅ Code block has ' python' tag (acceptable but should be trimmed)")
    else:
        logger.error("❌ Code block MISSING language tag or malformed")


if __name__ == "__main__":
    run_diagnostic()
