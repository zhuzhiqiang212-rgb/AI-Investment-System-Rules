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

INTERFACES = [
    "STRATEGY",
    "FLOW",
    "SECTOR_ROTATION",
    "COMPANY_SECURITY",
    "PORTFOLIO_POSITION",
    "TODAY_ACTION",
    "PDCA",
    "EVIDENCE_TRACE",
]
CHAIN = ["MACRO", "STRATEGY", "FLOW", "SECTOR", "COMPANY", "PORTFOLIO", "ACTION", "PDCA"]
TRACE_FIELDS = [
    "macro_judgement_id",
    "strategy_judgement_id",
    "flow_judgement_id",
    "sector_judgement_id",
    "company_judgement_id",
    "portfolio_judgement_id",
    "action_id",
    "source_ids",
    "evidence_ids",
]
V13_SHA = "C726C9BA04A51E107162F6ECA5AD396294B58F132F361A7257755A2E8E8C90A4"
PHASE2_SHA = "718A2E8824985A40D3F83C2DB72A218D88135C7A641D8346D55CE046883B75B6"
SOP_SHA = "DA8B76F6638857F97187BB03E28D03399FD8A8E36683284E26B436F24205B227"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Phase 3 root must be an object")
    return value


def interface_set_valid(data: dict[str, Any]) -> bool:
    return list(data.get("interfaces", {})) == INTERFACES


def trace_complete(trace: dict[str, Any]) -> bool:
    return all(field in trace and trace[field] not in (None, "", []) for field in TRACE_FIELDS)


def company_overlay_allowed(changed_fields: set[str]) -> bool:
    forbidden = {"BASELINE_ID", "BASELINE_FILE", "BASELINE_SHA256"}
    return not bool(changed_fields & forbidden)


def action_eligible(
    level: str,
    portfolio_state: str,
    trigger: bool,
    invalid_condition: bool,
    source_of_funds: bool,
) -> bool:
    if level != "A_EXECUTE":
        return True
    return (
        portfolio_state == "CURRENT"
        and trigger
        and invalid_condition
        and source_of_funds
    )


def target_calculation_status(has_real_portfolio: bool, has_real_forecast: bool) -> str:
    return "CALCULABLE" if has_real_portfolio and has_real_forecast else "TARGET_CALCULATION_UNAVAILABLE"


def source_fact_winner(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return min(candidates, key=lambda item: int(item["tier"]))


def evidence_resolves(evidence_records: list[dict[str, Any]], conclusion_id: str) -> bool:
    for record in evidence_records:
        required = {
            "evidence_id",
            "source_id",
            "source_class",
            "artifact_id",
            "sha256_or_version",
            "supports_conclusion_ids",
        }
        if required.issubset(record) and conclusion_id in record["supports_conclusion_ids"]:
            return True
    return False


def apply_pdca_feedback(state: dict[str, Any], feedback: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "signal_weight",
        "confidence",
        "required_confirmation",
        "timing_rule",
        "source_weight",
        "model_notes",
    }
    output = dict(state)
    output.update({key: value for key, value in feedback.items() if key in allowed})
    return output


def validate(data: dict[str, Any], project_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(check_id: str, ok: bool, actual: Any) -> None:
        checks.append({"check_id": check_id, "result": "PASS" if ok else "FAIL", "actual": actual})

    identity = data.get("identity", {})
    check(
        "IDENTITY",
        identity.get("artifact_id") == "V7_PHASE3_DOWNSTREAM_DECISION_CURRENT_v1.0"
        and identity.get("status") == "CURRENT"
        and identity.get("production_ready") == "NO"
        and identity.get("contains_real_daily_content") is False,
        identity,
    )

    bindings = data.get("governance_bindings", {})
    phase2_path = project_root / "harness/v7_phase2_macro_worldview/macro_worldview_current.json"
    sop_path = project_root / "harness/v7_production_sop_v1/V7正式生产SOP_Current_v1.0.json"
    v13_path = project_root / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/V13普通中文完整投资产品.html"
    check(
        "ACCEPTED_INPUT_BINDINGS",
        bindings.get("phase2_acceptance_commit") == "57e2a0618ad41287e3fdd70a068cebc6b6c6301c"
        and bindings.get("phase2_macro_worldview_sha256") == PHASE2_SHA
        and bindings.get("production_sop_sha256") == SOP_SHA
        and bindings.get("research_baseline_sha256") == V13_SHA,
        bindings,
    )
    check(
        "ACCEPTED_INPUT_ARTIFACTS_UNCHANGED",
        phase2_path.is_file()
        and sop_path.is_file()
        and v13_path.is_file()
        and sha256_file(phase2_path) == PHASE2_SHA
        and sha256_file(sop_path) == SOP_SHA
        and sha256_file(v13_path) == V13_SHA,
        {
            "phase2": sha256_file(phase2_path) if phase2_path.is_file() else None,
            "sop": sha256_file(sop_path) if sop_path.is_file() else None,
            "v13": sha256_file(v13_path) if v13_path.is_file() else None,
        },
    )

    disposition = data.get("sample_disposition", {})
    check(
        "UNAUTHORIZED_SAMPLE_NOT_PROMOTED",
        disposition.get("sample_commit", "").startswith("d137904")
        and disposition.get("formal_status") == "UNAUTHORIZED_SAMPLE_SUPERSEDED"
        and disposition.get("handling") == "REVIEWED_THEN_FULLY_REBUILT_AND_OVERWRITTEN"
        and disposition.get("automatic_promotion") is False
        and disposition.get("release_basis") is False,
        disposition,
    )

    forbidden = set(data.get("phase3_scope", {}).get("forbidden", []))
    check(
        "SCOPE_LOCK",
        {
            "REAL_NEWS_SCAN",
            "REAL_MARKET_DATA_FETCH",
            "REAL_EDINET_FETCH",
            "REAL_BROKER_API_CALL",
            "PRODUCE_OR_OVERWRITE_DAILY_REPORT",
            "MODIFY_V13_HTML",
            "MODIFY_V13_PDF",
            "RELEASE",
            "TRADE",
            "ORDER",
            "AUTO_START_NEXT_PHASE",
        }.issubset(forbidden),
        sorted(forbidden),
    )

    interfaces = data.get("interfaces", {})
    check("EIGHT_INTERFACES_EXACT", interface_set_valid(data), list(interfaces))
    check(
        "INTERFACE_IDENTITY_COMPLETE",
        all(
            interfaces[name].get("interface_id")
            and interfaces[name].get("section_id")
            and interfaces[name].get("required_inputs")
            and interfaces[name].get("required_fields")
            and interfaces[name].get("output")
            for name in INTERFACES
        ),
        list(interfaces),
    )
    check(
        "NO_REAL_INTERFACE_RECORDS",
        all(interfaces[name].get("real_records") == [] for name in INTERFACES),
        {name: len(interfaces[name].get("real_records", [])) for name in INTERFACES},
    )

    strategy = interfaces.get("STRATEGY", {})
    check(
        "STRATEGY_MACRO_DEPENDENCY",
        "MACRO_JUDGEMENT_IDS" in strategy.get("required_inputs", [])
        and {"why_a_not_b", "macro_dependency_ids", "counterevidence", "invalid_conditions"}.issubset(strategy.get("required_fields", [])),
        strategy,
    )
    flow = interfaces.get("FLOW", {})
    check(
        "FLOW_FRESHNESS_AND_CONTRADICTION",
        {"freshness_class", "strategy_support_state", "counterevidence", "source_ids", "evidence_ids"}.issubset(flow.get("required_fields", []))
        and "CONTRADICTS" in flow.get("states", []),
        flow,
    )
    sector = interfaces.get("SECTOR_ROTATION", {})
    check(
        "SECTOR_STRATEGY_FLOW_TRACE",
        {"STRATEGY_JUDGEMENT_IDS", "FLOW_JUDGEMENT_IDS"}.issubset(sector.get("required_inputs", []))
        and {"strategy_judgement_ids", "flow_judgement_ids"}.issubset(sector.get("required_fields", [])),
        sector,
    )
    company = interfaces.get("COMPANY_SECURITY", {})
    check(
        "COMPANY_BASELINE_DYNAMIC_SEPARATION",
        company.get("baseline_identity_immutable") is True
        and "V13_RESEARCH_BASELINE_ID" in company.get("required_inputs", [])
        and {"BASELINE_ID", "BASELINE_FILE", "BASELINE_SHA256"}.issubset(company.get("dynamic_overlay_may_not_update", [])),
        company,
    )
    portfolio = interfaces.get("PORTFOLIO_POSITION", {})
    check(
        "PORTFOLIO_ACCOUNT_AND_CONTRIBUTION",
        {"PORTFOLIO_SNAPSHOT_ID", "ACCOUNT_SCOPE", "RISK_BUDGET_ID"}.issubset(portfolio.get("required_inputs", []))
        and {"expected_contribution", "bull_contribution", "bear_contribution", "source_of_funds_boundary"}.issubset(portfolio.get("required_fields", []))
        and portfolio.get("fabricated_contribution_allowed") is False,
        portfolio,
    )
    check(
        "PORTFOLIO_FRESHNESS_BOUNDARY",
        portfolio.get("portfolio_states") == ["CURRENT", "STALE", "UNVERIFIED"]
        and portfolio.get("unverified_blocks_precise_amount_action") is True,
        portfolio,
    )
    action = interfaces.get("TODAY_ACTION", {})
    check(
        "ACTION_PREDICTION_SEPARATION",
        action.get("prediction_action_independent") is True
        and action.get("bullish_wait_legal") is True
        and action.get("no_trade_legal") is True,
        action,
    )
    check(
        "ACTION_AUTHORITY_AND_ORDER_LOCK",
        action.get("phase3_real_action_allowed") is False
        and action.get("broker_order_api_allowed") is False
        and {"authorization_state", "order_state"}.issubset(action.get("required_fields", [])),
        action,
    )
    pdca = interfaces.get("PDCA", {})
    check(
        "PDCA_FEEDBACK",
        pdca.get("new_prediction_status") == "PENDING_NOT_DUE"
        and pdca.get("same_day_correctness_verdict_allowed") is False
        and {"signal_weight", "confidence", "required_confirmation", "timing_rule", "source_weight", "model_notes"}.issubset(pdca.get("feedback_fields", [])),
        pdca,
    )
    evidence = interfaces.get("EVIDENCE_TRACE", {})
    check(
        "EVIDENCE_INTERFACE_STANDALONE",
        evidence.get("section_id") == "SECTION_9"
        and evidence.get("orphan_material_conclusion_allowed") is False
        and evidence.get("opinion_may_override_primary_fact") is False,
        evidence,
    )
    check(
        "EVIDENCE_IDENTITY_FIELDS",
        {"evidence_id", "source_id", "source_class", "source_tier", "artifact_id", "file_or_url", "sha256_or_version", "published_at", "as_of", "supports_conclusion_ids", "conflict_state"}.issubset(evidence.get("required_fields", [])),
        evidence.get("required_fields", []),
    )

    chain = data.get("causal_chain", {})
    check(
        "CAUSAL_CHAIN",
        chain.get("ordered_layers") == CHAIN
        and chain.get("cross_cutting_interface") == "EVIDENCE_TRACE"
        and chain.get("no_layer_may_skip_trace") is True,
        chain,
    )
    check("TRACE_FIELDS", all(field in chain.get("required_trace_fields", []) for field in TRACE_FIELDS), chain.get("required_trace_fields", []))

    cross = data.get("cross_layer_rules", {})
    check(
        "TARGET_BOUNDARY",
        cross.get("target_calculation_boundary", {}).get("missing_data_output") == "TARGET_CALCULATION_UNAVAILABLE"
        and cross.get("target_calculation_boundary", {}).get("plus_100_default_mode") == "INACTIVE"
        and cross.get("target_calculation_boundary", {}).get("target_backsolve_allowed") is False,
        cross.get("target_calculation_boundary", {}),
    )
    check(
        "SOURCE_PRIORITY",
        cross.get("source_priority", {}).get("lower_tier_opinion_overrides_primary_fact") is False
        and cross.get("source_priority", {}).get("unresolved_material_conflict_result") == "PRODUCTION_BLOCKED",
        cross.get("source_priority", {}),
    )

    sections = data.get("product_section_binding", {})
    check(
        "SECTION_BINDINGS",
        set(sections.get("interface_to_section", {}).values())
        == {"SECTION_0", "SECTION_3", "SECTION_4", "SECTION_5", "SECTION_6", "SECTION_7", "SECTION_8", "SECTION_9"}
        and sections.get("all_required_sections_bound") is True,
        sections,
    )

    readiness = data.get("readiness", {})
    check(
        "PRODUCTION_NOT_READY",
        readiness.get("phase3_implementation") == "PASS"
        and readiness.get("production_ready") == "NO"
        and readiness.get("next_phase_auto_start") is False,
        readiness,
    )
    safety = data.get("safety", {})
    check("NO_REAL_PRODUCTION", bool(safety) and not any(safety.values()), safety)
    success = data.get("success_criteria", {})
    check("SUCCESS_CRITERIA", len(success) == 12 and all(value == "PASS" for value in success.values()), success)

    failures = [item for item in checks if item["result"] == "FAIL"]
    return {
        "result": "PHASE3_DOWNSTREAM_DECISION_VALID" if not failures else "PHASE3_DOWNSTREAM_DECISION_INVALID",
        "check_count": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(load(args.input), args.project_root.resolve())
    except Exception as exc:
        result = {
            "result": "PHASE3_DOWNSTREAM_DECISION_INVALID",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return 0 if result.get("result") == "PHASE3_DOWNSTREAM_DECISION_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
