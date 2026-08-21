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


def guidance_summary(guidance: dict[str, Any]) -> str:
    facts = "；".join(str(value) for value in guidance.get("facts", []) if value)
    status = guidance.get("plain_status") or "公司指引状态未登记"
    period = guidance.get("period") or "期间未登记"
    return f"{status}。期间：{period}。{facts}".strip("。") + "。"


def quality_explanation(symbol: str) -> str:
    if symbol in {"BTC", "ETH"}:
        return "该资产不是经营公司，企业收入、利润率和企业现金流指标不适用；本期改看协议、使用、流动性、交易结构和监管风险。"
    if symbol in {"JP.8766", "US.IBKR"}:
        return "金融机构不宜用普通制造业自由现金流机械比较；本期重点看净资产、资本回报、承保或净息差、资本充足与股东回报。"
    if symbol == "JP.9984":
        return "控股公司优先看持股资产价值、净债务、每股净资产价值和负债价值比；普通经营利润率只作补充。"
    if symbol in {"US.MSTR", "US.SPCX"}:
        return "资产与资本结构决定风险，普通利润率不能单独解释价值；本期重点看资产价值、债务、稀释、融资能力和流动性。"
    if symbol in {"KRX.005930", "US.SNDK", "JP.4063", "JP.6857", "JP.6954", "US.NVDA", "US.AVGO", "US.TSM"}:
        return "周期与资本开支会放大单期数字；机械比率只用于勾稽，还要结合订单、售价、毛利率、产能和中周期现金流。"
    return "机械比率只用于勾稽正式财务，不能单独替代公司指引、估值依据、竞争判断和反向证据。"


def first_url(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("source_url", "url", "source"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.startswith(("https://", "http://")):
                return candidate
        for child in value.values():
            candidate = first_url(child)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for child in value:
            candidate = first_url(child)
            if candidate:
                return candidate
    return None


def precise_evidence_roles(item: dict[str, Any], cap: dict[str, Any], numeric: bool) -> list[dict[str, Any]]:
    financial = cap["latest_formal_financial"]
    guidance = cap["company_guidance"]
    reverse = cap["reverse_evidence"]
    event = cap.get("company_or_industry_event")
    forward = item["valuation"].get("forward_input")
    account_names = "、".join(cap.get("quantity_by_account", {}).keys()) or "账户归属未闭合"
    roles = [{
        "role": "账户事实", "status": "已取得本批次账户实物", "title": f"{item['name']}账户数量与已知市值",
        "publisher": "Futu OpenD及已确认账户实物", "published_at": item["account_fact"].get("data_boundary"),
        "period": "各账户按原始实物日期分别登记", "locator": f"账户：{account_names}；数量：{item['account_fact'].get('quantity_by_account')}",
        "url": None, "supports": "证明本批次已知账户中的数量、已知市值和权重分母。", "cannot_prove": "不能证明未知账户字段、完整同日净值或交易历史。",
    }]
    if item["asset_id"] in {"BTC", "ETH"}:
        roles.append({
            "role": "财务事实", "status": "不适用企业财务口径", "title": "非企业资产，不套用企业三张报表", "publisher": "不适用",
            "published_at": "不适用", "period": "不适用", "locator": "无企业利润表、资产负债表或现金流量表", "url": None,
            "supports": "说明企业财务指标不适用。", "cannot_prove": "不能据此证明价格、流动性或收益前景。",
        })
    else:
        roles.append({
            "role": "财务事实", "status": "已取得正式财务原文", "title": financial.get("source_title"), "publisher": financial.get("publisher"),
            "published_at": financial.get("precise_locator", {}).get("published_at") or "发布日期见原文", "period": financial.get("financial_period"),
            "locator": financial.get("precise_locator"), "url": financial.get("source_url"), "supports": "证明所列财务期间、合并口径和正式财务字段。",
            "cannot_prove": "不能单独证明当前市场价格、合理倍数或当期公司事件。",
        })
    roles.append({
        "role": "公司指引或替代指引", "status": guidance.get("plain_status"), "title": guidance.get("source_title"), "publisher": guidance.get("publisher"),
        "published_at": guidance.get("published_at"), "period": guidance.get("period"), "locator": guidance.get("locator"), "url": guidance.get("url"),
        "supports": "；".join(guidance.get("facts", [])), "cannot_prove": "公司或协议资料不能单独证明当前市场价格，也不构成自动交易线。",
    })
    roles.append({
        "role": "估值输入", "status": "已取得可复算外部输入" if numeric else "本期不采用数值估值",
        "title": (forward or {}).get("source_title") if isinstance(forward, dict) else "非价格风险框架",
        "publisher": (forward or {}).get("publisher") if isinstance(forward, dict) else "GPT总控最终能力判断",
        "published_at": (forward or {}).get("retrieved_at_jst") if isinstance(forward, dict) else "本批次判断形成时间",
        "period": str((forward or {}).get("selected_nearest_forward_eps", {}).get("period") or "不适用") if isinstance(forward, dict) else "不适用",
        "locator": "前瞻输入、情景参数和公式" if numeric else "只保留风险、触发条件和动作边界", "url": first_url(forward),
        "supports": "支持已批准条件情景的机械复算。" if numeric else "说明为什么本期不能给出可靠数值估值。",
        "cannot_prove": "条件情景不是历史合理价值，也不单独支持加减仓。" if numeric else "不证明内在价值、目标价或收益概率。",
    })
    if isinstance(event, dict) and first_url(event):
        roles.append({
            "role": "公司或行业事件", "status": "已取得本批次事件原文", "title": event.get("title"), "publisher": event.get("publisher") or event.get("source_name"),
            "published_at": event.get("published_at") or event.get("source_date"), "period": event.get("data_period") or "本批次事实截止前",
            "locator": event.get("locator") or event.get("section"), "url": first_url(event), "supports": event.get("supports") or event.get("impact"),
            "cannot_prove": event.get("cannot_prove") or "单一事件不能独立证明估值或交易动作。",
        })
    else:
        roles.append({
            "role": "公司或行业事件", "status": "限定范围内未取得独立公司级新事件", "title": "本批次事件检索结果",
            "publisher": "生产批次新闻与事件账本", "published_at": "截至统一事实截止时间", "period": "本批次", "locator": "没有用财报或宏观新闻占位",
            "url": None, "supports": "只证明限定检索范围内没有取得可独立使用的新公司事件。", "cannot_prove": "不能写成市场上没有发生事件，也不能支持估值或动作。",
        })
    roles.append({
        "role": "反向证据", "status": "已取得反向证据", "title": reverse.get("section"), "publisher": reverse.get("publisher"),
        "published_at": reverse.get("source_date"), "period": reverse.get("source_date"), "locator": reverse.get("section"), "url": first_url(reverse),
        "supports": reverse.get("opposes"), "cannot_prove": reverse.get("role_boundary"),
    })
    roles.append({
        "role": "Current规则", "status": "已取得正式规则", "title": "Current完整产品与风险边界", "publisher": "AI投资系统Current",
        "published_at": "当前有效版本", "period": "本批次", "locator": "Current启动包、总则、蓝图与正式五关", "url": None,
        "supports": "证明不机械使用15%、20%或未经确认的30%硬线，并保持候选、非Release和无订单边界。",
        "cannot_prove": "规则定义动作边界，不证明公司财务、市场价格或投资收益。",
    })
    return roles

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
        account_names = "、".join(cap["quantity_by_account"].keys()) or "账户归属未闭合"
        item["account_fact"]["data_boundary"] = (
            f"账户数据边界：本卡数量来自{account_names}的最后有效实物；各账户原始日期见全账户表。"
            "只用于已知资产风险，不代表四账户同日完整净值。"
        )
        item["valuation"]["current_price"] = cap["current_price"].get("value")
        item["valuation"]["current_price_time"] = cap["current_price"].get("time")
        item["valuation"]["current_price_source"] = cap["current_price"].get("source")
        item["financial"]["guidance"] = guidance_summary(cap["company_guidance"])
        item["financial"]["guidance_evidence"] = copy.deepcopy(cap["company_guidance"])
        item["financial"]["guidance_evidence"]["reverse_impact"] = cap["reverse_evidence"].get("opposes")
        item["financial"]["guidance_evidence"]["update_condition"] = cap.get("update_condition")
        item["financial"]["quality"]["industry_explanation"] = quality_explanation(symbol)
        item["financial"]["quality"]["summary"] = (
            f"{item['financial']['quality'].get('summary', '')} {quality_explanation(symbol)}"
        ).strip()
        item["company_guidance_capability"] = cap["company_guidance"]
        item["current_reverse_evidence_capability"] = cap["reverse_evidence"]
        item["forecast"]["medium_term"] = re.sub(
            r"[，,]?(?:主逻辑成立)?概率约\d+(?:\.\d+)?%[。.]?", "。", item["forecast"].get("medium_term", "")
        ).replace("。。", "。").strip()
        if isinstance(item["valuation"].get("formula"), dict):
            item["valuation"]["formula"].pop("missing_for_final", None)
        item["valuation"]["missing"] = [
            value for value in item["valuation"].get("missing", [])
            if value != "GPT总控最终参数及情景权重"
        ]

        if symbol in numeric_map:
            judgment = numeric_map[symbol]
            probs = judgment["probability_pct"]
            item["valuation"]["final_control_answer"] = scenario_summary(cap)
            item["valuation"]["price_boundary"] = (
                "条件情景只用于检验盈利和估值变化；不单独支持加仓、减仓或目标承诺。"
            )
            item["valuation"]["missing"] = []
            item["valuation"]["missing_plain"] = "本期总控参数、情景权重与动作边界已裁定；没有仍待总控填写的参数。"
            if isinstance(item["valuation"].get("formula"), dict):
                item["valuation"]["formula"].pop("missing_for_final", None)
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
            item["valuation"]["missing_plain"] = "本期不采用数值估值；未闭合输入按风险框架隔离，不进入目标贡献。"
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
        item["precise_evidence_roles"] = precise_evidence_roles(item, cap, symbol in numeric_map)
        item.pop("evidence_roles", None)
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
        for gate in item["gates"]:
            source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
            clickable = bool(source.get("title")) and str(source.get("url", "")).startswith(("https://", "http://"))
            claimed_complete = "已取得" in str(gate.get("status", "")) or "已完成" in str(gate.get("status", ""))
            if (claimed_complete or gate.get("evidence_complete")) and clickable:
                gate["missing"] = []
                gate["evidence_complete"] = True
            elif claimed_complete and not clickable:
                gate["status"] = "本关证据未闭合，停止在本关"
                gate["evidence_complete"] = False
                gate["missing"] = ["缺少可点击的正式原文，不能把本关标为已完成。"]
            elif gate.get("evidence_complete") and not clickable:
                gate["evidence_complete"] = False
                gate["missing"] = gate.get("missing") or ["缺少可点击的正式原文。"]
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


def locator_text(value: Any) -> str:
    if not value:
        return "原文位置未单独登记"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(locator_text(item) for item in value)
    if isinstance(value, dict):
        labels = {
            "doc_id": "文件编号", "published_at": "发布时间", "accounting_standard": "会计准则",
            "locator_type": "定位方式", "statement_locations": "报表或章节", "period_rule": "期间规则",
            "boundary": "定位边界", "section": "章节", "page": "页码", "field": "字段",
        }
        parts = []
        for key, item in value.items():
            if key == "selected_metrics" and isinstance(item, dict):
                metrics = []
                for metric, detail in item.items():
                    if isinstance(detail, dict):
                        metrics.append(
                            f"{metric}：字段{detail.get('qname', '未登记')}，期间{detail.get('contextRef', '未登记')}，单位{detail.get('unitRef', '未登记')}"
                        )
                parts.append("财务字段：" + "；".join(metrics))
            elif key in labels:
                parts.append(f"{labels[key]}：{locator_text(item)}")
        return "；".join(parts) or "原文位置见正式来源中的对应财务表或风险章节"
    return str(value)


def render_guidance_card(guidance: dict[str, Any], base: Any) -> str:
    facts = "".join(f"<li>{base.esc(value)}</li>" for value in guidance.get("facts", [])) or "<li>该资产不适用企业业绩指引。</li>"
    source = base.link(guidance.get("url")) if guidance.get("url") else '<span class="muted">没有独立外部链接；已明确隔离用途。</span>'
    return (
        f"<p><b>状态：</b>{base.esc(guidance.get('plain_status'))}</p>"
        f"<p><b>期间：</b>{base.esc(guidance.get('period'))}</p><ul>{facts}</ul>"
        f"<p><b>正式来源：</b>{base.esc(guidance.get('source_title'))}｜{base.esc(guidance.get('publisher'))}｜"
        f"{base.esc(guidance.get('published_at'))}<br>{source}</p>"
        f"<p><b>原文位置：</b>{base.esc(guidance.get('locator'))}</p>"
        f"<p><b>反向影响：</b>{base.esc(guidance.get('reverse_impact'))}</p>"
        f"<p><b>下次更新条件：</b>{base.esc(guidance.get('update_condition'))}</p>"
    )


def render_precise_evidence_roles(item: dict[str, Any], base: Any) -> str:
    rows = []
    for role in item["precise_evidence_roles"]:
        source = base.link(role.get("url")) if role.get("url") else '<span class="muted">无外部链接；状态和使用边界已明确</span>'
        rows.append(
            "<tr>"
            f"<td>{base.esc(role.get('role'))}<br><small>{base.esc(role.get('status'))}</small></td>"
            f"<td><b>{base.esc(role.get('title'))}</b><br>{base.esc(role.get('publisher'))}<br>{source}</td>"
            f"<td>{base.esc(role.get('published_at'))}<br>{base.esc(role.get('period'))}</td>"
            f"<td>{base.esc(locator_text(role.get('locator')))}</td>"
            f"<td>{base.esc(role.get('supports'))}</td><td>{base.esc(role.get('cannot_prove'))}</td></tr>"
        )
    return (
        "<table><thead><tr><th>证据角色与状态</th><th>标题、机构与原文</th><th>时间与期间</th>"
        "<th>原文位置</th><th>实际证明</th><th>不能证明</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def render_holding_card(item: dict[str, Any], base: Any) -> str:
    financial = item["financial"]
    quality = financial["quality"]
    metrics = "".join(
        f'<li>{base.esc(key)}：{base.fmt_num(value)}{("%" if "率" in key else "")}</li>'
        for key, value in quality.get("metrics", {}).items()
    ) or '<li>没有取得足够字段，不能计算同口径机械比率。</li>'
    source_url = financial.get("url")
    event_rows = "".join(
        f'<li>{base.esc(value.get("published_at"))}｜{base.esc(value.get("title"))}｜{base.link(value.get("url"))}</li>'
        for value in item["event_leads"]
    ) or '<li>限定范围内未取得可独立使用的新公司事件；这不等于市场上没有发生事件。</li>'
    adjustment = (
        f'<p class="alert"><b>Marvell事件下推：</b>{base.esc(item["action"]["marvell_event_adjustment"])}</p>'
        if item["action"].get("marvell_event_adjustment") else ""
    )
    valuation_missing = item["valuation"].get("missing_plain") or "已按本期边界登记"
    guidance = item["financial"]["guidance_evidence"]
    body = f'''
    <div class="asset-summary"><div><b>唯一动作</b><strong>{base.esc(item['action']['unique_action'])}</strong></div><div><b>已知账户权重</b><strong>{item['account_fact']['weight_of_known_assets_pct']:.2f}%</strong></div><div><b>下次复核</b><strong>{base.esc(item['action']['next_review'])}</strong></div></div>
    <p><b>为什么：</b>{base.esc(item['action']['reason'])}</p>{adjustment}
    <div class="research-grid">
      <article><h4>公司或资产做什么</h4><p>{base.esc(item['business_model'])}</p><h4>如何赚钱</h4><p>{base.esc(item['how_it_makes_money'])}</p><h4>增长驱动</h4><p>{base.esc(item['growth_drivers'])}</p></article>
      <article><h4>账户事实</h4><p>{base.esc(base.account_quantity_text(item['account_fact']['quantity_by_account']))}</p><p>已知市值：¥{base.fmt_num(item['account_fact']['known_market_value_jpy'])}</p><p><b>{base.esc(item['account_fact']['data_boundary'])}</b></p></article>
      <article><h4>财务质量</h4><p>期间：{base.esc(financial.get('period'))}｜口径：{base.esc(financial.get('consolidation'))}</p><p>{base.esc(quality.get('summary'))}</p><ul>{metrics}</ul></article>
      <article><h4>公司正式指引</h4>{render_guidance_card(guidance, base)}</article>
      <article><h4>护城河与竞争</h4><p><b>护城河：</b>{base.esc(item['moat_and_competition']['moat'])}</p><p><b>主要竞争者：</b>{base.esc(item['moat_and_competition']['competitors'])}</p><p><b>反向竞争证据：</b>{base.esc(item['moat_and_competition']['reverse_competition'])}</p></article>
      <article><h4>估值或风险定价</h4><p>{base.esc(item['valuation']['classification'])}</p><p><b>方法：</b>{base.esc(item['valuation']['method'])}</p><p><b>适用原因：</b>{base.esc(item['valuation']['method_reason'])}</p><p><b>总控答案：</b>{base.esc(item['valuation']['final_control_answer'])}</p><p><b>数值边界：</b>{base.esc(item['valuation']['price_boundary'])}</p></article>
      <article><h4>双时间尺度</h4><p><b>短期：</b>{base.esc(item['forecast']['short_term'])}</p><p><b>中期：</b>{base.esc(item['forecast']['medium_term'])}</p><p><b>把握度：</b>{base.esc(item['forecast']['control_confidence'])}</p><p class="muted">{base.esc(item['forecast']['confidence_boundary'])}</p></article>
      <article><h4>催化剂、反方与失效</h4><p><b>催化剂：</b>{base.esc(item['action']['catalysts'])}</p><p><b>当前反向证据：</b>{base.esc(item['action']['current_reverse_evidence'])}</p><p><b>未来失效条件：</b>{base.esc(item['action']['invalidation'])}</p></article>
      <article><h4>替换、目标和验证</h4><p><b>替换比较：</b>{base.esc(item['action']['replacement'])}</p><p><b>目标作用：</b>{base.esc(item['action']['target_contribution'])}</p><p><b>验证日：</b>{base.esc(item['action']['next_review'])}</p></article>
    </div>
    {base.details('正式财务字段、来源与定位', (base.render_period_blocks(financial) if financial.get("period_blocks") else f'<table><thead><tr><th>字段</th><th>数值</th><th>使用状态</th></tr></thead><tbody>{base.value_rows(financial.get("fields", dict()), financial.get("currency"))}</tbody></table>') + (f'<p><b>来源：</b>{base.esc(financial.get("source_title"))}｜{base.esc(financial.get("publisher"))}｜{base.link(source_url)}</p><p><b>原文位置：</b>{base.esc(locator_text(financial.get("locator")))}</p>' if source_url else '<p class="boundary">该资产不适用企业财务口径，未使用企业利润表、资产负债表或现金流量表。</p>'))}
    {base.details('估值输入、公式与缺口', f'<p><b>唯一当前价格：</b>{base.fmt_num(item["valuation"].get("current_price"),4)} {base.esc(item["valuation"].get("current_price_currency"))}｜{base.esc(item["valuation"].get("current_price_time"))}｜{base.esc(item["valuation"].get("current_price_timezone"))}｜{base.esc(item["valuation"].get("current_price_type"))}｜{base.esc(item["valuation"].get("current_price_source"))}</p><p><b>前瞻输入：</b>{base.human_text(item["valuation"].get("forward_input"))}</p><p><b>公式：</b>{base.human_text(item["valuation"].get("formula"))}</p><p><b>未闭合项及影响：</b>{base.esc(valuation_missing)}</p>')}
    {base.details('七类证据角色、原文与使用边界', render_precise_evidence_roles(item, base))}
    {base.details('公司事件线索与证据边界', f'<ul>{event_rows}</ul><p class="muted">新闻线索不等同公司正式公告；无正式原文时不支持估值或动作。</p>')}
    '''
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-holding="{base.esc(item["asset_id"])}"')


def render_gate_card(item: dict[str, Any], base: Any) -> str:
    rows = []
    for gate in item["gates"]:
        source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
        source_html = f'<b>{base.esc(source.get("title"))}</b><br>{base.link(source.get("url"))}' if source.get("url") else '<span class="missing">未取得可点击正式原文</span>'
        if gate.get("evidence_complete"):
            missing_html = '<span class="ok">本关所列事实和可点击原文已取得；本关无缺项。</span>'
        else:
            missing = gate.get("missing") or ["本关证据尚未闭合，因此不形成可执行动作。"]
            missing_html = '<ul>' + ''.join(f'<li>{base.esc(value)}</li>' for value in missing) + '</ul>'
        rows.append(
            f'<tr data-gate-row="1"><td>第{gate["gate"]}关</td><td>{base.esc(gate["status"])}</td>'
            f'<td>{base.esc(gate["fact"])}</td><td>{source_html}</td><td>{missing_html}</td></tr>'
        )
    body = f'''
    <div class="asset-summary"><div><b>身份</b><strong>{base.esc(item['identity'])}</strong></div><div><b>停关</b><strong>{base.esc(item['formal_gate_stop'])}</strong></div><div><b>可执行</b><strong>否</strong></div></div>
    <p><b>激活方向：</b>{base.esc(item['activated_sector'])}</p>
    <table><thead><tr><th>正式关卡</th><th>状态</th><th>事实与理由</th><th>可点击原文</th><th>未闭合项</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p><b>估值或风险定价：</b>{base.esc(item['valuation_or_risk_pricing'])}</p><p><b>与现金/持仓比较：</b>{base.esc(item['replacement_target'])}</p>
    <p><b>执行条件：</b>{base.esc(item['executable_condition'])}</p><p><b>短期：</b>{base.esc(item['short_term'])}</p><p><b>中期：</b>{base.esc(item['medium_term'])}</p><p><b>下一次验证：</b>{base.esc(item['next_review'])}</p>
    '''
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-research="{base.esc(item["asset_id"])}"')

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
    model_text = json.dumps(model, ensure_ascii=False)
    generic_guidance_phrase = "现有已核材料中没有为本包逐项独立提取公司指引"
    guidance_failures = []
    for item in model["holdings"]:
        guidance = item.get("financial", {}).get("guidance_evidence", {})
        required = ("plain_status", "period", "facts", "source_title", "publisher", "published_at", "url", "locator", "reverse_impact", "update_condition")
        if any(guidance.get(key) in (None, "", []) for key in required):
            guidance_failures.append(item["asset_id"])
    stale_term = "GPT总控最终参数及情景权重"
    risk_probability_errors = []
    for item in model["holdings"]:
        if item["asset_id"] in risk:
            risk_text = json.dumps({"forecast": item.get("forecast"), "valuation": item.get("valuation")}, ensure_ascii=False)
            if re.search(r"(?:概率|把握度)[^。；]{0,12}(?:约)?\d+(?:\.\d+)?%", risk_text):
                risk_probability_errors.append(item["asset_id"])
    gate_complete_count = 0
    gate_contradictions = []
    gate_source_failures = []
    for item in model["research_gates"]:
        for gate in item["gates"]:
            source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
            clickable = bool(source.get("title")) and str(source.get("url", "")).startswith(("https://", "http://"))
            if gate.get("evidence_complete"):
                gate_complete_count += 1
                if gate.get("missing"):
                    gate_contradictions.append(f"{item['asset_id']}-G{gate['gate']}")
                if not clickable:
                    gate_source_failures.append(f"{item['asset_id']}-G{gate['gate']}")
    required_role_url_failures = []
    for item in model["holdings"]:
        for role in item.get("precise_evidence_roles", []):
            required_url = (
                role["role"] in {"公司指引或替代指引", "反向证据"}
                or (role["role"] == "财务事实" and item["asset_id"] not in {"BTC", "ETH"})
                or (role["role"] == "估值输入" and item["asset_id"] in numeric)
                or (role["role"] == "公司或行业事件" and role["status"].startswith("已取得"))
            )
            if required_url and not str(role.get("url", "")).startswith(("https://", "http://")):
                required_role_url_failures.append(f"{item['asset_id']}:{role['role']}")
    unlabeled_missing_hits = len(re.findall(r"已知市值[^<]{0,160}(?:<[^>]+>\s*)*尚未取得", html_text))
    quality_explanation_failures = [
        item["asset_id"] for item in model["holdings"]
        if not item.get("financial", {}).get("quality", {}).get("industry_explanation")
    ]
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
        "J14公司指引逐项恢复": {
            "pass": not guidance_failures and visible.count(generic_guidance_phrase) == 0,
            "detail": {"holding_count": 24, "complete_guidance_count": 24 - len(guidance_failures), "failures": guidance_failures, "old_generic_phrase_hits": visible.count(generic_guidance_phrase)},
        },
        "J15总控估值裁定状态一致": {
            "pass": visible.count(stale_term) == 0 and model_text.count(stale_term) == 0,
            "detail": {"visible_stale_hits": visible.count(stale_term), "machine_stale_hits": model_text.count(stale_term), "numeric_scenarios": len(numeric)},
        },
        "J16风险框架禁用伪精确概率": {
            "pass": not risk_probability_errors,
            "detail": {"risk_asset_count": len(risk), "probability_conflicts": risk_probability_errors},
        },
        "J17五关状态来源缺项互斥": {
            "pass": not gate_contradictions and not gate_source_failures and visible.count("本批次未取得；不据此形成动作") == 0,
            "detail": {"complete_gate_rows": gate_complete_count, "complete_with_missing": gate_contradictions, "complete_without_clickable_source": gate_source_failures, "old_empty_list_render_hits": visible.count("本批次未取得；不据此形成动作")},
        },
        "J18关键证据直接可追溯": {
            "pass": visible.count("详见机器附件") == 0 and not required_role_url_failures,
            "detail": {"machine_attachment_placeholder_hits": visible.count("详见机器附件"), "required_role_url_failures": required_role_url_failures, "evidence_role_rows": sum(len(item.get("precise_evidence_roles", [])) for item in model["holdings"])},
        },
        "J19缺失字段有标签及行业解释": {
            "pass": unlabeled_missing_hits == 0 and not quality_explanation_failures,
            "detail": {"unlabeled_missing_after_market_value": unlabeled_missing_hits, "industry_explanation_failures": quality_explanation_failures},
        },
        "J20可见HTML与机器源交叉检查": {
            "pass": (
                html_text.count('data-holding=') == 24
                and html_text.count('data-research=') == 18
                and visible.count("公司正式指引") >= 24
                and visible.count("账户数据边界：") >= 24
            ),
            "detail": {
                "visible_holding_cards": html_text.count('data-holding='),
                "visible_research_cards": html_text.count('data-research='),
                "visible_guidance_sections": visible.count("公司正式指引"),
                "visible_labeled_account_boundaries": visible.count("账户数据边界："),
            },
        },
    }
    failures = [name for name, row in checks.items() if not row["pass"]]
    return {
        "schema_version": "V7-FINAL-HTML-SUBSTANTIVE-QA-2.0",
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
    prior_today_action = copy.deepcopy(model.get("judgment", {}).get("today_action", {}))
    model["judgment"] = {
        "today_action": prior_today_action,
        "source": "GPT总控最终能力判断唯一源",
        "legacy_asset_answers_removed": True,
    }
    model["holdings"] = merge_holdings(model["holdings"], capability, final)
    model["research_gates"] = merge_research(model["research_gates"], capability, final)
    model["target_bridge"] = build_target_bridge(capability, final)
    model["final_capability_judgment"] = final
    model["pdf_generated"] = False
    model["pdf_authorization_received"] = False
    update_first_layer(model, final)

    original_target_renderer = base.render_target_bridge
    original_holding_renderer = base.render_holding_card
    original_gate_renderer = base.render_gate_card
    base.render_target_bridge = lambda target: render_target_bridge(target, base)
    base.render_holding_card = lambda item: render_holding_card(item, base)
    base.render_gate_card = lambda item: render_gate_card(item, base)
    try:
        html_text = base.build_html(model)
    finally:
        base.render_target_bridge = original_target_renderer
        base.render_holding_card = original_holding_renderer
        base.render_gate_card = original_gate_renderer
    html_text = replace_identity(html_text, args.run_id, model["generated_at_jst"])
    html_path = args.output_dir / "★2026-08-20完整投研产品候选_v2.0_最终完整HTML.html"
    html_path.write_text(html_text, encoding="utf-8")

    qa = semantic_qa(model, html_text, capability, final, args.output_dir)
    write_json(args.output_dir / "01_最终完整HTML实质语义QA.json", qa)
    if qa["status"] != "PASS_FOR_GPT_FULL_HTML_CONTENT_GATE":
        raise RuntimeError(f"semantic QA failed: {qa['failures']}")
    repair_rows = [
        {"item": "24类持仓公司指引", "before": "24张卡统一显示未提取", "after": "24张卡逐项显示状态、期间、事实、正式来源、反向影响和更新条件", "reason": "恢复已闭合能力输入，禁止通用占位"},
        {"item": "估值裁定状态", "before": "28处已裁定参数仍列为缺口", "after": "用户HTML和机器源中的过期待办均为0", "reason": "以最终能力判断为唯一源"},
        {"item": "风险框架概率", "before": "软银、爱德万测试等出现未经批准的约60%", "after": "15项风险框架资产不显示伪精确概率", "reason": "没有数值情景时只保留风险和验证条件"},
        {"item": "18只正式五关", "before": "已取得与未取得同格", "after": "完成关写本关无缺项；缺证据关明确停关和缺项", "reason": "状态、来源和缺项互斥"},
        {"item": "关键证据", "before": "54处详见机器附件", "after": "证据表直接显示标题、机构、时间、期间、定位、链接、证明内容和边界", "reason": "董事长可直接追溯"},
        {"item": "缺失字段和行业解释", "before": "市值后出现无标签尚未取得，机械比率缺行业说明", "after": "账户数据边界明确，24张卡均有行业适用性解释", "reason": "避免把缺口或不适用指标误读为质量结论"},
        {"item": "语义QA", "before": "13项检查未发现七类矛盾", "after": "20项检查直接交叉读取最终HTML和机器源，记录命中与失败数", "reason": "任一实质项失败即禁止PASS"},
    ]
    write_json(args.output_dir / "02_七项返修修改前后原因清单.json", {"run_id": args.run_id, "count": len(repair_rows), "items": repair_rows})

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
    write_json(args.output_dir / "03_正式日报未覆盖及阶段边界.json", boundary)
    if not boundary["unchanged"]:
        raise RuntimeError("daily report changed")

    manifest_path = args.output_dir / "04_全部实物SHA256清单.json"
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
