from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
PROJECT = Path(r"G:\我的云端硬盘\AI_Investment_System")
sys.path.insert(0, str(HARNESS))
from validate_run_control import sha256_file, validate_control, validate_path  # noqa: E402

V13 = PROJECT / "output" / "candidates" / "2026-08-29" / "V13-USER-READABLE-20260829015943-JST" / "V13普通中文完整投资产品.html"
V13_SHA = "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4"


def fixture(root: Path) -> dict:
    source, output = root / "input.json", root / "output.json"
    source.write_text('{"input":"bound"}\n', encoding="utf-8")
    output.write_text('{"output":"executed"}\n', encoding="utf-8")
    source_sha, output_sha = sha256_file(source), sha256_file(output)
    return {
        "schema_version": "V7_MINIMAL_HARNESS_PHASE1_1.0",
        "harness_id": "V7_MINIMAL_HARNESS_PHASE1",
        "run_id": "TEST-RUN",
        "generated_at_jst": "2026-08-30T00:00:00+09:00",
        "control_status": "VALIDATED",
        "active_task_id": "TASK-1",
        "tasks": [{"task_id": "TASK-1", "status": "VALIDATED"}],
        "roles": {
            "CHAIRMAN": {"permissions": ["APPROVE", "AUTHORIZE_RELEASE"]},
            "GPT_CONTROL": {"permissions": ["DEFINE", "AUTHORIZE", "ACCEPT"]},
            "CODEX_EXECUTOR": {"permissions": ["BIND_INPUT", "EXECUTE", "TEST"]},
            "INDEPENDENT_VALIDATOR": {"permissions": ["READ", "VALIDATE", "REPORT"]},
        },
        "task": {
            "task_id": "TASK-1", "task_name": "fixture",
            "owner_controller": {"role": "GPT_CONTROL", "actor": "V7总控-3"},
            "executor": {"role": "CODEX_EXECUTOR", "actor": "Codex-V7-1"},
            "acceptance_owner": {"role": "GPT_CONTROL", "actor": "V7总控-3"},
        },
        "scope": {
            "allowed": ["CREATE_MINIMAL_HARNESS", "RUN_LOCAL_TESTS"],
            "forbidden": ["MODIFY_V13_HTML", "MODIFY_V13_PDF", "RESEARCH_SECURITIES", "BUILD_FULL_PRODUCT", "CONNECT_MACRO_PIPELINE", "CONNECT_PDCA_PIPELINE", "PRODUCE_DAILY_REPORT", "OVERWRITE_DAILY_REPORT", "RELEASE", "TRADE", "ORDER", "BROKER_ORDER_API", "BUILD_FULL_HARNESS"],
        },
        "stages": {
            "ordered": ["S0_DEFINED", "S1_INPUT_BOUND", "S2_AUTHORIZED", "S3_EXECUTED", "S4_VALIDATED", "S5_ACCEPTANCE_PENDING", "S5_ACCEPTED"],
            "current": "S4_VALIDATED",
            "history": [
                {"stage": "S0_DEFINED", "status": "PASS", "actor_role": "GPT_CONTROL"},
                {"stage": "S1_INPUT_BOUND", "status": "PASS", "actor_role": "CODEX_EXECUTOR"},
                {"stage": "S2_AUTHORIZED", "status": "PASS", "actor_role": "GPT_CONTROL"},
                {"stage": "S3_EXECUTED", "status": "PASS", "actor_role": "CODEX_EXECUTOR"},
                {"stage": "S4_VALIDATED", "status": "PASS", "actor_role": "INDEPENDENT_VALIDATOR"},
            ],
        },
        "authorization": {"authorized_by_role": "GPT_CONTROL", "authorized_by_actor": "V7总控-3", "modify_input_allowed": False, "production_allowed": False, "release_allowed": False, "trade_allowed": False, "order_allowed": False},
        "inputs": [{"artifact_id": "INPUT-1", "path": str(source), "version": "1", "size_bytes": source.stat().st_size, "sha256": source_sha, "input_role": "FORMAL_TASK_INPUT", "binding_status": "BOUND"}],
        "outputs": [{"artifact_id": "OUTPUT-1", "path": str(output), "size_bytes": output.stat().st_size, "sha256": output_sha, "producer_role": "CODEX_EXECUTOR"}],
        "consumption_chain": [{"relation_id": "OUTPUT-TO-VALIDATOR", "producer": "CODEX_EXECUTOR", "produced_artifact": "OUTPUT-1", "produced_artifact_sha256": output_sha, "consumer": "INDEPENDENT_VALIDATOR", "consumed_artifact_sha256": output_sha}],
        "validation": {"validator_mode": "READ_ONLY", "auto_repair": False, "auto_advance": False, "result": "TECHNICAL_CHECK_PASS"},
        "pass_levels": [
            {"level": 1, "name": "TECHNICAL_CHECK_PASS", "status": "PASS", "decided_by_role": "INDEPENDENT_VALIDATOR", "basis": "DIRECT_VALIDATION"},
            {"level": 2, "name": "CONTENT_OR_LOCAL_ACCEPTANCE_PASS", "status": "PENDING", "decided_by_role": None, "basis": None},
            {"level": 3, "name": "INDEPENDENT_FINAL_ACCEPTANCE_PASS", "status": "PENDING", "decided_by_role": None, "basis": None},
            {"level": 4, "name": "GPT_BUSINESS_ACCEPTANCE_PASS", "status": "PENDING", "decided_by_role": None, "basis": None},
            {"level": 5, "name": "CHAIRMAN_APPROVED", "status": "PENDING", "decided_by_role": None, "basis": None},
        ],
        "release": {"chairman_decision": "PENDING", "decision_by_role": None, "release_authorized": False, "authorized_by_role": None},
        "safety_counters": {"v13_modified_count": 0, "release_executed_count": 0, "trade_executed_count": 0, "order_executed_count": 0, "daily_report_overwrite_count": 0, "full_product_build_started_count": 0, "scope_deviation_count": 0},
        "recovery": {"last_valid_stage": "S4_VALIDATED", "last_valid_input": "INPUT-1", "last_valid_output": "OUTPUT-1", "failed_stage": None, "blocked_reason": "WAITING_ACCEPTANCE", "retry_allowed": True, "resume_from": "S5_ACCEPTANCE_PENDING"},
        "next_action": {"auto_continue": False, "required_role": "GPT_CONTROL", "action": "WAIT_FOR_ACCEPTANCE"},
    }


class MinimalHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.control = fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, control=None):
        return validate_control(control or self.control, self.root)

    def test_01_normal_s0_to_s4_passes(self):
        self.assertEqual(self.run_check()["control_result"], "CONTROL_VALID")

    def test_02_s1_to_s3_skip_authorization_fails(self):
        c = copy.deepcopy(self.control)
        c["stages"]["history"] = [c["stages"]["history"][0], c["stages"]["history"][1], c["stages"]["history"][3]]
        c["stages"]["current"] = "S3_EXECUTED"
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_03_changed_input_sha_invalidates_binding(self):
        Path(self.control["inputs"][0]["path"]).write_text('{"input":"changed"}\n', encoding="utf-8")
        self.assertEqual(self.run_check()["control_result"], "CONTROL_INVALID")

    def test_04_codex_cannot_approve_for_chairman(self):
        c = copy.deepcopy(self.control)
        c["release"].update({"chairman_decision": "APPROVED", "decision_by_role": "CODEX_EXECUTOR", "release_authorized": False})
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_05_local_pass_cannot_auto_promote_final_pass(self):
        c = copy.deepcopy(self.control)
        c["pass_levels"][1].update({"status": "PASS", "decided_by_role": "CODEX_EXECUTOR", "basis": "EXPLICIT_REVIEW"})
        c["pass_levels"][2].update({"status": "PASS", "decided_by_role": "CODEX_EXECUTOR", "basis": "AUTO_DERIVED"})
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_06_release_true_without_chairman_authorization_fails(self):
        c = copy.deepcopy(self.control)
        c["release"]["release_authorized"] = True
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_07_consumed_sha_mismatch_fails(self):
        c = copy.deepcopy(self.control)
        c["consumption_chain"][0]["consumed_artifact_sha256"] = "B" * 64
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_08_second_active_task_is_blocked(self):
        c = copy.deepcopy(self.control)
        c["tasks"].append({"task_id": "TASK-2", "status": "DEFINED"})
        self.assertEqual(self.run_check(c)["control_result"], "CONTROL_INVALID")

    def test_09_failure_reports_recovery_fields(self):
        c = copy.deepcopy(self.control)
        c["stages"]["history"] = [c["stages"]["history"][0], c["stages"]["history"][1], c["stages"]["history"][3]]
        c["stages"]["current"] = "S3_EXECUTED"
        result = self.run_check(c)
        self.assertEqual(result["control_result"], "CONTROL_INVALID")
        self.assertEqual(result["recovery"]["last_valid_stage"], "S4_VALIDATED")
        self.assertEqual(result["recovery"]["resume_from"], "S5_ACCEPTANCE_PENDING")

    def test_10_validator_does_not_modify_v13(self):
        self.assertTrue(V13.is_file())
        before = sha256_file(V13)
        path = self.root / "RUN_CONTROL.json"
        path.write_text(json.dumps(self.control, ensure_ascii=False, indent=2), encoding="utf-8")
        control_before = sha256_file(path)
        result = validate_path(path, self.root)
        self.assertEqual(result["control_result"], "CONTROL_VALID")
        self.assertEqual(sha256_file(path), control_before)
        self.assertEqual(before, V13_SHA)
        self.assertEqual(sha256_file(V13), V13_SHA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
