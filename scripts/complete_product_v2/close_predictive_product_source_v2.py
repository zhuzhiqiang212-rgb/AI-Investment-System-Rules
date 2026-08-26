from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JST = timezone(timedelta(hours=9))
LOCKED = ROOT / "output/decision_inputs/2026-08-26/V7-V20-FORECAST-LOCK-20260826175555-JST/84份正式预测_LOCKED.json"
REGISTRY = ROOT / "data/forecast/locked_predictions_registry.json"
FUTU = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/FUTU预测型目标桥_完整账户版.json"
SBI = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/SBI预测型目标桥_完整账户版.json"
NONPOSITION = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-BRIDGE-20260827011449-JST/FUTU_SBI非持仓收益_GPT裁决写回.json"
COMPARISON = ROOT / "output/decision_inputs/2026-08-26/V7-V20-TARGET-BRIDGE-20260826-191511-JST/现有持仓_vs_最终18预测比较.json"
FINAL18_IDENTITY = ROOT / "00_任务中心/V7_v2.0_最终18身份映射_Current.json"
OPPORTUNITY = ROOT / "00_任务中心/V7_v2.0_预测型机会候选宇宙_GPT总控判断包_Current.json"
TAIL_SCAN = ROOT / "output/decision_inputs/2026-08-26/V7-V20-FORECAST-LOCK-20260826175555-JST/最终增量新闻尾扫报告.json"
SBI_EVIDENCE = ROOT / "output/decision_inputs/2026-08-27/V7-V20-NONPOSITION-RETURN-20260827005103-JST/SBI个人账户最新直接证据冻结报告.json"
FUTU_ACCOUNT = ROOT / "data/accounts/futu_readonly_snapshot_20260826_target_bridge.json"
LEGACY_SOURCE = ROOT / "output/candidates/2026-08-24/V7-V20-UNIFIED-HTML-20260825-100649-JST/02_统一事实与判断冻结源.json"
V1_SOURCE = ROOT / "output/decision_inputs/2026-08-27/V7-V20-PREDICTIVE-PRODUCT-SOURCE-20260827051618-JST/V7_v2.0_预测型完整产品源_Current.json"
CURRENT_V2 = ROOT / "00_任务中心/V7_v2.0_预测型完整产品源_Current_v2.json"
CURRENT_ALIAS = ROOT / "00_任务中心/V7_v2.0_预测型完整产品源_Current.json"
CURRENT_POINTER = ROOT / "00_任务中心/V7_v2.0_最终完整HTML_Current.json"
DAILY_REPORT = ROOT / "00_请先看这里/00_今日日报.pdf"

WORLDVIEW_RULE = ROOT / "00_请先看这里/右栏_完整世界观描述.html"
STRATEGY_RULE = ROOT / "00_请先看这里/右栏_完整国家战略地图.html"
FUND_FLOW_RULE = ROOT / "00_请先看这里/右栏_资金流动完整机制.html"
SECTOR_RULE = ROOT / "00_请先看这里/右栏_板块地图.html"
PDCA_RULE = ROOT / "00_请先看这里/PDCA记分规则准绳.html"
TARGET_RULE = ROOT / "00_请先看这里/目标倒推框架_定稿_1年双档_20260719.html"


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


def mtime_jst(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat()


def complete_contract(c: dict) -> dict:
    return {
        "source_forecast_id": c["forecast_id"],
        "source_canonical_sha256": c["canonical_content_sha256"],
        "copied_without_business_change": True,
        "locked_contract": c,
    }


def main() -> None:
    now = datetime.now(JST)
    run_id = f"V7-V20-PREDICTIVE-PRODUCT-SOURCE-V2-{now:%Y%m%d%H%M%S}-JST"
    out = ROOT / "output/decision_inputs" / now.strftime("%Y-%m-%d") / run_id
    if out.exists():
        raise RuntimeError(f"run already exists: {out}")
    out.mkdir(parents=True)

    immutable = [LOCKED, REGISTRY, FUTU, SBI, NONPOSITION, DAILY_REPORT]
    before_hashes = {str(path): sha(path) for path in immutable}
    locked, registry = load(LOCKED), load(REGISTRY)
    futu, sbi, nonposition = load(FUTU), load(SBI), load(NONPOSITION)
    comparison, final18_identity = load(COMPARISON), load(FINAL18_IDENTITY)
    opportunity, tail_scan = load(OPPORTUNITY), load(TAIL_SCAN)
    sbi_evidence, legacy = load(SBI_EVIDENCE), load(LEGACY_SOURCE)

    contracts = locked["contracts"]
    by_key = {(c["asset_id"], c["horizon"]): c for c in contracts}
    holdings = sorted({c["asset_id"] for c in contracts if c["asset_identity"] == "HOLDING"})
    final18 = [row["asset_id"] for row in final18_identity["assets"]]
    detailed_rows = [complete_contract(c) for c in contracts]
    detailed_by_key = {
        (row["locked_contract"]["asset_id"], row["locked_contract"]["horizon"]): row
        for row in detailed_rows
    }

    registry_rows = next(value for value in registry.values() if isinstance(value, list) and len(value) == 132)
    registry_by_id = {
        row["forecast_id"]: row
        for row in registry_rows
        if isinstance(row, dict) and row.get("forecast_id")
    }
    holding_comparisons = {
        row["asset_id"]: row
        for row in comparison["assets"]
        if row.get("role") == "EXISTING_HOLDING"
    }
    opportunity_by_id = {row["asset_id"]: row for row in opportunity["candidate_universe"]}
    identity_by_id = {row["asset_id"]: row for row in final18_identity["assets"]}

    holding_rows = []
    for asset_id in holdings:
        compare = holding_comparisons[asset_id]
        short = detailed_by_key[(asset_id, "0-30D")]
        year = detailed_by_key[(asset_id, "1Y")]
        holding_rows.append({
            "asset_id": asset_id,
            "asset_name": year["locked_contract"]["asset_name"],
            "identity": "HOLDING",
            "locked_forecasts": {"0-30D": short, "1Y": year},
            "relative_replacement_status": compare["label"],
            "mechanically_dominating_candidates": compare["mechanically_dominating_candidates"],
            "shared_risk_group": compare["shared_risk_group"],
            "comparison_basis": comparison["rule"]["comparison_basis"],
            "comparison_forecast_id": compare["forecast_id"],
            "comparison_boundary": comparison["rule"]["boundary"],
            "action_authorization": "NO_ACTION_AUTHORIZED",
            "plain_language_boundary": {
                "KEEP_EXISTING_HOLDING": "暂时保留只表示当前证据下没有更好的机械替换结果，不是永远持有。",
                "WATCH_REPLACEMENT": "值得继续和最终18比较，不表示现在卖出。",
                "INSUFFICIENT_EVIDENCE": "比较证据还不够，不表示这项资产没有预测。",
            }[compare["label"]],
        })

    final18_rows = []
    action_gate_inputs = []
    for asset_id in final18:
        identity = identity_by_id[asset_id]
        candidate = opportunity_by_id[asset_id]
        short = detailed_by_key[(asset_id, "0-30D")]
        year = detailed_by_key[(asset_id, "1Y")]
        questions = candidate["prediction_questions"]
        final18_row = {
            "asset_id": asset_id,
            "asset_name": identity["asset_name"],
            "identity": "FINAL_18_FOR_FORECAST_RESEARCH",
            "not_buy_list": True,
            "future_sector": identity["future_sector"],
            "Q1_future_business_change": questions["Q1_future_business_change"],
            "Q2_earnings_bridge": questions["Q2_earnings_bridge"],
            "Q3_priced_in": questions["Q3_priced_in"],
            "Q4_payoff_source": questions["Q4_payoff_source"],
            "Q5_disproof": questions["Q5_disproof"],
            "comparison_dimensions": candidate["comparison_dimensions"],
            "evidence_refs": candidate["evidence_refs"],
            "missing_inputs": candidate["missing_inputs"],
            "previous_identity": identity["previous_identity"],
            "legacy_candidate": identity["legacy_candidate"],
            "locked_forecasts": {"0-30D": short, "1Y": year},
            "prediction_research_status": "COMPLETE",
            "action_five_gate_status": "WAITING_GPT_JUDGMENT",
            "action_authorization": "NO_ACTION_AUTHORIZED",
        }
        final18_rows.append(final18_row)
        action_gate_inputs.append({
            "asset_id": asset_id,
            "asset_name": identity["asset_name"],
            "identity": "FINAL_18_FOR_FORECAST_RESEARCH",
            "prediction_research_status": "COMPLETE",
            "action_five_gate_status": "WAITING_GPT_JUDGMENT",
            "action_authorization": "NO_ACTION_AUTHORIZED",
            "gate_inputs": {
                "gate_1_future_sector_and_event": {
                    "future_sector": identity["future_sector"],
                    "future_business_change": questions["Q1_future_business_change"],
                    "short_event": short["locked_contract"].get("short_horizon_event"),
                },
                "gate_2_financial_and_guidance": {
                    "earnings_bridge": questions["Q2_earnings_bridge"],
                    "formal_accounting_start": year["locked_contract"].get("formal_accounting_start"),
                    "locked_forecast_evidence_refs": year["locked_contract"]["evidence_refs"],
                    "candidate_universe_evidence_refs": candidate["evidence_refs"],
                    "one_year_business_bridges": {
                        key: year["locked_contract"].get(key)
                        for key in (
                            "bear_earnings_or_value",
                            "base_earnings_or_value",
                            "bull_earnings_or_value",
                            "forecast_revenue_range",
                            "forecast_operating_margin_range",
                            "forecast_net_income_range",
                            "forecast_eps_range",
                            "forecast_fcf_range",
                            "forecast_nav_range",
                        )
                    },
                },
                "gate_3_valuation_and_payoff": {
                    "priced_in": questions["Q3_priced_in"],
                    "payoff_source": questions["Q4_payoff_source"],
                    "one_year_forecast_id": year["source_forecast_id"],
                    "one_year_scenarios": {
                        "bear": year["locked_contract"]["bear_price_range"],
                        "base": year["locked_contract"]["base_price_range"],
                        "bull": year["locked_contract"]["bull_price_range"],
                    },
                    "one_year_expected_return": year["locked_contract"]["expected_return_candidate"],
                },
                "gate_4_competition_and_disproof": {
                    "disproof": questions["Q5_disproof"],
                    "current_counterevidence": year["locked_contract"]["current_counterevidence"],
                    "future_invalidation_condition": year["locked_contract"]["future_invalidation_condition"],
                },
                "gate_5_replacement_comparison": candidate["comparison_dimensions"],
            },
            "gpt_judgment_fields": {
                "gate_1": None,
                "gate_2": None,
                "gate_3": None,
                "gate_4": None,
                "gate_5": None,
                "final_action_judgment": None,
            },
            "boundary": "只供GPT判断行动五关；不得由Codex形成买入、卖出、资金金额或订单。",
        })

    global_terms = {
        "business_direction": "公司生意未来会不会变好。",
        "price_direction": "从锁定参考价格出发，未来股价是否可能上涨。",
        "direction_difference": "两者可以不同：公司赚钱增加，但当前股价太贵，未来股价仍可能下跌。",
        "PDCA": "到约定日期再检查预测是否兑现，并记录错在哪里。",
        "contribution_percentage_point": "贡献百分点是某只持仓给整个账户收益增加或减少多少个百分点。",
    }
    plain_pairs = {}
    for asset_id in sorted(holdings + final18):
        pair = [
            by_key[(asset_id, horizon)]["chairman_plain_language"]
            for horizon in ("0-30D", "1Y")
        ]
        plain_pairs[asset_id] = hashlib.sha256(
            json.dumps(pair, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
    duplicate_plain_hashes = {
        digest for digest, count in Counter(plain_pairs.values()).items() if count > 1
    }
    plain_audit = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "global_term_explanations_appears_once": True,
        "asset_count": 42,
        "horizon_plain_language_count": sum(
            bool(c.get("chairman_plain_language")) for c in contracts
        ),
        "unique_asset_plain_language_pair_count": len(set(plain_pairs.values())),
        "generic_plain_language_only_asset_count": sum(
            digest in duplicate_plain_hashes for digest in plain_pairs.values()
        ),
        "asset_plain_language_fingerprints": plain_pairs,
        "rule": "资产专属说明逐字复制锁定合同，不使用通用模板替代。",
    }

    legacy_rules = {
        "run_id": run_id,
        "legacy_run_id": legacy["run_id"],
        "legacy_source": file_info(LEGACY_SOURCE),
        "legacy_identity": "LEGACY_STRUCTURE_TEMPLATE_ONLY",
        "allowed_legacy_fields": [
            {"jsonpath": "$.layers[*].layer", "mode": "COPY_FIXED_LAYER_NUMBER_ONLY"},
            {"jsonpath": "$.layers[*].name", "mode": "COPY_FIXED_LAYER_TITLE_ONLY"},
            {"jsonpath": "$.pdca", "mode": "SCHEMA_KEYS_ONLY_NO_HISTORICAL_VALUE_COPY"},
            {"jsonpath": "$.<top_level_key_order>", "mode": "LAYOUT_ORDER_REFERENCE_ONLY"},
        ],
        "forbidden_legacy_fields": [
            "$.accounts",
            "$.holdings",
            "$.research",
            "$.asset_events",
            "$.news",
            "$.layers[*].facts",
            "$.layers[*].source",
            "$.judgment",
            "$.judgment.account_target_paths",
            "$.portfolio_decisions",
            "$.production_refresh",
            "$.authorization",
            "$.time_boundary",
            "$.identity",
            "$.source_hashes",
            "$.holdings[*].positions",
            "$.holdings[*].current_price",
            "$.holdings[*].valuation",
            "$.research[*].quote",
            "$.research[*].valuation",
            "$.research[*].five_gates",
            "$.research[*].action",
        ],
        "enforcement": {
            "deny_precedence": True,
            "default_for_legacy_source": "DENY",
            "renderer_must_match_allowlist_path_exactly": True,
            "legacy_dynamic_value_copy_allowed": False,
            "legacy_final18_or_90_gate_copy_allowed": False,
        },
        "plain_language": "旧源只提供页面骨架和固定栏目名称；旧账户、旧价格、旧机会池、旧五关、旧目标桥、旧动作和旧新闻时间一律不能进入Current。",
    }

    forecast_as_of = locked["forecast_as_of_jst"]
    forecast_locked_at = locked["locked_at"]
    account_facts_latest = "2026-08-26T23:39:00+09:00"
    target_bridge_as_of = max(futu["generated_at_jst"], sbi["generated_at_jst"])
    nonforecast_as_of = legacy["evidence_cutoff_jst"]
    final_tail_end = tail_scan["scan_end"]
    time_boundaries = {
        "product_source_generated_at_jst": now.isoformat(),
        "forecast_as_of_jst": forecast_as_of,
        "forecast_locked_at_jst": forecast_locked_at,
        "account_facts_as_of_jst": account_facts_latest,
        "account_fact_detail": {
            "FUTU": "2026-08-26T19:03:51+09:00",
            "SBI_PERSONAL": sbi_evidence["account_facts"]["snapshot_time_jst"],
        },
        "target_bridge_as_of_jst": target_bridge_as_of,
        "nonforecast_context_as_of_jst": nonforecast_as_of,
        "final_news_tail_scan_end_jst": final_tail_end,
        "intended_product_as_of_jst": None,
        "intended_product_as_of_status": "PRE_HTML_FULL_PRODUCT_REFRESH_PENDING",
        "warning": "源文件生成于8月27日，不代表所有新闻、宏观、资金流、板块和账户事实都截至8月27日。",
    }

    def source_entry(path: Path, role: str) -> dict:
        return {**file_info(path), "role": role}

    render_manifest = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "intended_product_as_of_status": "PRE_HTML_FULL_PRODUCT_REFRESH_PENDING",
        "layers": [
            {
                "layer": 1,
                "name": "世界观",
                "current_source": [
                    source_entry(WORLDVIEW_RULE, "CURRENT_STATIC_RULE"),
                    source_entry(LEGACY_SOURCE, "LEGACY_STRUCTURE_TEMPLATE_ONLY"),
                ],
                "source_sha256": [sha(WORLDVIEW_RULE), sha(LEGACY_SOURCE)],
                "as_of": nonforecast_as_of,
                "field_allowlist": ["静态世界观定义", "层级编号", "固定栏目标题"],
                "field_denylist": ["旧事实", "旧新闻", "旧市场数值", "旧判断"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "STATIC_RULE_CURRENT / DYNAMIC_CONTEXT_REFRESH_PENDING",
            },
            {
                "layer": 2,
                "name": "战略",
                "current_source": [source_entry(STRATEGY_RULE, "CURRENT_STATIC_RULE")],
                "source_sha256": [sha(STRATEGY_RULE)],
                "as_of": mtime_jst(STRATEGY_RULE),
                "field_allowlist": ["国家战略定义", "传导栏目结构"],
                "field_denylist": ["旧当日政策判断", "旧资产动作"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "STATIC_RULE_CURRENT / DYNAMIC_CONTEXT_REFRESH_PENDING",
            },
            {
                "layer": 3,
                "name": "资金流",
                "current_source": [source_entry(FUND_FLOW_RULE, "CURRENT_STATIC_RULE")],
                "source_sha256": [sha(FUND_FLOW_RULE)],
                "as_of": mtime_jst(FUND_FLOW_RULE),
                "field_allowlist": ["资金流定义", "判定方法", "固定栏目"],
                "field_denylist": ["旧利率", "旧汇率", "旧资金方向结论"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "STATIC_RULE_CURRENT / DYNAMIC_CONTEXT_REFRESH_PENDING",
            },
            {
                "layer": 4,
                "name": "板块轮动",
                "current_source": [source_entry(SECTOR_RULE, "CURRENT_STATIC_RULE")],
                "source_sha256": [sha(SECTOR_RULE)],
                "as_of": mtime_jst(SECTOR_RULE),
                "field_allowlist": ["板块定义", "板块传导结构"],
                "field_denylist": ["旧板块激活状态", "旧行情", "旧动作"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "STATIC_RULE_CURRENT / DYNAMIC_CONTEXT_REFRESH_PENDING",
            },
            {
                "layer": 5,
                "name": "机会池",
                "current_source": [
                    source_entry(OPPORTUNITY, "CURRENT_FORECAST_RESEARCH_SOURCE"),
                    source_entry(FINAL18_IDENTITY, "CURRENT_FINAL18_IDENTITY"),
                    source_entry(LOCKED, "CURRENT_LOCKED_FORECAST"),
                ],
                "source_sha256": [sha(OPPORTUNITY), sha(FINAL18_IDENTITY), sha(LOCKED)],
                "as_of": forecast_as_of,
                "field_allowlist": ["最终18身份", "预测五问", "两期限锁定预测", "比较维度"],
                "field_denylist": ["旧18名单", "旧18的90关", "买入名单", "交易动作"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "CURRENT_FORECAST_RESEARCH / ACTION_GATE_JUDGMENT_PENDING",
            },
            {
                "layer": 6,
                "name": "持仓",
                "current_source": [
                    source_entry(LOCKED, "CURRENT_LOCKED_FORECAST"),
                    source_entry(FUTU, "CURRENT_FUTU_TARGET_BRIDGE"),
                    source_entry(SBI, "CURRENT_SBI_TARGET_BRIDGE"),
                    source_entry(COMPARISON, "CURRENT_RELATIVE_RESEARCH"),
                ],
                "source_sha256": [sha(LOCKED), sha(FUTU), sha(SBI), sha(COMPARISON)],
                "as_of": account_facts_latest,
                "field_allowlist": ["24项持仓预测", "账户事实", "相对比较标签", "完整目标贡献"],
                "field_denylist": ["旧账户金额", "旧数量", "旧Current价格", "旧静态目标桥", "交易动作"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "CURRENT_ACCOUNT_AND_FORECAST / PRE_HTML_ACCOUNT_REFRESH_PENDING",
            },
            {
                "layer": 7,
                "name": "PDCA与目标桥",
                "current_source": [
                    source_entry(REGISTRY, "CURRENT_PDCA_REGISTRY"),
                    source_entry(FUTU, "CURRENT_FUTU_TARGET_BRIDGE"),
                    source_entry(SBI, "CURRENT_SBI_TARGET_BRIDGE"),
                    source_entry(PDCA_RULE, "CURRENT_STATIC_RULE"),
                    source_entry(TARGET_RULE, "CURRENT_STATIC_RULE"),
                ],
                "source_sha256": [sha(REGISTRY), sha(FUTU), sha(SBI), sha(PDCA_RULE), sha(TARGET_RULE)],
                "as_of": target_bridge_as_of,
                "field_allowlist": ["132条登记册", "本批84条", "完整目标桥", "非持仓假设", "验证日期"],
                "field_denylist": ["旧静态收益", "旧目标金额", "未授权动作"],
                "refresh_required_before_html": True,
                "current_or_historical_status": "CURRENT / PRE_HTML_ACCOUNT_AND_CONTEXT_REFRESH_PENDING",
            },
        ],
    }

    current_registry_rows = [
        registry_by_id[c["forecast_id"]]
        for c in contracts
        if c["forecast_id"] in registry_by_id
    ]
    pdca_section = {
        "registry_total_count": len(registry_rows),
        "current_batch_count": len(current_registry_rows),
        "registry_source": file_info(REGISTRY),
        "entries": current_registry_rows,
        "plain_language": "PDCA是到约定日期再检查预测是否兑现，并记录错在哪里。",
    }
    action_gate_package = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "identity": "GPT_ACTION_FIVE_GATE_JUDGMENT_INPUT",
        "asset_count": len(action_gate_inputs),
        "assets": action_gate_inputs,
        "boundaries": ["NO_ACTION_AUTHORIZED", "NO_TRADE", "NO_ORDER"],
    }
    detailed_package = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "source_locked_forecast": file_info(LOCKED),
        "contract_count": len(detailed_rows),
        "contracts": detailed_rows,
    }
    holdings_package = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "source_comparison": file_info(COMPARISON),
        "count": len(holding_rows),
        "label_counts": dict(Counter(row["relative_replacement_status"] for row in holding_rows)),
        "assets": holding_rows,
    }
    final18_package = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "identity": "FINAL_18_FOR_FORECAST_RESEARCH",
        "not_buy_list": True,
        "count": len(final18_rows),
        "assets": final18_rows,
    }

    current_source = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "candidate_identity": "RENDERABLE_PREDICTIVE_COMPLETE_PRODUCT_SOURCE / NOT_RELEASED / NOT_TRADE_ACTION",
        "source_v1": {
            **file_info(V1_SOURCE),
            "status": "PREDICTIVE_SOURCE_MECHANICAL_PASS / SUPERSEDED_BY_V2_CURRENT",
        },
        "time_boundaries": time_boundaries,
        "global_term_explanations": global_terms,
        "render_source_manifest": render_manifest,
        "current_sections": {
            "detailed_locked_forecasts": detailed_rows,
            "holdings": holding_rows,
            "final18": final18_rows,
            "final18_action_five_gate_input": action_gate_package,
            "account_target_bridges": {
                "FUTU": futu,
                "SBI_PERSONAL": sbi,
                "nonposition_assumptions": nonposition,
            },
            "forecast_pdca": pdca_section,
        },
        "legacy_source_rules": legacy_rules,
        "boundaries": ["NO_HTML", "NO_PDF", "NO_RELEASE", "NO_DAILY_REPORT_OVERWRITE", "NO_TRADE", "NO_ORDER"],
    }

    payloads = {
        "V7_v2.0_预测型完整产品源_Current_v2.json": current_source,
        "84份锁定预测_完整产品内容接线.json": detailed_package,
        "24类持仓_绝对预测与相对替换完整接线.json": holdings_package,
        "最终18_预测五问及行动五关输入接线.json": final18_package,
        "最终18_行动五关_GPT判断输入.json": action_gate_package,
        "七层渲染源清单与时间边界.json": {
            "run_id": run_id,
            "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
            "time_boundaries": time_boundaries,
            "render_source_manifest": render_manifest,
        },
        "旧源字段白名单与黑名单.json": legacy_rules,
        "董事长大白话专属内容审计.json": plain_audit,
    }
    for name, value in payloads.items():
        dump(out / name, value)

    detailed_check = load(out / "84份锁定预测_完整产品内容接线.json")["contracts"]
    holding_check = load(out / "24类持仓_绝对预测与相对替换完整接线.json")["assets"]
    final18_check = load(out / "最终18_预测五问及行动五关输入接线.json")["assets"]
    action_check = load(out / "最终18_行动五关_GPT判断输入.json")["assets"]
    after_hashes = {str(path): sha(path) for path in immutable}

    core_groups = {
        "business": ("bear_business_assumption", "base_business_assumption", "bull_business_assumption"),
        "earnings_or_value": ("bear_earnings_or_value", "base_earnings_or_value", "bull_earnings_or_value"),
        "valuation": ("bear_valuation_assumption", "base_valuation_assumption", "bull_valuation_assumption"),
    }
    detailed_missing = 84 - len(detailed_check)
    business_missing = sum(
        any(not row["locked_contract"].get(key) for key in core_groups["business"])
        for row in detailed_check
    )
    bridge_missing = sum(
        any(not row["locked_contract"].get(key) for key in core_groups["earnings_or_value"])
        for row in detailed_check
    )
    valuation_missing = sum(
        any(not row["locked_contract"].get(key) for key in core_groups["valuation"])
        for row in detailed_check
    )
    evidence_missing = sum(not row["locked_contract"].get("evidence_refs") for row in detailed_check)
    plain_missing = sum(not row["locked_contract"].get("chairman_plain_language") for row in detailed_check)
    copied_id_mismatch = sum(
        row["source_forecast_id"] != row["locked_contract"]["forecast_id"]
        or row["source_canonical_sha256"] != row["locked_contract"]["canonical_content_sha256"]
        or not row["copied_without_business_change"]
        for row in detailed_check
    )
    holding_compare_missing = sum(
        not row.get("relative_replacement_status")
        or row.get("relative_replacement_status") == "NOT_EVALUATED_AS_ACTION"
        or "mechanically_dominating_candidates" not in row
        or "shared_risk_group" not in row
        or not row.get("comparison_basis")
        or not row.get("comparison_forecast_id")
        for row in holding_check
    )
    final18_questions_missing = sum(
        any(not row.get(key) for key in (
            "future_sector",
            "Q1_future_business_change",
            "Q2_earnings_bridge",
            "Q3_priced_in",
            "Q4_payoff_source",
            "Q5_disproof",
            "comparison_dimensions",
            "evidence_refs",
        ))
        for row in final18_check
    )
    action_status_missing = sum(
        row.get("prediction_research_status") != "COMPLETE"
        or row.get("action_five_gate_status") != "WAITING_GPT_JUDGMENT"
        or row.get("action_authorization") != "NO_ACTION_AUTHORIZED"
        for row in final18_check
    )
    legacy_forbidden_roots = {
        "accounts", "holdings", "research", "asset_events", "news", "layers",
        "judgment", "portfolio_decisions", "production_refresh", "authorization",
        "time_boundary", "identity",
    }
    legacy_forbidden_current_hits = len(legacy_forbidden_roots.intersection(current_source.keys()))

    def count_key(value, forbidden):
        if isinstance(value, dict):
            return sum(key in forbidden for key in value) + sum(count_key(item, forbidden) for item in value.values())
        if isinstance(value, list):
            return sum(count_key(item, forbidden) for item in value)
        return 0

    old_gate_hits = count_key(final18_check, {"five_gates", "old_five_gates", "legacy_90_gates", "action_decision"})
    required_time_keys = {
        "product_source_generated_at_jst",
        "forecast_as_of_jst",
        "forecast_locked_at_jst",
        "account_facts_as_of_jst",
        "target_bridge_as_of_jst",
        "nonforecast_context_as_of_jst",
        "final_news_tail_scan_end_jst",
        "intended_product_as_of_jst",
    }
    time_missing = len(required_time_keys.difference(time_boundaries))
    time_missing += sum(
        not layer.get("as_of") or "refresh_required_before_html" not in layer
        for layer in render_manifest["layers"]
    )
    trade_or_order_count = sum(
        row.get("action_authorization") != "NO_ACTION_AUTHORIZED"
        for row in holding_check + final18_check
    )
    html_count = len(list(out.glob("*.html")))
    pdf_count = len(list(out.glob("*.pdf")))
    action_gate_financial_input_missing = sum(
        not row["gate_inputs"]["gate_2_financial_and_guidance"].get("formal_accounting_start")
        or not row["gate_inputs"]["gate_2_financial_and_guidance"].get("locked_forecast_evidence_refs")
        for row in action_check
    )

    metrics = {
        "detailed_forecast_contract_missing_count": detailed_missing,
        "scenario_business_basis_missing_count": business_missing,
        "scenario_earnings_or_value_bridge_missing_count": bridge_missing,
        "scenario_valuation_basis_missing_count": valuation_missing,
        "evidence_refs_missing_count": evidence_missing,
        "asset_specific_plain_language_missing_count": plain_missing,
        "generic_plain_language_only_asset_count": plain_audit["generic_plain_language_only_asset_count"],
        "holding_relative_comparison_mapping_missing_count": holding_compare_missing,
        "final18_prediction_questions_missing_count": final18_questions_missing,
        "final18_action_gate_status_missing_count": action_status_missing,
        "legacy_forbidden_field_current_hit_count": legacy_forbidden_current_hits,
        "old_final18_gate_current_hit_count": old_gate_hits,
        "product_section_as_of_missing_count": time_missing,
        "locked_forecast_change_count": int(before_hashes[str(LOCKED)] != after_hashes[str(LOCKED)]),
        "registry_change_count": int(before_hashes[str(REGISTRY)] != after_hashes[str(REGISTRY)]),
        "target_bridge_change_count": sum(
            before_hashes[str(path)] != after_hashes[str(path)]
            for path in (FUTU, SBI, NONPOSITION)
        ),
        "trade_or_order_count": trade_or_order_count,
        "html_count": html_count,
        "pdf_count": pdf_count,
        "copied_contract_identity_mismatch_count": copied_id_mismatch,
        "action_gate_input_missing_count": 18 - len(action_check),
        "action_gate_financial_input_missing_count": action_gate_financial_input_missing,
    }
    label_counts = Counter(row["relative_replacement_status"] for row in holding_check)
    registry_mapping_mismatch = sum(
        registry_by_id.get(row["source_forecast_id"], {}).get("sha256")
        != row["source_canonical_sha256"]
        for row in detailed_check
    )
    gates = [
        ("84份完整合同全部接入", detailed_missing == 0 and copied_id_mismatch == 0),
        ("三情景业务依据完整", business_missing == 0),
        ("三情景盈利或价值桥完整", bridge_missing == 0),
        ("三情景估值依据完整", valuation_missing == 0),
        ("正式证据链接完整", evidence_missing == 0),
        ("84份资产专属大白话完整", plain_missing == 0),
        ("42项没有通用模板替代专属说明", plain_audit["generic_plain_language_only_asset_count"] == 0),
        ("24类持仓相对比较全部映射", holding_compare_missing == 0 and len(holding_check) == 24),
        ("持仓比较标签数量为3/17/4", label_counts == Counter({"KEEP_EXISTING_HOLDING": 3, "WATCH_REPLACEMENT": 17, "INSUFFICIENT_EVIDENCE": 4})),
        ("最终18预测五问完整", final18_questions_missing == 0 and len(final18_check) == 18),
        ("最终18行动五关状态完整", action_status_missing == 0),
        ("最终18行动五关判断输入18/18", len(action_check) == 18 and all(all(value is None for value in row["gpt_judgment_fields"].values()) for row in action_check)),
        ("最终18行动五关财务起点与证据18/18", action_gate_financial_input_missing == 0),
        ("旧源身份为纯结构模板", legacy_rules["legacy_identity"] == "LEGACY_STRUCTURE_TEMPLATE_ONLY"),
        ("旧源字段白名单黑名单可机器执行", legacy_rules["enforcement"]["default_for_legacy_source"] == "DENY" and len(legacy_rules["forbidden_legacy_fields"]) >= 10),
        ("Current没有旧源动态根字段", legacy_forbidden_current_hits == 0),
        ("Current没有旧最终18五关", old_gate_hits == 0),
        ("产品各层时间边界完整", time_missing == 0 and len(render_manifest["layers"]) == 7),
        ("产品日期没有冒充完成刷新", time_boundaries["intended_product_as_of_jst"] is None and time_boundaries["intended_product_as_of_status"] == "PRE_HTML_FULL_PRODUCT_REFRESH_PENDING"),
        ("登记册84条逐项匹配", registry_mapping_mismatch == 0),
        ("锁定预测未改变", before_hashes[str(LOCKED)] == after_hashes[str(LOCKED)] == "FFA84D49E20CFB0D15A5220E33A94547BA16683B2B4D8C4C731E549635F382B8"),
        ("登记册未改变", before_hashes[str(REGISTRY)] == after_hashes[str(REGISTRY)] == "93EA7C5AFC7AF0999A16EBA57EFFD4FDDF16D86A1AE1CFB82127CA30CE1B2051"),
        ("完整目标桥与非持仓假设未改变", metrics["target_bridge_change_count"] == 0),
        ("没有交易或订单", trade_or_order_count == 0),
        ("没有生成HTML或PDF", html_count == 0 and pdf_count == 0),
        ("正式日报未覆盖", before_hashes[str(DAILY_REPORT)] == after_hashes[str(DAILY_REPORT)]),
    ]
    all_pass = all(result for _, result in gates)
    hard_gate = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW" if all_pass else "INTERNAL_HARD_GATE_FAILED",
        "result": f"{sum(result for _, result in gates)}/{len(gates)} PASS",
        "gates": [
            {"gate": index, "check": name, "result": "PASS" if result else "FAIL"}
            for index, (name, result) in enumerate(gates, 1)
        ],
        "metrics": metrics,
        "post_html_only": [
            {"check": "HTML正文与v2源逐字段一致", "status": "POST_HTML_ONLY / NOT_EVALUATED_YET"},
            {"check": "HTML普通用户阅读与视觉质量", "status": "POST_HTML_ONLY / NOT_EVALUATED_YET"},
        ],
    }
    hard_gate_path = out / "预测型完整产品源最终硬闸报告.json"
    dump(hard_gate_path, hard_gate)
    if not all_pass:
        raise RuntimeError(json.dumps(hard_gate, ensure_ascii=False))

    dump(CURRENT_V2, current_source)
    dump(CURRENT_ALIAS, current_source)
    previous_pointer = load(CURRENT_POINTER) if CURRENT_POINTER.exists() else None
    pointer = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "current_stage": "PREDICTIVE_COMPLETE_PRODUCT_SOURCE_V2_REVIEW",
        "current_source": file_info(CURRENT_ALIAS),
        "current_source_v2": file_info(CURRENT_V2),
        "html_status": "NO_HTML_GENERATED",
        "pdf_status": "NO_PDF_GENERATED",
        "previous_pointer": {
            "value": previous_pointer,
            "status": "HISTORICAL_SUPERSEDED / NOT_CURRENT",
        },
        "boundaries": ["NO_HTML", "NO_PDF", "NO_RELEASE", "NO_DAILY_REPORT_OVERWRITE", "NO_TRADE", "NO_ORDER"],
    }
    dump(CURRENT_POINTER, pointer)

    artifact_paths = [
        out / name for name in payloads
    ] + [hard_gate_path, CURRENT_ALIAS, CURRENT_V2, CURRENT_POINTER]
    manifest = {
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "generated_at_jst": datetime.now(JST).isoformat(),
        "artifacts": [file_info(path) for path in artifact_paths],
        "immutable_source_hashes_before": before_hashes,
        "immutable_source_hashes_after": after_hashes,
        "html_count": html_count,
        "pdf_count": pdf_count,
        "release_count": 0,
        "trade_or_order_count": trade_or_order_count,
    }
    manifest_path = out / "提交身份与SHA256清单.json"
    dump(manifest_path, manifest)

    delivered = list(out.glob("*.json")) + [CURRENT_ALIAS, CURRENT_V2, CURRENT_POINTER]
    replacement_count = sum(path.read_bytes().count(b"\xef\xbf\xbd") for path in delivered)
    if replacement_count:
        raise RuntimeError(f"UTF-8 replacement bytes: {replacement_count}")
    print(json.dumps({
        "run_id": run_id,
        "status": "WAITING_GPT_PRODUCT_SOURCE_V2_AND_ACTION_GATE_REVIEW",
        "output_dir": str(out),
        "hard_gate": hard_gate["result"],
        "current_v2": file_info(CURRENT_V2),
        "manifest": file_info(manifest_path),
        "metrics": metrics,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
