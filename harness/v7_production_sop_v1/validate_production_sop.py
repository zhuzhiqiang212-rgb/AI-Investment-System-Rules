from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOP_PATH = Path(__file__).with_name("V7正式生产SOP_Current_v1.0.json")
SOURCE_RULES_PATH = Path(__file__).with_name("source_classification_rules.json")
FRESHNESS_RULES_PATH = Path(__file__).with_name("freshness_and_consumption_rules.json")
STATE_MACHINE_PATH = Path(__file__).with_name("production_state_machine.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_single_current(records: list[dict[str, Any]]) -> bool:
    return sum(record.get("status") == "CURRENT" for record in records) == 1


def identity_complete(identity: dict[str, Any]) -> bool:
    required = ("sop_id", "name", "version", "status", "effective_at", "artifact_sha_binding")
    return all(identity.get(field) not in (None, "") for field in required)


def production_ready_allowed(
    sop: dict[str, Any], sop_records: list[dict[str, Any]], controller_approved: bool
) -> bool:
    return (
        identity_complete(sop.get("identity", {}))
        and validate_single_current(sop_records)
        and sop.get("readiness", {}).get("sop_implementation") == "PASS"
        and sop.get("readiness", {}).get("harness_validation") == "PASS"
        and sop.get("readiness", {}).get("sop_tests") == "PASS"
        and controller_approved
    )


def consumption_decision(
    previous_sha: str | None,
    current_sha: str | None,
    already_consumed: bool,
    review_trigger: bool,
    material_primary_disclosure: bool = False,
) -> str:
    if material_primary_disclosure:
        return "PRIMARY_DISCLOSURE_REFRESH_REQUIRED"
    if review_trigger:
        return "PENDING_REVIEW"
    if previous_sha != current_sha:
        return "PENDING_CONSUMPTION"
    if already_consumed:
        return "SKIP_FULL_RECONSUMPTION"
    return "PENDING_CONSUMPTION"


def source_fact_winner(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return min(candidates, key=lambda item: int(item["tier"]))


def refresh_trigger(event_type: str, material: bool = True) -> str:
    if event_type in {"NEW_EDINET_DISCLOSURE", "NEW_STATUTORY_DISCLOSURE"} and material:
        return "PRIMARY_DISCLOSURE_REFRESH_REQUIRED"
    if event_type in {
        "NEW_EARNINGS",
        "MATERIAL_GUIDANCE_CHANGE",
        "MATERIAL_EDINET_DISCLOSURE",
        "INVESTMENT_THESIS_INVALIDATED",
        "PDCA_REPEATED_LOGIC_FAILURE",
    } and material:
        return "FULL_COMPANY_REFRESH_REQUIRED"
    return "NO_FULL_REFRESH"


def precise_a_action_allowed(portfolio_state: str, amount_is_precise: bool) -> bool:
    if portfolio_state == "UNVERIFIED" and amount_is_precise:
        return False
    return portfolio_state in {"CURRENT", "STALE", "UNVERIFIED"}


def missing_data_mode(missing_class: str) -> str:
    if missing_class == "HARD_BLOCK":
        return "PRODUCTION_BLOCKED"
    if missing_class == "SOFT_MISSING":
        return "DEGRADED_MODE"
    return "NORMAL"


def action_pair_legal(prediction: str, action: str) -> bool:
    legal_actions = {"A_EXECUTE", "B_WAIT_TRIGGER", "C_WATCH", "D_EXCLUDE", "NO_TRADE"}
    return bool(prediction) and action in legal_actions


def apply_pdca_feedback(state: dict[str, Any], feedback: dict[str, Any]) -> dict[str, Any]:
    output = dict(state)
    allowed = {
        "signal_weight",
        "confidence",
        "required_confirmation",
        "timing_rule",
        "source_weight",
        "model_notes",
    }
    for key, value in feedback.items():
        if key in allowed:
            output[key] = value
    return output


def validate(sop: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    doc = sop or load_json(SOP_PATH)
    source_rules = load_json(SOURCE_RULES_PATH)
    freshness_rules = load_json(FRESHNESS_RULES_PATH)
    state_machine = load_json(STATE_MACHINE_PATH)
    checks: list[tuple[str, bool, str]] = []

    checks.append(("SOP_IDENTITY", identity_complete(doc.get("identity", {})), "Formal SOP identity is complete."))
    bindings = doc.get("governance_bindings", {})
    checks.append(("GOVERNANCE_BINDINGS", set(bindings) == {"business_blueprint", "phase1_structure", "minimal_harness", "sop_design_authority", "research_baseline"}, "Five required governance inputs are bound."))
    checks.append(("BLUEPRINT_SOP_SEPARATION", doc["identity"].get("is_business_blueprint") is False and bindings["business_blueprint"]["blueprint_id"] == "V7_COMPLETE_PRODUCT_CURRENT_v2.0", "Business blueprint and production SOP have separate identities."))
    expected_inputs = {"BUSINESS_BLUEPRINT", "PRODUCTION_SOP", "RESEARCH_BASELINE", "FRESH_INTEL", "PERSISTENT_KNOWLEDGE", "MARKET_DATA", "PORTFOLIO_STATE", "PDCA_STATE"}
    checks.append(("INPUT_SYSTEM", set(doc.get("input_system", {})) == expected_inputs, "All eight formal input classes exist."))
    checks.append(("SOURCE_HIERARCHY", source_rules["source_tiers"][0]["tier"] == 1 and source_rules["conflict_policy"]["lower_tier_may_override_higher_tier_fact"] is False, "Primary official facts outrank lower-tier sources."))
    checks.append(("EDINET_CLASS", doc["edinet_rules"]["source_class"] == "PRIMARY_REGULATORY_DISCLOSURE" and source_rules["edinet"]["tier"] == 1, "EDINET is a Tier 1 primary regulatory source."))
    checks.append(("FRESHNESS_CLASSES", freshness_rules["freshness_classes"] == ["HOT", "CURRENT", "STALE", "ARCHIVE"], "All four freshness classes exist."))
    checks.append(("LIFECYCLE_SEPARATION", len(freshness_rules["lifecycle_profiles"]) == 6 and freshness_rules["uniform_seven_day_rule"] is False, "Information classes have separate configurable lifecycles."))
    checks.append(("INCREMENTAL_CONSUMPTION", doc["incremental_consumption"]["unchanged_consumed_default"] == "SKIP_FULL_RECONSUMPTION" and doc["incremental_consumption"]["changed_sha_default"] == "PENDING_CONSUMPTION", "Unchanged consumed artifacts are skipped and changed artifacts are reread."))
    checks.append(("BASELINE_DYNAMIC", doc["baseline_dynamic_rules"]["baseline_identity_may_be_overwritten"] is False and doc["baseline_dynamic_rules"]["no_material_change_allowed"] is True, "V13 identity is protected while dynamic conclusions may update."))
    required_refresh = {"NEW_EARNINGS", "MATERIAL_GUIDANCE_CHANGE", "INVESTMENT_THESIS_INVALIDATED", "PDCA_REPEATED_LOGIC_FAILURE", "MATERIAL_NEW_EDINET_DISCLOSURE"}
    checks.append(("FULL_REFRESH_TRIGGERS", required_refresh.issubset(set(doc["full_refresh_triggers"])), "Required company refresh triggers are present."))
    checks.append(("PORTFOLIO_FRESHNESS", doc["portfolio_freshness_rules"]["states"] == ["CURRENT", "STALE", "UNVERIFIED"] and doc["portfolio_freshness_rules"]["unverified_blocks_precise_a_execute_amount"] is True, "Unverified portfolios block precise A-level position actions."))
    checks.append(("TARGET_RULES", doc["target_rules"]["plus_40"]["fabrication_allowed"] is False and doc["target_rules"]["plus_100"]["default_mode"] == "INACTIVE", "Target calculations cannot be fabricated and +100 defaults inactive."))
    checks.append(("ACTION_RULES", doc["action_rules"]["bullish_wait_is_legal"] is True and doc["action_rules"]["no_trade_is_legal"] is True, "Prediction/action separation and NO_TRADE are supported."))
    checks.append(("PDCA_FEEDBACK", {"signal_weight", "confidence", "required_confirmation", "timing_rule", "source_weight", "model_notes"}.issubset(set(doc["pdca_feedback_rules"]["next_run_adjustable_fields"])), "PDCA can modify the next run's process fields."))
    checks.append(("MISSING_DATA", doc["missing_data_rules"]["HARD_BLOCK"]["result"] == "PRODUCTION_BLOCKED" and doc["missing_data_rules"]["SOFT_MISSING"]["result"] == "DEGRADED_MODE", "Hard blocks stop production and soft missing enters degraded mode."))
    checks.append(("NEWS_CHAIN", doc["news_routing"]["direct_news_to_buy_allowed"] is False and len(doc["news_routing"]["required_chain"]) == 6, "News must pass fact, impact, judgement, and portfolio layers."))
    checks.append(("PRODUCTION_STEPS", [step["step"] for step in state_machine["steps"]] == list(range(17)) and len(doc["production_steps"]) == 17, "Steps 0 through 16 exist without gaps."))
    checks.append(("V13_SHA", sha256(ROOT / bindings["research_baseline"]["path"]) == bindings["research_baseline"]["sha256"], "Frozen V13 SHA matches the actual artifact."))
    safety = doc.get("safety", {})
    checks.append(("NO_REAL_PRODUCTION", bool(safety) and not any(safety.values()), "No EDINET fetch, news scan, production, release, trade, or order occurred."))
    checks.append(("PRODUCTION_NOT_READY", doc["readiness"]["production_ready"] == "NO" and doc["readiness"]["approval_required"] == "V7_CONTROL_3", "Production stays disabled pending controller acceptance."))

    return [
        {"check_id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail}
        for check_id, passed, detail in checks
    ]


def main() -> int:
    checks = validate()
    result = {
        "validator": "V7_PRODUCTION_SOP_READ_ONLY_VALIDATOR_1.0",
        "result": "SOP_STRUCTURE_VALID" if all(item["status"] == "PASS" for item in checks) else "SOP_STRUCTURE_INVALID",
        "check_count": len(checks),
        "failure_count": sum(item["status"] == "FAIL" for item in checks),
        "checks": checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
