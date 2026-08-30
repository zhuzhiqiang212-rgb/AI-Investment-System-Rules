#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_INPUTS = ["BUSINESS_BLUEPRINT", "PRODUCTION_SOP", "MARKET_DATA", "FRESH_INTEL", "PERSISTENT_KNOWLEDGE", "PDCA_STATE"]
AXES = ["US_MACRO", "JAPAN_MACRO", "CHINA_MACRO", "GLOBAL_LIQUIDITY", "AI_CAPEX_CYCLE", "GEOPOLITICAL_RISK"]
STATES = ["CHANGED", "UNCHANGED", "STRENGTHENED", "WEAKENED", "INVALIDATED"]
JUDGEMENT_FIELDS = ["judgement_id", "axis_id", "state", "plain_language_summary", "facts_checked", "source_ids", "source_tier_summary", "portfolio_relevance", "confidence", "what_would_change_this_view", "handoff_to_strategy"]
FORBIDDEN_TRUE = ["real_news_scan_executed", "real_market_data_fetch_executed", "real_edinet_fetch_executed", "daily_report_produced", "v13_modified", "phase3_started", "release_executed", "trade_executed", "order_executed"]


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
        raise ValueError("Phase 2 root must be an object")
    return value


def validate(data: dict[str, Any], project_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, ok: bool, actual: Any) -> None:
        checks.append({"check_id": check_id, "result": "PASS" if ok else "FAIL", "actual": actual})

    ident = data.get("identity", {})
    check("IDENTITY", ident.get("artifact_id") == "V7_PHASE2_MACRO_WORLDVIEW_CURRENT_v1.0" and ident.get("status") == "CURRENT" and ident.get("contains_real_daily_content") is False and ident.get("production_ready") == "NO", ident)

    bindings = data.get("governance_bindings", {})
    v13_path = project_root / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/V13普通中文完整投资产品.html"
    actual_v13 = sha256_file(v13_path) if v13_path.is_file() else None
    check("GOVERNANCE_BINDINGS", bindings.get("business_blueprint_id") == "V7_COMPLETE_PRODUCT_CURRENT_v2.0" and bindings.get("production_sop_id") == "V7_PRODUCTION_SOP_CURRENT_v1.0" and bindings.get("research_baseline_id") == "V13_RESEARCH_BASELINE", bindings)
    check("V13_NOT_MODIFIED", actual_v13 == bindings.get("research_baseline_sha256"), {"actual": actual_v13, "bound": bindings.get("research_baseline_sha256")})

    scope = data.get("phase2_scope", {})
    forbidden = set(scope.get("forbidden", []))
    check("SCOPE_FORBIDS_PRODUCTION_AND_RELEASE", {"PRODUCE_DAILY_REPORT", "GENERATE_TODAY_ACTION", "START_PHASE3", "RELEASE", "TRADE", "ORDER"}.issubset(forbidden), sorted(forbidden))

    contract = data.get("macro_input_contract", {})
    check("MACRO_INPUT_CONTRACT", contract.get("required_inputs") == REQUIRED_INPUTS and contract.get("stale_core_market_data_result") == "PRODUCTION_BLOCKED", contract)

    axes = data.get("worldview_axes", [])
    axis_ids = [axis.get("axis_id") for axis in axes if isinstance(axis, dict)]
    check("WORLDVIEW_AXES", axis_ids == AXES and all(axis.get("required_topics") for axis in axes), axis_ids)
    check("MACRO_DELTA_STATES", data.get("macro_delta_states") == STATES, data.get("macro_delta_states"))

    judgement = data.get("macro_judgement_contract", {})
    shortcuts = set(judgement.get("forbidden_shortcuts", []))
    check("MACRO_JUDGEMENT_FIELDS", judgement.get("required_fields") == JUDGEMENT_FIELDS, judgement.get("required_fields"))
    check("NO_DIRECT_NEWS_TO_ACTION", "NEWS_DIRECTLY_TO_BUY" in shortcuts and "MISSING_DATA_AS_NO_RISK" in shortcuts, sorted(shortcuts))

    handoff = data.get("handoff_rules", {})
    check("MACRO_TO_STRATEGY_HANDOFF", handoff.get("no_action_generation_in_phase2") is True and handoff.get("phase3_required_for_strategy_flow_sector") is True, handoff)

    section = data.get("product_section_binding", {})
    check("SECTION_2_BOUND", section.get("section_id") == "SECTION_2" and section.get("status") == "INTERFACE_READY_NO_REAL_DATA", section)

    safety = data.get("safety", {})
    check("NO_REAL_PRODUCTION", all(safety.get(name) is False for name in FORBIDDEN_TRUE), safety)

    success = data.get("success_criteria", {})
    check("SUCCESS_CRITERIA", all(value == "PASS" for value in success.values()) and len(success) >= 6, success)

    failures = [item for item in checks if item["result"] == "FAIL"]
    return {"result": "PHASE2_MACRO_WORLDVIEW_VALID" if not failures else "PHASE2_MACRO_WORLDVIEW_INVALID", "check_count": len(checks), "failure_count": len(failures), "failures": failures, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(load(args.input), args.project_root.resolve())
    except Exception as exc:
        result = {"result": "PHASE2_MACRO_WORLDVIEW_INVALID", "error_type": type(exc).__name__, "error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return 0 if result.get("result") == "PHASE2_MACRO_WORLDVIEW_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
