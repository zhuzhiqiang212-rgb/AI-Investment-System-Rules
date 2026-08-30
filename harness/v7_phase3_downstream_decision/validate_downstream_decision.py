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

LAYERS = ["STRATEGY", "FLOW", "SECTOR", "COMPANY", "PORTFOLIO", "ACTION", "PDCA"]
ORDERED = ["MACRO", "STRATEGY", "FLOW", "SECTOR", "COMPANY", "PORTFOLIO", "ACTION", "PDCA"]
V13_SHA = "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4"
PHASE2_SHA = "718A2E8824985A40D3F83C2DB72A218D88135C7A641D8346D55CE046883B75B6"


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
        raise ValueError("Phase 3 root must be an object")
    return value


def validate(data: dict[str, Any], project_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, ok: bool, actual: Any) -> None:
        checks.append({"check_id": check_id, "result": "PASS" if ok else "FAIL", "actual": actual})

    identity = data.get("identity", {})
    check("IDENTITY", identity.get("artifact_id") == "V7_PHASE3_DOWNSTREAM_DECISION_CURRENT_v1.0" and identity.get("status") == "CURRENT" and identity.get("production_ready") == "NO" and identity.get("contains_real_daily_content") is False, identity)

    bindings = data.get("governance_bindings", {})
    v13 = project_root / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/V13普通中文完整投资产品.html"
    phase2 = project_root / "harness/v7_phase2_macro_worldview/macro_worldview_current.json"
    check("GOVERNANCE_BINDINGS", bindings.get("phase2_macro_worldview_sha256") == PHASE2_SHA and bindings.get("research_baseline_sha256") == V13_SHA, bindings)
    check("V13_AND_PHASE2_NOT_MODIFIED", v13.is_file() and phase2.is_file() and sha256_file(v13) == V13_SHA and sha256_file(phase2) == PHASE2_SHA, {"v13": sha256_file(v13) if v13.is_file() else None, "phase2": sha256_file(phase2) if phase2.is_file() else None})

    forbidden = set(data.get("phase3_scope", {}).get("forbidden", []))
    check("SCOPE_FORBIDS_PRODUCTION_RELEASE_TRADE", {"REAL_NEWS_SCAN", "REAL_MARKET_DATA_FETCH", "PRODUCE_DAILY_REPORT", "GENERATE_TODAY_ACTION", "RELEASE", "TRADE", "ORDER", "BROKER_ORDER_API"}.issubset(forbidden), sorted(forbidden))

    interfaces = data.get("layer_interfaces", [])
    layer_map = {item.get("layer"): item for item in interfaces if isinstance(item, dict)}
    check("ALL_DOWNSTREAM_LAYERS_BOUND", list(layer_map) == LAYERS, list(layer_map))
    check("EACH_LAYER_HAS_INPUT_FIELDS_OUTPUT", all(layer_map.get(layer, {}).get("required_inputs") and layer_map.get(layer, {}).get("required_fields") and layer_map.get(layer, {}).get("output") for layer in LAYERS), layer_map)

    strategy = layer_map.get("STRATEGY", {})
    check("STRATEGY_DEPENDS_ON_MACRO", "MACRO_JUDGEMENT_IDS" in strategy.get("required_inputs", []) and "why_a_not_b" in strategy.get("required_fields", []), strategy)
    flow = layer_map.get("FLOW", {})
    check("FLOW_REQUIRES_FRESHNESS_AND_SOURCES", "freshness_class" in flow.get("required_fields", []) and "source_ids" in flow.get("required_fields", []), flow)
    company = layer_map.get("COMPANY", {})
    check("COMPANY_PRESERVES_V13_BASELINE", "V13_RESEARCH_BASELINE" in company.get("required_inputs", []) and "baseline_reference" in company.get("required_fields", []), company)
    action = layer_map.get("ACTION", {})
    check("ACTION_REQUIRES_CONFIRMATION", "chairman_confirmation_required" in action.get("required_fields", []) and "BROKER_REALITY_CHECK" in action.get("required_inputs", []), action)

    chain = data.get("causal_chain", {})
    check("CAUSAL_CHAIN_ORDER", chain.get("ordered_layers") == ORDERED and chain.get("no_layer_may_skip_source_trace") is True, chain)
    trace = chain.get("required_trace_fields", [])
    check("TRACE_FIELDS_COMPLETE", all(name in trace for name in ["macro_judgement_id", "strategy_judgement_id", "company_judgement_id", "portfolio_judgement_id", "action_id", "source_ids"]), trace)

    safety = data.get("action_safety", {})
    check("ACTION_SAFETY_LOCKED", safety.get("real_action_present") is False and safety.get("broker_order_api_allowed") is False and safety.get("trade_execution_allowed") is False and safety.get("phase3_may_generate_today_action") is False, safety)
    section = data.get("product_section_binding", {})
    check("PRODUCT_SECTIONS_BOUND", set(section.get("sections_bound", [])) == {"SECTION_0", "SECTION_3", "SECTION_4", "SECTION_5", "SECTION_6", "SECTION_7", "SECTION_8"} and section.get("section_9_evidence_required") is True, section)
    no_real = data.get("safety", {})
    check("NO_REAL_PRODUCTION", all(value is False for value in no_real.values()), no_real)
    success = data.get("success_criteria", {})
    check("SUCCESS_CRITERIA", len(success) >= 9 and all(value == "PASS" for value in success.values()), success)

    failures = [item for item in checks if item["result"] == "FAIL"]
    return {"result": "PHASE3_DOWNSTREAM_DECISION_VALID" if not failures else "PHASE3_DOWNSTREAM_DECISION_INVALID", "check_count": len(checks), "failure_count": len(failures), "failures": failures, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(load(args.input), args.project_root.resolve())
    except Exception as exc:
        result = {"result": "PHASE3_DOWNSTREAM_DECISION_INVALID", "error_type": type(exc).__name__, "error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return 0 if result.get("result") == "PHASE3_DOWNSTREAM_DECISION_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
