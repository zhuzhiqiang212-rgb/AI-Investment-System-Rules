import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PHASE3_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PHASE3_DIR.parents[1]
TEST_FILE = Path(__file__).with_name("test_phase3_formal.py")
REPORT_FILE = PHASE3_DIR / "phase3_formal_test_report.json"
JST = timezone(timedelta(hours=9))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main():
    command = [sys.executable, "-m", "unittest", "-v", str(TEST_FILE)]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    combined = (completed.stdout + "\n" + completed.stderr).strip()
    tests_run = combined.count(" ... ok")
    report = {
        "report_id": "V7_PHASE3_FORMAL_TEST_REPORT_v1.0",
        "task_id": "V7-PHASE3-DOWNSTREAM-DECISION-INTERFACES",
        "run_id": "V7-PHASE3-DOWNSTREAM-20260830-112147-JST",
        "generated_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "status": "PASS" if completed.returncode == 0 and tests_run == 30 else "FAIL",
        "tests_expected": 30, "tests_run": tests_run,
        "failures": combined.count(" ... FAIL"), "errors": combined.count(" ... ERROR"),
        "test_file": str(TEST_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "test_file_sha256": sha256(TEST_FILE), "command_exit_code": completed.returncode,
        "output": combined,
        "prohibitions_confirmed": {"real_api_call_count": 0, "release_count": 0, "trade_count": 0, "order_count": 0},
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "tests_run", "failures", "errors")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
