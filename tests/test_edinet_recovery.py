import io
import json
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_v7_scan_research_package as scan_package
from scripts import edinet_financials


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class EdinetDateAndSecurityTests(unittest.TestCase):
    def test_normalize_date_accepts_compact_and_iso(self):
        self.assertEqual(edinet_financials._normalize_date("20260815"), "20260815")
        self.assertEqual(edinet_financials._normalize_date("2026-08-15"), "20260815")

    def test_normalize_date_rejects_invalid_calendar_date(self):
        with self.assertRaises(ValueError):
            edinet_financials._normalize_date("20260230")

    def test_tls_context_verifies_certificates(self):
        context = edinet_financials._ctx()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_find_annual_doc_starts_from_explicit_as_of_date(self):
        seen_urls = []

        def fake_urlopen(request, **kwargs):
            seen_urls.append(request.full_url)
            return FakeResponse({
                "results": [{
                    "edinetCode": "E00001",
                    "docTypeCode": "120",
                    "docID": "S100TEST",
                    "docDescription": "annual",
                    "periodEnd": "2026-03-31",
                }]
            })

        with patch.object(edinet_financials.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = edinet_financials.find_annual_doc(
                "E00001", "test-key", days_back=1, as_of_date="20260815"
            )

        self.assertEqual(result["docID"], "S100TEST")
        self.assertIn("date=2026-08-15", seen_urls[0])

    def test_verify_result_contains_no_key_fragment(self):
        payload = {"metadata": {"status": "200"}, "results": []}
        with patch.object(edinet_financials, "_load_key", return_value="SECRET-KEY-VALUE"), \
             patch.object(edinet_financials.urllib.request, "urlopen", return_value=FakeResponse(payload)):
            result = edinet_financials.verify("20260815")

        rendered = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("SECRET", rendered)
        self.assertNotIn("masked", rendered)
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)


class EdinetStatusRegistrationTests(unittest.TestCase):
    def test_connected_status_is_registered_without_key_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "edinet-api-key.txt"
            key_path.write_text("fake-test-key", encoding="utf-8")
            status = scan_package.get_edinet_current_status(
                "20260815",
                key_path=key_path,
                verify_func=lambda date: {
                    "ok": True,
                    "date": date,
                    "http_status": 200,
                    "count": 0,
                    "note": "metadata.status=200",
                },
            )

        self.assertEqual(status["current_status"], "READ_ONLY_API_CONNECTED")
        self.assertTrue(status["current_api_call_attempted"])
        self.assertFalse(status["key_value_logged"])
        self.assertNotIn("fake-test-key", json.dumps(status))

    def test_missing_key_fails_closed_without_api_call(self):
        called = False

        def verify_func(_date):
            nonlocal called
            called = True

        status = scan_package.get_edinet_current_status(
            "20260815", key_path=Path("Z:/missing/edinet-api-key.txt"), verify_func=verify_func
        )
        self.assertEqual(status["current_status"], "BLOCKED_KEY_NOT_FOUND")
        self.assertFalse(status["current_api_call_attempted"])
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
