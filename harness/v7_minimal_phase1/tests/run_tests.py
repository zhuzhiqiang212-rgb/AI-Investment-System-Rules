from __future__ import annotations
import argparse, json, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.records = []
    def addSuccess(self, test):
        super().addSuccess(test); self.records.append({"test_id": test._testMethodName, "result": "PASS"})
    def addFailure(self, test, err):
        super().addFailure(test, err); self.records.append({"test_id": test._testMethodName, "result": "FAIL", "detail": self._exc_info_to_string(err, test)})
    def addError(self, test, err):
        super().addError(test, err); self.records.append({"test_id": test._testMethodName, "result": "FAIL", "detail": self._exc_info_to_string(err, test)})

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--report", type=Path, required=True); args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    records = sorted(result.records, key=lambda item: item["test_id"])
    report = {"report_type": "V7_MINIMAL_HARNESS_PHASE1_SELF_TEST", "generated_at_jst": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"), "test_count": len(records), "pass_count": sum(x["result"] == "PASS" for x in records), "fail_count": sum(x["result"] != "PASS" for x in records), "tests": records}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__": raise SystemExit(main())
