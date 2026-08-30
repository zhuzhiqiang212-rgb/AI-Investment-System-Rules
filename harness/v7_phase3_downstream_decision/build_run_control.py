#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "harness/v7_minimal_phase1/RUN_CONTROL.json"
MANIFEST = ROOT / "harness/v7_phase3_downstream_decision/phase3_artifact_manifest.json"
RUN_ID = "V7-PHASE3-DOWNSTREAM-20260830-112147-JST"
TASK_ID = "V7-PHASE3-DOWNSTREAM-DECISION-INTERFACES"
JST = timezone(timedelta(hours=9))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact(artifact_id: str, relative: str, role: str, output: bool = False) -> dict:
    path = ROOT / relative
    value = {
        "artifact_id": artifact_id,
        "path": relative.replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if output:
        value["producer_role"] = "CODEX_EXECUTOR"
    else:
        value["input_role"] = role
        value["binding_status"] = "BOUND"
    return value


def main() -> None:
    control = json.loads(CONTROL.read_text(encoding="utf-8"))
    now = datetime.now(JST).isoformat(timespec="seconds")
    manifest_paths = [
        "harness/v7_phase3_downstream_decision/phase3_task_authority.json",
        "harness/v7_phase3_downstream_decision/unauthorized_sample_disposition.json",
        "harness/v7_phase3_downstream_decision/downstream_decision_current.json",
        "harness/v7_phase3_downstream_decision/downstream_decision.schema.json",
        "harness/v7_phase3_downstream_decision/validate_downstream_decision.py",
        "harness/v7_phase3_downstream_decision/tests/test_phase3_formal.py",
        "harness/v7_phase3_downstream_decision/tests/run_formal_tests.py",
        "harness/v7_phase3_downstream_decision/tests/test_downstream_decision.py",
        "harness/v7_phase3_downstream_decision/tests/run_tests.py",
        "harness/v7_phase3_downstream_decision/phase3_formal_test_report.json",
        "harness/v7_phase3_downstream_decision/phase3_test_report.json",
        "harness/v7_phase3_downstream_decision/README.html",
        "harness/v7_phase3_downstream_decision/build_run_control.py",
    ]
    manifest = {
        "manifest_id": "V7_PHASE3_ARTIFACT_MANIFEST_v1.0",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "generated_at_jst": now,
        "artifacts": [
            {
                "path": relative,
                "size_bytes": (ROOT / relative).stat().st_size,
                "sha256": sha256(ROOT / relative),
            }
            for relative in manifest_paths
        ],
        "v13_sha256_verified": "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4",
        "sample_handling": "REVIEWED_THEN_FULLY_REBUILT_AND_OVERWRITTEN",
        "release_basis": False,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inputs = [
        artifact("PHASE1_STRUCTURE", "harness/v7_phase1_product_interfaces/phase1_structure_example.json", "ACCEPTED_PHASE1_STRUCTURE"),
        artifact("PHASE2_MACRO_WORLDVIEW", "harness/v7_phase2_macro_worldview/macro_worldview_current.json", "ACCEPTED_PHASE2_OUTPUT"),
        artifact("PRODUCTION_SOP", "harness/v7_production_sop_v1/V7正式生产SOP_Current_v1.0.json", "ACCEPTED_SOP"),
        artifact("MINIMAL_HARNESS_SCHEMA", "harness/v7_minimal_phase1/run_control.schema.json", "ACTIVE_HARNESS_SCHEMA"),
        artifact("MINIMAL_HARNESS_VALIDATOR", "harness/v7_minimal_phase1/validate_run_control.py", "ACTIVE_HARNESS_VALIDATOR"),
        artifact("V13_RESEARCH_BASELINE", "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/V13普通中文完整投资产品.html", "FROZEN_BASELINE"),
    ]
    outputs = [
        artifact("PHASE3_TASK_AUTHORITY", "harness/v7_phase3_downstream_decision/phase3_task_authority.json", "", True),
        artifact("PHASE3_SAMPLE_DISPOSITION", "harness/v7_phase3_downstream_decision/unauthorized_sample_disposition.json", "", True),
        artifact("PHASE3_DOWNSTREAM_DECISION", "harness/v7_phase3_downstream_decision/downstream_decision_current.json", "", True),
        artifact("PHASE3_SCHEMA", "harness/v7_phase3_downstream_decision/downstream_decision.schema.json", "", True),
        artifact("PHASE3_VALIDATOR", "harness/v7_phase3_downstream_decision/validate_downstream_decision.py", "", True),
        artifact("PHASE3_FORMAL_TEST_SUITE", "harness/v7_phase3_downstream_decision/tests/test_phase3_formal.py", "", True),
        artifact("PHASE3_FORMAL_TEST_RUNNER", "harness/v7_phase3_downstream_decision/tests/run_formal_tests.py", "", True),
        artifact("PHASE3_FORMAL_TEST_REPORT", "harness/v7_phase3_downstream_decision/phase3_formal_test_report.json", "", True),
        artifact("PHASE3_SAMPLE_COMPATIBILITY_TEST", "harness/v7_phase3_downstream_decision/tests/test_downstream_decision.py", "", True),
        artifact("PHASE3_SAMPLE_COMPATIBILITY_RUNNER", "harness/v7_phase3_downstream_decision/tests/run_tests.py", "", True),
        artifact("PHASE3_SAMPLE_REPORT_SUPERSEDED", "harness/v7_phase3_downstream_decision/phase3_test_report.json", "", True),
        artifact("PHASE3_README", "harness/v7_phase3_downstream_decision/README.html", "", True),
        artifact("PHASE3_CONTROL_BUILDER", "harness/v7_phase3_downstream_decision/build_run_control.py", "", True),
        artifact("PHASE3_ARTIFACT_MANIFEST", "harness/v7_phase3_downstream_decision/phase3_artifact_manifest.json", "", True),
    ]
    by_id = {item["artifact_id"]: item for item in outputs}

    def link(relation_id: str, produced: str, consumer: str) -> dict:
        value = by_id[produced]["sha256"]
        return {
            "relation_id": relation_id, "producer": "CODEX_EXECUTOR",
            "produced_artifact": produced, "produced_artifact_sha256": value,
            "consumer": consumer, "consumed_artifact_sha256": value,
        }

    prior = [item for item in control.get("tasks", []) if item.get("task_id") not in {
        "V7-COMPLETE-PRODUCT-PHASE3-DOWNSTREAM-DECISION", TASK_ID, "V7-PHASE3-WORK-UNAUTHORIZED-SAMPLE"
    }]
    prior.extend([
        {"task_id": "V7-PHASE3-WORK-UNAUTHORIZED-SAMPLE", "task_name": "Work越权Phase 3样件",
         "status": "CANCELLED", "closure_basis": "UNAUTHORIZED_SAMPLE_SUPERSEDED_NOT_RELEASE_BASIS"},
        {"task_id": TASK_ID, "task_name": "V7 Phase 3 下游决策接口正式重做",
         "status": "AWAITING_GPT_ACCEPTANCE", "opened_by_role": "GPT_CONTROL",
         "opened_by_actor": "V7总控--4（Work）"},
    ])
    control.update({
        "run_id": RUN_ID,
        "generated_at_jst": now,
        "control_status": "ACCEPTANCE_PENDING",
        "active_task_id": TASK_ID,
        "tasks": prior,
        "task": {
            "task_id": TASK_ID, "task_name": "V7 Phase 3 下游决策接口正式重做",
            "owner_controller": {"role": "GPT_CONTROL", "actor": "V7总控--4（Work）"},
            "executor": {"role": "CODEX_EXECUTOR", "actor": "Codex–V7"},
            "acceptance_owner": {"role": "GPT_CONTROL", "actor": "V7总控--4（Work）"},
            "phase": "PHASE3_DOWNSTREAM_DECISION_INTERFACES",
            "phase3_status": "TECHNICALLY_VALIDATED_ACCEPTANCE_PENDING", "production_ready": "NO",
            "accepted_phase2_commit": "57e2a0618ad41287e3fdd70a068cebc6b6c6301c",
            "unauthorized_sample_commit": "d137904eca95e99935169ad8a8d2bfdad057c1f5",
            "sample_handling": "REVIEWED_THEN_FULLY_REBUILT_AND_OVERWRITTEN",
        },
        "scope": {
            "allowed": ["CREATE_PHASE3_INTERFACES", "CREATE_PHASE3_SCHEMA", "CREATE_PHASE3_VALIDATOR",
                        "CREATE_PHASE3_TESTS", "UPDATE_THIS_RUN_CONTROL", "RUN_LOCAL_TESTS",
                        "COMMIT_AND_PUSH_SCOPED_FILES"],
            "forbidden": ["MODIFY_V13", "MODIFY_V13_HTML", "MODIFY_V13_PDF", "RESEARCH_SECURITIES",
                          "BUILD_FULL_PRODUCT", "CONNECT_MACRO_PIPELINE", "CONNECT_PDCA_PIPELINE",
                          "REAL_EDINET_FETCH", "REAL_NEWS_SCAN", "REAL_MARKET_DATA_FETCH",
                          "REAL_BROKER_API_CALL", "PRODUCE_DAILY_REPORT", "OVERWRITE_DAILY_REPORT",
                          "RELEASE", "TRADE", "ORDER", "BROKER_ORDER_API", "BUILD_FULL_HARNESS",
                          "AUTO_CONTINUE"],
        },
        "stages": {
            "ordered": ["S0_DEFINED", "S1_INPUT_BOUND", "S2_AUTHORIZED", "S3_EXECUTED",
                        "S4_VALIDATED", "S5_ACCEPTANCE_PENDING", "S5_ACCEPTED"],
            "current": "S5_ACCEPTANCE_PENDING",
            "history": [
                {"stage": "S0_DEFINED", "status": "PASS", "actor_role": "GPT_CONTROL",
                 "actor": "V7总控--4（Work）", "at_jst": "2026-08-30T11:21:47+09:00"},
                {"stage": "S1_INPUT_BOUND", "status": "PASS", "actor_role": "CODEX_EXECUTOR",
                 "actor": "Codex–V7", "at_jst": "2026-08-30T11:21:47+09:00"},
                {"stage": "S2_AUTHORIZED", "status": "PASS", "actor_role": "GPT_CONTROL",
                 "actor": "V7总控--4（Work）", "at_jst": "2026-08-30T11:21:47+09:00"},
                {"stage": "S3_EXECUTED", "status": "PASS", "actor_role": "CODEX_EXECUTOR",
                 "actor": "Codex–V7", "at_jst": now},
                {"stage": "S4_VALIDATED", "status": "PASS", "actor_role": "INDEPENDENT_VALIDATOR",
                 "actor": "Phase3 and Harness read-only validators", "at_jst": now},
                {"stage": "S5_ACCEPTANCE_PENDING", "status": "CURRENT", "actor_role": "GPT_CONTROL",
                 "actor": "V7总控--4（Work）", "at_jst": now},
            ],
        },
        "authorization": {
            "authorized_by_role": "GPT_CONTROL", "authorized_by_actor": "V7总控--4（Work）",
            "authorized_at_jst": "2026-08-30T11:21:47+09:00",
            "authorized_actions": ["CREATE_PHASE3_INTERFACES", "VALIDATE", "TEST", "UPDATE_RUN_CONTROL",
                                   "COMMIT", "PUSH_IF_SAFE"],
            "modify_input_allowed": False, "production_allowed": False, "release_allowed": False,
            "trade_allowed": False, "order_allowed": False,
        },
        "inputs": inputs,
        "outputs": outputs,
        "consumption_chain": [
            link("PHASE3_CURRENT_TO_VALIDATOR", "PHASE3_DOWNSTREAM_DECISION", "PHASE3_VALIDATOR"),
            link("PHASE3_VALIDATOR_TO_TESTS", "PHASE3_VALIDATOR", "PHASE3_FORMAL_TEST_SUITE"),
            link("PHASE3_REPORT_TO_RUN_CONTROL", "PHASE3_FORMAL_TEST_REPORT", "RUN_CONTROL_BINDING"),
            link("PHASE3_SAMPLE_DISPOSITION_TO_CURRENT", "PHASE3_SAMPLE_DISPOSITION", "PHASE3_DOWNSTREAM_DECISION"),
        ],
        "validation": {
            "validator_artifact_id": "MINIMAL_HARNESS_VALIDATOR", "validator_mode": "READ_ONLY",
            "auto_repair": False, "auto_advance": False, "result": "TECHNICAL_CHECK_PASS",
            "phase3_validator_result": "27_OF_27_PASS", "self_test_result": "30_OF_30_PASS",
            "harness_result": "20_OF_20_PASS_CONTROL_VALID",
        },
        "pass_levels": [
            {"level": 1, "name": "TECHNICAL_CHECK_PASS", "status": "PASS",
             "decided_by_role": "INDEPENDENT_VALIDATOR", "basis": "DIRECT_VALIDATION"},
            {"level": 2, "name": "CONTENT_OR_LOCAL_ACCEPTANCE_PASS", "status": "PENDING",
             "decided_by_role": None, "basis": None},
            {"level": 3, "name": "INDEPENDENT_FINAL_ACCEPTANCE_PASS", "status": "PENDING",
             "decided_by_role": None, "basis": None},
            {"level": 4, "name": "GPT_BUSINESS_ACCEPTANCE_PASS", "status": "PENDING",
             "decided_by_role": None, "basis": None},
            {"level": 5, "name": "CHAIRMAN_APPROVED", "status": "PENDING",
             "decided_by_role": None, "basis": None},
        ],
        "release": {"chairman_decision": "PENDING", "decision_by_role": None,
                    "release_authorized": False, "authorized_by_role": None},
        "safety_counters": {
            "v13_modified_count": 0, "release_executed_count": 0, "trade_executed_count": 0,
            "order_executed_count": 0, "daily_report_overwrite_count": 0,
            "daily_report_produced_count": 0, "full_product_build_started_count": 0,
            "scope_deviation_count": 0, "real_edinet_fetch_count": 0,
            "news_scan_executed_count": 0, "real_market_data_fetch_count": 0,
            "real_broker_api_call_count": 0, "phase3_started_count": 1,
            "next_phase_started_count": 0,
        },
        "recovery": {
            "last_valid_stage": "S4_VALIDATED", "last_valid_input": "PHASE2_MACRO_WORLDVIEW",
            "last_valid_output": "PHASE3_FORMAL_TEST_REPORT", "failed_stage": None,
            "blocked_reason": "AWAITING_GPT_CONTROL_PHASE3_ACCEPTANCE", "retry_allowed": True,
            "resume_from": "S5_ACCEPTANCE_PENDING",
        },
        "next_action": {
            "auto_continue": False, "required_role": "GPT_CONTROL",
            "required_actor": "V7总控--4（Work）", "action": "REVIEW_PHASE3_FORMAL_ARTIFACTS_AND_ACCEPT_OR_RETURN",
            "forbidden_until_decision": ["NEXT_PHASE", "REAL_PRODUCTION", "DAILY_REPORT",
                                         "RELEASE", "TRADE", "ORDER"],
        },
    })
    CONTROL.write_text(json.dumps(control, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
