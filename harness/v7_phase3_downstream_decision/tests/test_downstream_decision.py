"""Compatibility checks for the superseded Work sample.

The unauthorized sample is preserved in Git history, but this entrypoint no longer
asserts its obsolete seven-interface shape.
"""
import json
import unittest
from pathlib import Path


PHASE3_DIR = Path(__file__).resolve().parents[1]


class SupersededSampleCompatibilityTests(unittest.TestCase):
    def test_sample_is_explicitly_superseded(self):
        data = json.loads((PHASE3_DIR / "unauthorized_sample_disposition.json").read_text(encoding="utf-8"))
        self.assertEqual(data["formal_status"], "UNAUTHORIZED_SAMPLE_SUPERSEDED")
        self.assertFalse(data["automatic_promotion"])
        self.assertFalse(data["release_basis"])

    def test_formal_test_suite_is_the_active_suite(self):
        self.assertTrue((PHASE3_DIR / "tests/test_phase3_formal.py").is_file())
        report = json.loads((PHASE3_DIR / "phase3_formal_test_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["tests_run"], 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
