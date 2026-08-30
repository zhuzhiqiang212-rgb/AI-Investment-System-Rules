#!/usr/bin/env python3
"""Read-only validator for V7 complete-product Phase 1 interfaces."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CORE = ["BUSINESS_BLUEPRINT", "PRODUCTION_SOP", "RESEARCH_BASELINE", "FRESH_INTEL", "MARKET_DATA", "PORTFOLIO_STATE", "PDCA_STATE"]
ALL_INTERFACES = CORE + ["PERSISTENT_KNOWLEDGE"]
SECTIONS = [f"SECTION_{i}" for i in range(10)]
LAYER_CHAIN = ["MACRO", "STRATEGY", "FLOW", "SECTOR", "COMPANY", "PORTFOLIO", "ACTION", "PDCA"]
READING_ORDER = ["SECTION_0", "SECTION_1", "SECTION_7", "SECTION_6", "SECTION_2", "SECTION_3", "SECTION_4", "SECTION_5", "SECTION_8", "SECTION_9"]
IDENTITY_FIELDS = ["name", "type", "version", "lifecycle_status", "file_name", "file_path", "sha256", "effective_at", "updated_at"]
TRACE_FIELDS = ["action_id", "portfolio_judgement_id", "company_judgement_id", "sector_judgement_id", "strategy_judgement_id", "macro_judgement_id", "source_ids"]
CONTRIBUTION_FIELDS = ["portfolio_weight", "expected_return", "expected_contribution", "bull_case_contribution", "bear_case_contribution", "confidence", "time_horizon"]
FRESHNESS = ["HOT", "CURRENT", "STALE", "ARCHIVE"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("Phase 1 root must be an object")
    return value


def resolve(raw: str, root: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def identity_valid(record: dict[str, Any], root: Path, allow_not_built: bool = False) -> tuple[bool, dict[str, Any]]:
    missing = [field for field in IDENTITY_FIELDS if field not in record]
    if missing:
        return False, {"missing_fields": missing}
    if allow_not_built and record.get("lifecycle_status") == "NOT_BUILT":
        null_ok = all(record.get(field) is None for field in ("version", "file_name", "file_path", "sha256", "effective_at", "updated_at"))
        return null_ok, {"not_built_null_contract": null_ok}
    path = resolve(record.get("file_path", ""), root)
    actual = sha256_file(path) if path.is_file() else None
    ok = all(record.get(field) not in (None, "") for field in IDENTITY_FIELDS) and actual == record.get("sha256")
    return ok, {"path_exists": path.is_file(), "actual_sha256": actual}


def validate_phase1(data: dict[str, Any], root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def check(check_id: str, ok: bool, actual: Any) -> None:
        checks.append({"check_id": check_id, "result": "PASS" if ok else "FAIL", "actual": actual})

    interfaces = data.get("interfaces", {})
    check("CORE_INPUT_INTERFACES", all(name in interfaces for name in ALL_INTERFACES), sorted(interfaces))
    blueprint = interfaces.get("BUSINESS_BLUEPRINT", {})
    records = blueprint.get("records", [])
    current = [item for item in records if isinstance(item, dict) and item.get("status") == "CURRENT"]
    blueprint_id_ok = len(current) == 1 and blueprint.get("current_blueprint_id") == "V7_COMPLETE_PRODUCT_CURRENT_v2.0" and current[0].get("blueprint_id") == "V7_COMPLETE_PRODUCT_CURRENT_v2.0"
    blueprint_file_ok, blueprint_detail = identity_valid(current[0], root) if len(current) == 1 else (False, {"current_count": len(current)})
    check("SINGLE_CURRENT_BLUEPRINT", blueprint_id_ok and blueprint_file_ok, {"current_count": len(current), "identity": blueprint_detail})

    sop = interfaces.get("PRODUCTION_SOP", {})
    sop_ok, sop_detail = identity_valid(sop, root, allow_not_built=True)
    check("PRODUCTION_SOP_INTERFACE", sop_ok and sop.get("status") == "NOT_BUILT", sop_detail)
    baseline = interfaces.get("RESEARCH_BASELINE", {})
    baseline_ok, baseline_detail = identity_valid(baseline, root)
    check("V13_RESEARCH_BASELINE", baseline_ok and baseline.get("baseline_id") == "V13_RESEARCH_BASELINE", baseline_detail)

    fresh = interfaces.get("FRESH_INTEL", {})
    check("FRESH_INTEL_CLASSES", fresh.get("freshness_classes") == FRESHNESS and fresh.get("status") == "INTERFACE_ONLY", fresh)
    empty_interfaces_ok = all(interfaces.get(name, {}).get("status") == "INTERFACE_ONLY" and interfaces.get(name, {}).get("records") == [] for name in ("PERSISTENT_KNOWLEDGE", "MARKET_DATA", "PORTFOLIO_STATE", "PDCA_STATE"))
    check("INTERFACE_ONLY_NO_PRODUCTION", empty_interfaces_ok, {name: interfaces.get(name, {}).get("status") for name in ("PERSISTENT_KNOWLEDGE", "MARKET_DATA", "PORTFOLIO_STATE", "PDCA_STATE")})

    separation = data.get("baseline_dynamic_model", {})
    base_model, overlay = separation.get("research_baseline", {}), separation.get("dynamic_overlay", {})
    forbidden_overlay_keys = set(overlay).intersection({"baseline_id", "baseline_version", "baseline_file_path", "baseline_sha256"})
    separation_ok = base_model.get("baseline_id") == "V13_RESEARCH_BASELINE" and base_model.get("identity_immutable") is True and overlay.get("baseline_reference_id") == "V13_RESEARCH_BASELINE" and not forbidden_overlay_keys
    check("BASELINE_DYNAMIC_SEPARATION", separation_ok, {"forbidden_overlay_keys": sorted(forbidden_overlay_keys)})

    skeleton = data.get("product_skeleton", {})
    section_ids = [item.get("section_id") for item in skeleton.get("sections", []) if isinstance(item, dict)]
    check("PRODUCT_SECTIONS_0_TO_9", section_ids == SECTIONS and all(item.get("status") == "INTERFACE_ONLY_NO_DATA" for item in skeleton.get("sections", [])), section_ids)
    check("DECISION_FIRST_READING_ORDER", skeleton.get("chairman_reading_order") == READING_ORDER, skeleton.get("chairman_reading_order"))
    check("LAYER_CHAIN", skeleton.get("layer_chain") == LAYER_CHAIN, skeleton.get("layer_chain"))

    trace = skeleton.get("conclusion_trace", {})
    trace_fields = all(field in trace for field in TRACE_FIELDS)
    if skeleton.get("action_interface", {}).get("real_action_present"):
        trace_fields = trace_fields and all(trace.get(field) not in (None, [], "") for field in TRACE_FIELDS)
    check("DECISION_TRACEABILITY", trace_fields, trace)
    split = skeleton.get("prediction_action_separation", {})
    split_ok = split.get("prediction", {}).get("direction") == "BULLISH" and split.get("action", {}).get("action") == "WAIT" and split.get("bullish_requires_buy") is False
    check("PREDICTION_ACTION_SEPARATION", split_ok, split)

    target40 = skeleton.get("target_40_interface", {})
    no_fake = target40.get("records") == [] and target40.get("expected_portfolio_return") is None and target40.get("gap_to_40") is None and target40.get("calculation_status") == "NOT_CALCULATED_NO_REAL_DATA"
    check("TARGET_40_CONTRIBUTION_INTERFACE", target40.get("asset_contribution_fields") == CONTRIBUTION_FIELDS and no_fake, target40)
    target100 = skeleton.get("target_100_interface", {})
    check("TARGET_100_DEFAULT_INACTIVE", target100.get("100_TARGET_MODE") == "INACTIVE", target100.get("100_TARGET_MODE"))
    action = skeleton.get("action_interface", {})
    action_ok = action.get("levels") == ["A_EXECUTE", "B_WAIT_TRIGGER", "C_WATCH", "D_EXCLUDE"] and set(action.get("fields", [])) == {"action", "target_position", "amount", "trigger", "invalid_condition", "reason", "source_of_funds"} and action.get("real_action_present") is False
    check("ACTION_INTERFACE", action_ok, action)

    governance = data.get("version_governance", {})
    governance_ok = governance.get("required_identity_fields") == IDENTITY_FIELDS and governance.get("single_current_per_type") is True and governance.get("missing_version_or_sha_blocks_production_ready") is True and governance.get("ambiguous_latest_file_reference_allowed") is False
    check("VERSION_IDENTITY_MODEL", governance_ok, governance)
    phase = data.get("phase_status", {})
    readiness_ok = skeleton.get("production_readiness") == "NO" and skeleton.get("production_readiness_reason") == "PRODUCTION_SOP_NOT_BUILT" and phase.get("PHASE1_COMPLETE") == "YES" and phase.get("PRODUCT_PRODUCTION_STARTED") == "NO" and phase.get("PRODUCTION_SOP_BUILT") == "NO" and phase.get("PHASE2_STARTED") == "NO"
    check("PRODUCTION_NOT_READY", readiness_ok, {"production_readiness": skeleton.get("production_readiness"), **phase})

    failures = [item for item in checks if item["result"] == "FAIL"]
    return {"result": "PHASE1_STRUCTURE_VALID" if not failures else "PHASE1_STRUCTURE_INVALID", "check_count": len(checks), "failure_count": len(failures), "failures": failures, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--input", type=Path, required=True); parser.add_argument("--project-root", type=Path, required=True); parser.add_argument("--compact", action="store_true"); args = parser.parse_args()
    try: result = validate_phase1(load(args.input), args.project_root.resolve())
    except Exception as exc: result = {"result": "PHASE1_STRUCTURE_INVALID", "error_type": type(exc).__name__, "error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2); sys.stdout.write("\n")
    return 0 if result.get("result") == "PHASE1_STRUCTURE_VALID" else 1

if __name__ == "__main__": raise SystemExit(main())
