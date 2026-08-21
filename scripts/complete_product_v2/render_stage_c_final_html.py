from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
STATUS = {
    "business_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "final_product_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "release_status": "NOT_AUTHORIZED",
    "current_executable": False,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_base_module(path: Path):
    module_name = "scripts.complete_product_v2.render_stage_c_rebuild"
    project_root = str(path.resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def numeric_judgment_map(final: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in final["numeric_holding_judgments"]}


def risk_judgment_map(final: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in final["risk_framework_holding_judgments"]}


def capability_holding_map(capability: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in capability["holdings_24"]}


def probability_text(probabilities: dict[str, int]) -> str:
    return (
        f"悲观{probabilities['bear']}%／基准{probabilities['base']}%／"
        f"乐观{probabilities['bull']}%"
    )


def scenario_summary(capability_row: dict[str, Any]) -> str:
    pricing = capability_row["valuation_or_risk_pricing"]
    values = pricing["scenario_values"]
    currency = pricing.get("currency") or "原报价币种"
    return (
        f"条件情景价格：悲观{values['bear']:,.2f}、基准{values['base']:,.2f}、"
        f"乐观{values['bull']:,.2f}（{currency}）。公式和算术可复算，参数是条件情景，"
        "不是收益承诺或自动交易线。"
    )


def merge_holdings(
    old_holdings: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    capability_map = capability_holding_map(capability)
    numeric_map = numeric_judgment_map(final)
    risk_map = risk_judgment_map(final)
    merged: list[dict[str, Any]] = []
    for source in old_holdings:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        cap = capability_map[symbol]
        item["account_fact"]["known_market_value_jpy"] = cap["market_value_jpy"]
        item["account_fact"]["weight_of_known_assets_pct"] = cap["known_asset_weight_pct"]
        item["account_fact"]["quantity_by_account"] = cap["quantity_by_account"]
        item["valuation"]["current_price"] = cap["current_price"].get("value")
        item["valuation"]["current_price_time"] = cap["current_price"].get("time")
        item["valuation"]["current_price_source"] = cap["current_price"].get("source")
        item["company_guidance_capability"] = cap["company_guidance"]
        item["current_reverse_evidence_capability"] = cap["reverse_evidence"]

        if symbol in numeric_map:
            judgment = numeric_map[symbol]
            probs = judgment["probability_pct"]
            item["valuation"]["final_control_answer"] = scenario_summary(cap)
            item["valuation"]["price_boundary"] = (
                "条件情景只用于检验盈利和估值变化；不单独支持加仓、减仓或目标承诺。"
            )
            item["forecast"]["control_confidence"] = probability_text(probs)
            item["forecast"]["confidence_boundary"] = final["probability_method"]["meaning"]
            item["action"]["unique_action"] = judgment["final_action_boundary"]
            item["action"]["reason"] = (
                f"总控采用条件情景并给出{probability_text(probs)}；"
                f"该资产对已知资产目标桥的概率加权贡献为"
                f"{judgment['expected_contribution_pp']:+.6f}个百分点。"
            )
            item["action"]["replacement"] = judgment["replacement_if_any"]
            item["action"]["target_contribution"] = (
                f"纳入可复算目标桥：{judgment['expected_contribution_pp']:+.6f}个百分点。"
            )
            item["final_capability_judgment"] = judgment
        else:
            judgment = risk_map[symbol]
            item["valuation"]["final_control_answer"] = (
                "本期不采用数值情景；只保留经总控批准的风险定价框架和验证条件。"
            )
            item["valuation"]["price_boundary"] = (
                "不提供伪精确收益区间、成功概率或目标贡献；不以估值支持新增动作。"
            )
            item["forecast"]["control_confidence"] = "不填伪精确概率"
            item["forecast"]["confidence_boundary"] = final["probability_method"]["risk_only_rule"]
            item["action"]["unique_action"] = judgment["final_action_boundary"]
            item["action"]["reason"] = (
                f"总控分类为{judgment['scenario_adoption']}；没有获批的数值情景，"
                "因此不进入数值目标贡献。"
            )
            item["action"]["replacement"] = judgment["replacement_if_any"]
            item["action"]["target_contribution"] = (
                "退出可复算目标桥；这里的退出不等于预期收益为0。"
            )
            item["final_capability_judgment"] = judgment
        merged.append(item)
    return merged


def merge_research(
    old_research: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    opportunity_input = {row["symbol"]: row for row in capability["priority_opportunity_gates"]}
    judgments = {row["symbol"]: row for row in final["priority_opportunity_judgments"]}
    merged: list[dict[str, Any]] = []
    for source in old_research:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        if symbol in judgments:
            decision = judgments[symbol]
            gate_input = opportunity_input[symbol]
            item["identity"] = f"研究优先级第{decision['rank']}；第五关未通过；当前不可执行。"
            item["retain_or_drop"] = "继续研究，不升级为可执行机会"
            item["valuation_or_risk_pricing"] = gate_input["gate_4_valuation_or_risk_pricing"]["conclusion_input"]
            item["replacement_target"] = decision["replacement"]
            item["executable_condition"] = decision["trigger"]
            item["next_review"] = gate_input["next_verification"]
            item["executable"] = False
            item["final_opportunity_judgment"] = decision
            gate5 = next(row for row in item["gates"] if row["gate"] == 5)
            gate5["status"] = "第五关未通过，继续研究"
            gate5["fact"] = (
                f"当前不值得替换现金或现有持仓。比较对象：{decision['replacement']}。"
                f"重新审查条件：{decision['trigger']}。失效条件：{decision['invalidation']}。"
            )
            gate5["missing"] = [
                "尚未同时闭合可复算风险收益、替换优势和正式执行条件。"
            ]
            gate5["evidence_complete"] = False
            item["formal_gate_stop"] = (
                f"第五关未通过；当前最大允许新增权重为{decision['max_weight_pct']}%。"
            )
        item["executable"] = False
        merged.append(item)
    return merged


def build_target_bridge(
    capability: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    cap_map = capability_holding_map(capability)
    numeric_map = numeric_judgment_map(final)
    risk_map = risk_judgment_map(final)
    portfolio = final["portfolio_judgment"]
    input_bridge = capability["target_contribution_bridge"]
    asset_rows: list[dict[str, Any]] = []
    for symbol, cap in cap_map.items():
        pricing = cap["valuation_or_risk_pricing"]
        if symbol in numeric_map:
            judgment = numeric_map[symbol]
            returns = pricing["scenario_returns"]
            probs = judgment["probability_pct"]
            asset_rows.append(
                {
                    "asset_id": symbol,
                    "name": cap["name"],
                    "known_weight_pct": cap["known_asset_weight_pct"],
                    "bear_return_pct": returns["bear"] * 100,
                    "base_return_pct": returns["base"] * 100,
                    "bull_return_pct": returns["bull"] * 100,
                    "probability": probability_text(probs),
                    "probability_weighted_contribution_pp": judgment["expected_contribution_pp"],
                    "status": "纳入可复算目标贡献桥",
                    "missing": "无；但概率是总控主观条件概率，不是历史频率。",
                }
            )
        else:
            judgment = risk_map[symbol]
            asset_rows.append(
                {
                    "asset_id": symbol,
                    "name": cap["name"],
                    "known_weight_pct": cap["known_asset_weight_pct"],
                    "bear_return_pct": None,
                    "base_return_pct": None,
                    "bull_return_pct": None,
                    "probability": "不填伪精确概率",
                    "probability_weighted_contribution_pp": None,
                    "status": "不进入数值目标贡献桥",
                    "missing": (
                        f"{judgment['scenario_adoption']}；只保留风险框架。"
                        "退出数值桥不表示预期收益为0。"
                    ),
                }
            )

    return {
        "boundary": portfolio["baseline_boundary"],
        "known_assets_jpy": portfolio["baseline_jpy"],
        "plus_40_observation_target_jpy": input_bridge["targets"]["plus_40_end_value_jpy"],
        "plus_40_gap_jpy": round(portfolio["baseline_jpy"] * 0.40, 2),
        "plus_100_observation_target_jpy": input_bridge["targets"]["plus_100_end_value_jpy"],
        "plus_100_gap_jpy": round(portfolio["baseline_jpy"] * 1.00, 2),
        "account_forward_baselines": {},
        "asset_rows": asset_rows,
        "quantified_asset_count": len(numeric_map),
        "quantified_weight_pct": portfolio["numeric_scenario_coverage_pct"],
        "unquantified_weight_pct": round(100 - portfolio["numeric_scenario_coverage_pct"], 6),
        "probability_weighted_contribution_pp": portfolio["numeric_scenario_probability_weighted_contribution_pp"],
        "plus_40_remaining_gap_pp": portfolio["plus40_feasibility"]["remaining_gap_pp"],
        "plus_100_remaining_gap_pp": portfolio["plus100_feasibility"]["remaining_gap_pp"],
        "plus_40_status": portfolio["plus40_feasibility"]["judgment"],
        "plus_100_status": portfolio["plus100_feasibility"]["judgment"],
        "cash_role": portfolio["cash_role"],
        "cash_assumption_boundary": portfolio["cash_assumption_boundary"],
        "risk_only_boundary": portfolio["risk_only_assets_assumption_boundary"],
        "required_change_plus40": portfolio["plus40_feasibility"]["required_change"],
        "required_change_plus100": portfolio["plus100_feasibility"]["required_change"],
        "next_review": portfolio["next_review"],
        "monthly_milestones": input_bridge["targets"]["monthly_milestones"],
    }


def render_target_bridge(target: dict[str, Any], base: Any) -> str:
    rows = []
    for row in target["asset_rows"]:
        def pct(value: Any) -> str:
            return "不提供" if value is None else f"{value:+.2f}%"

        contribution = (
            "不计入"
            if row["probability_weighted_contribution_pp"] is None
            else f"{row['probability_weighted_contribution_pp']:+.6f}个百分点"
        )
        rows.append(
            "<tr data-target-row=\"1\">"
            f"<td>{base.esc(row['asset_id'])}</td><td>{base.esc(row['name'])}</td>"
            f"<td>{row['known_weight_pct']:.2f}%</td><td>{pct(row['bear_return_pct'])}</td>"
            f"<td>{pct(row['base_return_pct'])}</td><td>{pct(row['bull_return_pct'])}</td>"
            f"<td>{base.esc(row['probability'])}</td><td>{contribution}</td>"
            f"<td>{base.esc(row['status'])}</td><td>{base.esc(row['missing'])}</td></tr>"
        )
    milestone_rows = "".join(
        f"<tr><td>{base.esc(row['date'])}</td><td>¥{base.fmt_num(row['plus_40_path_jpy'])}</td>"
        f"<td>¥{base.fmt_num(row['plus_100_path_jpy'])}</td><td>{base.esc(row['boundary'])}</td></tr>"
        for row in target["monthly_milestones"]
    )
    return f"""
    <div class="target-bars"><div><b>已知资产观察基线</b><span>¥{base.fmt_num(target['known_assets_jpy'])}</span><i style="width:50%"></i></div>
    <div><b>＋40%观察目标</b><span>¥{base.fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div>
    <div><b>＋100%压力目标</b><span>¥{base.fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{base.esc(target['boundary'])}</p>
    <div class="metric-grid"><article class="metric"><b>可复算覆盖</b><strong>{target['quantified_weight_pct']:.2f}%</strong><small>{target['quantified_asset_count']}项</small></article>
    <article class="metric"><b>概率加权组合贡献</b><strong>{target['probability_weighted_contribution_pp']:+.2f}个百分点</strong><small>只含九项获批数值情景</small></article>
    <article class="metric"><b>距离＋40%</b><strong>{target['plus_40_remaining_gap_pp']:.2f}个百分点</strong><small>路径尚未证明</small></article>
    <article class="metric"><b>距离＋100%</b><strong>{target['plus_100_remaining_gap_pp']:.2f}个百分点</strong><small>当前无可信可执行路径</small></article></div>
    <p><b>＋40%结论：</b>{base.esc(target['plus_40_status'])}</p>
    <p><b>＋100%结论：</b>{base.esc(target['plus_100_status'])}</p>
    <p><b>现金作用：</b>{base.esc(target['cash_role'])}</p>
    <p class="boundary">{base.esc(target['cash_assumption_boundary'])} {base.esc(target['risk_only_boundary'])}</p>
    <h4>要让路径成立，必须发生什么</h4><ul><li>{base.esc(target['required_change_plus40'])}</li><li>{base.esc(target['required_change_plus100'])}</li></ul>
    {base.details('逐资产收益—概率—仓位—贡献桥', '<table><thead><tr><th>代码</th><th>名称</th><th>已知权重</th><th>悲观收益</th><th>基准收益</th><th>乐观收益</th><th>情景概率</th><th>概率加权贡献</th><th>状态</th><th>边界</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>')}
    <h4>平滑复利观察里程碑</h4><table><thead><tr><th>日期</th><th>＋40%路径</th><th>＋100%路径</th><th>边界</th></tr></thead><tbody>{milestone_rows}</tbody></table>
    <p><b>下一次复核：</b>{base.esc(target['next_review'])}</p>
    """


def update_first_layer(model: dict[str, Any], final: dict[str, Any]) -> None:
    action = model["judgment"].setdefault("today_action", {})
    portfolio = final["portfolio_judgment"]
    action["headline"] = (
        "今天不新增仓位、不追高；保留现金选择权，等待正式五关和可复算替换优势。"
    )
    action["priority"] = [
        "现有持仓按24类唯一答案管理；不使用15%、20%或未经确认的30%固定硬线机械交易。",
        "AI核心持仓继续持有、不追价；任何新AI代理必须先证明比现金和现有核心更优。",
        "八项重点机会全部未通过第五关；研究顺序为MU→CEG→WDC→VRT→MUFG→SMFG→MRVL→瑞穗。",
        "若必须降低加密相关股票风险，复核顺序为COIN→CRCL→MSTR；本期不生成订单。",
        f"九项数值情景概率加权贡献约{portfolio['numeric_scenario_probability_weighted_contribution_pp']:+.2f}个百分点，仍不能证明＋40%路径成立。",
    ]
    action["cash_use_rule"] = portfolio["cash_role"]
    action["what_would_change_today_action"] = [
        portfolio["plus40_feasibility"]["required_change"],
        portfolio["plus100_feasibility"]["required_change"],
        f"下一次复核：{portfolio['next_review']}",
    ]


def replace_identity(html_text: str, run_id: str, generated_at: str) -> str:
    html_text = html_text.replace(
        "<title>★2026-08-20完整投研产品候选_v2.0_内容闸重建版</title>",
        "<title>★2026-08-20完整投研产品候选_v2.0_最终完整HTML</title>",
    )
    html_text = html_text.replace(
        "<h1>2026-08-20完整投研产品候选 v2.0｜内容闸重建版</h1>",
        "<h1>2026-08-20完整投研产品候选 v2.0｜最终完整HTML</h1>",
    )
    html_text = html_text.replace("返工生成时间", "最终HTML生成时间")
    html_text = html_text.replace("退回后重建，待总控全文复核", "最终完整HTML，待总控全文内容闸")
    html_text = html_text.replace(
        "第五关通过0只，可执行新增机会0只。MRVL是新加入的研究观察对象，不是正式机会。",
        "第五关通过0只，可执行新增机会0只。八项重点机会已完成总控排序，但均未被升级为正式机会。",
    )
    return html_text


def expected_contribution(cap_row: dict[str, Any], probabilities: dict[str, int]) -> float:
    contributions = cap_row["valuation_or_risk_pricing"]["scenario_contribution_pp"]
    return sum(contributions[key] * probabilities[key] / 100 for key in ("bear", "base", "bull"))


def visible_text(html_text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html_text)
    return html.unescape(text)


def semantic_qa(
    model: dict[str, Any], html_text: str, capability: dict[str, Any], final: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    visible = visible_text(html_text)
    cap_map = capability_holding_map(capability)
    numeric = numeric_judgment_map(final)
    risk = risk_judgment_map(final)
    opportunity = {row["symbol"]: row for row in final["priority_opportunity_judgments"]}
    recalculation_errors = []
    probability_errors = []
    for symbol, judgment in numeric.items():
        probs = judgment["probability_pct"]
        if sum(probs.values()) != 100:
            probability_errors.append(symbol)
        actual = expected_contribution(cap_map[symbol], probs)
        if abs(actual - judgment["expected_contribution_pp"]) > 0.00001:
            recalculation_errors.append({"symbol": symbol, "calculated": actual, "approved": judgment["expected_contribution_pp"]})
    recalculated_total = sum(expected_contribution(cap_map[s], numeric[s]["probability_pct"]) for s in numeric)
    approved_total = final["portfolio_judgment"]["numeric_scenario_probability_weighted_contribution_pp"]
    target = model["target_bridge"]
    priority_order = final["cross_asset_unique_answers"]["research_priority_order"]
    model_priority = [
        row["asset_id"]
        for row in sorted(
            (row for row in model["research_gates"] if row["asset_id"] in opportunity),
            key=lambda row: row["final_opportunity_judgment"]["rank"],
        )
    ]
    forbidden = [
        "等待GPT总控",
        "总控必须决定",
        "需GPT总控",
        "仅供总控",
        "path_proven=true",
        "当前组合可以证明＋40%路径成立",
    ]
    forbidden_hits = {term: visible.count(term) for term in forbidden if term in visible}
    checks = {
        "J01唯一判断源哈希": {
            "pass": final["status"] == "GPT_CONTROL_FINAL_JUDGMENT_COMPLETE",
            "detail": {"judgment_id": final["judgment_id"], "source_run_id": final["source_run_id"]},
        },
        "J02持仓覆盖与唯一答案": {
            "pass": len(model["holdings"]) == 24 and {x["asset_id"] for x in model["holdings"]} == set(numeric) | set(risk),
            "detail": {"holdings": len(model["holdings"]), "numeric": len(numeric), "risk_only": len(risk)},
        },
        "J03九项情景概率与逐项复算": {
            "pass": not probability_errors and not recalculation_errors,
            "detail": {"probability_sum_errors": probability_errors, "recalculation_errors": recalculation_errors},
        },
        "J04组合贡献复算": {
            "pass": abs(recalculated_total - approved_total) <= 0.00001 and abs(target["probability_weighted_contribution_pp"] - approved_total) <= 0.000001,
            "detail": {"calculated_pp": round(recalculated_total, 6), "approved_pp": approved_total},
        },
        "J05风险框架资产隔离": {
            "pass": len(risk) == 15 and all(not row["target_contribution_inclusion"] and row["probability"] == "NO_NUMERIC_PROBABILITY" for row in risk.values()),
            "detail": {"count": len(risk), "numeric_probability_count": 0},
        },
        "J06目标差额与可行性": {
            "pass": abs(target["plus_40_remaining_gap_pp"] - 31.583365) < 1e-9 and abs(target["plus_100_remaining_gap_pp"] - 91.583365) < 1e-9 and "尚未形成可执行路径" in target["plus_40_status"] and "没有可信可执行路径" in target["plus_100_status"],
            "detail": {"plus40_gap_pp": target["plus_40_remaining_gap_pp"], "plus100_gap_pp": target["plus_100_remaining_gap_pp"]},
        },
        "J07八项重点机会排序与停关": {
            "pass": model_priority == priority_order and all(not row["executable"] and row["final_opportunity_judgment"]["max_weight_pct"] == 0 for row in model["research_gates"] if row["asset_id"] in opportunity),
            "detail": {"expected_order": priority_order, "actual_order": model_priority, "gate5_pass": 0},
        },
        "J08研究池完整保留": {
            "pass": len(model["research_gates"]) == 18 and all(len(row["gates"]) == 5 for row in model["research_gates"]),
            "detail": {"research_objects": len(model["research_gates"]), "gate_rows": sum(len(row["gates"]) for row in model["research_gates"])},
        },
        "J09第一层与目标桥一致": {
            "pass": ("＋8.42个百分点" in visible or "+8.42个百分点" in visible) and "距离＋40%" in visible and "31.58个百分点" in visible and "当前无可信可执行路径" in visible,
            "detail": "第一层、目标驾驶舱和逐资产桥使用同一判断源。",
        },
        "J10过期待办清零": {"pass": not forbidden_hits, "detail": forbidden_hits},
        "J11冻结能力完整": {
            "pass": len(model["layers"]) == 7 and len(model["pdca"]["plain_records"]) == 57 and len(model["external_views"]) == model["external_view_expected_count"] and all(f'data-module="{name}"' in html_text for name in ("causal-chart", "risk-penetration", "replacement-engine", "shadow-portfolio", "issue-ledger")),
            "detail": {"layers": len(model["layers"]), "pdca_records": len(model["pdca"]["plain_records"]), "external_views": len(model["external_views"])},
        },
        "J12状态与PDF边界": {
            "pass": model["status"] == STATUS and not list(output_dir.glob("*.pdf")) and "未授权、未生成" in visible,
            "detail": {"status": model["status"], "pdf_count": len(list(output_dir.glob("*.pdf")))},
        },
        "J13UTF8与唯一HTML": {
            "pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8") and len(list(output_dir.glob("*.html"))) == 1,
            "detail": {"replacement_character_bytes": html_text.encode("utf-8").count(b"\xef\xbf\xbd"), "html_count": len(list(output_dir.glob("*.html")))},
        },
    }
    failures = [name for name, row in checks.items() if not row["pass"]]
    return {
        "schema_version": "V7-FINAL-HTML-SUBSTANTIVE-QA-1.0",
        "run_id": model["run_id"],
        "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "checks": checks,
        "pass_count": len(checks) - len(failures),
        "check_count": len(checks),
        "failures": failures,
        "status": "PASS_FOR_GPT_FULL_HTML_CONTENT_GATE" if not failures else "FAIL",
        "pdf_render_authorized": False,
        "independent_review_pass": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-renderer", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--capability-input", required=True, type=Path)
    parser.add_argument("--final-judgment", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise RuntimeError(f"output exists: {args.output_dir}")
    base = load_base_module(args.base_renderer)
    model = load_json(args.base_model)
    capability = load_json(args.capability_input)
    final = load_json(args.final_judgment)
    if sha256(args.final_judgment) != "D6AB5862EA2F2A8F1BC3EB0F7A6D8CB9AA93AB3659B96E4D1BBFFD687847B291":
        raise RuntimeError("final judgment SHA256 mismatch")
    if final["source_run_id"] != capability["run_id"]:
        raise RuntimeError("judgment and capability input run mismatch")
    if len(final["numeric_holding_judgments"]) != 9 or len(final["risk_framework_holding_judgments"]) != 15:
        raise RuntimeError("final judgment holding coverage mismatch")
    if len(final["priority_opportunity_judgments"]) != 8:
        raise RuntimeError("final judgment opportunity coverage mismatch")

    daily_before = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    args.output_dir.mkdir(parents=True, exist_ok=False)

    model["schema_version"] = "V7-COMPLETE-PRODUCT-MODEL-2.2-FINAL-HTML"
    model["run_id"] = args.run_id
    model["source_html_run_id"] = load_json(args.base_model)["run_id"]
    model["final_capability_input_run_id"] = capability["run_id"]
    model["final_capability_judgment_id"] = final["judgment_id"]
    model["final_capability_judgment_sha256"] = sha256(args.final_judgment)
    model["judgment_formed_at_jst"] = final["judged_at_jst"]
    model["generated_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
    model["status"] = STATUS
    model["holdings"] = merge_holdings(model["holdings"], capability, final)
    model["research_gates"] = merge_research(model["research_gates"], capability, final)
    model["target_bridge"] = build_target_bridge(capability, final)
    model["final_capability_judgment"] = final
    model["pdf_generated"] = False
    model["pdf_authorization_received"] = False
    update_first_layer(model, final)

    original_target_renderer = base.render_target_bridge
    base.render_target_bridge = lambda target: render_target_bridge(target, base)
    try:
        html_text = base.build_html(model)
    finally:
        base.render_target_bridge = original_target_renderer
    html_text = replace_identity(html_text, args.run_id, model["generated_at_jst"])
    html_path = args.output_dir / "★2026-08-20完整投研产品候选_v2.0_最终完整HTML.html"
    html_path.write_text(html_text, encoding="utf-8")

    write_json(args.output_dir / "01_最终完整产品机器模型.json", model)
    write_json(args.output_dir / "02_24类持仓总控唯一答案落地.json", {"count": len(model["holdings"]), "items": model["holdings"]})
    write_json(args.output_dir / "03_18只研究对象及八项优先机会落地.json", {"count": len(model["research_gates"]), "priority_count": 8, "gate5_pass": 0, "items": model["research_gates"]})
    write_json(args.output_dir / "04_收益概率仓位组合贡献桥.json", model["target_bridge"])

    qa = semantic_qa(model, html_text, capability, final, args.output_dir)
    write_json(args.output_dir / "05_最终完整HTML实质语义QA.json", qa)
    if qa["status"] != "PASS_FOR_GPT_FULL_HTML_CONTENT_GATE":
        raise RuntimeError(f"semantic QA failed: {qa['failures']}")

    daily_after = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    boundary = {
        "before": daily_before,
        "after": daily_after,
        "unchanged": daily_before == daily_after,
        "pdf_generated": False,
        "release": False,
        "trade_calls": 0,
        "order_calls": 0,
        "content_gate_status": "WAITING_FOR_GPT_FULL_HTML_REVIEW",
    }
    write_json(args.output_dir / "06_正式日报未覆盖及阶段边界.json", boundary)
    if not boundary["unchanged"]:
        raise RuntimeError("daily report changed")

    manifest_path = args.output_dir / "07_全部实物SHA256清单.json"
    items = []
    for path in sorted(args.output_dir.iterdir(), key=lambda p: p.name):
        if path.is_file() and path != manifest_path:
            items.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                    "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds"),
                }
            )
    write_json(
        manifest_path,
        {
            "run_id": args.run_id,
            "item_count": len(items),
            "items": items,
            "pdf_generated": False,
            "self_hash_excluded": True,
        },
    )

    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "html": str(html_path),
                "html_size": html_path.stat().st_size,
                "html_sha256": sha256(html_path),
                "holdings": len(model["holdings"]),
                "research_objects": len(model["research_gates"]),
                "numeric_holdings": len(final["numeric_holding_judgments"]),
                "risk_only_holdings": len(final["risk_framework_holding_judgments"]),
                "probability_weighted_contribution_pp": model["target_bridge"]["probability_weighted_contribution_pp"],
                "qa": qa["status"],
                "pdf_generated": False,
                "daily_report_unchanged": boundary["unchanged"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
