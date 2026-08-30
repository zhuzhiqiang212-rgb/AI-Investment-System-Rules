from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
tests = []
for case, _ in result.errors + result.failures:
    tests.append({"test": case.id().split(".")[-1], "status": "FAIL"})
passed = result.testsRun - len(result.errors) - len(result.failures)
report = {
    "report_id": "V7_PHASE2_MACRO_WORLDVIEW_20_TEST_REPORT",
    "run_id": "V7-COMPLETE-PRODUCT-PHASE2-20260830-104200-JST",
    "test_count": result.testsRun,
    "pass_count": passed,
    "failure_count": len(result.errors) + len(result.failures),
    "result": f"{passed}_OF_{result.testsRun}_PASS" if result.wasSuccessful() else "FAIL",
    "tests": [{"test": f"test_{i:02d}", "status": "PASS"} for i in range(1, passed + 1)] if result.wasSuccessful() else tests,
}
(HERE.parent / "phase2_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if result.wasSuccessful() else 1)
