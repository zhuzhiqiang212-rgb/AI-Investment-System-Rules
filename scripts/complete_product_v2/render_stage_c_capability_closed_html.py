from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.complete_product_v2 import render_stage_c_final_html as legacy


JST = timezone(timedelta(hours=9))
STATUS = {
    "business_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "final_product_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "release_status": "NOT_AUTHORIZED",
    "current_executable": False,
}

GATE_STATUS = {
    "PASS": "本关通过",
    "PASS_WITH_RISK_FRAMEWORK": "使用风险定价框架通过",
    "FAIL_CURRENTLY": "当前未通过",
    "CONDITIONAL_PASS_NOT_TRIGGERED": "条件通过，但尚未触发",
    "FAIL_NOT_ACTIVATED": "未取得直接激活证据",
    "NOT_ENTERED": "前一关未通过，本关未进入",
}

PROBABILITY_SCORE = {"很低": 10, "较低": 30, "中等": 50, "较高": 70, "很高": 90}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def currency_for(symbol: str, cap: dict[str, Any]) -> str:
    pricing = cap.get("valuation_or_risk_pricing") or {}
    if pricing.get("currency"):
        return str(pricing["currency"])
    if symbol.startswith("JP.") or symbol in {"BTC", "ETH"}:
        return "JPY"
    if symbol.startswith("KRX."):
        return "KRW"
    return "USD"


def timezone_for(symbol: str) -> str:
    if symbol.startswith("JP.") or symbol in {"BTC", "ETH"}:
        return "JST"
    if symbol.startswith("KRX."):
        return "KST"
    return "ET（原始行情时间）"


def scenario_text(decision: dict[str, Any]) -> str:
    values = decision["scenario_values"]
    probs = decision["scenario_probability_pct"]
    currency = values["currency"]
    return (
        f"悲观{values['bear']:,.2f}、基准{values['base']:,.2f}、乐观{values['bull']:,.2f}（{currency}）；"
        f"对应条件概率为{probs['bear']}%／{probs['base']}%／{probs['bull']}%。"
        "这些是可复算的条件情景，不是收益承诺或自动交易线。"
    )


def clean_forward_evidence(cap: dict[str, Any]) -> dict[str, Any] | None:
    evidence = (cap.get("decision_input_v2") or {}).get("valuation_evidence")
    if not isinstance(evidence, dict):
        return None
    return {
        "source_title": evidence.get("source_title"),
        "publisher": evidence.get("publisher"),
        "source_url": evidence.get("source_url"),
        "retrieved_at_jst": evidence.get("retrieved_file_time_jst"),
        "sample_window": evidence.get("sample_window"),
        "dated_forward_pe_sequence": evidence.get("dated_forward_pe_sequence") or [],
        "selected_nearest_forward_eps": evidence.get("selected_forward_input") or {},
        "official_financial_source": evidence.get("official_financial_source"),
        "role_boundary": evidence.get("role_boundary"),
    }


def apply_holdings(
    old_holdings: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    rows: list[dict[str, Any]] = []
    for source in old_holdings:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        cap = copy.deepcopy(cap_map[symbol])
        decision = copy.deepcopy(decision_map[symbol])
        guidance = legacy.apply_guidance_override(symbol, cap["company_guidance"])
        account_names = "、".join(cap.get("quantity_by_account", {}).keys()) or "账户归属尚未确认"

        item["account_fact"]["known_market_value_jpy"] = cap["market_value_jpy"]
        item["account_fact"]["weight_of_known_assets_pct"] = cap["known_asset_weight_pct"]
        item["account_fact"]["quantity_by_account"] = cap["quantity_by_account"]
        item["account_fact"]["data_boundary"] = (
            f"数量来自{account_names}的最后有效账户实物；各账户原始日期见全账户表。"
            "这里只计算已知资产风险，不代表四账户同日完整净值。"
        )

        item["financial"]["guidance"] = legacy.guidance_summary(guidance)
        item["financial"]["guidance_evidence"] = copy.deepcopy(guidance)
        item["financial"]["guidance_evidence"]["reverse_impact"] = cap["reverse_evidence"].get("opposes")
        item["financial"]["guidance_evidence"]["update_condition"] = cap.get("update_condition")
        item["financial"]["quality"]["industry_explanation"] = legacy.quality_explanation(symbol)
        item["financial"]["quality"]["summary"] = (
            f"{item['financial']['quality'].get('summary', '')} {legacy.quality_explanation(symbol)}"
        ).strip()

        current = cap["current_price"]
        item["valuation"]["current_price"] = current.get("value")
        item["valuation"]["current_price_time"] = current.get("time")
        item["valuation"]["current_price_source"] = current.get("source")
        item["valuation"]["current_price_currency"] = currency_for(symbol, cap)
        item["valuation"]["current_price_timezone"] = timezone_for(symbol)
        item["valuation"]["current_price_type"] = "统一证据截止前最后可得报价"
        item["forecast"]["short_term"] = (
            f"观察窗口：{cap['decision_input_v2']['short_term']['window']}。"
            f"向上条件：{cap['decision_input_v2']['short_term']['up_condition']}"
            f"向下条件：{cap['decision_input_v2']['short_term']['down_condition']}"
        )
        item["forecast"]["medium_term"] = (
            f"观察窗口：{cap['decision_input_v2']['medium_term']['window']}。"
            f"向上条件：{cap['decision_input_v2']['medium_term']['up_condition']}"
            f"向下条件：{cap['decision_input_v2']['medium_term']['down_condition']}"
        )
        if decision["target_contribution_included"]:
            probs = decision["scenario_probability_pct"]
            item["forecast"]["control_confidence"] = (
                f"悲观情景{probs['bear']:.0f}%；基准情景{probs['base']:.0f}%；"
                f"乐观情景{probs['bull']:.0f}%"
            )
        else:
            item["forecast"]["control_confidence"] = (
                f"短期{decision['short_probability_band']}；中期{decision['medium_probability_band']}"
            )
        item["forecast"]["confidence_boundary"] = (
            "把握度使用本批次固定档位；只有完成外部验证后才进入校准统计，不能称为历史胜率。"
        )

        item["action"]["unique_action"] = decision["unique_action"]
        item["action"]["replacement"] = decision["cash_or_replacement"]
        item["action"]["reason"] = decision["framework"]
        item["action"]["target_contribution"] = (
            f"纳入目标桥：{decision['target_contribution_pp']:+.6f}个百分点。"
            if decision["target_contribution_included"]
            else "不进入数值目标贡献；这不表示预期收益为0。"
        )
        item["action"]["next_review"] = cap.get("update_condition") or item["action"].get("next_review")
        item["final_capability_judgment"] = decision

        forward = clean_forward_evidence(cap)
        if decision["target_contribution_included"]:
            item["valuation"]["classification"] = "可复算的条件估值情景"
            item["valuation"]["method"] = cap["valuation_or_risk_pricing"].get("method") or decision["framework"]
            item["valuation"]["method_reason"] = (
                "使用带日期的前瞻盈利和逐期前瞻市盈率序列形成条件情景；参数由本期唯一判断确定。"
            )
            item["valuation"]["forward_input"] = forward
            item["valuation"]["formula"] = {
                "公式": "每股条件价值 = 前瞻每股盈利 × 条件市盈率",
                "本期框架": decision["framework"],
            }
            item["valuation"]["final_control_answer"] = scenario_text(decision)
            item["valuation"]["price_boundary"] = (
                "公式和算术可复算，但倍数仍是条件情景假设；不单独构成买入、加仓或减仓依据。"
            )
            item["valuation"]["missing_plain"] = "本期数值输入、情景概率和动作边界已经形成唯一答案。"
            item["scenario_decision"] = decision
        else:
            item["valuation"]["classification"] = "非价格风险框架"
            item["valuation"]["method"] = decision["framework"]
            item["valuation"]["method_reason"] = "传统数值估值输入不足或不适用，本期只使用可核验风险条件管理。"
            item["valuation"]["forward_input"] = None
            item["valuation"]["formula"] = None
            item["valuation"]["final_control_answer"] = (
                "当前无法形成可靠数值估值，不提供数值收益范围、目标价或自动交易线。"
            )
            item["valuation"]["price_boundary"] = "只按风险事实、验证条件和唯一动作管理。"
            item["valuation"]["missing_plain"] = "未量化部分不按0处理，也不进入精确目标贡献。"
            item["scenario_decision"] = None

        item["company_guidance_capability"] = guidance
        item["current_reverse_evidence_capability"] = cap["reverse_evidence"]
        item["precise_evidence_roles"] = legacy.precise_evidence_roles(
            item, cap, bool(decision["target_contribution_included"])
        )
        item.pop("evidence_roles", None)
        rows.append(item)
    return rows


def apply_research(
    old_research: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    cap_map = {row["asset_id"]: row for row in capability["research_18"]}
    decision_map = {row["asset_id"]: row for row in final["research_judgments"]}
    rows: list[dict[str, Any]] = []
    for source in old_research:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        cap = copy.deepcopy(cap_map[symbol])
        decision = copy.deepcopy(decision_map[symbol])
        item["identity"] = "研究观察对象；当前不可执行。"
        item["current_quote"] = cap["current_quote"]
        item["executable"] = False
        item["final_opportunity_judgment"] = decision
        item["replacement_target"] = decision.get("replacement_object") or "没有形成替换对象"
        item["executable_condition"] = decision.get("catalyst") or "等待直接证据和正式触发"
        item["next_review"] = decision.get("decision_time") or "下一次正式财报或公司公告"
        item["retain_or_drop"] = decision.get("reason") or "研究尚未闭合"
        item["short_term"] = f"把握度：{decision.get('probability_band') or '不提供'}。观察催化剂：{decision.get('catalyst') or '尚未取得'}。"
        item["medium_term"] = f"见分晓时间：{item['next_review']}。"

        gates: list[dict[str, Any]] = []
        for index, cap_gate in enumerate(cap["gates"], 1):
            code = decision["gate_decisions"][index - 1]
            gate = copy.deepcopy(cap_gate)
            gate["gate"] = index
            gate["status"] = GATE_STATUS[code]
            source_record = gate.get("source") if isinstance(gate.get("source"), dict) else None
            gate["evidence_complete"] = code in {"PASS", "PASS_WITH_RISK_FRAMEWORK"}
            if index == 5:
                gate["fact"] = (
                    f"第五关结论：{decision['gate5']}。原因：{decision.get('reason') or '尚未闭合'}。"
                    f"与现金或持仓比较：{decision.get('replacement_object') or '没有形成替换对象'}。"
                    f"催化剂：{decision.get('catalyst') or '尚未取得'}。"
                    f"重新判断时间：{decision.get('decision_time') or '下一次正式披露'}。"
                )
            gate["missing"] = [] if gate["evidence_complete"] else [
                "本关尚未形成可执行结论；只有取得对应正式证据或触发条件后才重新判断。"
            ]
            if code == "NOT_ENTERED":
                gate["source"] = None
                gate["fact"] = "前一关未通过，本关未进入；没有用后续材料倒填通过。"
            elif source_record:
                gate["source"] = source_record
            gates.append(gate)
        item["gates"] = gates
        first_not_pass = next(
            (idx for idx, code in enumerate(decision["gate_decisions"], 1) if code not in {"PASS", "PASS_WITH_RISK_FRAMEWORK"}),
            5,
        )
        item["formal_gate_stop"] = f"第{first_not_pass}关：{GATE_STATUS[decision['gate_decisions'][first_not_pass - 1]]}"
        item["valuation_or_risk_pricing"] = str(cap["gates"][3].get("fact") or "本关未进入")
        rows.append(item)
    return rows


def build_target_bridge(
    capability: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    portfolio = final["portfolio_target_judgment"]
    asset_rows = []
    for symbol, cap in cap_map.items():
        decision = decision_map[symbol]
        pricing = cap["valuation_or_risk_pricing"]
        row = {
            "asset_id": symbol,
            "name": cap["name"],
            "known_weight_pct": cap["known_asset_weight_pct"],
            "framework": decision["framework"],
            "probability_band": (
                f"悲观{decision['scenario_probability_pct']['bear']:.0f}%／"
                f"基准{decision['scenario_probability_pct']['base']:.0f}%／"
                f"乐观{decision['scenario_probability_pct']['bull']:.0f}%"
                if decision["target_contribution_included"]
                else f"短期{decision['short_probability_band']}／中期{decision['medium_probability_band']}"
            ),
            "target_contribution_included": decision["target_contribution_included"],
            "target_contribution_pp": decision["target_contribution_pp"],
            "unique_action": decision["unique_action"],
            "cash_or_replacement": decision["cash_or_replacement"],
            "scenario_values": decision.get("scenario_values"),
            "scenario_probability_pct": decision.get("scenario_probability_pct"),
            "expected_return_pct": decision.get("expected_return_pct"),
            "input_boundary": pricing.get("boundary"),
        }
        asset_rows.append(row)
    return {
        "boundary": "8月18日已知资产前瞻观察基线；不代表2026年1月1日起的实际年度完成度。",
        "known_assets_jpy": portfolio["known_asset_baseline_jpy"],
        "plus_40_observation_target_jpy": portfolio["plus_40_target_jpy"],
        "plus_100_observation_target_jpy": portfolio["plus_100_target_jpy"],
        "quantified_asset_count": 9,
        "quantified_weight_pct": portfolio["numeric_valuation_weight_pct"],
        "unquantified_weight_pct": portfolio["unquantified_residual_weight_pct"],
        "probability_weighted_contribution_pp": portfolio["numeric_scenario_contribution_pp"]["probability_weighted"],
        "scenario_contribution_pp": portfolio["numeric_scenario_contribution_pp"],
        "plus_40_status": portfolio["plus_40_path_status"],
        "plus_100_status": portfolio["plus_100_path_status"],
        "plain_language_reason": portfolio["plain_language_reason"],
        "residual_required_average_return_pct": portfolio["residual_required_average_return_pct"],
        "required_monthly_compound_pct": portfolio["required_monthly_compound_from_august_18_pct"],
        "cash_role": portfolio["cash_opportunity_cost"],
        "fallback_route": portfolio["fallback_route"],
        "monthly_milestones": portfolio["monthly_milestones"],
        "next_review": portfolio["next_full_review_jst"],
        "asset_rows": asset_rows,
        "unquantified_is_zero": False,
    }


def apply_pdca(model: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    audit = legacy.rebuild_pdca_quality(model)
    predictions = copy.deepcopy(final["pdca_new_predictions"])
    policy = copy.deepcopy(final["probability_policy"])
    model["pdca"]["body_summary"]["new_predictions"] = predictions
    model["pdca"]["body_summary"]["new_quality_baseline"] = predictions
    model["pdca"]["body_summary"]["new_quality_baseline_count"] = len(predictions)
    model["pdca"]["body_summary"]["probability_policy"] = policy
    audit["new_quality_baseline_count"] = len(predictions)
    audit["new_quality_baseline"] = predictions
    audit["probability_policy"] = policy
    return audit


def apply_first_layer(model: dict[str, Any], final: dict[str, Any]) -> None:
    action = model["judgment"].setdefault("today_action", {})
    market = final["market_and_policy_judgment"]
    portfolio = final["portfolio_target_judgment"]
    action["headline"] = "今天不强行新增仓位；按24类持仓唯一答案管理，18只研究对象继续等待正式触发。"
    action["priority"] = [
        "9项数值情景只作为可复算条件估值；现有组合的概率加权贡献约8.42个百分点，尚不能证明＋40%路径成立。",
        "其余15类资产使用非价格风险框架；未量化部分不按0处理，也不为追求目标强行补数。",
        "18只研究对象均不可执行；条件通过但未触发的对象仍不得生成订单。",
        "AI同一驱动已经较高；Marvell与Google合作强化定制芯片竞争，新增AI代理必须先证明优于现金和现有核心。",
        "日本银行股等待正式政策、净息差和信用成本同时验证；媒体加息预期不是已经加息。",
    ]
    action["cash_use_rule"] = market["cash_role"]
    action["what_would_change_today_action"] = [
        portfolio["fallback_route"],
        f"下一次全量复核：{portfolio['next_full_review_jst']}",
    ]


def rebuild_traceability(model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for layer in model["layers"]:
        details = []
        for fact in layer.get("facts", [])[:4]:
            details.append({
                "title": fact.get("title") or "事实标题已登记",
                "publisher": fact.get("publisher") or fact.get("source_name") or "发布机构见原文",
                "published_at": fact.get("published_at") or fact.get("data_date") or "日期见原文",
                "url": fact.get("url"),
                "supports": fact.get("supports") or fact.get("fact"),
                "cannot_prove": fact.get("cannot_prove") or "单一事实不能独立形成交易动作。",
            })
        rows.append({
            "conclusion": f"第{layer['layer']}层：{layer['name']}",
            "plain_answer": layer["final_judgment"],
            "evidence_details": details,
            "rule": "七层必须按顺序传导，反向证据和推翻条件必须同时保留。",
            "boundary": layer["reversal"],
        })
    for item in model["holdings"]:
        roles = [role for role in item.get("precise_evidence_roles", []) if role.get("role") in {"财务事实", "公司指引或替代指引", "估值输入", "反向证据"}]
        rows.append({
            "conclusion": f"{item['asset_id']}｜{item['name']}唯一动作",
            "plain_answer": item["action"]["unique_action"],
            "evidence_details": [{
                "title": role.get("title"), "publisher": role.get("publisher"),
                "published_at": role.get("published_at"), "url": role.get("url"),
                "supports": role.get("supports"), "cannot_prove": role.get("cannot_prove"),
            } for role in roles],
            "rule": "账户事实、财务、估值、事件和反向证据分角色使用。",
            "boundary": item["action"]["invalidation"],
        })
    for item in model["research_gates"]:
        evidence = []
        for gate in item["gates"]:
            source = gate.get("source") if isinstance(gate.get("source"), dict) else None
            if source:
                evidence.append({
                    "title": source.get("title"), "publisher": source.get("publisher"),
                    "published_at": source.get("published_at"), "url": source.get("url"),
                    "supports": gate.get("fact"), "cannot_prove": "不能越过前一关，也不自动形成交易动作。",
                })
        rows.append({
            "conclusion": f"{item['asset_id']}｜{item['name']}五关结论",
            "plain_answer": item["retain_or_drop"],
            "evidence_details": evidence,
            "rule": "正式五关按顺序执行；条件通过但未触发仍不可执行。",
            "boundary": item["next_review"],
        })
    return rows


PLAIN_FIELD_NAMES = {
    "method": "估值或风险定价方法",
    "current_price": "当前价格",
    "price_time": "报价时间",
    "pe_ratio_market_snapshot": "市盈率市场快照",
    "pb_ratio_market_snapshot": "市净率市场快照",
    "boundary": "使用边界",
    "period": "数据期间",
    "value": "数值",
    "source": "来源",
}


def plain_value(value: Any) -> str:
    if value is None or value == "":
        return "尚未取得"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, dict):
        return "；".join(
            f"{PLAIN_FIELD_NAMES.get(str(key), str(key).replace('_', ' '))}：{plain_value(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return "；".join(plain_value(item) for item in value) if value else "尚未取得"
    return str(value)

def render_holding_card(item: dict[str, Any], base: Any) -> str:
    financial = item["financial"]
    guidance = item["financial"]["guidance_evidence"]
    scenario = item.get("scenario_decision")
    if scenario:
        forward = item["valuation"].get("forward_input") or {}
        selected = forward.get("selected_nearest_forward_eps") or {}
        values = scenario["scenario_values"]
        probs = scenario["scenario_probability_pct"]
        sequence_rows = "".join(
            f"<tr><td>{base.esc(row.get('period'))}</td><td>{base.fmt_num(row.get('eps'), 5)}</td><td>{base.fmt_num(row.get('forward_pe'), 3)}</td></tr>"
            for row in forward.get("dated_forward_pe_sequence", [])
        )
        valuation_body = f"""
        <p><b>方法：</b>{base.esc(item['valuation']['method'])}</p>
        <p><b>前瞻输入：</b>{base.fmt_num(selected.get('eps'), 5)}｜期间{base.esc(selected.get('period'))}｜分析师数量{base.fmt_num(selected.get('analyst_count'))}</p>
        <p><b>来源：</b>{base.esc(forward.get('source_title'))}｜{base.esc(forward.get('publisher'))}｜{base.link(forward.get('source_url'))}</p>
        <table><thead><tr><th>情景</th><th>条件价格</th><th>概率</th></tr></thead><tbody>
        <tr><td>悲观</td><td>{base.fmt_num(values['bear'],2)} {base.esc(values['currency'])}</td><td>{probs['bear']}%</td></tr>
        <tr><td>基准</td><td>{base.fmt_num(values['base'],2)} {base.esc(values['currency'])}</td><td>{probs['base']}%</td></tr>
        <tr><td>乐观</td><td>{base.fmt_num(values['bull'],2)} {base.esc(values['currency'])}</td><td>{probs['bull']}%</td></tr></tbody></table>
        <p><b>复算公式：</b>{base.esc(scenario['framework'])}</p>
        <p><b>概率加权预期收益：</b>{scenario['expected_return_pct']:+.3f}%；<b>组合贡献：</b>{scenario['target_contribution_pp']:+.6f}个百分点。</p>
        <p class="boundary">公式和算术可复算，但倍数是条件情景假设，不是收益承诺或自动交易线。</p>
        {base.details('逐期前瞻市盈率样本', '<table><thead><tr><th>期间</th><th>每股盈利</th><th>前瞻市盈率</th></tr></thead><tbody>'+sequence_rows+'</tbody></table>')}
        """
    else:
        valuation_body = (
            f"<p><b>风险定价框架：</b>{base.esc(item['valuation']['method'])}</p>"
            "<p>当前无法形成可靠数值估值，不提供数值收益范围、目标价或自动交易线。</p>"
            "<p class='boundary'>未量化不表示预期收益为0；本期只按风险事实、验证条件和唯一动作管理。</p>"
        )
    facts = "".join(f"<li>{base.esc(value)}</li>" for value in guidance.get("facts", [])) or "<li>该资产不适用企业业绩指引。</li>"
    source = base.link(guidance.get("url")) if guidance.get("url") else "<span class='muted'>没有独立外部链接，已隔离用途。</span>"
    body = f"""
    <div class="asset-summary"><div><b>唯一动作</b><strong>{base.esc(item['action']['unique_action'])}</strong></div>
    <div><b>已知账户权重</b><strong>{item['account_fact']['weight_of_known_assets_pct']:.2f}%</strong></div>
    <div><b>下次复核</b><strong>{base.esc(item['action']['next_review'])}</strong></div></div>
    <p><b>为什么：</b>{base.esc(item['action']['reason'])}</p>
    <div class="research-grid">
    <article><h4>业务和赚钱方式</h4><p>{base.esc(item['business_model'])}</p><p>{base.esc(item['how_it_makes_money'])}</p><p><b>增长驱动：</b>{base.esc(item['growth_drivers'])}</p></article>
    <article><h4>账户事实</h4><p>{base.esc(base.account_quantity_text(item['account_fact']['quantity_by_account']))}</p><p>已知市值：¥{base.fmt_num(item['account_fact']['known_market_value_jpy'])}</p><p>{base.esc(item['account_fact']['data_boundary'])}</p></article>
    <article><h4>公司正式指引</h4><p>{base.esc(guidance.get('plain_status'))}｜{base.esc(guidance.get('period'))}</p><ul>{facts}</ul><p>{base.esc(guidance.get('source_title'))}｜{base.esc(guidance.get('publisher'))}<br>{source}</p></article>
    <article><h4>护城河与竞争</h4><p>{base.esc(item['moat_and_competition']['moat'])}</p><p><b>竞争者：</b>{base.esc(item['moat_and_competition']['competitors'])}</p><p><b>反向竞争证据：</b>{base.esc(item['moat_and_competition']['reverse_competition'])}</p></article>
    <article><h4>估值或风险定价</h4>{valuation_body}</article>
    <article><h4>双时间尺度</h4><p><b>短期：</b>{base.esc(item['forecast']['short_term'])}</p><p><b>中期：</b>{base.esc(item['forecast']['medium_term'])}</p><p><b>把握度：</b>{base.esc(item['forecast']['control_confidence'])}</p></article>
    <article><h4>催化剂、反方与失效</h4><p><b>催化剂：</b>{base.esc(item['action']['catalysts'])}</p><p><b>当前反向证据：</b>{base.esc(item['action']['current_reverse_evidence'])}</p><p><b>未来失效条件：</b>{base.esc(item['action']['invalidation'])}</p></article>
    <article><h4>替换和目标作用</h4><p><b>替换比较：</b>{base.esc(item['action']['replacement'])}</p><p><b>目标作用：</b>{base.esc(item['action']['target_contribution'])}</p></article>
    </div>
    {base.details('正式财务字段与原文定位', (base.render_period_blocks(financial) if financial.get('period_blocks') else f'<table><thead><tr><th>字段</th><th>数值</th><th>状态</th></tr></thead><tbody>{base.value_rows(financial.get("fields", dict()), financial.get("currency"))}</tbody></table>') + (f'<p>{base.esc(financial.get("source_title"))}｜{base.esc(financial.get("publisher"))}｜{base.link(financial.get("url"))}</p>' if financial.get('url') else '<p>该资产不适用企业财务口径。</p>'))}
    {base.details('证据角色与使用边界', legacy.render_precise_evidence_roles(item, base))}
    """
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-holding="{base.esc(item["asset_id"])}"')


def render_gate_card(item: dict[str, Any], base: Any) -> str:
    rows = []
    for gate in item["gates"]:
        source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
        source_html = (
            f"<b>{base.esc(source.get('title'))}</b><br>{base.esc(source.get('publisher'))}<br>{base.link(source.get('url'))}"
            if source.get("url") else "<span class='muted'>本关没有独立可点击原文，已按未取得处理。</span>"
        )
        missing = "<span class='ok'>本关输入已取得。</span>" if gate.get("evidence_complete") else "<span class='missing'>" + base.esc("；".join(gate.get("missing") or [])) + "</span>"
        rows.append(
            f"<tr data-gate-row='1'><td>第{gate['gate']}关</td><td>{base.esc(gate['status'])}</td><td>{base.esc(plain_value(gate['fact']))}</td><td>{source_html}</td><td>{missing}</td></tr>"
        )
    decision = item["final_opportunity_judgment"]
    body = f"""
    <div class="asset-summary"><div><b>身份</b><strong>{base.esc(item['identity'])}</strong></div><div><b>停关</b><strong>{base.esc(item['formal_gate_stop'])}</strong></div><div><b>可执行</b><strong>否</strong></div></div>
    <p><b>本期结论：</b>{base.esc(decision.get('gate5'))}。{base.esc(decision.get('reason'))}</p>
    <p><b>统一行情：</b>{base.fmt_num(item['current_quote'].get('last_price'),4)}｜{base.esc(item['current_quote'].get('update_time'))}｜{base.esc(item['current_quote'].get('source'))}</p>
    <table><thead><tr><th>正式关卡</th><th>结论</th><th>公司具体事实</th><th>原文</th><th>缺口或边界</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p><b>概率档位：</b>{base.esc(decision.get('probability_band') or '不提供')}</p><p><b>催化剂：</b>{base.esc(decision.get('catalyst'))}</p>
    <p><b>与现金或持仓比较：</b>{base.esc(decision.get('replacement_object'))}</p><p><b>见分晓时间：</b>{base.esc(decision.get('decision_time'))}</p>
    """
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-research="{base.esc(item["asset_id"])}"')


def render_target_bridge(target: dict[str, Any], base: Any) -> str:
    rows = []
    for row in target["asset_rows"]:
        if row["target_contribution_included"]:
            values = row["scenario_values"]
            probs = row["scenario_probability_pct"]
            scenario = f"悲观{values['bear']:,.2f}／基准{values['base']:,.2f}／乐观{values['bull']:,.2f} {values['currency']}"
            probability = f"{probs['bear']}%／{probs['base']}%／{probs['bull']}%"
            contribution = f"{row['target_contribution_pp']:+.6f}个百分点"
        else:
            scenario = "不提供数值情景"
            probability = row["probability_band"]
            contribution = "未量化，不按0处理"
        rows.append(
            f"<tr data-target-row='{base.esc(row['asset_id'])}'><td>{base.esc(row['asset_id'])}</td><td>{base.esc(row['name'])}</td><td>{row['known_weight_pct']:.2f}%</td><td>{base.esc(scenario)}</td><td>{base.esc(probability)}</td><td>{base.esc(contribution)}</td><td>{base.esc(row['unique_action'])}</td></tr>"
        )
    checkpoints = "".join(
        f"<tr><td>{base.esc(row['check_date'])}</td><td>{base.esc(row['check'])}</td></tr>"
        for row in target["monthly_milestones"]
    )
    return f"""
    <div class="target-bars"><div><b>已知资产观察基线</b><span>¥{base.fmt_num(target['known_assets_jpy'])}</span><i style="width:50%"></i></div>
    <div><b>＋40%观察目标</b><span>¥{base.fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div>
    <div><b>＋100%压力目标</b><span>¥{base.fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{base.esc(target['boundary'])}</p>
    <div class="metric-grid"><article class="metric"><b>数值情景覆盖</b><strong>{target['quantified_weight_pct']:.2f}%</strong><small>9项可复算条件情景</small></article>
    <article class="metric"><b>概率加权贡献</b><strong>{target['probability_weighted_contribution_pp']:+.2f}个百分点</strong><small>只覆盖已量化部分</small></article>
    <article class="metric"><b>＋40%路径</b><strong>尚未证明</strong><small>剩余资产平均需贡献{target['residual_required_average_return_pct']['for_plus_40']:.2f}%</small></article>
    <article class="metric"><b>＋100%路径</b><strong>当前不可行</strong><small>剩余资产平均需贡献{target['residual_required_average_return_pct']['for_plus_100']:.2f}%</small></article></div>
    <p>{base.esc(target['plain_language_reason'])}</p><p><b>现金机会成本：</b>{base.esc(target['cash_role'])}</p><p><b>落后时的替代路线：</b>{base.esc(target['fallback_route'])}</p>
    {base.details('24类资产贡献明细', '<table><thead><tr><th>代码</th><th>名称</th><th>权重</th><th>三情景或框架</th><th>概率</th><th>组合贡献</th><th>唯一动作</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>')}
    <h4>复核里程碑</h4><table><thead><tr><th>日期</th><th>检查内容</th></tr></thead><tbody>{checkpoints}</tbody></table><p><b>下一次全量复核：</b>{base.esc(target['next_review'])}</p>
    """


def render_pdca(pdca: dict[str, Any], base: Any) -> str:
    summary = pdca["body_summary"]
    predictions = summary.get("new_predictions") or []
    rows = "".join(
        f"<tr><td>{index}</td><td>{base.esc(row['statement'])}</td><td>{row['probability_pct']}%</td><td>{base.esc(row['success_definition'])}</td><td>{base.esc(row['counterfactual'])}</td><td>{base.esc(row['verification_date'])}</td><td>{base.esc(row['evidence_role'])}</td></tr>"
        for index, row in enumerate(predictions, 1)
    )
    bins = "".join(
        f"<tr><td>{base.esc(row['label'])}</td><td>{base.esc(row['range_pct'])}%</td><td>{row['scoring_value_pct']}%</td></tr>"
        for row in summary["probability_policy"]["approved_bins"]
    )
    return f"""
    <p><b>历史记录：</b>57条旧记录保留为历史缺陷账本，因缺少逐条可点击外部证据，全部退出预测能力统计。</p>
    <p><b>本期改变：</b>新建{len(predictions)}条预测，每条锁定概率、成功定义、反事实、证据角色和验证时间。</p>
    <table><thead><tr><th>序号</th><th>本期预测</th><th>概率</th><th>成功定义</th><th>反事实</th><th>验证时间</th><th>结果证据</th></tr></thead><tbody>{rows}</tbody></table>
    {base.details('固定概率档位与评分方法', '<table><thead><tr><th>档位</th><th>范围</th><th>评分代表值</th></tr></thead><tbody>'+bins+'</tbody></table><p>'+base.esc(summary['probability_policy']['scoring'])+'</p><p>'+base.esc(summary['probability_policy']['publication_threshold'])+'</p>')}
    """


def render_trace(rows: list[dict[str, Any]], base: Any) -> str:
    body = []
    for row in rows:
        evidence = "".join(
            f"<li><b>{base.esc(item.get('title'))}</b>｜{base.esc(item.get('publisher'))}｜{base.esc(item.get('published_at'))}<br>{base.link(item.get('url')) if item.get('url') else '<span class=\"muted\">没有独立网页链接，见同批次证据实物。</span>'}<br>证明：{base.esc(plain_value(item.get('supports')))}<br>不能证明：{base.esc(plain_value(item.get('cannot_prove')))}</li>"
            for item in row.get("evidence_details", [])
        ) or "<li>本结论没有独立新证据，已在动作边界中隔离。</li>"
        body.append(
            f"<tr><td><b>{base.esc(row['conclusion'])}</b><br>{base.esc(row['plain_answer'])}</td><td><ul>{evidence}</ul></td><td>{base.esc(row['rule'])}</td><td>{base.esc(row['boundary'])}</td></tr>"
        )
    return "<table><thead><tr><th>结论</th><th>真实证据、机构与原文</th><th>适用规则</th><th>推翻条件或边界</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def attachment_table(rows: list[dict[str, Any]]) -> str:
    body = "".join(
        f"<tr><td><a href='{html.escape(row['name'], quote=True)}'>{html.escape(row['name'])}</a></td><td>{html.escape(row['purpose'])}</td><td>{row['size']:,}</td><td><code>{row['sha256']}</code></td></tr>"
        for row in rows
    )
    return "<table data-attachment-table='1'><thead><tr><th>附件</th><th>用途</th><th>字节</th><th>SHA256</th></tr></thead><tbody>" + body + "</tbody></table>"


def write_attachment(path: Path, value: Any, purpose: str) -> dict[str, Any]:
    write_json(path, value)
    return {"name": path.name, "purpose": purpose, "size": path.stat().st_size, "sha256": sha256(path)}


def visible_text(value: str) -> str:
    return html.unescape(re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", value))


def semantic_qa(
    model: dict[str, Any], html_text: str, capability: dict[str, Any], final: dict[str, Any],
    output_dir: Path, attachment_rows: list[dict[str, Any]], decision_hash: str,
) -> dict[str, Any]:
    visible = visible_text(html_text)
    holding_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    numeric = [row for row in final["holdings_judgments"] if row["target_contribution_included"]]
    contribution = sum(row["target_contribution_pp"] for row in numeric)
    research = {row["asset_id"]: row for row in final["research_judgments"]}
    cap_research = {row["asset_id"]: row for row in capability["research_18"]}
    expected_product_date = final["source_evidence_cutoff_jst"][:10]
    quote_errors = [symbol for symbol, row in cap_research.items() if not str(row["current_quote"].get("update_time", "")).startswith(expected_product_date)]
    quote_cutoff_errors = [
        symbol for symbol, row in cap_research.items()
        if str(row["current_quote"].get("update_time", ""))[:10] > expected_product_date
    ]
    identity_ok = (
        model.get("data_date") == expected_product_date
        and model.get("evidence_cutoff_jst") == final["source_evidence_cutoff_jst"]
        and f"<title>★{expected_product_date}完整投研产品候选_v2.0_最终完整HTML</title>" in html_text
        and f"<b>数据日</b><br>{expected_product_date}" in html_text
        and f"<h1>{expected_product_date}完整投研产品候选 v2.0｜最终完整HTML</h1>" in html_text
    )
    gate_errors = [symbol for symbol, row in research.items() if len(row["gate_decisions"]) != 5]
    numeric_errors = []
    for row in numeric:
        if sum(row["scenario_probability_pct"].values()) != 100:
            numeric_errors.append(f"{row['asset_id']}:概率不等于100")
        if row["scenario_values"]["bear"] > row["scenario_values"]["base"] or row["scenario_values"]["base"] > row["scenario_values"]["bull"]:
            numeric_errors.append(f"{row['asset_id']}:情景值顺序错误")
    forbidden = {
        term: visible.count(term) for term in (
            "retrieved at jst", "selected nearest forward eps", "historical forward pe reference",
            "locator_type", "proof=", "boundary=", "待总控", "总控必须", "详见机器附件",
        ) if visible.count(term)
    }
    local_paths = len(re.findall(r"(?i)(?:[A-Z]:\\|file://)", visible))
    program_structures = {
        "Python字典": len(re.findall(r"\{\s*['\"]", visible)),
        "Python列表": len(re.findall(r"\[\s*['\"]", visible)),
    }
    program_structures = {key: value for key, value in program_structures.items() if value}
    html_structure = {
        "holding_cards": len(re.findall(r"data-holding=['\"]", html_text)),
        "research_cards": len(re.findall(r"data-research=['\"]", html_text)),
        "gate_rows": len(re.findall(r"data-gate-row=['\"]1['\"]", html_text)),
        "target_rows": len(re.findall(r"data-target-row=['\"]", html_text)),
    }
    declared = set(re.findall(r"href=['\"]([^'\"]+\.json)['\"]", html_text))
    expected = {row["name"] for row in attachment_rows}
    checks = {
        "Q01判断源承接": {"pass": final["source_run_id"] == capability["run_id"] and decision_hash == sha256(Path(args_final_judgment_global)), "detail": {"source_run_id": final["source_run_id"], "decision_sha256": decision_hash}},
        "Q02唯一HTML与PDF冻结": {"pass": len(list(output_dir.glob("*.html"))) == 1 and not list(output_dir.glob("*.pdf")), "detail": {"html": len(list(output_dir.glob('*.html'))), "pdf": len(list(output_dir.glob('*.pdf')))}},
        "Q03结构与数量": {"pass": len(model["layers"]) == 7 and len(model["holdings"]) == 24 and len(model["research_gates"]) == 18 and len(model["pdca"]["plain_records"]) == 57 and html_structure == {"holding_cards": 24, "research_cards": 18, "gate_rows": 90, "target_rows": 24}, "detail": {"layers": len(model["layers"]), "holdings": len(model["holdings"]), "research": len(model["research_gates"]), "pdca_history": len(model["pdca"]["plain_records"]), "html_structure": html_structure}},
        "Q04九项估值可复算": {"pass": len(numeric) == 9 and not numeric_errors and all((next(x for x in capability["holdings_24"] if x["symbol"] == row["asset_id"])["decision_input_v2"].get("valuation_evidence")) for row in numeric), "detail": {"count": len(numeric), "errors": numeric_errors}},
        "Q05组合贡献复算": {"pass": abs(contribution - final["portfolio_target_judgment"]["numeric_scenario_contribution_pp"]["probability_weighted"]) < 0.00001, "detail": {"calculated": contribution, "approved": final["portfolio_target_judgment"]["numeric_scenario_contribution_pp"]["probability_weighted"]}},
        "Q06目标路径边界": {"pass": model["target_bridge"]["unquantified_is_zero"] is False and model["target_bridge"]["plus_40_status"] == "NOT_PROVEN" and model["target_bridge"]["plus_100_status"] == "NOT_FEASIBLE_UNDER_CURRENT_EVIDENCE", "detail": {"quantified_weight_pct": model["target_bridge"]["quantified_weight_pct"], "unquantified_weight_pct": model["target_bridge"]["unquantified_weight_pct"]}},
        "Q07研究行情时间": {"pass": len(cap_research) == 18 and not quote_errors, "detail": {"count": len(cap_research), "errors": quote_errors}},
        "Q08五关唯一裁定": {"pass": len(research) == 18 and not gate_errors and all(not row["executable"] for row in research.values()), "detail": {"count": len(research), "errors": gate_errors, "executable": sum(row["executable"] for row in research.values())}},
        "Q09公司指引与证据": {"pass": all(item["financial"]["guidance_evidence"].get("plain_status") and item["financial"]["guidance_evidence"].get("source_title") for item in model["holdings"]), "detail": {"holding_count": len(model["holdings"])}},
        "Q10同股唯一答案": {"pass": len(holding_map) == 24 and len({item["asset_id"] for item in model["holdings"]}) == 24 and len({item["asset_id"] for item in model["research_gates"]}) == 18, "detail": {"holdings": len(holding_map), "research": len(research)}},
        "Q11PDCA校准": {"pass": len(final["pdca_new_predictions"]) == 6 and all(row.get("probability_pct") in {10, 30, 50, 70, 90} for row in final["pdca_new_predictions"]) and len(final["probability_policy"]["approved_bins"]) == 5, "detail": {"new_predictions": len(final["pdca_new_predictions"]), "bins": len(final["probability_policy"]["approved_bins"])}},
        "Q12正文大白话": {"pass": not forbidden and local_paths == 0 and not program_structures, "detail": {"forbidden": forbidden, "local_paths": local_paths, "program_structures": program_structures}},
        "Q13附件实物": {"pass": declared == expected and all((output_dir / row["name"]).exists() and sha256(output_dir / row["name"]) == row["sha256"] for row in attachment_rows), "detail": {"declared": len(declared), "expected": len(expected)}},
        "Q14UTF8": {"pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8"), "detail": {"replacement_bytes": html_text.encode("utf-8").count(b"\xef\xbf\xbd")}},
        "Q15候选边界": {"pass": model["status"] == STATUS and model["pdf_generated"] is False and model["pdf_authorization_received"] is False, "detail": model["status"]},
        "Q16产品身份与时间截止": {"pass": identity_ok and not quote_cutoff_errors, "detail": {"product_date": expected_product_date, "evidence_cutoff_jst": model.get("evidence_cutoff_jst"), "quote_after_cutoff": quote_cutoff_errors}},
    }
    failures = [name for name, result in checks.items() if not result["pass"]]
    return {
        "schema_version": "V7-STAGEC-CAPABILITY-CLOSED-SEMANTIC-QA-1.0",
        "run_id": model["run_id"],
        "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "checks": checks,
        "pass_count": len(checks) - len(failures),
        "check_count": len(checks),
        "failures": failures,
        "status": "INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_CONTENT_GATE" if not failures else "FAIL",
        "self_declared_content_gate_pass": False,
        "pdf_render_authorized": False,
    }


args_final_judgment_global = ""


def main() -> int:
    global args_final_judgment_global
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-renderer", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--capability-input", required=True, type=Path)
    parser.add_argument("--final-judgment", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()
    args_final_judgment_global = str(args.final_judgment)

    if args.output_dir.exists():
        raise RuntimeError(f"output exists: {args.output_dir}")
    capability = load_json(args.capability_input)
    final = load_json(args.final_judgment)
    decision_hash = sha256(args.final_judgment)
    if decision_hash != "F0EDC7999B18E404C3ADA60C5CC3EDDD1D8723C8EB8694F7926A7378F5126376":
        raise RuntimeError("final judgment SHA256 mismatch")
    if final["source_run_id"] != capability["run_id"]:
        raise RuntimeError("final judgment and capability input run mismatch")
    if final["source_files"]["json_sha256"] != sha256(args.capability_input):
        raise RuntimeError("capability input SHA256 mismatch")
    if final["authorization"]["final_complete_html_generation"] != "AUTHORIZED_ONCE":
        raise RuntimeError("final complete HTML is not authorized")
    if final["authorization"]["pdf_render"] != "NOT_AUTHORIZED_PENDING_FULL_HTML_CONTENT_GATE":
        raise RuntimeError("unexpected PDF authorization state")
    if len(final["holdings_judgments"]) != 24 or len(final["research_judgments"]) != 18:
        raise RuntimeError("final judgment coverage mismatch")

    base = legacy.load_base_module(args.base_renderer)
    model = load_json(args.base_model)
    daily_before = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    args.output_dir.mkdir(parents=True, exist_ok=False)

    product_date = final["source_evidence_cutoff_jst"][:10]
    model["schema_version"] = "V7-COMPLETE-PRODUCT-MODEL-2.3-CAPABILITY-CLOSED"
    model["data_date"] = product_date
    model["evidence_cutoff_jst"] = final["source_evidence_cutoff_jst"]
    model["run_id"] = args.run_id
    model["source_html_run_id"] = load_json(args.base_model)["run_id"]
    model["final_capability_input_run_id"] = capability["run_id"]
    model["final_capability_judgment_id"] = final["judgment_id"]
    model["final_capability_judgment_sha256"] = decision_hash
    model["judgment_formed_at_jst"] = final["generated_at_jst"]
    model["generated_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
    model["status"] = STATUS
    model["content_gate_status"] = "PENDING_FULL_HTML_CONTENT_GATE"
    model["pdf_generated"] = False
    model["pdf_authorization_received"] = False
    model["judgment"] = {"today_action": model.get("judgment", {}).get("today_action", {}), "source": "本期唯一业务判断"}

    model["holdings"] = apply_holdings(model["holdings"], capability, final)
    model["research_gates"] = apply_research(model["research_gates"], capability, final)
    model["target_bridge"] = build_target_bridge(capability, final)
    market_audit = legacy.inject_market_reversal(model)
    pdca_audit = apply_pdca(model, final)
    apply_first_layer(model, final)
    model["traceability"] = rebuild_traceability(model)
    model["final_capability_judgment"] = {
        "judgment_id": final["judgment_id"], "sha256": decision_hash,
        "source_run_id": final["source_run_id"], "decision_status": final["decision_status"],
    }
    model = legacy.humanize_visible_value(model)

    attachment_rows: list[dict[str, Any]] = []
    attachment_rows.append(write_attachment(args.output_dir / "01_PDCA历史57条及新预测.json", model["pdca"], "57条历史缺陷账本与6条新校准预测"))
    attachment_rows.append(write_attachment(args.output_dir / "02_唯一账户事实源.json", {"run_id": args.run_id, "data": model["single_portfolio_source"]}, "全账户已知与未知边界"))
    attachment_rows.append(write_attachment(args.output_dir / "03_18只正式五关矩阵.json", {"run_id": args.run_id, "data": model["research_gates"]}, "18只逐关事实、裁定与停止位置"))
    attachment_rows.append(write_attachment(args.output_dir / "04_24类目标贡献桥.json", {"run_id": args.run_id, "data": model["target_bridge"]}, "24类权重、情景、概率、组合贡献与目标路径"))
    attachment_rows.append(write_attachment(args.output_dir / "05_外部观点映射.json", {"run_id": args.run_id, "data": model["external_views"]}, "湖水、老雷观点与持仓动作影响"))
    attachment_rows.append(write_attachment(args.output_dir / "06_历史功能数据.json", {"run_id": args.run_id, "data": model["capabilities"]}, "替换发动机、影子组合和风险穿透"))
    attachment_rows.append(write_attachment(args.output_dir / "07_证据注册与结论追踪.json", {"run_id": args.run_id, "data": model["traceability"]}, "真实标题、机构、日期、原文及边界"))
    valuation_rows = [row for row in capability["valuation_evidence_9"]]
    attachment_rows.append(write_attachment(args.output_dir / "08_九项估值输入与裁定复算.json", {"run_id": args.run_id, "inputs": valuation_rows, "decisions": [row for row in final["holdings_judgments"] if row["target_contribution_included"]]}, "九项逐期样本、参数、概率和复算结果"))
    attachment_rows.append(write_attachment(args.output_dir / "09_24类持仓唯一答案.json", {"run_id": args.run_id, "data": final["holdings_judgments"]}, "24类持仓唯一动作与替换比较"))
    attachment_rows.append(write_attachment(args.output_dir / "10_18只研究对象最终裁定.json", {"run_id": args.run_id, "data": final["research_judgments"]}, "18只五关、概率、催化剂和见分晓时间"))
    attachment_rows.append(write_attachment(args.output_dir / "11_18只行情时间审计.json", {"run_id": args.run_id, "data": capability["quote_refresh"]}, "18只统一截止行情和时间"))
    attachment_rows.append(write_attachment(args.output_dir / "12_PDCA概率校准规则.json", {"run_id": args.run_id, "probability_policy": final["probability_policy"], "new_predictions": final["pdca_new_predictions"], "historical_audit": pdca_audit}, "固定概率档位、Brier评分及6条新预测"))
    changes = {
        "run_id": args.run_id,
        "changes": [
            {"item": "九项估值", "before": "上一HTML撤回全部数值情景", "after": "恢复带日期样本、前瞻输入、条件参数、概率与复算结果", "reason": "外部输入和总控唯一裁定已经闭合"},
            {"item": "24类目标桥", "before": "数值贡献0项", "after": "9项覆盖53.362934%，概率加权贡献8.416635个百分点；其余15项不按0处理", "reason": "目标路径必须区分已量化与未量化"},
            {"item": "18只研究对象", "before": "10只停在第二或第三关", "after": "按总控逐关裁定；条件通过但未触发仍不可执行", "reason": "补齐财务、风险定价、护城河和替换比较"},
            {"item": "PDCA", "before": "只有3条中等把握基线", "after": "采用5档概率、Brier评分和6条带成功定义的新预测", "reason": "为后续校准预测能力建立真实起点"},
            {"item": "正文", "before": "可见机器字段和本地路径", "after": "正文只保留大白话、必要数字和原文链接；机器明细进入JSON附件", "reason": "董事长可直接阅读"},
        ],
        "market_reversal_frozen": market_audit,
    }
    attachment_rows.append(write_attachment(args.output_dir / "13_能力闭合修改前后清单.json", changes, "能力闭合前后及冻结章节说明"))

    old_target = base.render_target_bridge
    old_holding = base.render_holding_card
    old_gate = base.render_gate_card
    old_facts = base.render_layer_fact_list
    old_news = base.render_news
    old_pdca = base.render_pdca_main
    old_trace = base.render_trace
    base.render_target_bridge = lambda target: render_target_bridge(target, base)
    base.render_holding_card = lambda item: render_holding_card(item, base)
    base.render_gate_card = lambda item: render_gate_card(item, base)
    base.render_layer_fact_list = lambda facts: legacy.render_layer_fact_list(facts, base)
    base.render_news = lambda news: legacy.render_news(news, base)
    base.render_pdca_main = lambda pdca: render_pdca(pdca, base)
    base.render_trace = lambda rows: render_trace(rows, base)
    try:
        html_text = base.build_html(model)
    finally:
        base.render_target_bridge = old_target
        base.render_holding_card = old_holding
        base.render_gate_card = old_gate
        base.render_layer_fact_list = old_facts
        base.render_news = old_news
        base.render_pdca_main = old_pdca
        base.render_trace = old_trace
    html_text = legacy.replace_identity(html_text, args.run_id, model["generated_at_jst"])
    html_text = html_text.replace(
        "<title>★2026-08-20完整投研产品候选_v2.0_最终完整HTML</title>",
        f"<title>★{product_date}完整投研产品候选_v2.0_最终完整HTML</title>",
    )
    identity_start = f'<div class="identity"><span><b>当前批次</b><br>{html.escape(args.run_id)}</span>'
    if identity_start not in html_text:
        raise RuntimeError("identity header marker missing")
    html_text = html_text.replace(
        identity_start,
        identity_start + f'<span><b>数据日</b><br>{product_date}</span>',
        1,
    )
    html_text = html_text.replace(
        "<h1>2026-08-20完整投研产品候选 v2.0｜最终完整HTML</h1>",
        f"<h1>{product_date}完整投研产品候选 v2.0｜最终完整HTML</h1>",
    )
    old_promise = (
        '<p class="muted">57条PDCA逐项记录、唯一账户机器源、五关矩阵、目标贡献桥、'
        '外部观点映射和功能数据均另存JSON附件；机器字段不进入董事长正文。</p>'
    )
    if old_promise not in html_text:
        raise RuntimeError("attachment promise marker missing")
    html_text = html_text.replace(old_promise, attachment_table(attachment_rows))
    for source, replacement in legacy.VISIBLE_TERM_MAP.items():
        html_text = html_text.replace(source, replacement)
    html_text = html_text.replace("第五关通过0只，可执行新增机会0只。八项重点机会已完成总控排序，但均未被升级为正式机会。", "18只研究对象当前可执行新增机会为0；其中部分完成前四关但第五关尚未触发，其余按最早失败关停止。")
    html_path = args.output_dir / f"★{product_date}完整投研产品候选_v2.0_最终完整HTML.html"
    html_path.write_text(html_text, encoding="utf-8")

    qa = semantic_qa(model, html_text, capability, final, args.output_dir, attachment_rows, decision_hash)
    write_json(args.output_dir / "14_完整HTML实质语义QA.json", qa)
    if qa["status"] != "INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_CONTENT_GATE":
        raise RuntimeError(f"semantic QA failed: {qa['failures']}")
    daily_after = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    boundary = {
        "run_id": args.run_id, "before": daily_before, "after": daily_after,
        "unchanged": daily_before == daily_after, "pdf_generated": False,
        "release": False, "trade_calls": 0, "order_calls": 0,
        "content_gate_status": "PENDING_FULL_HTML_CONTENT_GATE",
    }
    write_json(args.output_dir / "15_正式日报未覆盖及阶段边界.json", boundary)
    if not boundary["unchanged"]:
        raise RuntimeError("daily report changed")

    manifest_path = args.output_dir / "16_全部实物SHA256清单.json"
    items = []
    for path in sorted(args.output_dir.iterdir(), key=lambda value: value.name):
        if path.is_file() and path != manifest_path:
            items.append({
                "name": path.name, "path": str(path), "size": path.stat().st_size,
                "sha256": sha256(path),
                "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds"),
            })
    write_json(manifest_path, {"run_id": args.run_id, "item_count": len(items), "items": items, "pdf_generated": False, "self_hash_excluded": True})
    pointer = ROOT / "00_任务中心" / "V7_v2.0_最终完整HTML_Current.json"
    write_json(pointer, {
        "run_id": args.run_id, "status": "PENDING_FULL_HTML_CONTENT_GATE",
        "html_path": str(html_path), "html_size": html_path.stat().st_size,
        "html_sha256": sha256(html_path), "output_dir": str(args.output_dir),
        "qa_path": str(args.output_dir / "14_完整HTML实质语义QA.json"),
        "pdf_generated": False, "pdf_render_authorized": False,
    })
    print(json.dumps({
        "run_id": args.run_id, "html": str(html_path), "html_size": html_path.stat().st_size,
        "html_sha256": sha256(html_path), "holdings": len(model["holdings"]),
        "research": len(model["research_gates"]), "numeric_holdings": 9,
        "probability_weighted_contribution_pp": model["target_bridge"]["probability_weighted_contribution_pp"],
        "new_pdca_predictions": len(final["pdca_new_predictions"]), "qa": qa["status"],
        "pdf_generated": False, "daily_report_unchanged": boundary["unchanged"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
