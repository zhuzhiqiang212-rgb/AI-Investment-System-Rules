import tempfile
import unittest
from pathlib import Path

from scripts.complete_product_v2.contracts import (
    ContractError,
    PDF_AUTHORIZATION,
    assert_no_prior_candidate_dependency,
    validate_final_judgment,
    validate_handoff,
    validate_pdf_authorization,
)


class CompleteProductV2GateTests(unittest.TestCase):
    def test_prior_candidate_dependency_is_blocked(self):
        with self.assertRaises(ContractError):
            assert_no_prior_candidate_dependency([r"output/candidates/2026-08-20/failed.html"])

    def test_missing_final_judgment_is_blocked(self):
        with self.assertRaises(ContractError):
            validate_final_judgment({"parent_run_id": "RUN"}, "RUN")

    def test_pdf_without_exact_authorization_is_blocked(self):
        with self.assertRaises(ContractError):
            validate_pdf_authorization({"run_id": "RUN", "authorization": "PASS"}, "RUN")

    def test_pdf_exact_authorization_is_accepted(self):
        validate_pdf_authorization({"run_id": "RUN", "authorization": PDF_AUTHORIZATION}, "RUN")

    def test_stage_ab_handoff_must_not_claim_product_or_pdf(self):
        payload = {
            "run_id": "RUN", "evidence_cutoff_jst": "2026-08-20T22:41:45+09:00",
            "feature_matrix": {}, "accounts_and_risk": {"account_known_values_jpy": {}},
            "seven_layers": [], "formal_gates": {}, "judgment_matrix": {}, "evidence_registry": [],
            "product_generated": True, "safety": {"pdf_generated": True, "trade_calls": 0, "order_calls": 0},
        }
        errors = validate_handoff(payload)
        self.assertIn("stage_ab_must_not_generate_product", errors)
        self.assertIn("stage_ab_must_not_generate_pdf", errors)


if __name__ == "__main__":
    unittest.main()