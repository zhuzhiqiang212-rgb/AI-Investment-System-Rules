from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JST = timezone(timedelta(hours=9))
LOCKED = ROOT / "output/decision_inputs/2026-08-26/V7-V20-FORECAST-LOCK-20260826175555-JST/84份正式预测_LOCKED.json"
REGISTRY = ROOT / "data/forecast/locked_predictions_registry.json"
FUTU = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/FUTU预测型目标桥_完整账户版.json"
SBI = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/SBI预测型目标桥_完整账户版.json"
NONPOSITION = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/FUTU_SBI非持仓收益_GPT裁决写回.json"
FUTU_DETAIL = ROOT / "output/decision_inputs/2026-08-26/V7-V20-TARGET-BRIDGE-20260826-191511-JST/FUTU预测型目标桥.json"
FINAL18_IDENTITY = ROOT / "00_任务中心/V7_v2.0_最终18身份映射_Current.json"
OPPORTUNITY = ROOT / "00_任务中心/V7_v2.0_预测型机会候选宇宙_GPT总控判断包_Current.json"
BASE_SOURCE = ROOT / "output/candidates/2026-08-24/V7-V20-UNIFIED-HTML-20260825-100649-JST/02_统一事实与判断冻结源.json"
CURRENT_POINTER = ROOT / "00_任务中心/V7_v2.0_最终完整HTML_Current.json"
CURRENT_SOURCE = ROOT / "00_任务中心/V7_v2.0_预测型完整产品源_Current.json"
DAILY_REPORT = ROOT / "00_请先看这里/00_今日日报.pdf"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def file_info(path: Path) -> dict:
    return {"path": str(path), "size": path.stat().st_size, "sha256": sha(path)}


def equal(a, b, tolerance=1e-9) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tolerance
    return a == b


def locked_view(c: dict) -> dict:
    return {
        "forecast_id": c["forecast_id"],
        "horizon": c["horizon"],
        "forecast_status": c["forecast_status"],
        "lock_reference_price": c["lock_reference_price"],
        "bear_price_range": c["bear_price_range"],
        "base_price_range": c["base_price_range"],
        "bull_price_range": c["bull_price_range"],
        "probabilities": c["probability_candidate"],
        "expected_price": c["expected_price_candidate"],
        "expected_return": c["expected_return_candidate"],
        "business_direction": c["business_direction"],
        "price_direction": c["price_direction"],
        "confidence": c["confidence"],
        "evidence_confidence": c["evidence_confidence"],
        "current_counterevidence": c["current_counterevidence"],
        "future_invalidation_condition": c["future_invalidation_condition"],
        "next_verification_date": c["verdict_date"],
        "pdca_status": "PENDING / NOT_DUE",
        "canonical_content_sha256": c["canonical_content_sha256"],
        "locked_at": c["locked_at"],
        "trade_action_status": c["trade_action_status"],
    }


def absolute_outlook(expected_return: float) -> str:
    pct = expected_return * 100
    if pct > 5:
        return "ABSOLUTE_POSITIVE"
    if pct < -5:
        return "ABSOLUTE_NEGATIVE"
    return "ABSOLUTE_NEUTRAL"


def main() -> None:
    started = datetime.now(JST)
    run_id = f"V7-V20-PREDICTIVE-PRODUCT-SOURCE-{started:%Y%m%d%H%M%S}-JST"
    out = ROOT / "output/decision_inputs" / started.strftime("%Y-%m-%d") / run_id
    if out.exists():
        raise RuntimeError(f"run already exists: {out}")
    out.mkdir(parents=True)

    source_before = {p.name: sha(p) for p in (LOCKED, REGISTRY, DAILY_REPORT)}
    locked, registry = load(LOCKED), load(REGISTRY)
    futu, sbi, nonposition = load(FUTU), load(SBI), load(NONPOSITION)
    futu_detail = load(FUTU_DETAIL)
    final18_identity, opportunity = load(FINAL18_IDENTITY), load(OPPORTUNITY)
    base_source = load(BASE_SOURCE)

    contracts = locked["contracts"]
    by_key = {(c["asset_id"], c["horizon"]): c for c in contracts}
    holdings = sorted({c["asset_id"] for c in contracts if c["asset_identity"] == "HOLDING"})
    final18 = [a["asset_id"] for a in final18_identity["assets"]]
    if (len(holdings), len(final18), len(contracts)) != (24, 18, 84):
        raise RuntimeError("frozen source count mismatch")

    registry_rows = next(v for v in registry.values() if isinstance(v, list) and len(v) == 132)
    reg_by_id = {r.get("forecast_id"): r for r in registry_rows}
    futu_positions = {p["asset_id"]: p for p in futu_detail["positions"]}
    sbi_positions = {p["ticker"]: p for p in sbi["positions"]}
    account_map = {aid: [] for aid in holdings}
    for aid in holdings:
        if aid in futu_positions:
            account_map[aid].append({"account": "FUTU", "quantity": futu_positions[aid].get("quantity")})
        if aid in sbi_positions:
            account_map[aid].append({"account": "SBI_PERSONAL", "quantity": sbi_positions[aid]["quantity"]})
    for aid, account in (("US.META", "IBKR"), ("BTC", "bitFlyer"), ("ETH", "bitFlyer")):
        if aid in account_map and all(x["account"] != account for x in account_map[aid]):
            account_map[aid].append({"account": account, "quantity": None, "target_management": False})

    holding_rows = []
    for aid in holdings:
        short, year = by_key[(aid, "0-30D")], by_key[(aid, "1Y")]
        holding_rows.append({
            "asset_id": aid,
            "asset_name": year["asset_name"],
            "current_identity": "HOLDING",
            "accounts": account_map[aid],
            "forecasts": {"0-30D": locked_view(short), "1Y": locked_view(year)},
            "absolute_price_outlook": absolute_outlook(year["expected_return_candidate"]),
            "relative_replacement_status": "NOT_EVALUATED_AS_ACTION",
            "action_authorization": "NO_ACTION_AUTHORIZED",
            "valuation_background_role": "VALUATION_INPUT_ONLY / NOT_FORECAST_CONCLUSION",
            "chairman_plain_language": {
                "business_direction": "公司生意未来会不会变好。",
                "price_direction": "从锁定参考价格出发，未来股价是否可能上涨。",
                "difference": "公司赚钱可能增加，但当前股价太贵时，未来股价仍可能下跌。",
                "pdca": "到约定日期再检查预测是否兑现，并记录错在哪里。",
            },
        })

    opp_by_id = {x["asset_id"]: x for x in opportunity["candidate_universe"]}
    final18_rows = []
    for aid in final18:
        short, year = by_key[(aid, "0-30D")], by_key[(aid, "1Y")]
        absolute = absolute_outlook(year["expected_return_candidate"])
        relative = (
            "RELATIVE_REPLACEMENT_RESEARCH_ALLOWED"
            if absolute == "ABSOLUTE_POSITIVE"
            else "RELATIVE_ONLY_IF_APPLICABLE"
            if absolute == "ABSOLUTE_NEUTRAL"
            else "RELATIVE_ONLY_IF_APPLICABLE / NOT_ABSOLUTE_POSITIVE_OPPORTUNITY"
        )
        final18_rows.append({
            "asset_id": aid,
            "asset_name": year["asset_name"],
            "identity": "FINAL_18_FOR_FORECAST_RESEARCH",
            "not_buy_list": True,
            "forecasts": {"0-30D": locked_view(short), "1Y": locked_view(year)},
            "absolute_price_outlook": absolute,
            "relative_replacement_status": relative,
            "replacement_comparison_context": opp_by_id.get(aid, {}).get("comparison_dimensions"),
            "action_authorization": "NO_ACTION_AUTHORIZED",
            "evidence_limit": "C_GRADE_LIMIT_VISIBLE" if aid in {"KRX.000660", "JP.3436"} else None,
            "chairman_plain_language": {
                "absolute_outlook": "绝对预测是从锁定参考价格出发，判断这项资产自身未来可能涨跌。",
                "relative_status": "相对替换只比较它是否比现金或某项现有持仓更合适，不等于应该买入。",
                "pdca": "到约定日期再检查预测是否兑现，并记录错在哪里。",
            },
        })

    futu_rows = futu_detail["positions"]
    futu_ranked = sorted(futu_rows, key=lambda x: x["contribution_pp"], reverse=True)
    futu_return = futu["calculation"]["full_account_expected_return_pct"]
    futu_top3 = sum(x["contribution_pp"] for x in futu_ranked[:3])
    futu_top5 = sum(x["contribution_pp"] for x in futu_ranked[:5])
    sbi_rows = sbi["positions"]
    sbi_return = sbi["calculation"]["full_account_expected_return_pct"]
    softbank = next(x for x in sbi_rows if x["ticker"] == "JP.9984")
    bridge_wire = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
        "source_run_id": "V7-V20-NONPOSITION-BRIDGE-20260827011449-JST",
        "FUTU": {
            "account_facts": futu["account_facts"],
            "positions": futu_rows,
            "nonposition_assumptions": futu["nonposition_assumptions"],
            "calculation": futu["calculation"],
            "concentration": {
                "top3_assets": [x["asset_id"] for x in futu_ranked[:3]],
                "top3_contribution_pp": futu_top3,
                "top3_share_of_full_return_pct": futu_top3 / futu_return * 100,
                "top5_contribution_pp": futu_top5,
                "top5_share_of_full_return_pct": futu_top5 / futu_return * 100,
                "boundary": "这是预测贡献集中度，不是减持判断。",
            },
            "fund_plain_language": "这笔基金身份尚未取得，证据为C档，只采用宽情景账户假设；概率加权收益2.50%，对整个FUTU账户贡献约0.061612个百分点。取得基金身份后只允许前瞻更新。贡献百分点是它给整个账户收益增加或减少多少个百分点。",
        },
        "SBI_PERSONAL": {
            "account_facts": sbi["account_facts"],
            "positions": sbi_rows,
            "nonposition_assumptions": [sbi["nonposition_assumption"]],
            "calculation": sbi["calculation"],
            "current_holding_count": 9,
            "softbank_quantity": softbank["quantity"],
            "nintendo_status": "NOT_HELD",
            "concentration": {
                "softbank_contribution_pp": softbank["contribution_pp"],
                "softbank_share_of_full_return_pct": softbank["contribution_pp"] / sbi_return * 100,
                "other_eight_net_contribution_pp": sum(x["contribution_pp"] for x in sbi_rows if x["ticker"] != "JP.9984"),
                "boundary": "这是预测贡献集中度，不是自动减仓或加仓指令。",
            },
        },
        "action_authorization": "NO_ACTION_AUTHORIZED",
    }

    pdca_rows = []
    for c in contracts:
        reg = reg_by_id.get(c["forecast_id"])
        pdca_rows.append({
            "forecast_id": c["forecast_id"],
            "asset_id": c["asset_id"],
            "horizon": c["horizon"],
            "canonical_content_sha256": c["canonical_content_sha256"],
            "registry_sha256": reg.get("sha256") if reg else None,
            "pdca_status": (reg or {}).get("pdca_status", "PENDING / NOT_DUE"),
            "verdict_date": c["verdict_date"],
            "registered_at": c["registered_at"],
        })
    pdca_wire = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
        "registry_total_count": len(registry_rows),
        "current_batch_count": len(pdca_rows),
        "plain_language": "PDCA是到约定日期再检查预测是否兑现，并记录错在哪里。",
        "entries": pdca_rows,
    }

    required_positive = {"US.MU", "US.ORCL", "JP.7735", "US.ETN", "US.CRDO", "US.VRT"}
    semantic = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
        "threshold_rule": {
            "above_plus_5_pct": "ABSOLUTE_POSITIVE",
            "minus_5_to_plus_5_pct": "ABSOLUTE_NEUTRAL",
            "below_minus_5_pct": "ABSOLUTE_NEGATIVE",
        },
        "final18_positive": sorted(x["asset_id"] for x in final18_rows if x["absolute_price_outlook"] == "ABSOLUTE_POSITIVE"),
        "final18_neutral": sorted(x["asset_id"] for x in final18_rows if x["absolute_price_outlook"] == "ABSOLUTE_NEUTRAL"),
        "final18_negative": sorted(x["asset_id"] for x in final18_rows if x["absolute_price_outlook"] == "ABSOLUTE_NEGATIVE"),
        "required_positive_set": sorted(required_positive),
        "action_authorization": "NO_ACTION_AUTHORIZED",
        "plain_language": {
            "business_direction": "公司生意未来会不会变好。",
            "price_direction": "从今天锁定的参考价格出发，未来股价是否可能上涨。",
            "difference": "两者可以不同：公司赚钱增加，但当前股价太贵，未来股价仍可能下跌。",
            "replacement": "比另一项资产更好，只表示值得比较，不表示自身一定上涨，也不构成买入授权。",
        },
    }

    retired = {
        "run_id": run_id,
        "status": "HISTORICAL_SUPERSEDED / NOT_CURRENT",
        "items": [
            {"item": "FUTU旧静态约＋17.27%", "replacement": "FUTU完整账户预测收益33.48952570415816%"},
            {"item": "SBI旧静态约-4.23%", "replacement": "SBI完整账户预测收益17.835622010764844%"},
            {"item": "旧SBI 10只持仓派生表", "replacement": "SBI_PERSONAL九只Current持仓"},
            {"item": "SBI任天堂旧持仓行", "replacement": "JP.7974 NOT_HELD"},
            {"item": "软银3600股旧Current数量", "replacement": "JP.9984 4200股"},
            {"item": "旧静态目标贡献桥", "replacement": "完整预测型FUTU/SBI目标桥"},
            {"item": "原18只旧机会池Current身份", "replacement": "FINAL_18_FOR_FORECAST_RESEARCH"},
            {"item": "旧HTML中的两套账户数值", "replacement": "完整账户桥权威值"},
            {"item": "旧EPS或旧估值输入冒充预测的结果", "replacement": "VALUATION_INPUT_ONLY / NOT_FORECAST_CONCLUSION"},
        ],
        "preservation": "历史证据保留，但任何Current、目标桥、动作或产品渲染不得引用。",
    }

    current_source = {
        "run_id": run_id,
        "generated_at_jst": started.isoformat(),
        "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
        "candidate_identity": "PREDICTIVE_COMPLETE_PRODUCT_SOURCE / NOT_RELEASED / NOT_TRADE_ACTION",
        "source_precedence": {
            "forecast": file_info(LOCKED),
            "pdca": file_info(REGISTRY),
            "futu_bridge": file_info(FUTU),
            "sbi_bridge": file_info(SBI),
            "nonposition_assumptions": file_info(NONPOSITION),
            "final18_identity": file_info(FINAL18_IDENTITY),
            "historical_context_only": {**file_info(BASE_SOURCE), "role": "HISTORICAL_CONTEXT_ONLY / NOT_CURRENT"},
        },
        "counts": {
            "holding_assets": 24,
            "final18_assets": 18,
            "locked_forecasts": 84,
            "registry_total": len(registry_rows),
            "registry_current_batch": 84,
        },
        "current_sections": {
            "holdings": holding_rows,
            "final18": final18_rows,
            "account_target_bridges": bridge_wire,
            "forecast_pdca": pdca_wire,
            "semantic_separation": semantic,
            "retired_static_paths": retired,
        },
        "frozen_nonforecast_context": {
            "source_run_id": base_source.get("run_id"),
            "role": "STRUCTURE_AND_NONFORECAST_CONTEXT_ONLY",
            "warning": "旧账户、旧行情、旧静态估值和旧目标桥不得作为Current读取。",
        },
        "chairman_plain_language": {
            "business_direction": "公司生意未来会不会变好。",
            "price_direction": "从今天锁定的参考价格出发，未来股价是否可能上涨。",
            "difference": "公司生意变好和股价上涨不是同一件事；当前价格太贵时，公司赚钱增加，股价仍可能下跌。",
            "pdca": "到约定日期再检查预测是否兑现，并记录错在哪里。",
            "contribution_pp": "贡献百分点是某只持仓给整个账户收益增加或减少多少个百分点。",
        },
        "boundaries": ["NO_HTML", "NO_PDF", "NO_RELEASE", "NO_DAILY_REPORT_OVERWRITE", "NO_TRADE", "NO_ORDER"],
    }

    payloads = {
        "V7_v2.0_预测型完整产品源_Current.json": current_source,
        "24类持仓_锁定预测产品接线.json": {
            "run_id": run_id,
            "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
            "count": len(holding_rows),
            "assets": holding_rows,
        },
        "最终18_锁定预测产品接线.json": {
            "run_id": run_id,
            "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW",
            "identity": "FINAL_18_FOR_FORECAST_RESEARCH",
            "not_buy_list": True,
            "count": len(final18_rows),
            "assets": final18_rows,
        },
        "FUTU_SBI完整目标桥_产品接线.json": bridge_wire,
        "预测PDCA_产品接线.json": pdca_wire,
        "绝对预测与相对替换语义纠正报告.json": semantic,
        "旧静态路径退役映射.json": retired,
    }
    for name, value in payloads.items():
        dump(out / name, value)
    dump(CURRENT_SOURCE, current_source)

    source_after = {p.name: sha(p) for p in (LOCKED, REGISTRY, DAILY_REPORT)}
    holding_check = load(out / "24类持仓_锁定预测产品接线.json")["assets"]
    final18_check = load(out / "最终18_锁定预测产品接线.json")["assets"]
    bridge_check = load(out / "FUTU_SBI完整目标桥_产品接线.json")
    all_rows = holding_check + final18_check
    mapped = [forecast for row in all_rows for forecast in row["forecasts"].values()]

    forecast_id_mismatch = 0
    canonical_mismatch = 0
    registry_mismatch = 0
    probability_mismatch = 0
    scenario_mismatch = 0
    direction_mismatch = 0
    for row in all_rows:
        for horizon, view in row["forecasts"].items():
            original = by_key[(row["asset_id"], horizon)]
            forecast_id_mismatch += view["forecast_id"] != original["forecast_id"]
            canonical_mismatch += view["canonical_content_sha256"] != original["canonical_content_sha256"]
            probability_mismatch += view["probabilities"] != original["probability_candidate"]
            scenario_mismatch += sum(
                view[field] != original[field]
                for field in ("bear_price_range", "base_price_range", "bull_price_range")
            )
            direction_mismatch += view["business_direction"] != original["business_direction"]
            registered = reg_by_id.get(view["forecast_id"])
            registry_mismatch += registered is None or registered.get("sha256") != view["canonical_content_sha256"]

    negative_bad = sum(
        row["absolute_price_outlook"] == "ABSOLUTE_NEGATIVE"
        and "NOT_ABSOLUTE_POSITIVE_OPPORTUNITY" not in row["relative_replacement_status"]
        for row in final18_check
    )
    current_active_text = json.dumps({
        "holdings": holding_check,
        "final18": final18_check,
        "bridges": bridge_check,
    }, ensure_ascii=False)
    stale_patterns = ["17.27%", "-4.23%", '"softbank_quantity": 3600', '"nintendo_status": "HELD"']
    stale_hits = sum(current_active_text.count(value) for value in stale_patterns)
    html_count = len(list(out.glob("*.html")))
    pdf_count = len(list(out.glob("*.pdf")))
    action_values = [row["action_authorization"] for row in all_rows] + [bridge_check["action_authorization"]]

    gates = [
        (1, "持仓预测接线24/24", len(holding_check) == 24),
        (2, "机会对象预测接线18/18", len(final18_check) == 18),
        (3, "双期限预测84/84", len(mapped) == 84 and len({x["forecast_id"] for x in mapped}) == 84),
        (4, "forecast_id与登记册逐条相等", forecast_id_mismatch == 0 and registry_mismatch == 0),
        (5, "canonical SHA逐条相等", canonical_mismatch == 0),
        (6, "预测概率没有变化", probability_mismatch == 0),
        (7, "情景价格没有变化", scenario_mismatch == 0),
        (8, "业务方向没有变化", direction_mismatch == 0),
        (9, "账户事实与正式目标桥一致", bridge_check["FUTU"]["account_facts"] == futu["account_facts"] and bridge_check["SBI_PERSONAL"]["account_facts"] == sbi["account_facts"]),
        (10, "FUTU完整收益准确", equal(bridge_check["FUTU"]["calculation"]["full_account_expected_return_pct"], 33.48952570415816)),
        (11, "SBI完整收益准确", equal(bridge_check["SBI_PERSONAL"]["calculation"]["full_account_expected_return_pct"], 17.835622010764844)),
        (12, "＋40%和＋100%结论准确", all(bridge_check[a]["calculation"][k] == v for a in ("FUTU", "SBI_PERSONAL") for k, v in (("plus_40_path", "PLUS_40_NOT_PROVEN"), ("plus_100_path", "PLUS_100_NOT_PROVEN")))),
        (13, "非持仓假设身份正确", nonposition.get("assumption_count") == 3 and nonposition.get("security_forecast_registry_write_count") == 0),
        (14, "静态估值没有冒充预测", all(row["valuation_background_role"] == "VALUATION_INPUT_ONLY / NOT_FORECAST_CONCLUSION" for row in holding_check)),
        (15, "负预期候选未称绝对正机会", negative_bad == 0),
        (16, "旧SBI任天堂未重新进入Current", bridge_check["SBI_PERSONAL"]["nintendo_status"] == "NOT_HELD" and all(p["ticker"] != "JP.7974" for p in bridge_check["SBI_PERSONAL"]["positions"])),
        (17, "软银数量为4200股", bridge_check["SBI_PERSONAL"]["softbank_quantity"] == 4200),
        (18, "没有任何交易动作", all(value == "NO_ACTION_AUTHORIZED" for value in action_values)),
        (19, "没有生成HTML", html_count == 0),
        (20, "没有生成PDF", pdf_count == 0),
        (21, "没有覆盖正式日报", source_before[DAILY_REPORT.name] == source_after[DAILY_REPORT.name]),
        (22, "锁定预测及登记册SHA保持不变", source_before == source_after and source_after[LOCKED.name] == "FFA84D49E20CFB0D15A5220E33A94547BA16683B2B4D8C4C731E549635F382B8" and source_after[REGISTRY.name] == "93EA7C5AFC7AF0999A16EBA57EFFD4FDDF16D86A1AE1CFB82127CA30CE1B2051"),
    ]
    metrics = {
        "holding_forecast_mapping_missing_count": 24 - len(holding_check),
        "opportunity_forecast_mapping_missing_count": 18 - len(final18_check),
        "forecast_id_mismatch_count": forecast_id_mismatch + registry_mismatch,
        "canonical_sha_mismatch_count": canonical_mismatch,
        "locked_forecast_change_count": int(source_before[LOCKED.name] != source_after[LOCKED.name]),
        "registry_change_count": int(source_before[REGISTRY.name] != source_after[REGISTRY.name]),
        "static_valuation_as_forecast_count": sum(row["valuation_background_role"] != "VALUATION_INPUT_ONLY / NOT_FORECAST_CONCLUSION" for row in holding_check),
        "negative_candidate_labeled_absolute_opportunity_count": negative_bad,
        "stale_account_fact_current_hit_count": stale_hits,
        "trade_or_order_count": 0 if all(value == "NO_ACTION_AUTHORIZED" for value in action_values) else 1,
        "html_count": html_count,
        "pdf_count": pdf_count,
    }
    gate_report = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_REVIEW" if all(ok for _, _, ok in gates) else "INTERNAL_HARD_GATE_FAILED",
        "result": f"{sum(ok for _, _, ok in gates)}/22 PASS",
        "gates": [{"gate": n, "check": label, "result": "PASS" if ok else "FAIL"} for n, label, ok in gates],
        "metrics": metrics,
        "post_html_only": [
            {"check": "HTML正文与源逐字段一致", "status": "POST_HTML_ONLY / NOT_EVALUATED_YET"},
            {"check": "HTML阅读与视觉质量", "status": "POST_HTML_ONLY / NOT_EVALUATED_YET"},
        ],
    }
    dump(out / "预测型产品源硬闸报告.json", gate_report)

    old_pointer = load(CURRENT_POINTER) if CURRENT_POINTER.exists() else None
    pointer = {
        "run_id": run_id,
        "status": gate_report["status"],
        "current_stage": "PREDICTIVE_PRODUCT_SOURCE_REVIEW",
        "current_source": file_info(CURRENT_SOURCE),
        "html_status": "NO_HTML_GENERATED",
        "pdf_status": "NO_PDF_GENERATED",
        "historical_html_pointer": {**old_pointer, "status": "HISTORICAL_SUPERSEDED / NOT_CURRENT"} if isinstance(old_pointer, dict) else old_pointer,
        "boundaries": ["NO_HTML", "NO_PDF", "NO_RELEASE", "NO_DAILY_REPORT_OVERWRITE", "NO_TRADE", "NO_ORDER"],
    }
    dump(CURRENT_POINTER, pointer)

    artifact_paths = [out / name for name in payloads] + [out / "预测型产品源硬闸报告.json", CURRENT_SOURCE, CURRENT_POINTER]
    manifest = {
        "run_id": run_id,
        "status": gate_report["status"],
        "generated_at_jst": datetime.now(JST).isoformat(),
        "artifacts": [file_info(path) for path in artifact_paths],
        "immutable_source_hashes_before": source_before,
        "immutable_source_hashes_after": source_after,
        "html_count": html_count,
        "pdf_count": pdf_count,
        "release_count": 0,
        "trade_or_order_count": metrics["trade_or_order_count"],
    }
    manifest_path = out / "提交身份与SHA256清单.json"
    dump(manifest_path, manifest)

    delivered = list(out.glob("*.json")) + [CURRENT_SOURCE, CURRENT_POINTER]
    replacements = {str(path): path.read_bytes().count(b"\xef\xbf\xbd") for path in delivered}
    if any(replacements.values()):
        raise RuntimeError(f"UTF-8 replacement bytes found: {replacements}")
    if not all(ok for _, _, ok in gates):
        raise RuntimeError(json.dumps(gate_report, ensure_ascii=False))
    print(json.dumps({
        "run_id": run_id,
        "output_dir": str(out),
        "status": gate_report["status"],
        "gate_result": gate_report["result"],
        "current_source": file_info(CURRENT_SOURCE),
        "manifest": file_info(manifest_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
