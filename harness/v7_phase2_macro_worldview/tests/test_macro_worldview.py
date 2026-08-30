from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PROJECT = STAGE.parents[1]
sys.path.insert(0, str(STAGE))

from validate_macro_worldview import load, validate  # noqa: E402

SOURCE = STAGE / "macro_worldview_current.json"


class Phase2MacroWorldviewTests(unittest.TestCase):
    def setUp(self):
        self.data = load(SOURCE)

    def result(self, data=None):
        return validate(data or self.data, PROJECT)

    def test_01_identity_is_current_but_not_production_ready(self):
        self.assertEqual(self.data["identity"]["status"], "CURRENT")
        self.assertEqual(self.data["identity"]["production_ready"], "NO")
        self.assertEqual(self.result()["result"], "PHASE2_MACRO_WORLDVIEW_VALID")

    def test_02_current_blueprint_and_sop_are_bound(self):
        b = self.data["governance_bindings"]
        self.assertEqual(b["business_blueprint_id"], "V7_COMPLETE_PRODUCT_CURRENT_v2.0")
        self.assertEqual(b["production_sop_id"], "V7_PRODUCTION_SOP_CURRENT_v1.0")
        self.assertEqual(self.result()["result"], "PHASE2_MACRO_WORLDVIEW_VALID")

    def test_03_v13_identity_is_protected(self):
        self.assertEqual(self.data["governance_bindings"]["research_baseline_id"], "V13_RESEARCH_BASELINE")
        self.assertEqual(self.result()["result"], "PHASE2_MACRO_WORLDVIEW_VALID")

    def test_04_missing_v13_sha_fails(self):
        data = copy.deepcopy(self.data)
        data["governance_bindings"]["research_baseline_sha256"] = "0" * 64
        self.assertEqual(self.result(data)["result"], "PHASE2_MACRO_WORLDVIEW_INVALID")

    def test_05_required_inputs_are_exactly_defined(self):
        self.assertEqual(self.data["macro_input_contract"]["required_inputs"], ["BUSINESS_BLUEPRINT", "PRODUCTION_SOP", "MARKET_DATA", "FRESH_INTEL", "PERSISTENT_KNOWLEDGE", "PDCA_STATE"])

    def test_06_market_data_staleness_hard_blocks(self):
        self.assertEqual(self.data["macro_input_contract"]["stale_core_market_data_result"], "PRODUCTION_BLOCKED")

    def test_07_worldview_axes_are_complete(self):
        self.assertEqual([x["axis_id"] for x in self.data["worldview_axes"]], ["US_MACRO", "JAPAN_MACRO", "CHINA_MACRO", "GLOBAL_LIQUIDITY", "AI_CAPEX_CYCLE", "GEOPOLITICAL_RISK"])

    def test_08_each_axis_has_topics_and_output(self):
        self.assertTrue(all(x["required_topics"] and x["output"] for x in self.data["worldview_axes"]))

    def test_09_delta_states_match_sop(self):
        self.assertEqual(self.data["macro_delta_states"], ["CHANGED", "UNCHANGED", "STRENGTHENED", "WEAKENED", "INVALIDATED"])

    def test_10_macro_judgement_has_plain_language_summary(self):
        self.assertIn("plain_language_summary", self.data["macro_judgement_contract"]["required_fields"])

    def test_11_macro_judgement_requires_source_ids(self):
        self.assertIn("source_ids", self.data["macro_judgement_contract"]["required_fields"])

    def test_12_macro_judgement_requires_portfolio_relevance(self):
        self.assertIn("portfolio_relevance", self.data["macro_judgement_contract"]["required_fields"])

    def test_13_news_cannot_directly_create_buy_action(self):
        self.assertIn("NEWS_DIRECTLY_TO_BUY", self.data["macro_judgement_contract"]["forbidden_shortcuts"])

    def test_14_missing_data_cannot_be_no_risk(self):
        self.assertIn("MISSING_DATA_AS_NO_RISK", self.data["macro_judgement_contract"]["forbidden_shortcuts"])

    def test_15_handoff_to_strategy_has_required_ids(self):
        self.assertIn("macro_judgement_id", self.data["handoff_rules"]["macro_to_strategy_requires"])

    def test_16_phase2_cannot_generate_action(self):
        self.assertTrue(self.data["handoff_rules"]["no_action_generation_in_phase2"])

    def test_17_phase3_is_required_for_strategy_flow_sector(self):
        self.assertTrue(self.data["handoff_rules"]["phase3_required_for_strategy_flow_sector"])

    def test_18_section_2_is_bound(self):
        self.assertEqual(self.data["product_section_binding"]["section_id"], "SECTION_2")

    def test_19_no_real_production_flags_are_false(self):
        self.assertTrue(all(value is False for value in self.data["safety"].values()))

    def test_20_forbidden_scope_contains_release_trade_order(self):
        forbidden = set(self.data["phase2_scope"]["forbidden"])
        self.assertTrue({"RELEASE", "TRADE", "ORDER"}.issubset(forbidden))


if __name__ == "__main__":
    unittest.main(verbosity=2)
