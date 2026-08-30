from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PROJECT = STAGE.parents[1]
sys.path.insert(0, str(STAGE))

from validate_downstream_decision import load, validate  # noqa: E402

SOURCE = STAGE / "downstream_decision_current.json"


class Phase3DownstreamDecisionTests(unittest.TestCase):
    def setUp(self):
        self.data = load(SOURCE)

    def result(self, data=None):
        return validate(data or self.data, PROJECT)

    def test_01_identity(self):
        self.assertEqual(self.data["identity"]["status"], "CURRENT")
        self.assertEqual(self.result()["result"], "PHASE3_DOWNSTREAM_DECISION_VALID")

    def test_02_phase2_bound(self):
        self.assertEqual(self.data["governance_bindings"]["phase2_macro_worldview_id"], "V7_PHASE2_MACRO_WORLDVIEW_CURRENT_v1.0")

    def test_03_v13_bound(self):
        self.assertEqual(self.data["governance_bindings"]["research_baseline_id"], "V13_RESEARCH_BASELINE")

    def test_04_layers_exact(self):
        self.assertEqual([x["layer"] for x in self.data["layer_interfaces"]], ["STRATEGY", "FLOW", "SECTOR", "COMPANY", "PORTFOLIO", "ACTION", "PDCA"])

    def test_05_strategy_depends_on_macro(self):
        strategy = self.data["layer_interfaces"][0]
        self.assertIn("MACRO_JUDGEMENT_IDS", strategy["required_inputs"])

    def test_06_flow_requires_freshness(self):
        flow = self.data["layer_interfaces"][1]
        self.assertIn("freshness_class", flow["required_fields"])

    def test_07_sector_has_ranking(self):
        sector = self.data["layer_interfaces"][2]
        self.assertIn("ranking", sector["required_fields"])

    def test_08_company_preserves_baseline(self):
        company = self.data["layer_interfaces"][3]
        self.assertIn("V13_RESEARCH_BASELINE", company["required_inputs"])

    def test_09_portfolio_requires_account_confirmation(self):
        portfolio = self.data["layer_interfaces"][4]
        self.assertIn("account_confirmation_required", portfolio["required_fields"])

    def test_10_action_requires_chairman_confirmation(self):
        action = self.data["layer_interfaces"][5]
        self.assertIn("chairman_confirmation_required", action["required_fields"])

    def test_11_pdca_has_error_loop(self):
        pdca = self.data["layer_interfaces"][6]
        self.assertIn("error", pdca["required_fields"])

    def test_12_causal_chain_order(self):
        self.assertEqual(self.data["causal_chain"]["ordered_layers"][0], "MACRO")
        self.assertEqual(self.data["causal_chain"]["ordered_layers"][-1], "PDCA")

    def test_13_trace_includes_action_and_sources(self):
        trace = self.data["causal_chain"]["required_trace_fields"]
        self.assertIn("action_id", trace)
        self.assertIn("source_ids", trace)

    def test_14_no_layer_may_skip_source_trace(self):
        self.assertTrue(self.data["causal_chain"]["no_layer_may_skip_source_trace"])

    def test_15_action_safety(self):
        self.assertFalse(self.data["action_safety"]["broker_order_api_allowed"])
        self.assertFalse(self.data["action_safety"]["trade_execution_allowed"])

    def test_16_action_levels(self):
        self.assertEqual(self.data["action_safety"]["allowed_action_levels"], ["A_EXECUTE", "B_WAIT_TRIGGER", "C_WATCH", "D_EXCLUDE"])

    def test_17_phase3_cannot_generate_today_action(self):
        self.assertFalse(self.data["action_safety"]["phase3_may_generate_today_action"])

    def test_18_sections_bound(self):
        self.assertIn("SECTION_6", self.data["product_section_binding"]["sections_bound"])

    def test_19_evidence_section_required(self):
        self.assertTrue(self.data["product_section_binding"]["section_9_evidence_required"])

    def test_20_release_trade_order_forbidden(self):
        forbidden = set(self.data["phase3_scope"]["forbidden"])
        self.assertTrue({"RELEASE", "TRADE", "ORDER"}.issubset(forbidden))

    def test_21_daily_report_forbidden(self):
        self.assertIn("PRODUCE_DAILY_REPORT", self.data["phase3_scope"]["forbidden"])

    def test_22_no_real_production_flags(self):
        self.assertTrue(all(value is False for value in self.data["safety"].values()))

    def test_23_mutated_phase2_sha_fails(self):
        data = copy.deepcopy(self.data)
        data["governance_bindings"]["phase2_macro_worldview_sha256"] = "0" * 64
        self.assertEqual(self.result(data)["result"], "PHASE3_DOWNSTREAM_DECISION_INVALID")

    def test_24_success_criteria(self):
        self.assertTrue(all(value == "PASS" for value in self.data["success_criteria"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
