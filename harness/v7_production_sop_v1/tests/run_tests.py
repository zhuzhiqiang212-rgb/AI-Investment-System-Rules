from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path


HERE = Path(__file__).resolve()
SOP_DIR = HERE.parents[1]
sys.path.insert(0, str(HERE))

from test_production_sop import ProductionSopTests  # noqa: E402


class CaptureResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records: list[dict[str, str]] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test._testMethodName, "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"test": test._testMethodName, "status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"test": test._testMethodName, "status": "ERROR", "detail": self._exc_info_to_string(err, test)})


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProductionSopTests)
    runner = unittest.TextTestRunner(verbosity=2, resultclass=CaptureResult)
    result: CaptureResult = runner.run(suite)
    report = {
        "report_id": "V7_PRODUCTION_SOP_V1_20_TEST_REPORT",
        "generated_at_jst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "test_count": result.testsRun,
        "pass_count": sum(item["status"] == "PASS" for item in result.records),
        "failure_count": len(result.failures) + len(result.errors),
        "result": "20_OF_20_PASS" if result.wasSuccessful() and result.testsRun == 20 else "TESTS_FAILED",
        "tests": result.records,
    }
    (SOP_DIR / "sop_test_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if result.wasSuccessful() and result.testsRun == 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
