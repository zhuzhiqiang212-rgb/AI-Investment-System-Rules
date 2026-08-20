from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_FEATURES = (
    "three_layer_reading",
    "seven_layer_causal_chain",
    "same_day_news_and_research",
    "all_accounts_and_assets",
    "holding_deep_research",
    "formal_five_gates_and_discovery",
    "target_paths_40_100",
    "evidence_chain",
    "pdca_learning_loop",
    "historical_important_functions",
    "plain_language_experience",
)

REQUIRED_ACCOUNT_KEYS = ("FUTU", "SBI_归属未闭合", "IBKR", "bitFlyer")
REQUIRED_GATE_KEYS = ("gate_1", "gate_2", "gate_3", "gate_4", "gate_5")
PDF_AUTHORIZATION = "FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED"


class ContractError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def assert_no_prior_candidate_dependency(paths: list[str]) -> None:
    bad = [p for p in paths if "output/candidates" in p.replace("\\", "/").lower()]
    if bad:
        raise ContractError(f"historical candidate dependency is forbidden: {bad}")


def validate_handoff(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("run_id", "evidence_cutoff_jst", "feature_matrix", "accounts_and_risk", "seven_layers", "formal_gates", "judgment_matrix", "evidence_registry", "safety"):
        if key not in payload:
            errors.append(f"missing:{key}")
    matrix = payload.get("feature_matrix", {})
    for feature in REQUIRED_FEATURES:
        row = matrix.get(feature)
        if not isinstance(row, dict):
            errors.append(f"feature_missing:{feature}")
            continue
        if row.get("data_interface") in (None, "") or row.get("render_location") in (None, "") or row.get("qa_gate") in (None, ""):
            errors.append(f"feature_incomplete:{feature}")
    layers = payload.get("seven_layers", [])
    if not isinstance(layers, list) or len(layers) != 7:
        errors.append("seven_layers_count")
    gates = payload.get("formal_gates", {})
    for key in REQUIRED_GATE_KEYS:
        if key not in gates:
            errors.append(f"formal_gate_missing:{key}")
    accounts = payload.get("accounts_and_risk", {}).get("account_known_values_jpy", {})
    for key in REQUIRED_ACCOUNT_KEYS:
        if key not in accounts:
            errors.append(f"account_missing:{key}")
    if payload.get("product_generated") is not False:
        errors.append("stage_ab_must_not_generate_product")
    safety = payload.get("safety", {})
    if safety.get("pdf_generated") is not False:
        errors.append("stage_ab_must_not_generate_pdf")
    if safety.get("trade_calls", 0) != 0 or safety.get("order_calls", 0) != 0:
        errors.append("trade_boundary_broken")
    return errors


def validate_final_judgment(payload: dict[str, Any], expected_run_id: str) -> None:
    if payload.get("parent_run_id") != expected_run_id:
        raise ContractError("final judgment parent_run_id mismatch")
    required = ("seven_layer_final_judgment", "asset_final_answers", "research_gate_answers", "target_and_cash_plan", "pdca_decisions")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ContractError(f"final judgment fields missing: {missing}")


def validate_pdf_authorization(payload: dict[str, Any], expected_run_id: str) -> None:
    if payload.get("run_id") != expected_run_id:
        raise ContractError("PDF authorization run_id mismatch")
    if payload.get("authorization") != PDF_AUTHORIZATION:
        raise ContractError("PDF render is not authorized")