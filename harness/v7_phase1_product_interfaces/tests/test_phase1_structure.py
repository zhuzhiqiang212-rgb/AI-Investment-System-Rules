from __future__ import annotations
import copy, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PROJECT = Path(r"G:\我的云端硬盘\AI_Investment_System")
sys.path.insert(0, str(STAGE))
from validate_phase1_structure import load, sha256_file, validate_phase1  # noqa: E402

SOURCE = STAGE / "phase1_structure_example.json"
V13 = PROJECT / "output" / "candidates" / "2026-08-29" / "V13-USER-READABLE-20260829015943-JST" / "V13普通中文完整投资产品.html"
V13_SHA = "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4"

class Phase1Tests(unittest.TestCase):
    def setUp(self): self.data = load(SOURCE)
    def result(self, data=None): return validate_phase1(data or self.data, PROJECT)

    def test_01_seven_core_interfaces_are_represented(self):
        names = self.data["interfaces"]
        self.assertTrue(all(name in names for name in ["BUSINESS_BLUEPRINT", "PRODUCTION_SOP", "RESEARCH_BASELINE", "FRESH_INTEL", "MARKET_DATA", "PORTFOLIO_STATE", "PDCA_STATE"]))
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")

    def test_02_missing_version_or_sha_cannot_be_ready(self):
        data = copy.deepcopy(self.data); current = data["interfaces"]["BUSINESS_BLUEPRINT"]["records"][0]
        current["version"] = None; data["product_skeleton"]["production_readiness"] = "YES"
        self.assertEqual(self.result(data)["result"], "PHASE1_STRUCTURE_INVALID")

    def test_03_two_current_blueprints_fail(self):
        data = copy.deepcopy(self.data); data["interfaces"]["BUSINESS_BLUEPRINT"]["records"].append(copy.deepcopy(data["interfaces"]["BUSINESS_BLUEPRINT"]["records"][0]))
        self.assertEqual(self.result(data)["result"], "PHASE1_STRUCTURE_INVALID")

    def test_04_v13_baseline_and_dynamic_overlay_can_coexist(self):
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")
        self.assertEqual(self.data["baseline_dynamic_model"]["dynamic_overlay"]["baseline_reference_id"], "V13_RESEARCH_BASELINE")

    def test_05_dynamic_overlay_cannot_override_baseline_identity(self):
        data = copy.deepcopy(self.data); data["baseline_dynamic_model"]["dynamic_overlay"]["baseline_sha256"] = "0" * 64
        self.assertEqual(self.result(data)["result"], "PHASE1_STRUCTURE_INVALID")

    def test_06_bullish_prediction_and_wait_action_are_legal(self):
        split = self.data["product_skeleton"]["prediction_action_separation"]
        self.assertEqual(split["prediction"]["direction"], "BULLISH"); self.assertEqual(split["action"]["action"], "WAIT")
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")

    def test_07_action_trace_can_reference_all_upstream_ids(self):
        data = copy.deepcopy(self.data); trace = data["product_skeleton"]["conclusion_trace"]
        trace.update({"action_id": "EXAMPLE_ACTION", "portfolio_judgement_id": "P1", "company_judgement_id": "C1", "sector_judgement_id": "S1", "strategy_judgement_id": "ST1", "macro_judgement_id": "M1", "source_ids": ["SRC1"]})
        self.assertEqual(self.result(data)["result"], "PHASE1_STRUCTURE_VALID")

    def test_08_target40_fields_aggregate_without_fake_return(self):
        target = self.data["product_skeleton"]["target_40_interface"]
        self.assertIsNone(target["expected_portfolio_return"]); self.assertEqual(target["records"], [])
        bad = copy.deepcopy(self.data); bad["product_skeleton"]["target_40_interface"]["expected_portfolio_return"] = 0
        self.assertEqual(self.result(bad)["result"], "PHASE1_STRUCTURE_INVALID")

    def test_09_target100_defaults_inactive(self):
        self.assertEqual(self.data["product_skeleton"]["target_100_interface"]["100_TARGET_MODE"], "INACTIVE")
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")

    def test_10_missing_production_sop_keeps_production_not_ready(self):
        self.assertEqual(self.data["interfaces"]["PRODUCTION_SOP"]["status"], "NOT_BUILT")
        self.assertEqual(self.data["product_skeleton"]["production_readiness"], "NO")
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")

    def test_11_fresh_intel_supports_four_freshness_classes(self):
        self.assertEqual(self.data["interfaces"]["FRESH_INTEL"]["freshness_classes"], ["HOT", "CURRENT", "STALE", "ARCHIVE"])
        self.assertEqual(self.result()["result"], "PHASE1_STRUCTURE_VALID")

    def test_12_phase1_does_not_modify_v13(self):
        before = sha256_file(V13); self.assertEqual(before, V13_SHA)
        self.result(); self.assertEqual(sha256_file(V13), before)

if __name__ == "__main__": unittest.main(verbosity=2)
