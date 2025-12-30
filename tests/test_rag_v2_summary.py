import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock

from app.ai.prompts.compiler import build_system_prompt


def run_tests():
    print("STARTING TESTS")

    # TEST 1: Summary Mode
    print("Testing Case 1: RagActive=True, SummaryMode=True")
    try:
        p1 = build_system_prompt(user=MagicMock(), rag_v2_active=True, rag_v2_summary_mode=True)
        if "CONTROLLED SUMMARY CONTRACT" not in p1:
            print("FAIL: 'CONTROLLED SUMMARY CONTRACT' missing in Summary Mode!")
            print("FULL PROMPT P1:\n", p1)
            return False
        if "ANSWER CONTRACT" in p1:
            print("FAIL: 'ANSWER CONTRACT' present in Summary Mode (should be swapped out)!")
            return False
        print("PASS Case 1")
    except Exception as e:
        print(f"Exception in Case 1: {e}")
        return False

    # TEST 2: Normal Mode
    print("Testing Case 2: RagActive=True, SummaryMode=False")
    try:
        p2 = build_system_prompt(user=MagicMock(), rag_v2_active=True, rag_v2_summary_mode=False)
        if "ANSWER CONTRACT" not in p2:
            print("FAIL: 'ANSWER CONTRACT' missing in Normal Mode!")
            print("FULL PROMPT P2:\n", p2)
            return False
        if "CONTROLLED SUMMARY CONTRACT" in p2:
            print("FAIL: 'CONTROLLED SUMMARY CONTRACT' present in Normal Mode!")
            return False
        print("PASS Case 2")
    except Exception as e:
        print(f"Exception in Case 2: {e}")
        return False

    return True


if __name__ == "__main__":
    if run_tests():
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
