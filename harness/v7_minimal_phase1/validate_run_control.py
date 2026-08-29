#!/usr/bin/env python3
"""Read-only semantic validator for the V7 minimal Harness."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERSION = "V7_MINIMAL_HARNESS_PHASE1_1.0"
HARNESS = "V7_MINIMAL_HARNESS_PHASE1"
STAGES = ["S0_DEFINED", "S1_INPUT_BOUND", "S2_AUTHORIZED", "S3_EXECUTED", "S4_VALIDATED", "S5_ACCEPTANCE_PENDING", "S5_ACCEPTED"]
BASE = {name: min(index, 5) for index, name in enumerate(STAGES)}
ROLES = {"CHAIRMAN", "GPT_CONTROL", "CODEX_EXECUTOR", "INDEPENDENT_VALIDATOR"}
STAGE_ROLES = {
    "S0_DEFINED": {"GPT_CONTROL"}, "S1_INPUT_BOUND": {"CODEX_EXECUTOR", "GPT_CONTROL"},
    "S2_AUTHORIZED": {"GPT_CONTROL"}, "S3_EXECUTED": {"CODEX_EXECUTOR"},
    "S4_VALIDATED": {"INDEPENDENT_VALIDATOR"}, "S5_ACCEPTANCE_PENDING": {"GPT_CONTROL"},
    "S5_ACCEPTED": {"GPT_CONTROL", "CHAIRMAN"},
}
PASS_NAMES = ["TECHNICAL_CHECK_PASS", "CONTENT_OR_LOCAL_ACCEPTANCE_PASS", "INDEPENDENT_FINAL_ACCEPTANCE_PASS", "GPT_BUSINESS_ACCEPTANCE_PASS", "CHAIRMAN_APPROVED"]
PASS_ROLES = {1: {"CODEX_EXECUTOR", "INDEPENDENT_VALIDATOR"}, 2: {"CODEX_EXECUTOR", "GPT_CONTROL"}, 3: {"INDEPENDENT_VALIDATOR"}, 4: {"GPT_CONTROL"}, 5: {"CHAIRMAN"}}
FORBIDDEN = {"MODIFY_V13_HTML", "MODIFY_V13_PDF", "RESEARCH_SECURITIES", "BUILD_FULL_PRODUCT", "CONNECT_MACRO_PIPELINE", "CONNECT_PDCA_PIPELINE", "PRODUCE_DAILY_REPORT", "OVERWRITE_DAILY_REPORT", "RELEASE", "TRADE", "ORDER", "BROKER_ORDER_API", "BUILD_FULL_HARNESS"}
COUNTERS = {"v13_modified_count", "release_executed_count", "trade_executed_count", "order_executed_count", "daily_report_overwrite_count", "full_product_build_started_count", "scope_deviation_count"}
TOP = {"schema_version", "harness_id", "run_id", "generated_at_jst", "control_status", "active_task_id", "tasks", "roles", "task", "scope", "stages", "authorization", "inputs", "outputs", "consumption_chain", "validation", "pass_levels", "release", "safety_counters", "recovery", "next_action"}
CLOSED = {"COMPLETED", "FAILED_CLOSED", "CANCELLED"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("RUN_CONTROL root must be an object")
    return value


def resolved(raw: str, root: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def validate_control(control: dict[str, Any], root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, ok: bool, actual: Any) -> None:
        checks.append({"check_id": check_id, "result": "PASS" if ok else "FAIL", "actual": actual})

    check("TOP_LEVEL_FIELDS", TOP.issubset(control), sorted(control))
    check("IDENTITY", control.get("schema_version") == VERSION and control.get("harness_id") == HARNESS, [control.get("schema_version"), control.get("harness_id")])
    roles = control.get("roles", {})
    check("REQUIRED_ROLES", isinstance(roles, dict) and ROLES.issubset(roles) and all(roles.get(role, {}).get("permissions") for role in ROLES), sorted(roles) if isinstance(roles, dict) else roles)
    task = control.get("task", {})
    bindings = {task.get(key, {}).get("role") for key in ("owner_controller", "executor", "acceptance_owner")}
    check("TASK_ROLE_BINDINGS", {"GPT_CONTROL", "CODEX_EXECUTOR"}.issubset(bindings), sorted(x for x in bindings if x))

    scope = control.get("scope", {})
    allowed, forbidden = set(scope.get("allowed", [])), set(scope.get("forbidden", []))
    check("SCOPE_LOCK", bool(allowed) and FORBIDDEN.issubset(forbidden) and not allowed & forbidden, {"missing": sorted(FORBIDDEN - forbidden), "conflicts": sorted(allowed & forbidden)})

    stages = control.get("stages", {})
    history = stages.get("history", [])
    names = [item.get("stage") for item in history if isinstance(item, dict)]
    check("STAGE_MODEL", stages.get("ordered") == STAGES and bool(names) and stages.get("current") == names[-1], {"ordered": stages.get("ordered"), "current": stages.get("current"), "history": names})
    values = [BASE.get(name, -99) for name in names]
    no_skip = all(right - left == 1 for left, right in zip(values, values[1:])) and len(values) == len(set(values)) and all(value >= 0 for value in values)
    check("NO_STAGE_SKIP", no_skip, names)
    bad_stage_roles = [{"stage": item.get("stage"), "actor_role": item.get("actor_role")} for item in history if isinstance(item, dict) and item.get("actor_role") not in STAGE_ROLES.get(item.get("stage"), set())]
    check("STAGE_ROLE_PERMISSION", not bad_stage_roles, bad_stage_roles)
    s2 = names.index("S2_AUTHORIZED") if "S2_AUTHORIZED" in names else None
    s3 = names.index("S3_EXECUTED") if "S3_EXECUTED" in names else None
    check("AUTHORIZATION_BEFORE_EXECUTION", s3 is None or (s2 is not None and s2 < s3), {"S2": s2, "S3": s3})

    auth = control.get("authorization", {})
    denied = all(auth.get(key) is False for key in ("modify_input_allowed", "production_allowed", "release_allowed", "trade_allowed", "order_allowed"))
    check("AUTHORIZATION_BOUNDARY", auth.get("authorized_by_role") == "GPT_CONTROL" and denied, auth)

    tasks = control.get("tasks", [])
    open_tasks = [item for item in tasks if isinstance(item, dict) and item.get("status") not in CLOSED]
    active_id = control.get("active_task_id")
    single = (len(open_tasks) == 1 and open_tasks[0].get("task_id") == active_id) or (not open_tasks and active_id is None)
    check("SINGLE_ACTIVE_TASK", single, {"active_task_id": active_id, "open": [item.get("task_id") for item in open_tasks]})

    input_errors = []
    seen = set()
    for item in control.get("inputs", []):
        artifact_id = item.get("artifact_id") if isinstance(item, dict) else None
        path = resolved(item.get("path", ""), root) if isinstance(item, dict) else Path()
        actual_sha = sha256_file(path) if path.is_file() else None
        actual_size = path.stat().st_size if path.is_file() else None
        good = artifact_id not in seen and path.is_file() and item.get("sha256") == actual_sha and item.get("size_bytes") == actual_size and item.get("binding_status") == "BOUND"
        if not good:
            input_errors.append({"artifact_id": artifact_id, "actual_sha256": actual_sha, "actual_size_bytes": actual_size})
        seen.add(artifact_id)
    check("INPUT_BINDINGS", bool(control.get("inputs")) and not input_errors, input_errors)

    output_errors, outputs = [], {}
    for item in control.get("outputs", []):
        artifact_id = item.get("artifact_id") if isinstance(item, dict) else None
        path = resolved(item.get("path", ""), root) if isinstance(item, dict) else Path()
        actual_sha = sha256_file(path) if path.is_file() else None
        actual_size = path.stat().st_size if path.is_file() else None
        good = artifact_id not in outputs and path.is_file() and item.get("sha256") == actual_sha and item.get("size_bytes") == actual_size and item.get("producer_role") == "CODEX_EXECUTOR"
        if not good:
            output_errors.append({"artifact_id": artifact_id, "actual_sha256": actual_sha, "actual_size_bytes": actual_size})
        if artifact_id:
            outputs[artifact_id] = item
    check("OUTPUT_IDENTITIES", bool(control.get("outputs")) and not output_errors, output_errors)

    chain_errors = []
    for link in control.get("consumption_chain", []):
        artifact = outputs.get(link.get("produced_artifact")) if isinstance(link, dict) else None
        expected = artifact.get("sha256") if artifact else None
        good = bool(artifact and link.get("producer") and link.get("consumer") and link.get("produced_artifact_sha256") == expected and link.get("consumed_artifact_sha256") == expected)
        if not good:
            chain_errors.append({"relation_id": link.get("relation_id") if isinstance(link, dict) else None, "expected": expected, "produced": link.get("produced_artifact_sha256") if isinstance(link, dict) else None, "consumed": link.get("consumed_artifact_sha256") if isinstance(link, dict) else None})
    check("CONSUMPTION_SHA_BINDING", bool(control.get("consumption_chain")) and not chain_errors, chain_errors)

    validation = control.get("validation", {})
    check("VALIDATOR_READ_ONLY", validation.get("validator_mode") == "READ_ONLY" and validation.get("auto_repair") is False and validation.get("auto_advance") is False, validation)
    levels, level_errors = control.get("pass_levels", []), []
    for index, level in enumerate(levels, 1):
        if not isinstance(level, dict) or index > 5 or level.get("level") != index or level.get("name") != PASS_NAMES[index - 1]:
            level_errors.append({"level": index, "error": "IDENTITY"})
        elif level.get("status") == "PASS" and (level.get("decided_by_role") not in PASS_ROLES[index] or level.get("basis") not in {"DIRECT_VALIDATION", "EXPLICIT_REVIEW", "EXPLICIT_DECISION"}):
            level_errors.append({"level": index, "role": level.get("decided_by_role"), "basis": level.get("basis")})
    check("PASS_LEVEL_SEPARATION", len(levels) == 5 and not level_errors, level_errors)

    release = control.get("release", {})
    decision, authorized, role = release.get("chairman_decision"), release.get("release_authorized"), release.get("authorized_by_role")
    release_ok = (decision != "APPROVED" and authorized is False and role is None) or (decision == "APPROVED" and authorized is True and role == "CHAIRMAN" and release.get("decision_by_role") == "CHAIRMAN")
    check("RELEASE_AUTHORIZATION", release_ok, release)
    counters = control.get("safety_counters", {})
    check("FORBIDDEN_ACTION_COUNTERS", COUNTERS.issubset(counters) and all(counters.get(name) == 0 for name in COUNTERS), counters)
    recovery = control.get("recovery", {})
    recovery_fields = {"last_valid_stage", "last_valid_input", "last_valid_output", "failed_stage", "blocked_reason", "retry_allowed", "resume_from"}
    check("RECOVERY_STATE", recovery_fields.issubset(recovery) and bool(recovery.get("last_valid_stage")) and bool(recovery.get("resume_from")), recovery)
    next_action = control.get("next_action", {})
    check("NO_AUTOMATIC_ADVANCE", next_action.get("auto_continue") is False and next_action.get("required_role") == "GPT_CONTROL", next_action)

    failures = [item for item in checks if item["result"] == "FAIL"]
    return {"control_result": "CONTROL_VALID" if not failures else "CONTROL_INVALID", "technical_result": "TECHNICAL_CHECK_PASS" if not failures else "TECHNICAL_CHECK_FAIL", "check_count": len(checks), "failure_count": len(failures), "failures": failures, "checks": checks, "recovery": {key: recovery.get(key) for key in ("last_valid_stage", "blocked_reason", "resume_from")}}


def validate_path(control_path: Path, project_root: Path | None = None) -> dict[str, Any]:
    path = control_path.resolve()
    root = project_root.resolve() if project_root else path.parents[2]
    return validate_control(load_json(path), root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only V7 minimal Harness validator")
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_path(args.control, args.project_root)
    except Exception as exc:
        result = {"control_result": "CONTROL_INVALID", "technical_result": "TECHNICAL_CHECK_FAIL", "error_type": type(exc).__name__, "error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return 0 if result.get("control_result") == "CONTROL_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
