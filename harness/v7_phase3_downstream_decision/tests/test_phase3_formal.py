import sys
import unittest
from pathlib import Path


PHASE3_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PHASE3_DIR.parents[1]
sys.path.insert(0, str(PHASE3_DIR))

from validate_downstream_decision import (  # noqa: E402
    CHAIN,
    INTERFACES,
    action_eligible,
    apply_pdca_feedback,
    company_overlay_allowed,
    evidence_resolves,
    interface_set_valid,
    load,
    source_fact_winner,
    target_calculation_status,
    trace_complete,
    validate,
)


CURRENT = PHASE3_DIR / "downstream_decision_current.json"


class Phase3FormalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load(CURRENT)

    def test_01_validator_accepts_formal_current(self):
        report = validate(self.doc, PROJECT_ROOT)
        self.assertEqual(report["result"], "PHASE3_DOWNSTREAM_DECISION_VALID", report)

    def test_02_exact_eight_interfaces(self):
        self.assertTrue(interface_set_valid(self.doc))
        self.assertEqual(set(self.doc["interfaces"]), set(INTERFACES))

    def test_03_evidence_trace_is_standalone(self):
        evidence = self.doc["interfaces"]["EVIDENCE_TRACE"]
        self.assertEqual(evidence["section_id"], "SECTION_9")
        self.assertIn("EVIDENCE_TRACE", self.doc["interfaces"])

    def test_04_causal_chain_order_is_fixed(self):
        self.assertEqual(self.doc["causal_chain"]["ordered_layers"], CHAIN)

    def test_05_complete_trace_passes(self):
        trace = {field: f"VALUE-{field}" for field in (
            "macro_judgement_id", "strategy_judgement_id", "flow_judgement_id",
            "sector_judgement_id", "company_judgement_id", "portfolio_judgement_id",
            "action_id", "source_ids", "evidence_ids",
        )}
        self.assertTrue(trace_complete(trace))

    def test_06_incomplete_trace_fails(self):
        self.assertFalse(trace_complete({"evidence_id": "E-1"}))

    def test_07_strategy_requires_macro_dependency(self):
        self.assertIn("MACRO_JUDGEMENT_IDS", self.doc["interfaces"]["STRATEGY"]["required_inputs"])

    def test_08_flow_requires_freshness_and_contradiction(self):
        flow = self.doc["interfaces"]["FLOW"]
        self.assertIn("freshness_class", flow["required_fields"])
        self.assertIn("CONTRADICTS", flow["states"])

    def test_09_sector_depends_on_strategy_and_flow(self):
        required = set(self.doc["interfaces"]["SECTOR_ROTATION"]["required_inputs"])
        self.assertEqual(required, {"STRATEGY_JUDGEMENT_IDS", "FLOW_JUDGEMENT_IDS"})

    def test_10_company_overlay_allows_current_price(self):
        self.assertTrue(company_overlay_allowed({"LATEST_PRICE"}))

    def test_11_company_overlay_rejects_baseline_sha_change(self):
        self.assertFalse(company_overlay_allowed({"BASELINE_SHA256"}))

    def test_12_company_baseline_identity_is_immutable(self):
        company = self.doc["interfaces"]["COMPANY_SECURITY"]
        self.assertTrue(company["baseline_identity_immutable"])
        self.assertIn("BASELINE_SHA256", company["dynamic_overlay_may_not_update"])

    def test_13_portfolio_has_contribution_and_source_funds(self):
        fields = set(self.doc["interfaces"]["PORTFOLIO_POSITION"]["required_fields"])
        for field in ("expected_contribution", "bear_contribution", "source_of_funds_boundary"):
            self.assertIn(field, fields)

    def test_14_unverified_account_blocks_precise_action(self):
        self.assertFalse(action_eligible("A_EXECUTE", "UNVERIFIED", True, True, True))

    def test_15_complete_current_account_can_form_action_candidate(self):
        self.assertTrue(action_eligible("A_EXECUTE", "CURRENT", True, True, True))

    def test_16_bullish_wait_is_legal(self):
        self.assertTrue(action_eligible("C_WATCH", "UNVERIFIED", False, False, False))

    def test_17_no_trade_is_legal(self):
        self.assertTrue(action_eligible("NO_TRADE", "UNVERIFIED", False, False, False))

    def test_18_missing_trigger_blocks_precise_action(self):
        self.assertFalse(action_eligible("A_EXECUTE", "CURRENT", False, True, True))

    def test_19_target_unavailable_without_real_data(self):
        self.assertEqual(target_calculation_status(False, True), "TARGET_CALCULATION_UNAVAILABLE")

    def test_20_target_calculable_with_complete_data(self):
        self.assertEqual(target_calculation_status(True, True), "CALCULABLE")

    def test_21_plus_100_is_inactive_by_default(self):
        self.assertEqual(self.doc["interfaces"]["PORTFOLIO_POSITION"]["target_100_default_mode"], "INACTIVE")

    def test_22_pdca_starts_pending_not_due(self):
        pdca = self.doc["interfaces"]["PDCA"]
        self.assertEqual(pdca["new_prediction_status"], "PENDING_NOT_DUE")
        self.assertFalse(pdca["same_day_correctness_verdict_allowed"])

    def test_23_pdca_feedback_does_not_rewrite_locked_prediction(self):
        locked = {"forecast_id": "F-1", "expected_return": 0.1}
        updated = apply_pdca_feedback(locked, {"outcome": "MISS", "confidence": "LOW"})
        self.assertEqual(updated["forecast_id"], "F-1")
        self.assertEqual(updated["expected_return"], 0.1)
        self.assertNotIn("outcome", updated)
        self.assertEqual(updated["confidence"], "LOW")

    def test_24_primary_source_wins_conflict(self):
        winner = source_fact_winner([{"tier": 3, "value": 1}, {"tier": 1, "value": 2}])
        self.assertEqual(winner["value"], 2)

    def test_25_evidence_reference_resolves(self):
        pool = [{"evidence_id": "E-1", "source_id": "S-1", "source_class": "OFFICIAL",
                 "artifact_id": "A-1", "sha256_or_version": "a" * 64,
                 "supports_conclusion_ids": ["C-1"]}]
        self.assertTrue(evidence_resolves(pool, "C-1"))
        self.assertFalse(evidence_resolves(pool, "C-2"))

    def test_26_sections_zero_and_three_through_nine_are_bound(self):
        bindings = self.doc["product_section_binding"]["interface_to_section"].values()
        for section in ("Section0", "Section3", "Section4", "Section5", "Section6", "Section7", "Section8", "Section9"):
            self.assertIn(section.replace("Section", "SECTION_"), bindings)

    def test_27_unauthorized_sample_is_not_promoted(self):
        disposition = self.doc["sample_disposition"]
        self.assertFalse(disposition["automatic_promotion"])
        self.assertFalse(disposition["release_basis"])

    def test_28_no_real_records_or_production_calls(self):
        self.assertEqual(sum(len(item["real_records"]) for item in self.doc["interfaces"].values()), 0)
        self.assertEqual(self.doc["identity"]["production_ready"], "NO")
        self.assertFalse(any(self.doc["safety"].values()))

    def test_29_v13_binding_is_frozen(self):
        self.assertEqual(self.doc["governance_bindings"]["research_baseline_sha256"],
                         "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4")

    def test_30_phase2_binding_is_accepted_commit(self):
        self.assertEqual(self.doc["governance_bindings"]["phase2_acceptance_commit"],
                         "57e2a0618ad41287e3fdd70a068cebc6b6c6301c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
