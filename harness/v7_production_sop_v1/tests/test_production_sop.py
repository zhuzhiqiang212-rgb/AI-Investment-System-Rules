from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
SOP_DIR = HERE.parents[1]
ROOT = HERE.parents[3]
sys.path.insert(0, str(SOP_DIR))

from validate_production_sop import (  # noqa: E402
    SOP_PATH,
    action_pair_legal,
    apply_pdca_feedback,
    consumption_decision,
    load_json,
    missing_data_mode,
    precise_a_action_allowed,
    production_ready_allowed,
    refresh_trigger,
    source_fact_winner,
    validate_single_current,
)


class ProductionSopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sop = load_json(SOP_PATH)

    def test_01_blueprint_and_sop_bind_separately(self) -> None:
        self.assertNotEqual(
            self.sop["governance_bindings"]["business_blueprint"]["blueprint_id"],
            self.sop["identity"]["sop_id"],
        )

    def test_02_two_current_sops_fail(self) -> None:
        self.assertFalse(validate_single_current([{"status": "CURRENT"}, {"status": "CURRENT"}]))

    def test_03_missing_sop_version_blocks_ready(self) -> None:
        broken = copy.deepcopy(self.sop)
        broken["identity"]["version"] = None
        self.assertFalse(production_ready_allowed(broken, [{"status": "CURRENT"}], True))

    def test_04_unchanged_consumed_fresh_intel_is_skipped(self) -> None:
        self.assertEqual(
            consumption_decision("ABC", "ABC", True, False),
            "SKIP_FULL_RECONSUMPTION",
        )

    def test_05_changed_fresh_intel_sha_is_pending(self) -> None:
        self.assertEqual(
            consumption_decision("ABC", "DEF", True, False),
            "PENDING_CONSUMPTION",
        )

    def test_06_freshness_classes_are_complete(self) -> None:
        self.assertEqual(
            self.sop["freshness_management"]["classes"],
            ["HOT", "CURRENT", "STALE", "ARCHIVE"],
        )

    def test_07_persistent_knowledge_is_not_fresh_intel(self) -> None:
        inputs = self.sop["input_system"]
        self.assertNotEqual(inputs["PERSISTENT_KNOWLEDGE"]["read_mode"], inputs["FRESH_INTEL"]["read_mode"])

    def test_08_edinet_is_primary_regulatory_disclosure(self) -> None:
        self.assertEqual(self.sop["edinet_rules"]["source_class"], "PRIMARY_REGULATORY_DISCLOSURE")

    def test_09_media_cannot_override_edinet_fact(self) -> None:
        winner = source_fact_winner([
            {"source": "MEDIA", "tier": 3, "value": 1},
            {"source": "EDINET", "tier": 1, "value": 2},
        ])
        self.assertEqual(winner["source"], "EDINET")

    def test_10_unchanged_consumed_edinet_document_is_skipped(self) -> None:
        self.assertEqual(
            consumption_decision("DOCSHA", "DOCSHA", True, False, False),
            "SKIP_FULL_RECONSUMPTION",
        )

    def test_11_new_material_edinet_disclosure_refreshes(self) -> None:
        self.assertEqual(
            consumption_decision(None, "NEWSHA", False, False, True),
            "PRIMARY_DISCLOSURE_REFRESH_REQUIRED",
        )

    def test_12_new_earnings_triggers_full_company_refresh(self) -> None:
        self.assertEqual(refresh_trigger("NEW_EARNINGS"), "FULL_COMPANY_REFRESH_REQUIRED")

    def test_13_unverified_portfolio_blocks_precise_a_action(self) -> None:
        self.assertFalse(precise_a_action_allowed("UNVERIFIED", True))

    def test_14_hard_block_stops_production(self) -> None:
        self.assertEqual(missing_data_mode("HARD_BLOCK"), "PRODUCTION_BLOCKED")

    def test_15_soft_missing_allows_degraded_mode(self) -> None:
        self.assertEqual(missing_data_mode("SOFT_MISSING"), "DEGRADED_MODE")

    def test_16_bullish_and_wait_is_legal(self) -> None:
        self.assertTrue(action_pair_legal("BULLISH", "B_WAIT_TRIGGER"))

    def test_17_no_trade_is_legal(self) -> None:
        self.assertTrue(action_pair_legal("NEUTRAL", "NO_TRADE"))

    def test_18_pdca_changes_next_run_fields(self) -> None:
        prior = {"signal_weight": 1.0, "confidence": "B", "timing_rule": "BASE"}
        updated = apply_pdca_feedback(
            prior,
            {"signal_weight": 0.8, "confidence": "C", "timing_rule": "REQUIRE_CONFIRMATION"},
        )
        self.assertEqual(updated, {"signal_weight": 0.8, "confidence": "C", "timing_rule": "REQUIRE_CONFIRMATION"})

    def test_19_no_real_news_or_edinet_scan_occurred(self) -> None:
        safety = self.sop["safety"]
        self.assertFalse(safety["real_edinet_fetch_executed"])
        self.assertFalse(safety["news_scan_executed"])
        self.assertFalse(safety["laolei_scan_executed"])
        self.assertFalse(safety["hushui_scan_executed"])

    def test_20_v13_was_not_modified(self) -> None:
        baseline = self.sop["governance_bindings"]["research_baseline"]
        digest = hashlib.sha256((ROOT / baseline["path"]).read_bytes()).hexdigest().upper()
        self.assertEqual(digest, "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4")


if __name__ == "__main__":
    unittest.main()
