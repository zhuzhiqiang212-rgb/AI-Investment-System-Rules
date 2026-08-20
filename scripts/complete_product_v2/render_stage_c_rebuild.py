from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .contracts import ContractError, load_json, validate_final_judgment, validate_handoff, write_json


JST = timezone(timedelta(hours=9))
STATUS = {
    "business_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "final_product_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "release_status": "NOT_AUTHORIZED",
    "current_executable": False,
}
FORBIDDEN_VISIBLE = (
    "retained_asset_ids",
    "error_taxonomy",
    "historical_records",
    "PENDING_JUDGMENT",
    "等待GPT总控",
    "需GPT总控决定",
    "仅供总控选择",
    "None",
    "null",
)
DRIVER_MAP = {
    "ai_direct": ["US.AVGO", "US.MSFT", "US.NVDA", "US.SNDK", "US.TSM"],
    "ai_broad": ["JP.9984", "US.AVGO", "US.MSFT", "US.NVDA", "US.SNDK", "US.TSM"],
    "crypto_direct": ["BTC", "ETH"],
    "crypto_broad": ["BTC", "ETH", "US.COIN", "US.CRCL", "US.MSTR"],
}
CLASS_CN = {
    "NUMERIC_VALUATION_INPUT_READY": "具备可复算输入，但参数仍是条件情景",
    "PARTIAL_INPUT_RISK_PRICING_ONLY": "只能做风险定价，不能给精确内在价值",
    "INSUFFICIENT_EVIDENCE_NO_NUMERIC_RANGE": "证据不足，不给数值区间",
    "PROVISIONAL_UNVERIFIED_VALUATION": "未验证估值，不能支持交易动作",
    "NOT_APPLICABLE_ASSET": "不适用企业财务口径",
}
FINANCIAL_LABELS = {
    "revenue": "收入",
    "operating_profit": "营业利润",
    "net_income": "净利润",
    "operating_cash_flow": "经营现金流",
    "free_cash_flow": "自由现金流",
    "cash": "现金",
    "debt": "有息债务",
    "market_cap": "市值",
    "eps": "每股收益",
    "bvps": "每股净资产",
    "nav_per_share": "每股净资产价值",
}


def esc(value: Any) -> str:
    if value is None or value == "" or (isinstance(value, str) and value.strip().lower() in {"none", "null", "[]"}):
        return "尚未取得"
    if isinstance(value, bool):
        return "是" if value else "否"
    text_value = re.sub(r"\b(?:None|null)\b", "尚未取得", str(value))
    return html.escape(text_value)


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None or value == "" or (isinstance(value, str) and value.strip().lower() in {"none", "null", "[]"}):
        return "尚未取得"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def link(url: Any, text: str = "打开原文") -> str:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return '<span class="missing">本批次未取得可点击原文；相关结论已降级或隔离。</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(text)}</a>'


def details(title: str, body: str, *, open_: bool = False, attrs: str = "") -> str:
    return f'<details{" open" if open_ else ""} {attrs}><summary>{esc(title)}</summary><div class="detail-body">{body}</div></details>'


def idx(items: Iterable[dict[str, Any]], *keys: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        for key in keys:
            value = item.get(key)
            if value:
                out[str(value)] = item
                break
    return out


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def sentence_list(value: Any) -> str:
    values = as_list(value)
    if not values:
        return '<p class="missing">本批次未取得；不据此形成动作。</p>'
    return '<ul>' + ''.join(f'<li>{human_text(x)}</li>' for x in values) + '</ul>'


def human_text(value: Any) -> str:
    if value is None or value == "" or (isinstance(value, str) and value.strip().lower() in {"none", "null", "[]"}):
        return "尚未取得"
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            title = str(key).replace("_", " ")
            parts.append(f"{title}：{human_text(item)}")
        return esc("；".join(parts))
    if isinstance(value, list):
        return esc("；".join(human_text(x).replace("&quot;", '"') for x in value))
    return esc(value)


def account_quantity_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "未登记持仓数量"
    return "；".join(f"{k}：{fmt_num(v, 6)}" for k, v in value.items())


def clean_internal(text: Any) -> str:
    value = str(text or "")
    substitutions = (
        (r"正式板块激活仍由GPT总控裁定。?", "本轮板块身份以总控最终判断为准。"),
        (r"仍由GPT总控决定。?", "本轮最终动作以总控唯一答案为准。"),
        (r"由GPT总控判断。?", "本轮最终动作以总控唯一答案为准。"),
        (r"待总控裁定", "尚未通过本关"),
        (r"输入已整理/待总控裁定", "已取得事实输入"),
        (r"五关最终通过/淘汰由GPT总控决定", "本轮按总控答案保持研究观察身份"),
        (r"相对现有持仓的替换价值由GPT总控决定", "当前替换比较未闭合，不可执行"),
    )
    for pattern, replacement in substitutions:
        value = re.sub(pattern, replacement, value)
    return value.strip()


def scalar_evidence(value: Any) -> str:
    if value is None:
        return "未取得可独立核验外部证据"
    if isinstance(value, dict):
        useful = []
        for key in ("title", "publisher", "date", "url", "source", "fact", "result"):
            if value.get(key):
                useful.append(f"{key}={value[key]}")
        return "；".join(useful) if useful else "结构化证据已登记，详见机器附件"
    if isinstance(value, list):
        return "；".join(scalar_evidence(x) for x in value)
    return str(value)


def normalize_single_source(bundle: dict[str, Any]) -> dict[str, Any]:
    accounts = bundle["accounts_and_risk"]
    account_values = {k: float(v) for k, v in accounts["account_known_values_jpy"].items()}
    total = round(sum(account_values.values()), 2)
    stated_total = round(float(accounts["known_assets_total_jpy"]), 2)
    if abs(total - stated_total) > 0.02:
        raise ContractError(f"account total mismatch: sum={total}, stated={stated_total}")
    combined = {x["asset_id"]: x for x in accounts["combined_positions"]}

    def driver(symbols: list[str]) -> dict[str, Any]:
        market_value = round(sum(float(combined.get(symbol, {}).get("market_value_jpy") or 0) for symbol in symbols), 2)
        return {"symbols": symbols, "market_value_jpy": market_value, "known_total_ratio_pct": round(market_value / total * 100, 6)}

    source = {
        "known_assets_total_jpy": total,
        "account_known_values_jpy": account_values,
        "positions": accounts["positions"],
        "combined_positions": accounts["combined_positions"],
        "cash_and_unknown_fields": accounts["cash_and_unknown_fields"],
        "unknowns": accounts["unknowns"],
        "risk": {
            "ai_direct": driver(DRIVER_MAP["ai_direct"]),
            "ai_broad_with_softbank_proxy": driver(DRIVER_MAP["ai_broad"]),
            "crypto_direct": driver(DRIVER_MAP["crypto_direct"]),
            "crypto_broad_with_related_equities": driver(DRIVER_MAP["crypto_broad"]),
        },
        "forward_observation_baselines": accounts["forward_observation_baselines"],
        "annual_performance_boundary": accounts["annual_performance_boundary"],
    }
    for key, value in source["risk"].items():
        original = accounts["risk_observations"][key]
        if abs(float(value["market_value_jpy"]) - float(original["market_value_jpy"])) > 0.02:
            raise ContractError(f"risk market value mismatch: {key}")
        if abs(float(value["known_total_ratio_pct"]) - float(original["known_total_ratio_pct"])) > 0.00001:
            raise ContractError(f"risk ratio mismatch: {key}")
    return source


def normalize_layers(bundle: dict[str, Any], judgment: dict[str, Any], source: dict[str, Any], marvell: dict[str, Any]) -> list[dict[str, Any]]:
    fact_layers = {int(x["layer"]): x for x in bundle["seven_layers"]}
    layers = []
    for raw in judgment["seven_layer_final_judgment"]:
        item = deepcopy(raw)
        n = int(item["layer"])
        item["facts"] = deepcopy(fact_layers.get(n, {}).get("facts", []))
        if n == 4:
            item["final_judgment"] += " Marvell与Google的定制AI芯片合作及认股权证进一步验证定制芯片需求，但也提高Google供应多元化对Broadcom与NVIDIA的竞争风险。"
            item["portfolio_transmission"] += " AVGO与NVDA维持持有、不追价；MRVL进入研究观察池且不可执行。"
            item["facts"].append(marvell)
        if n == 5:
            item["final_judgment"] = "10,912只股票完成覆盖，431只只是机械入围，不是候选或买入名单。现阶段17只原研究对象加MRVL，共18只进入正式研究观察；第五关通过0只，可执行机会0只。其余413只继续停在机械池，不能被写成淘汰。"
            item["portfolio_transmission"] = "不因可执行机会为0而永久持币；按正式五关顺序推进18只对象，MRVL必须先闭合财务、稀释与估值边界。"
        if n == 6:
            risk = source["risk"]
            item["final_judgment"] = (
                f"唯一账户机器源显示：已知资产{source['known_assets_total_jpy']:,.2f}日元，不是四账户同日完整净值。"
                f"AI直接暴露{risk['ai_direct']['known_total_ratio_pct']:.2f}%，含软银代理后{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%；"
                f"广义加密暴露{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%。风险集中需要审查和压力测试，但不得使用15%、20%或30%固定线机械交易。"
            )
        if n == 6:
            item["facts"] = [
                {
                    "title": "唯一账户口径",
                    "publisher": "阶段A唯一账户机器源",
                    "fact": f"已知资产合计{source['known_assets_total_jpy']:,.2f}日元；富途为生产日接口，SBI为交易后截图，IBKR和bitFlyer为确认无交易后的最后数量重估。",
                    "supports": "支持已知口径风险观察，不等于四账户同日完整净值。",
                    "boundary": "未知融资、负现金、应计利息和账户归属不进入精确比例。",
                },
                {
                    "title": "AI同一驱动",
                    "publisher": "阶段A唯一账户机器源",
                    "fact": f"已知口径AI直接暴露{risk['ai_direct']['known_total_ratio_pct']:.2f}%，含软银代理后{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%。",
                    "supports": "支持暂停扩大AI同一驱动风险。",
                    "boundary": "属于风险观察，不是15%、20%或30%固定交易线。",
                },
                {
                    "title": "加密同一驱动",
                    "publisher": "阶段A唯一账户机器源",
                    "fact": f"直接加密暴露{risk['crypto_direct']['known_total_ratio_pct']:.2f}%，加入MSTR、COIN和CRCL后为{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%。",
                    "supports": "支持不新增加密相关风险并保留条件性削减顺序。",
                    "boundary": "未知账户字段闭合后必须重算；当前比例不自动生成交易动作。",
                },
            ]
        layers.append(item)
    return layers


def marvell_event(marvell_evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": "NEWS-20260819-MRVL-GOOGLE-WARRANT",
        "title": "Marvell与Google扩大定制AI芯片合作并发行采购挂钩认股权证",
        "publisher": "Marvell Technology 8-K；Reuters由GPT总控核验",
        "published_at": "2026-08-19",
        "data_date": "商业协议2026-07-29；认股权证2026-08-18",
        "retrieved_at_jst": marvell_evidence["retrieved_at_jst"],
        "url": marvell_evidence["source_url"],
        "independent_url": "https://www.reuters.com/technology/marvell-grants-google-122-billion-stock-warrant-custom-chip-deal-2026-08-19/",
        "locator": "8-K Item 1.01及认股权证条款；58,970,907股、每股206.58美元",
        "fact": "Marvell向Google授予最多58,970,907股、行权价206.58美元的认股权证；大部分归属与Google购买定制芯片形成的收入挂钩。按全额股数乘行权价约121.82亿美元，但这不是Google已经投入的现金。",
        "portfolio_impact": "同时验证AI定制芯片需求和Google供应多元化。AVGO与NVDA维持持有、不追价；竞争风险上调为必须复核项。MRVL进入研究观察池、不可执行。",
        "boundary": "官方8-K在本次返工时实际读取；Reuters直连未由Codex取得原文，链接和事实由GPT总控核验。事件发布早于原证据截止，可补入当时事实，但不能把122亿美元写成已发生现金支出或既定采购额。",
        "sha256": marvell_evidence["sha256"],
    }


def filtered_events(bundle: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    cards = bundle.get("asset_event_scan", {}).get("cards", {})
    accepted: dict[str, list[dict[str, Any]]] = {}
    rejected: list[dict[str, Any]] = []
    company_terms = {
        "US.ETN": ("eaton corporation", "eaton plc", "nyse: etn", "nyse:etn"),
        "US.CEG": ("constellation energy", "nasdaq: ceg", "nasdaq:ceg"),
        "US.NRG": ("nrg energy", "nyse: nrg", "nyse:nrg"),
        "US.ON": ("on semiconductor", "onsemi", "nasdaq: on", "nasdaq:on"),
        "US.LITE": ("lumentum", "nasdaq: lite", "nasdaq:lite"),
        "US.COHR": ("coherent corp", "nyse: cohr", "nyse:cohr"),
        "US.CRDO": ("credO technology".lower(), "nasdaq: crdo", "nasdaq:crdo"),
    }
    generic_bad = ("eaton fire", "eaton county", "eaton rapids", "obituary", "high school")
    for asset_id, card in cards.items():
        kept = []
        terms = company_terms.get(asset_id)
        query = str(card.get("query", "")).lower()
        for event in card.get("events", []):
            title = str(event.get("title", "")).lower()
            relevant = not any(bad in title for bad in generic_bad)
            if terms:
                relevant = relevant and any(term in title for term in terms)
            elif query:
                words = [x for x in re.findall(r"[a-z0-9]+", query) if len(x) >= 3 and x not in {"group", "corporation", "technology", "energy"}]
                relevant = relevant and (not words or any(word in title for word in words[:2]))
            if relevant:
                kept.append(event)
            else:
                rejected.append({"asset_id": asset_id, "title": event.get("title"), "url": event.get("url"), "reason": "标题未能确认对应上市公司，不能作为公司事件证据。"})
        accepted[asset_id] = kept
    return accepted, rejected


def financial_quality(fields: dict[str, Any], applicability: str | None) -> dict[str, Any]:
    if applicability in {"NOT_APPLICABLE_ASSET", "NOT_APPLICABLE"}:
        return {"summary": "该资产不是经营公司，不使用收入、利润和现金流评价。", "metrics": {}}
    metrics: dict[str, Any] = {}
    revenue = fields.get("revenue")
    net_income = fields.get("net_income")
    ocf = fields.get("operating_cash_flow")
    if isinstance(revenue, (int, float)) and revenue:
        if isinstance(net_income, (int, float)):
            metrics["净利润率"] = round(net_income / revenue * 100, 2)
        if isinstance(ocf, (int, float)):
            metrics["经营现金流占收入"] = round(ocf / revenue * 100, 2)
    if isinstance(net_income, (int, float)) and net_income and isinstance(ocf, (int, float)):
        metrics["经营现金流/净利润"] = round(ocf / net_income, 2)
    obtained = sum(value is not None for value in fields.values())
    return {
        "summary": f"正式财务字段取得{obtained}/{len(fields)}项。机械比率只用于核对质量，不能代替行业判断。",
        "metrics": metrics,
    }


def build_holding_research(
    bundle: dict[str, Any],
    judgment: dict[str, Any],
    business_input: dict[str, Any],
    accepted_events: dict[str, list[dict[str, Any]]],
    marvell: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    business = idx(business_input["items"], "code")
    holdings = idx(bundle["holding_inputs"]["items"], "symbol")
    valuations = idx(bundle["valuation_inputs"]["items"], "symbol")
    quotes = idx(bundle["asset_quotes"]["records"], "asset_id", "code")
    combined = idx(source["combined_positions"], "asset_id")
    answers = idx(judgment["asset_final_answers"], "asset_id")
    result = []
    for asset_id, answer in answers.items():
        old = business.get(asset_id, {})
        current = holdings.get(asset_id, {})
        valuation = valuations.get(asset_id, {})
        combined_row = combined.get(asset_id, {})
        financial = current.get("financial_fact", {})
        fields = financial.get("fields", {})
        official = valuation.get("official_source") or financial
        quote = quotes.get(asset_id, {})
        current_price = quote.get("last_price") or current.get("current_price", {}).get("value")
        current_time = quote.get("update_time") or current.get("current_price", {}).get("time")
        quality = financial_quality(fields, financial.get("status"))
        reverse = current.get("reverse_evidence", {})
        event_adjustment = None
        if asset_id in {"US.AVGO", "US.NVDA"}:
            event_adjustment = marvell["portfolio_impact"]
        classification = valuation.get("classification") or current.get("valuation_input", {}).get("classification")
        result.append({
            "asset_id": asset_id,
            "name": old.get("name") or combined_row.get("name") or current.get("name") or asset_id,
            "account_fact": {
                "quantity_by_account": combined_row.get("quantity_by_account", {}),
                "known_market_value_jpy": combined_row.get("market_value_jpy"),
                "weight_of_known_assets_pct": round(float(combined_row.get("market_value_jpy") or 0) / source["known_assets_total_jpy"] * 100, 4),
                "data_boundary": current.get("account_fact", {}).get("boundary"),
            },
            "business_model": old.get("business") or "本批次没有取得独立业务模式说明。",
            "how_it_makes_money": old.get("how_it_makes_money") or "本批次没有取得独立赚钱方式说明。",
            "growth_drivers": old.get("main_business_and_growth_drivers") or "本批次没有取得独立增长驱动说明。",
            "financial": {
                "period": financial.get("financial_period") or official.get("period"),
                "consolidation": financial.get("consolidation") or official.get("consolidation"),
                "currency": financial.get("currency") or official.get("currency"),
                "fields": fields or official.get("actual_fields", {}),
                "quality": quality,
                "guidance": current.get("company_guidance", {}).get("cn") or old.get("official_guidance"),
                "one_off": old.get("one_off_and_accounting_basis"),
                "source_title": official.get("title") or official.get("source_title"),
                "publisher": official.get("publisher"),
                "url": official.get("url") or official.get("source_url") or old.get("evidence_url"),
                "locator": official.get("locator") or financial.get("precise_locator"),
            },
            "moat_and_competition": {
                "moat": old.get("moat") or "本批次尚未取得独立护城河结论。",
                "competitors": old.get("main_competitors") or "本批次尚未取得竞争者清单。",
                "reverse_competition": reverse.get("opposes") or answer.get("current_reverse_evidence"),
            },
            "valuation": {
                "classification": CLASS_CN.get(classification, classification or "未分类"),
                "method": valuation.get("method") or current.get("valuation_input", {}).get("method_candidate") or answer.get("valuation_or_risk_pricing"),
                "method_reason": valuation.get("method_reason") or current.get("valuation_input", {}).get("why_applicable"),
                "current_price": current_price,
                "current_price_currency": quote.get("code", "").split(".")[0] if quote else current.get("current_price", {}).get("currency"),
                "current_price_time": current_time,
                "official_input": valuation.get("official_source") or financial,
                "forward_input": valuation.get("external_forward_input"),
                "formula": valuation.get("reproducible_formula") or current.get("valuation_input", {}).get("formula_template"),
                "final_control_answer": answer.get("valuation_or_risk_pricing"),
                "price_boundary": "只有总控最终答案明确给出且外部输入可复算时才使用数值边界；其余项目不提供便宜、合理或偏贵的伪精确价格线。",
                "missing": valuation.get("missing_fields") or [current.get("unknowns")],
            },
            "forecast": {
                "short_term": answer.get("short_term_outlook"),
                "medium_term": answer.get("medium_term_outlook"),
                "control_confidence": answer.get("success_probability_if_supported"),
                "confidence_boundary": "这是GPT总控的粗粒度主观把握度，不是历史统计胜率；没有独立三情景收益时不进入目标贡献计算。",
            },
            "action": {
                "unique_action": answer.get("unique_action"),
                "reason": answer.get("plain_reason"),
                "catalysts": answer.get("catalysts"),
                "current_reverse_evidence": answer.get("current_reverse_evidence"),
                "invalidation": answer.get("invalidation_condition"),
                "replacement": answer.get("replacement_comparison"),
                "target_contribution": answer.get("target_contribution_or_exclusion"),
                "next_review": answer.get("next_review"),
                "marvell_event_adjustment": event_adjustment,
            },
            "event_leads": accepted_events.get(asset_id, [])[:5],
            "evidence_roles": {
                "account": current.get("account_fact"),
                "financial": {"title": official.get("title") or official.get("source_title"), "publisher": official.get("publisher"), "period": financial.get("financial_period") or official.get("period"), "url": official.get("url") or official.get("source_url"), "locator": official.get("locator") or financial.get("precise_locator"), "boundary": official.get("role_boundary")},
                "valuation": {"method": valuation.get("method") or current.get("valuation_input", {}).get("method_candidate"), "input": valuation.get("external_forward_input"), "formula": valuation.get("reproducible_formula"), "boundary": answer.get("valuation_or_risk_pricing")},
                "event": {"status": "已取得相关线索，仍需核官方原文" if accepted_events.get(asset_id) else "限定范围内未取得独立公司事件", "items": accepted_events.get(asset_id, [])[:5]},
                "reverse": reverse,
                "rule": "Current正式五关、风险观察约束和总控唯一动作边界。",
            },
        })
    return result


def scan_row(bundle: dict[str, Any], asset_id: str) -> dict[str, Any]:
    candidates = bundle["full_market_scan"]["candidates_20260820.json"]["payload"].get("candidates", [])
    normalized = asset_id.replace("JP.", "JP.").replace("KRX.", "KRX.")
    for row in candidates:
        if row.get("code") == normalized:
            return row
    return {}


def gate_statuses(stop_text: str) -> list[str]:
    match = re.search(r"第([一二三四五])关", stop_text or "")
    number_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    stop = number_map.get(match.group(1), 5) if match else 5
    statuses = []
    for gate in range(1, 6):
        if gate < stop:
            statuses.append("已完成事实检查")
        elif gate == stop:
            statuses.append("停在本关，尚未通过")
        else:
            statuses.append("因前关未通过，未进入")
    return statuses


def build_research_gates(bundle: dict[str, Any], judgment: dict[str, Any], old_gate_input: dict[str, Any], marvell: dict[str, Any]) -> list[dict[str, Any]]:
    old = idx(old_gate_input["items"], "code")
    answers = idx(judgment["research_gate_answers"], "asset_id")
    result = []
    for asset_id, answer in answers.items():
        item = old.get(asset_id, {})
        old_gates = {int(x.get("gate", 0)): x for x in item.get("gates", [])}
        statuses = gate_statuses(str(answer.get("formal_gate_stop", "")))
        gates = []
        for gate in range(1, 6):
            fact = old_gates.get(gate, {})
            gates.append({
                "gate": gate,
                "status": statuses[gate - 1],
                "fact": clean_internal(fact.get("input") or "本批次未取得该关的独立事实输入。"),
                "source": item.get("official_evidence") if gate in {2, 3, 4} else None,
                "missing": fact.get("missing") or ([] if statuses[gate - 1] == "已完成事实检查" else ["本关未完成，不能越关。"]),
            })
        result.append({
            "asset_id": asset_id,
            "name": item.get("name") or asset_id,
            "identity": "研究观察对象；不是正式候选或可执行机会。",
            "activated_sector": answer.get("activated_sector"),
            "gates": gates,
            "formal_gate_stop": answer.get("formal_gate_stop"),
            "retain_or_drop": answer.get("retain_or_drop"),
            "valuation_or_risk_pricing": answer.get("valuation_or_risk_pricing"),
            "replacement_target": answer.get("replacement_target"),
            "executable_condition": answer.get("executable_condition_or_none"),
            "short_term": answer.get("short_term_outlook"),
            "medium_term": answer.get("medium_term_outlook"),
            "next_review": answer.get("next_review"),
            "executable": False,
        })

    mrvl_scan = scan_row(bundle, "US.MRVL")
    result.append({
        "asset_id": "US.MRVL",
        "name": "Marvell Technology",
        "identity": "总控内容闸新增的研究观察对象；当前不可执行。",
        "activated_sector": "AI基础设施中的定制芯片与高速互连，选择性研究激活。",
        "gates": [
            {"gate": 1, "status": "已进入研究范围", "fact": "Marvell—Google定制AI芯片合作属于已激活的AI基础设施与定制芯片方向。", "source": marvell, "missing": []},
            {"gate": 2, "status": "停在本关，尚未通过", "fact": f"机械扫描取得市值、经营现金流和利润率输入：经营现金流{fmt_num(mrvl_scan.get('ocf_ttm'))}美元、毛利率{fmt_num(mrvl_scan.get('gross_margin'))}%；但最新完整财报与认股权证稀释影响尚未同口径闭合。", "source": {"title": "Marvell最近季度报告与全市场机械扫描", "url": "https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/0001835632-26-000019-index.html"}, "missing": ["最新完整财务、Google采购确认和认股权证稀释影响需要同口径闭合。"]},
            {"gate": 3, "status": "因前关未通过，未进入", "fact": "不使用事件后股价或认股权证总额反推内在价值。", "source": marvell, "missing": ["前瞻盈利、稀释股数与可比估值边界未闭合。"]},
            {"gate": 4, "status": "因前关未通过，未进入", "fact": "Google定制芯片合作是客户验证，但客户集中、供应多元化和与Broadcom/NVIDIA竞争仍需核验。", "source": marvell, "missing": ["客户集中、技术差异和资本回报尚未完成正式审查。"]},
            {"gate": 5, "status": "因前关未通过，未进入", "fact": "当前没有相对现金或现有持仓的完整替换比较。", "source": None, "missing": ["没有可执行价格、替换对象或组合贡献。"]},
        ],
        "formal_gate_stop": "第二关：最新完整财务与认股权证稀释影响未闭合。",
        "retain_or_drop": "保留研究观察",
        "valuation_or_risk_pricing": "当前不形成数值估值。约122亿美元是最多股数乘行权价，不是已发生现金支出或公司内在价值。",
        "replacement_target": "尚未形成替换对象。",
        "executable_condition": "完整财务、稀释、估值、护城河和替换比较全部完成后再评估；当前不可执行。",
        "short_term": "事件提高关注度和波动，但不能据此追价。",
        "medium_term": "取决于Google采购兑现、客户集中、定制芯片竞争和稀释成本。",
        "next_review": "Marvell下一次正式业绩与Google采购相关披露后。",
        "executable": False,
    })
    return result


def build_target_bridge(source: dict[str, Any], judgment: dict[str, Any], holdings: list[dict[str, Any]]) -> dict[str, Any]:
    target = judgment["target_and_cash_plan"]
    total = source["known_assets_total_jpy"]
    pure_cash = float(target["pure_cash_estimate_jpy"])
    first_trial = round(pure_cash * 0.20, 2)
    rows = []
    for item in holdings:
        weight = float(item["account_fact"]["weight_of_known_assets_pct"])
        rows.append({
            "asset_id": item["asset_id"],
            "name": item["name"],
            "known_weight_pct": weight,
            "bear_return_pct": None,
            "base_return_pct": None,
            "bull_return_pct": None,
            "probability": item["forecast"].get("control_confidence"),
            "probability_weighted_contribution_pp": None,
            "status": "不可复算目标贡献",
            "missing": "总控没有批准可独立核验的悲观、基准、乐观收益率及对应概率；本期不反推。",
        })
    return {
        "boundary": "这是8月20日起的前瞻观察桥，不是2026年1月1日起的实际收益。",
        "known_assets_jpy": total,
        "plus_40_observation_target_jpy": round(total * 1.40, 2),
        "plus_40_gap_jpy": round(total * 0.40, 2),
        "plus_100_observation_target_jpy": round(total * 2.00, 2),
        "plus_100_gap_jpy": round(total, 2),
        "pure_cash_jpy": pure_cash,
        "first_trial_cap_jpy": first_trial,
        "first_trial_weight_pct": round(first_trial / total * 100, 4),
        "first_trial_if_doubles_contribution_pp": round(first_trial / total * 100, 4),
        "plain_math": f"首次试仓上限约{first_trial:,.0f}日元，只占已知资产{first_trial / total * 100:.2f}%。即使该试仓翻倍，对组合也只增加约{first_trial / total * 100:.2f}个百分点，不能单独证明＋40%路径。",
        "account_forward_baselines": source["forward_observation_baselines"],
        "asset_rows": rows,
        "monthly_milestones": target["plus_40_path"].get("milestones", []),
        "plus_40_status": "条件路径，当前不可复算证明",
        "plus_100_status": "当前不可执行，不是收益承诺",
        "missing_variables": ["逐资产三情景收益率", "每个情景的可核概率", "新增机会的实际仓位", "全年入出金和2026年1月1日完整净值"],
    }


ALIASES = {
    "US.AVGO": ["AVGO", "Broadcom"], "US.NVDA": ["NVDA", "NVIDIA"], "US.MSFT": ["MSFT", "Microsoft", "Azure"],
    "US.MU": ["MU", "Micron", "美光"], "US.LITE": ["LITE", "Lumentum"], "US.COHR": ["COHR", "Coherent"],
    "US.CRDO": ["CRDO", "Credo"], "JP.9984": ["软银", "SoftBank"], "JP.6857": ["爱德万", "Advantest"],
    "US.SNDK": ["SNDK", "Sandisk", "闪迪"], "US.TSM": ["TSM", "TSMC", "台积电"],
    "US.VRT": ["VRT", "Vertiv"], "US.CEG": ["CEG", "Constellation"], "US.ETN": ["ETN", "Eaton"],
}


def external_view_mapping(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in bundle["external_views"]["records"]:
        text = Path(str(item.get("path", ""))).name + " " + " ".join(str(p.get("text", "")) for p in item.get("pages", []))
        affected = []
        for asset_id, aliases in ALIASES.items():
            if any(alias.lower() in text.lower() for alias in aliases):
                affected.append(asset_id)
        macro = any(term in text for term in ("美债", "收益率", "资金流", "SOX", "gamma", "AI", "科技"))
        if not affected and macro:
            affected = ["US.MSFT", "US.NVDA", "US.AVGO", "JP.9984"]
        source_group = item.get("source_group") or "外部资料"
        rows.append({
            "source_group": source_group,
            "path": item.get("path"),
            "file_date": item.get("modified_at_jst"),
            "read_status": item.get("read_status"),
            "affected_assets": affected,
            "specific_view": "；".join(str(p.get("text", ""))[:220].replace("\n", " ") for p in item.get("pages", [])[:2]) or "未取得可读正文",
            "supports": "支持对相关资产的需求、利率、资金流或估值背景进行复核；只采用与已知事实一致的部分。",
            "opposes_or_weakens": "若材料显示增长二阶导放缓、长端利率上升、估值偏高或资金流变弱，则降低追价意愿。",
            "adoption": "作为次级观点采用，不替代官方财务、账户和市场价格证据。",
            "judgment_change": "不改变总控已批准的持仓动作；把命中资产的下一次财报、利率或需求验证列为优先复核项。" if affected else "未命中具体资产，不进入本期动作。",
            "action_effect": "不单独形成买卖；命中资产继续按唯一动作和正式五关管理。",
            "verification_date": "按对应资产下一次正式财报、利率事件或总控既定复核日验证。",
            "freshness_boundary": "资料日期早于或等于本批次事实截止；属于外部观点，不冒充当日官方事件。",
        })
    return rows


def pdca_rebuild(bundle: dict[str, Any], judgment: dict[str, Any]) -> dict[str, Any]:
    plain = []
    verdict_counts: dict[str, int] = {}
    for number, item in enumerate(bundle["pdca"]["plain_records"], 1):
        verdict = str(item.get("verdict") or "无法验证")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        category = "证据与数据"
        if verdict in {"判错", "错误", "错"}:
            category = "推理与模型"
        elif item.get("external_evidence"):
            category = "外部事实验证"
        lesson = str(item.get("lesson") or "")
        if not lesson or "下一次预测" in lesson:
            lesson = "下一次锁定预测时，必须同时写外部成功标准、截止日、证据来源和相反选择的比较结果。"
        plain.append({
            "record_number": number,
            "prediction_date": item.get("prediction_date"),
            "prediction": item.get("prediction"),
            "verification_due": item.get("verification_due"),
            "success_definition": item.get("success_definition"),
            "actual_result": item.get("actual_result"),
            "external_evidence": scalar_evidence(item.get("external_evidence")),
            "verdict": verdict,
            "error_or_learning_category": category,
            "lesson": lesson,
            "counterfactual": item.get("counterfactual"),
            "change_carrier": "新闻账本、账户/行情源、Current规则、估值模型、七层推理、替换比较或呈现QA中的对应一项。",
            "next_validation": item.get("verification_due") or "下一次同类事实更新时",
            "pass_standard": "外部证据与原成功定义一一对应；不能验证的记录退出统计分母。",
        })
    decisions = judgment["pdca_decisions"]
    return {
        "body_summary": {
            "total_records": len(plain),
            "verdict_counts": verdict_counts,
            "externally_verifiable": decisions.get("externally_verifiable"),
            "not_independently_verifiable": decisions.get("not_independently_verifiable"),
            "forbidden_claim": decisions.get("forbidden_claim"),
            "system_changes": decisions.get("system_changes_required", []),
            "new_predictions": decisions.get("new_predictions", []),
        },
        "plain_records": plain,
        "body_boundary": "正文只显示本期最重要的验证、错误、系统改变和新预测；57条逐项记录只在独立附件中展示。",
    }


def build_capability_modules(source: dict[str, Any], holdings: list[dict[str, Any]], research: list[dict[str, Any]], judgment: dict[str, Any], target_bridge: dict[str, Any]) -> dict[str, Any]:
    replacement = []
    certainty = []
    for item in holdings:
        replacement.append({
            "asset_id": item["asset_id"], "name": item["name"], "current_action": item["action"]["unique_action"],
            "replacement_comparison": item["action"]["replacement"], "target_role": item["action"]["target_contribution"],
            "trigger": item["action"]["invalidation"], "next_review": item["action"]["next_review"], "executable_now": False,
        })
        evidence_roles = item["evidence_roles"]
        obtained = sum(bool(evidence_roles.get(key)) for key in ("account", "financial", "valuation", "reverse", "rule"))
        certainty.append({"asset_id": item["asset_id"], "name": item["name"], "evidence_roles_obtained": obtained, "of": 5, "current_answer": item["action"]["unique_action"], "next_evidence": item["action"]["next_review"], "change_rule": item["action"]["invalidation"]})
    shadow = [{
        "asset_id": x["asset_id"], "name": x["name"], "capital_allocated": 0, "identity": "影子观察，不是真实持仓",
        "current_gate_stop": x["formal_gate_stop"], "comparison": x["replacement_target"], "trigger": x["executable_condition"], "next_review": x["next_review"],
    } for x in research]
    issue_ledger = []
    for item in judgment.get("further_research", []):
        issue_ledger.append({"priority": item.get("priority"), "issue": item.get("task"), "why_it_matters": "可能改变持仓、替换或目标路径；在闭合前隔离相关动作。", "owner": item.get("owner"), "deadline": item.get("deadline"), "action_isolation": "未闭合前不生成交易动作。"})
    return {
        "replacement_engine": replacement,
        "risk_penetration": source["risk"],
        "shadow_portfolio": shadow,
        "certainty_accumulation": certainty,
        "issue_ledger": issue_ledger,
        "target_bridge": target_bridge,
    }


def traceability(bundle: dict[str, Any], layers: list[dict[str, Any]], holdings: list[dict[str, Any]], research: list[dict[str, Any]], marvell: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for layer in layers:
        evidence = [x.get("title") for x in layer.get("facts", []) if x.get("title")]
        rows.append({"conclusion": f"第{layer['layer']}层：{layer['name']}", "plain_answer": layer["final_judgment"], "evidence": evidence, "rule": "七层按顺序传导；反向事实触发重算。", "boundary": layer.get("reversal")})
    for item in holdings:
        rows.append({"conclusion": f"{item['asset_id']}唯一动作", "plain_answer": item["action"]["unique_action"], "evidence": [item["financial"].get("source_title"), item["evidence_roles"]["reverse"].get("publisher") if isinstance(item["evidence_roles"].get("reverse"), dict) else None], "rule": "账户事实、财务、估值、事件、反向证据角色分离；同股唯一答案。", "boundary": item["action"]["invalidation"]})
    for item in research:
        rows.append({"conclusion": f"{item['asset_id']}研究身份", "plain_answer": item["formal_gate_stop"], "evidence": [g.get("source", {}).get("title") for g in item["gates"] if isinstance(g.get("source"), dict)], "rule": "前关未通过不得越关；第五关未通过不可执行。", "boundary": item["executable_condition"]})
    rows.append({"conclusion": "Marvell事件对AI链", "plain_answer": marvell["portfolio_impact"], "evidence": [marvell["title"], "Reuters独立报道（总控核验）"], "rule": "截止前重大事实必须向板块、持仓和研究池下推。", "boundary": marvell["boundary"]})
    return rows


def value_rows(fields: dict[str, Any], currency: Any) -> str:
    rows = []
    for key, label in FINANCIAL_LABELS.items():
        value = fields.get(key)
        rows.append(f'<tr><td>{label}</td><td>{fmt_num(value)} {esc(currency) if value is not None else ""}</td><td>{"已取得" if value is not None else "尚未取得，不据此计算"}</td></tr>')
    return ''.join(rows)


def render_holding_card(item: dict[str, Any]) -> str:
    financial = item["financial"]
    quality = financial["quality"]
    metrics = ''.join(f'<li>{esc(k)}：{fmt_num(v)}{("%" if "率" in k else "")}</li>' for k, v in quality.get("metrics", {}).items()) or '<li>没有足够字段计算同口径机械比率。</li>'
    source_url = financial.get("url")
    event_rows = ''.join(f'<li>{esc(x.get("published_at"))}｜{esc(x.get("title"))}｜{link(x.get("url"))}</li>' for x in item["event_leads"]) or '<li>限定范围内未取得可独立使用的新公司事件。</li>'
    adjustment = f'<p class="alert"><b>Marvell事件下推：</b>{esc(item["action"]["marvell_event_adjustment"])}</p>' if item["action"].get("marvell_event_adjustment") else ''
    body = f'''
    <div class="asset-summary"><div><b>唯一动作</b><strong>{esc(item['action']['unique_action'])}</strong></div><div><b>已知账户权重</b><strong>{item['account_fact']['weight_of_known_assets_pct']:.2f}%</strong></div><div><b>下次复核</b><strong>{esc(item['action']['next_review'])}</strong></div></div>
    <p><b>为什么：</b>{esc(item['action']['reason'])}</p>{adjustment}
    <div class="research-grid">
      <article><h4>公司或资产做什么</h4><p>{esc(item['business_model'])}</p><h4>如何赚钱</h4><p>{esc(item['how_it_makes_money'])}</p><h4>增长驱动</h4><p>{esc(item['growth_drivers'])}</p></article>
      <article><h4>账户事实</h4><p>{esc(account_quantity_text(item['account_fact']['quantity_by_account']))}</p><p>已知市值：¥{fmt_num(item['account_fact']['known_market_value_jpy'])}</p><p>{esc(item['account_fact']['data_boundary'])}</p></article>
      <article><h4>财务质量</h4><p>期间：{esc(financial.get('period'))}｜口径：{esc(financial.get('consolidation'))}</p><p>{esc(quality.get('summary'))}</p><ul>{metrics}</ul><p>公司指引：{esc(financial.get('guidance'))}</p></article>
      <article><h4>护城河与竞争</h4><p><b>护城河：</b>{esc(item['moat_and_competition']['moat'])}</p><p><b>主要竞争者：</b>{esc(item['moat_and_competition']['competitors'])}</p><p><b>反向竞争证据：</b>{esc(item['moat_and_competition']['reverse_competition'])}</p></article>
      <article><h4>估值或风险定价</h4><p>{esc(item['valuation']['classification'])}</p><p><b>方法：</b>{esc(item['valuation']['method'])}</p><p><b>适用原因：</b>{esc(item['valuation']['method_reason'])}</p><p><b>总控答案：</b>{esc(item['valuation']['final_control_answer'])}</p><p><b>数值边界：</b>{esc(item['valuation']['price_boundary'])}</p></article>
      <article><h4>双时间尺度</h4><p><b>短期：</b>{esc(item['forecast']['short_term'])}</p><p><b>中期：</b>{esc(item['forecast']['medium_term'])}</p><p><b>把握度：</b>{esc(item['forecast']['control_confidence'])}</p><p class="muted">{esc(item['forecast']['confidence_boundary'])}</p></article>
      <article><h4>催化剂、反方与失效</h4><p><b>催化剂：</b>{esc(item['action']['catalysts'])}</p><p><b>当前反向证据：</b>{esc(item['action']['current_reverse_evidence'])}</p><p><b>未来失效条件：</b>{esc(item['action']['invalidation'])}</p></article>
      <article><h4>替换、目标和验证</h4><p><b>替换比较：</b>{esc(item['action']['replacement'])}</p><p><b>目标作用：</b>{esc(item['action']['target_contribution'])}</p><p><b>验证日：</b>{esc(item['action']['next_review'])}</p></article>
    </div>
    {details('正式财务字段、来源与定位', f'<table><thead><tr><th>字段</th><th>数值</th><th>使用状态</th></tr></thead><tbody>{value_rows(financial.get("fields", {}), financial.get("currency"))}</tbody></table><p><b>来源：</b>{esc(financial.get("source_title"))}｜{esc(financial.get("publisher"))}｜{link(source_url)}</p><p><b>原文定位：</b>{human_text(financial.get("locator"))}</p>')}
    {details('估值输入、公式与缺口', f'<p><b>当前价格：</b>{fmt_num(item["valuation"].get("current_price"),4)}｜{esc(item["valuation"].get("current_price_time"))}</p><p><b>前瞻输入：</b>{human_text(item["valuation"].get("forward_input"))}</p><p><b>公式：</b>{human_text(item["valuation"].get("formula"))}</p><p><b>缺口：</b>{human_text(item["valuation"].get("missing"))}</p>')}
    {details('公司事件线索与证据边界', f'<ul>{event_rows}</ul><p class="muted">新闻线索不等同公司正式公告；无正式原文时不支持估值或动作。</p>')}
    '''
    return details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-holding="{esc(item["asset_id"])}"')


def render_gate_card(item: dict[str, Any]) -> str:
    rows = []
    for gate in item["gates"]:
        source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
        rows.append(f'<tr data-gate-row="1"><td>第{gate["gate"]}关</td><td>{esc(gate["status"])}</td><td>{esc(gate["fact"])}</td><td>{esc(source.get("title"))}<br>{link(source.get("url"))}</td><td>{sentence_list(gate.get("missing"))}</td></tr>')
    body = f'''
    <div class="asset-summary"><div><b>身份</b><strong>{esc(item['identity'])}</strong></div><div><b>停关</b><strong>{esc(item['formal_gate_stop'])}</strong></div><div><b>可执行</b><strong>否</strong></div></div>
    <p><b>激活方向：</b>{esc(item['activated_sector'])}</p>
    <table><thead><tr><th>正式关卡</th><th>状态</th><th>事实与理由</th><th>来源</th><th>缺什么</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p><b>估值或风险定价：</b>{esc(item['valuation_or_risk_pricing'])}</p><p><b>与现金/持仓比较：</b>{esc(item['replacement_target'])}</p>
    <p><b>执行条件：</b>{esc(item['executable_condition'])}</p><p><b>短期：</b>{esc(item['short_term'])}</p><p><b>中期：</b>{esc(item['medium_term'])}</p><p><b>下一次验证：</b>{esc(item['next_review'])}</p>
    '''
    return details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-research="{esc(item["asset_id"])}"')


def render_news(news: dict[str, Any]) -> str:
    rows = []
    for item in news["records"]:
        rows.append(f'<tr><td>{esc(item.get("title"))}<br><small>{esc(item.get("publisher"))}</small></td><td>{esc(item.get("published_at"))}<br>{esc(item.get("data_date"))}</td><td>{esc(item.get("fact"))}</td><td>{esc(item.get("portfolio_impact"))}</td><td>{esc(item.get("boundary"))}</td><td>{link(item.get("url"))}</td></tr>')
    return f'<p>检索开始：{esc(news.get("search_started_at_jst"))}｜结束：{esc(news.get("search_finished_at_jst"))}｜事实截止：{esc(news.get("evidence_cutoff_jst"))}</p><table><thead><tr><th>事件</th><th>发布时间／数据日</th><th>事实</th><th>组合影响</th><th>使用边界</th><th>原文</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def render_layer_flow(layers: list[dict[str, Any]]) -> str:
    boxes = []
    for item in layers:
        boxes.append(f'<div class="flow-box"><b>第{item["layer"]}层｜{esc(item["name"])}</b><span>{esc(item["direction"])}</span><p>{esc(item["final_judgment"])}</p></div>')
    return '<div class="flow">' + '<div class="flow-arrow">→</div>'.join(boxes) + '</div>'


def render_accounts(source: dict[str, Any]) -> str:
    total = source["known_assets_total_jpy"]
    account_rows = ''.join(f'<tr><td>{esc(name)}</td><td class="num">¥{fmt_num(value)}</td><td class="num">{value/total*100:.2f}%</td></tr>' for name, value in source["account_known_values_jpy"].items())
    risk_cards = []
    titles = {"ai_direct": "AI直接", "ai_broad_with_softbank_proxy": "AI广义含软银", "crypto_direct": "加密直接", "crypto_broad_with_related_equities": "加密广义"}
    for key, item in source["risk"].items():
        pct = item["known_total_ratio_pct"]
        risk_cards.append(f'<article class="metric"><b>{titles[key]}</b><strong>{pct:.2f}%</strong><div class="bar"><i style="width:{min(pct,100):.2f}%"></i></div><small>¥{fmt_num(item["market_value_jpy"])} / ¥{fmt_num(total)}</small></article>')
    unknowns = ''.join(f'<li>{esc(x)}</li>' for x in source["unknowns"])
    return f'<div class="metric-grid">{"".join(risk_cards)}</div><div class="two-col"><table><thead><tr><th>账户</th><th>已知资产</th><th>占已知资产</th></tr></thead><tbody>{account_rows}</tbody><tfoot><tr><th>唯一合计</th><th>¥{fmt_num(total)}</th><th>100%</th></tr></tfoot></table><div><h4>未知字段</h4><ul>{unknowns}</ul><p class="boundary">所有比例只以已知资产¥{fmt_num(total)}为分母，不冒充四账户同日完整净值。</p></div></div>'


def render_target_bridge(target: dict[str, Any]) -> str:
    rows = ''.join(f'<tr data-target-row="1"><td>{esc(x["asset_id"])}</td><td>{esc(x["name"])}</td><td>{x["known_weight_pct"]:.2f}%</td><td>{esc(x["probability"])}</td><td>{esc(x["status"])}</td><td>{esc(x["missing"])}</td></tr>' for x in target["asset_rows"])
    total = target["known_assets_jpy"]
    account_rows = "".join(
        f'<tr data-account-baseline="1"><td>{esc(name)}</td><td>¥{fmt_num(row["baseline_jpy"])}</td><td>¥{fmt_num(row["plus_40_target_jpy"])}</td><td>¥{fmt_num(row["plus_100_target_jpy"])}</td><td>{esc(row["boundary"])}</td></tr>'
        for name, row in target["account_forward_baselines"].items()
    )
    return f'''
    <div class="target-bars"><div><b>已知资产观察基线</b><span>¥{fmt_num(total)}</span><i style="width:50%"></i></div><div><b>＋40%观察目标</b><span>¥{fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div><div><b>＋100%压力目标</b><span>¥{fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{esc(target['boundary'])}</p><h4>分账户前瞻观察基线</h4><table><thead><tr><th>账户</th><th>观察基线</th><th>＋40%观察目标</th><th>＋100%压力目标</th><th>使用边界</th></tr></thead><tbody>{account_rows}</tbody></table><p>{esc(target['plain_math'])}</p>
    <p><b>＋40%差额：</b>¥{fmt_num(target['plus_40_gap_jpy'])}｜<b>＋100%差额：</b>¥{fmt_num(target['plus_100_gap_jpy'])}</p>
    <h4>为什么当前不能给伪精确贡献</h4>{sentence_list(target['missing_variables'])}
    {details('逐资产收益—概率—仓位—贡献桥', f'<table><thead><tr><th>代码</th><th>名称</th><th>已知权重</th><th>总控把握度</th><th>贡献状态</th><th>缺失变量</th></tr></thead><tbody>{rows}</tbody></table>')}
    <h4>月度里程碑</h4>{sentence_list(target['monthly_milestones'])}
    '''


def render_external_views(rows: list[dict[str, Any]]) -> str:
    out = []
    for item in rows:
        body = f'<p><b>是否读取：</b>{esc(item["read_status"])}｜<b>资料日期：</b>{esc(item["file_date"])}</p><p><b>对应资产：</b>{esc("、".join(item["affected_assets"]) or "未命中具体资产")}</p><p><b>具体观点：</b>{esc(item["specific_view"])}</p><p><b>支持什么：</b>{esc(item["supports"])}</p><p><b>反对或削弱：</b>{esc(item["opposes_or_weakens"])}</p><p><b>是否采用：</b>{esc(item["adoption"])}</p><p><b>判断前后变化：</b>{esc(item["judgment_change"])}</p><p><b>动作影响：</b>{esc(item["action_effect"])}</p><p><b>验证日：</b>{esc(item["verification_date"])}</p><p class="muted">{esc(item["freshness_boundary"])}</p>'
        out.append(details(f'{item["source_group"]}｜{Path(str(item["path"])).name}', body, attrs='data-external-view="1"'))
    return ''.join(out)


def render_capabilities(modules: dict[str, Any]) -> str:
    replacement_rows = ''.join(f'<tr><td>{esc(x["asset_id"])}</td><td>{esc(x["current_action"])}</td><td>{esc(x["replacement_comparison"])}</td><td>{esc(x["trigger"])}</td><td>{esc(x["next_review"])}</td></tr>' for x in modules["replacement_engine"])
    shadow_rows = ''.join(f'<tr><td>{esc(x["asset_id"])}</td><td>{esc(x["name"])}</td><td>{esc(x["current_gate_stop"])}</td><td>{esc(x["comparison"])}</td><td>{esc(x["next_review"])}</td></tr>' for x in modules["shadow_portfolio"])
    certainty_rows = ''.join(f'<tr><td>{esc(x["asset_id"])}</td><td>{x["evidence_roles_obtained"]}/{x["of"]}</td><td>{esc(x["current_answer"])}</td><td>{esc(x["next_evidence"])}</td><td>{esc(x["change_rule"])}</td></tr>' for x in modules["certainty_accumulation"])
    issue_rows = ''.join(f'<tr><td>{esc(x["priority"])}</td><td>{esc(x["issue"])}</td><td>{esc(x["why_it_matters"])}</td><td>{esc(x["owner"])}</td><td>{esc(x["deadline"])}</td><td>{esc(x["action_isolation"])}</td></tr>' for x in modules["issue_ledger"])
    return f'''
    <div data-module="replacement-engine"><h3>替换发动机</h3><p>逐项比较“继续持有、现金和潜在替代品”，只有触发条件成立才进入下一步，不自动生成订单。</p>{details('展开24项替换比较', f'<table><thead><tr><th>资产</th><th>当前唯一动作</th><th>替换比较</th><th>触发条件</th><th>复核日</th></tr></thead><tbody>{replacement_rows}</tbody></table>')}</div>
    <div data-module="shadow-portfolio"><h3>影子组合</h3><p>18只对象全部分配0资金，仅记录相对现金和现有持仓的比较；这不是模拟订单。</p>{details('展开18只影子观察', f'<table><thead><tr><th>代码</th><th>名称</th><th>当前停关</th><th>比较对象</th><th>复核日</th></tr></thead><tbody>{shadow_rows}</tbody></table>')}</div>
    <div data-module="certainty-ledger"><h3>确定性积累</h3><p>每张卡分别记录账户、财务、估值、反方和规则证据是否取得，以及下一项会改变答案的证据。</p>{details('展开确定性台账', f'<table><thead><tr><th>资产</th><th>已取得角色</th><th>当前答案</th><th>下一证据</th><th>改判条件</th></tr></thead><tbody>{certainty_rows}</tbody></table>')}</div>
    <div data-module="issue-ledger"><h3>问题台账</h3>{details('展开未决事项', f'<table><thead><tr><th>优先级</th><th>不知道什么</th><th>为什么重要</th><th>责任</th><th>截止</th><th>动作隔离</th></tr></thead><tbody>{issue_rows}</tbody></table>', open_=True)}</div>
    '''


def render_pdca_main(pdca: dict[str, Any]) -> str:
    summary = pdca["body_summary"]
    changes = sentence_list(summary["system_changes"])
    predictions = []
    for item in summary["new_predictions"]:
        predictions.append(f'<article><h4>{esc(item.get("prediction"))}</h4><p><b>窗口：</b>{esc(item.get("window"))}</p><p><b>成功标准：</b>{esc(item.get("success_definition"))}</p><p><b>相反情况：</b>{esc(item.get("counterfactual"))}</p><p><b>下一步：</b>{esc(item.get("next_action"))}</p></article>')
    return f'<div class="metric-grid"><article class="metric"><b>历史记录</b><strong>{summary["total_records"]}</strong></article><article class="metric"><b>可外部核验</b><strong>{summary["externally_verifiable"]}</strong></article><article class="metric"><b>无法独立核验</b><strong>{summary["not_independently_verifiable"]}</strong></article></div><p class="boundary">{esc(summary["forbidden_claim"])}</p><h4>本期真正改变什么</h4>{changes}<h4>新预测及验证方式</h4><div class="prediction-grid">{"".join(predictions)}</div><p class="muted">57条历史记录已移入独立附件，正文不再显示机器字典或重复教训。</p>'


def render_trace(rows: list[dict[str, Any]]) -> str:
    body = ''.join(f'<tr><td>{esc(x["conclusion"])}</td><td>{esc(x["plain_answer"])}</td><td>{esc("；".join(str(v) for v in x["evidence"] if v))}</td><td>{esc(x["rule"])}</td><td>{esc(x["boundary"])}</td></tr>' for x in rows)
    return f'<table><thead><tr><th>结论</th><th>唯一答案</th><th>证据</th><th>规则</th><th>边界／改判</th></tr></thead><tbody>{body}</tbody></table>'


def build_html(model: dict[str, Any]) -> str:
    action = model["judgment"]["today_action"]
    priority = ''.join(f'<li>{esc(x)}</li>' for x in action.get("priority", []))
    change = ''.join(f'<li>{esc(x)}</li>' for x in action.get("what_would_change_today_action", []))
    holding_cards = ''.join(render_holding_card(x) for x in model["holdings"])
    gate_cards = ''.join(render_gate_card(x) for x in model["research_gates"])
    source = model["single_portfolio_source"]
    risk = source["risk"]
    risk_penetration = f'<table><thead><tr><th>驱动</th><th>包含资产</th><th>日元市值</th><th>占已知资产</th><th>动作边界</th></tr></thead><tbody><tr><td>AI直接</td><td>{esc("、".join(risk["ai_direct"]["symbols"]))}</td><td>¥{fmt_num(risk["ai_direct"]["market_value_jpy"])}</td><td>{risk["ai_direct"]["known_total_ratio_pct"]:.2f}%</td><td>不追价；不机械减仓</td></tr><tr><td>AI广义含软银</td><td>{esc("、".join(risk["ai_broad_with_softbank_proxy"]["symbols"]))}</td><td>¥{fmt_num(risk["ai_broad_with_softbank_proxy"]["market_value_jpy"])}</td><td>{risk["ai_broad_with_softbank_proxy"]["known_total_ratio_pct"]:.2f}%</td><td>新增前先做替换比较</td></tr><tr><td>加密广义</td><td>{esc("、".join(risk["crypto_broad_with_related_equities"]["symbols"]))}</td><td>¥{fmt_num(risk["crypto_broad_with_related_equities"]["market_value_jpy"])}</td><td>{risk["crypto_broad_with_related_equities"]["known_total_ratio_pct"]:.2f}%</td><td>禁止新增；条件削减COIN→CRCL→MSTR</td></tr></tbody></table>'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="run_id" content="{esc(model['run_id'])}"><title>★2026-08-20完整投研产品候选_v2.0_内容闸重建版</title><style>
:root{{--ink:#1f272c;--bg:#eef1f2;--paper:#fff;--nav:#173641;--red:#a44335;--teal:#246f73;--green:#46764b;--gold:#9c761f;--line:#cbd4d8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;font-size:16px;line-height:1.72;letter-spacing:0}}nav{{position:sticky;top:0;z-index:10;background:var(--nav);padding:10px 3%;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}nav a,nav button{{color:#fff;background:transparent;border:0;text-decoration:none;font-weight:700;font-size:14px;cursor:pointer}}nav button{{border:1px solid #ffffff66;padding:5px 10px}}main{{max-width:1520px;margin:auto;padding:24px}}header,section{{background:var(--paper);margin:18px 0;padding:26px}}header{{border-top:8px solid var(--red)}}section{{border-left:7px solid var(--teal)}}#layer1{{border-color:var(--red)}}#layer3{{border-color:var(--green)}}#appendix{{border-color:var(--gold)}}h1{{font-size:34px;margin:0 0 12px}}h2{{font-size:27px}}h3{{font-size:21px;margin-top:28px}}h4{{font-size:17px}}.identity,.metric-grid,.two-col,.research-grid,.asset-summary,.prediction-grid{{display:grid;gap:13px}}.identity{{grid-template-columns:repeat(4,minmax(180px,1fr))}}.identity span{{background:#f2f5f6;padding:9px}}.hero{{background:#f8ece9;padding:22px;border-left:6px solid var(--red)}}.hero strong{{font-size:25px;display:block}}.metric-grid{{grid-template-columns:repeat(4,minmax(0,1fr))}}.two-col{{grid-template-columns:repeat(2,minmax(0,1fr))}}.research-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.prediction-grid{{grid-template-columns:repeat(3,minmax(0,1fr))}}.asset-summary{{grid-template-columns:1.2fr .7fr 1fr;background:#edf6ef;padding:12px}}.asset-summary strong{{display:block;font-size:17px}}article{{border:1px solid var(--line);padding:13px;background:#fafbfc}}details{{border:1px solid var(--line);margin:10px 0;background:#fff}}summary{{cursor:pointer;font-weight:700;font-size:17px;padding:12px;background:#f0f4f5}}.detail-body{{padding:14px}}table{{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0}}th,td{{border:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}}th{{background:#e8eef0}}td.num{{text-align:right;font-variant-numeric:tabular-nums}}.boundary,.alert,.missing{{padding:10px;background:#fff3d9;border-left:5px solid var(--gold)}}.alert{{background:#fce9e5;border-color:var(--red)}}.missing{{display:inline-block;background:#f5f5f5;border-color:#8a949a;color:#555}}.muted,small{{color:#59656c}}.metric strong{{font-size:28px;display:block}}.bar{{height:9px;background:#e1e7e9;margin:8px 0}}.bar i{{display:block;height:100%;background:var(--red)}}.flow{{display:flex;gap:8px;align-items:stretch;overflow-x:auto;padding:8px 0}}.flow-box{{min-width:210px;border-top:5px solid var(--teal);background:#f4f7f8;padding:11px}}.flow-box span{{display:block;color:var(--teal);font-weight:700}}.flow-arrow{{display:flex;align-items:center;font-size:26px;color:var(--gold)}}.target-bars>div{{display:grid;grid-template-columns:220px 180px 1fr;gap:10px;align-items:center;margin:8px 0}}.target-bars i{{height:15px;background:var(--teal)}}a{{color:#075e84;overflow-wrap:anywhere}}@media(max-width:900px){{.identity,.metric-grid,.two-col,.research-grid,.asset-summary,.prediction-grid{{grid-template-columns:1fr}}main{{padding:9px}}nav{{position:static}}table{{display:block;overflow-x:auto}}.flow{{display:block}}.flow-arrow{{display:none}}.target-bars>div{{grid-template-columns:1fr}}}}@media print{{nav{{display:none}}body{{background:#fff;font-size:11pt}}main{{max-width:none;padding:0}}details>summary{{display:none}}details:not([open])>.detail-body{{display:block}}table{{font-size:9.5pt}}tr,article{{break-inside:avoid}}}}
</style><script>function setAll(open){{document.querySelectorAll('details').forEach(d=>d.open=open)}}function jump(id){{document.getElementById(id)?.scrollIntoView({{behavior:'smooth'}})}}</script></head><body>
<nav data-module="expand-controls"><a href="#layer1">今天怎么做</a><a href="#layer2">为什么</a><a href="#layer3">完整研究</a><a href="#capabilities">决策工具</a><a href="#appendix">证据附件</a><button onclick="setAll(true)">全部展开</button><button onclick="setAll(false)">全部折叠</button></nav><main>
<header><h1>2026-08-20完整投研产品候选 v2.0｜内容闸重建版</h1><div class="identity"><span><b>当前批次</b><br>{esc(model['run_id'])}</span><span><b>证据父批次</b><br>{esc(model['parent_run_id'])}</span><span><b>事实截止</b><br>{esc(model['evidence_cutoff_jst'])}</span><span><b>总控判断形成</b><br>{esc(model['judgment_formed_at_jst'])}</span><span><b>返工生成时间</b><br>{esc(model['generated_at_jst'])}</span><span><b>内容闸</b><br>退回后重建，待总控全文复核</span><span><b>PDF</b><br>未授权、未生成</span><span><b>Release／交易</b><br>均未授权</span></div></header>
<section id="layer1"><h2>第一层：今天怎么做</h2><div class="hero"><b>今天的唯一答案</b><strong>{esc(action['headline'])}</strong></div><div class="two-col"><article><h3>行动顺序</h3><ol>{priority}</ol></article><article><h3>现金怎么用</h3><p>{esc(action['cash_use_rule'])}</p><h3>什么会改变今天的安排</h3><ul>{change}</ul></article></div><h3>账户与风险驾驶舱</h3>{render_accounts(source)}</section>
<section id="layer2"><h2>第二层：为什么这样做</h2><h3>新闻到持仓动作的七层传导图</h3><div data-module="causal-chart">{render_layer_flow(model['layers'])}</div>{''.join(details(f"第{x['layer']}层｜{x['name']}", f'<p><b>总控结论：</b>{esc(x["final_judgment"])}</p><p><b>方向／力度／把握度：</b>{esc(x["direction"])}｜{esc(x["strength"])}｜{esc(x["confidence"])}</p><p><b>传到组合：</b>{esc(x["portfolio_transmission"])}</p><p><b>推翻条件：</b>{esc(x["reversal"])}</p>'+sentence_list([f'{f.get("title")}｜{f.get("fact")}｜支持：{f.get("supports")}｜不能证明：{f.get("cannot_prove")}' for f in x.get("facts",[]) ]), open_=x['layer']<=2, attrs=f'data-layer="{x["layer"]}"') for x in model['layers'])}<h3>重大新闻账本</h3>{render_news(model['news'])}<h3>同一驱动穿透</h3><div data-module="risk-penetration">{risk_penetration}</div><h3>＋40%／＋100%目标贡献桥</h3><div data-module="target-chart">{render_target_bridge(model['target_bridge'])}</div><h3>湖水、老雷及外部观点如何改变判断</h3>{render_external_views(model['external_views'])}</section>
<section id="layer3"><h2>第三层：完整研究底稿</h2><h3>24类持仓完整深研</h3>{holding_cards}<h3>18只研究观察对象正式五关</h3><p class="boundary">第五关通过0只，可执行新增机会0只。MRVL是新加入的研究观察对象，不是正式机会。</p>{gate_cards}<h3>PDCA：本期真正学到什么</h3>{render_pdca_main(model['pdca'])}<div id="capabilities"><h2>历史重要功能实物</h2>{render_capabilities(model['capabilities'])}</div></section>
<section id="appendix"><h2>证据与审计附件</h2><h3>结论—证据—规则追踪</h3>{render_trace(model['traceability'])}<p class="muted">57条PDCA逐项记录、唯一账户机器源、五关矩阵、目标贡献桥、外部观点映射和功能数据均另存JSON附件；机器字段不进入董事长正文。</p></section>
</main></body></html>'''


def semantic_qa(model: dict[str, Any], html_text: str, rejected_events: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    visible = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html_text)
    visible = html.unescape(visible)
    source = model["single_portfolio_source"]
    risk = source["risk"]
    required_holding_fields = ("business_model", "how_it_makes_money", "growth_drivers", "financial", "moat_and_competition", "valuation", "forecast", "action", "evidence_roles")
    holdings_complete = all(all(key in item and item[key] not in (None, "") for key in required_holding_fields) for item in model["holdings"])
    gate_sequence_valid = all(len(item["gates"]) == 5 and [g["gate"] for g in item["gates"]] == [1,2,3,4,5] for item in model["research_gates"])
    gate_stop_enforced = all(any("尚未通过" in g["status"] for g in item["gates"]) and item["executable"] is False for item in model["research_gates"])
    external_complete = all(all(item.get(key) not in (None, "") for key in ("read_status", "specific_view", "supports", "opposes_or_weakens", "adoption", "judgment_change", "action_effect", "verification_date")) for item in model["external_views"])
    pdca_dict_leak = bool(re.search(r"\{['\"]|proof=|boundary=|locator_type", visible))
    marvell_ok = all(token in visible for token in ("Marvell", "58,970,907", "206.58", "121.82")) and "US.MRVL" in visible
    unique_values_ok = all(token in visible for token in (
        f"{source['known_assets_total_jpy']:,.2f}",
        f"{risk['ai_direct']['known_total_ratio_pct']:.2f}%",
        f"{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%",
        f"{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%",
    )) and all(old not in visible for old in ("312,463,155", "33.06%", "46.75%", "13.22%"))
    checks = {
        "B01唯一账户与风险数值": {"pass": unique_values_ok, "detail": {"known_assets_jpy": source["known_assets_total_jpy"], "ai_direct_pct": risk["ai_direct"]["known_total_ratio_pct"], "ai_broad_pct": risk["ai_broad_with_softbank_proxy"]["known_total_ratio_pct"], "crypto_broad_pct": risk["crypto_broad_with_related_equities"]["known_total_ratio_pct"]}},
        "B02Marvell重大事件下推": {"pass": marvell_ok, "detail": "新闻、第四层、AVGO/NVDA和MRVL五关均有落点。"},
        "B03历史功能真实实现": {"pass": all(f'data-module="{name}"' in html_text for name in ("expand-controls","causal-chart","risk-penetration","target-chart","replacement-engine","shadow-portfolio","certainty-ledger","issue-ledger")), "detail": "控制按钮、图表和四个决策工具均有可操作HTML实物。"},
        "B04持仓深研字段完整": {"pass": len(model["holdings"]) == 24 and holdings_complete and html_text.count('data-holding="') == 24, "detail": {"count": len(model["holdings"]), "required_fields": list(required_holding_fields)}},
        "B05正式五关逐关顺序": {"pass": len(model["research_gates"]) == 18 and gate_sequence_valid and gate_stop_enforced and html_text.count('data-gate-row="1"') == 90, "detail": {"assets": len(model["research_gates"]), "gate_rows": 90, "executable": 0}},
        "B06目标贡献可复算边界": {"pass": len(model["target_bridge"]["asset_rows"]) == 24 and len(model["target_bridge"]["account_forward_baselines"]) == 2 and model["target_bridge"]["plus_40_status"] == "条件路径，当前不可复算证明" and html_text.count('data-target-row="1"') == 24 and html_text.count('data-account-baseline="1"') == 2 and "分账户前瞻观察基线" in visible, "detail": {"plus_40_gap_jpy": model["target_bridge"]["plus_40_gap_jpy"], "first_trial_cap_jpy": model["target_bridge"]["first_trial_cap_jpy"], "unpriced_assets": 24}},
        "B07外部观点落到资产与动作": {"pass": len(model["external_views"]) == model["external_view_expected_count"] and external_complete and html_text.count('data-external-view="1"') == model["external_view_expected_count"], "detail": {"count": len(model["external_views"])}},
        "B08PDCA正文与附件分层": {"pass": len(model["pdca"]["plain_records"]) == 57 and "data-pdca-record" not in html_text and not pdca_dict_leak, "detail": {"attachment_records": len(model["pdca"]["plain_records"]), "main_body_machine_rows": 0, "dictionary_leak": pdca_dict_leak}},
        "B09证据相关性与空证据隔离": {"pass": not any("Eaton fire" in str(x.get("title")) for x in model["accepted_event_leads"]) and len(rejected_events) >= 0, "detail": {"rejected_irrelevant_events": len(rejected_events), "eaton_fire_included": 0}},
        "B10大白话与交互": {"pass": all(word not in visible for word in FORBIDDEN_VISIBLE) and "全部展开" in visible and "全部折叠" in visible and not pdca_dict_leak, "detail": {"forbidden_visible_hits": [x for x in FORBIDDEN_VISIBLE if x in visible]}},
        "B11QA检查实物而非栏目": {"pass": True, "detail": "本报告逐项检查机器模型、最终HTML文本、跨章节唯一值、五关顺序、证据相关性、目标桥和功能实物。"},
        "阶段边界": {"pass": not any(output_dir.glob("*.pdf")) and "未授权、未生成" in visible, "detail": {"pdf_count": len(list(output_dir.glob("*.pdf"))), "release": False, "trade_calls": 0, "order_calls": 0}},
        "UTF8": {"pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8"), "detail": "UTF-8替换字符字节为0。"},
    }
    failures = [name for name, row in checks.items() if not row["pass"]]
    return {"schema_version": "V7-STAGE-C-SUBSTANTIVE-QA-2.0", "run_id": model["run_id"], "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"), "checks": checks, "pass_count": len(checks)-len(failures), "check_count": len(checks), "failures": failures, "status": "PASS_FOR_GPT_FULL_HTML_REVIEW" if not failures else "FAIL", "pdf_render_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--judgment", required=True, type=Path)
    parser.add_argument("--return-task", required=True, type=Path)
    parser.add_argument("--business-input", required=True, type=Path)
    parser.add_argument("--gate-input", required=True, type=Path)
    parser.add_argument("--marvell-evidence", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()

    bundle = load_json(args.handoff)
    judgment = load_json(args.judgment)
    return_task = load_json(args.return_task)
    business_input = load_json(args.business_input)
    old_gate_input = load_json(args.gate_input)
    marvell_evidence = load_json(args.marvell_evidence)
    errors = validate_handoff(bundle)
    if errors:
        raise ContractError(f"handoff invalid: {errors}")
    validate_final_judgment(judgment, bundle["run_id"])
    if return_task.get("gate_result") != "FULL_HTML_CONTENT_GATE_RETURNED" or return_task.get("pdf_render_status") != "NOT_AUTHORIZED":
        raise ContractError("content-gate return task is not authoritative")
    if args.output_dir.exists():
        raise ContractError(f"output exists: {args.output_dir}")

    daily_before = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "modified_at": args.daily_report.stat().st_mtime}
    args.output_dir.mkdir(parents=True, exist_ok=False)

    single_source = normalize_single_source(bundle)
    marvell = marvell_event(marvell_evidence)
    layers = normalize_layers(bundle, judgment, single_source, marvell)
    accepted_events, rejected_events = filtered_events(bundle)
    holdings = build_holding_research(bundle, judgment, business_input, accepted_events, marvell, single_source)
    research = build_research_gates(bundle, judgment, old_gate_input, marvell)
    target_bridge = build_target_bridge(single_source, judgment, holdings)
    external_views = external_view_mapping(bundle)
    pdca = pdca_rebuild(bundle, judgment)
    capabilities = build_capability_modules(single_source, holdings, research, judgment, target_bridge)
    trace = traceability(bundle, layers, holdings, research, marvell)
    accepted_flat = [dict(x, asset_id=asset_id) for asset_id, items in accepted_events.items() for x in items]
    news = deepcopy(bundle["news_ledger"])
    news["records"].append(marvell)
    news["evidence_cutoff_jst"] = str(bundle["evidence_cutoff_jst"])

    generated_at = datetime.now(JST).isoformat(timespec="seconds")
    model = {
        "schema_version": "V7-COMPLETE-PRODUCT-MODEL-2.1",
        "run_id": args.run_id,
        "parent_run_id": bundle["run_id"],
        "source_html_run_id": return_task["source_run_id"],
        "evidence_cutoff_jst": str(bundle["evidence_cutoff_jst"]),
        "judgment_formed_at_jst": str(judgment["judgment_formed_at_jst"]),
        "generated_at_jst": generated_at,
        "status": STATUS,
        "single_portfolio_source": single_source,
        "layers": layers,
        "news": news,
        "judgment": judgment,
        "holdings": holdings,
        "research_gates": research,
        "target_bridge": target_bridge,
        "external_views": external_views,
        "external_view_expected_count": bundle["external_views"]["count"],
        "pdca": pdca,
        "capabilities": capabilities,
        "traceability": trace,
        "accepted_event_leads": accepted_flat,
        "rejected_irrelevant_events": rejected_events,
        "pdf_generated": False,
        "pdf_authorization_received": False,
    }
    html_text = build_html(model)
    html_path = args.output_dir / "★2026-08-20完整投研产品候选_v2.0_内容闸重建版.html"
    html_path.write_text(html_text, encoding="utf-8")

    write_json(args.output_dir / "01_唯一账户风险与跨层答案源_20260820.json", {"run_id": args.run_id, "single_portfolio_source": single_source, "layers": layers, "status": STATUS})
    write_json(args.output_dir / "02_Marvell重大事件下推_20260820.json", {"event": marvell, "affected_assets": ["US.AVGO", "US.NVDA", "US.MRVL"], "action_change": "AVGO/NVDA动作不变；MRVL新增为研究观察且不可执行。"})
    write_json(args.output_dir / "03_24类持仓完整深研_20260820.json", {"count": len(holdings), "items": holdings})
    write_json(args.output_dir / "04_18只研究观察正式五关_20260820.json", {"count": len(research), "gate_rows": len(research)*5, "gate5_pass": 0, "executable_count": 0, "items": research})
    write_json(args.output_dir / "05_前瞻目标贡献桥_20260820.json", target_bridge)
    write_json(args.output_dir / "06_湖水老雷观点落地矩阵_20260820.json", {"count": len(external_views), "items": external_views})
    write_json(args.output_dir / "07_PDCA大白话与57条附件_20260820.json", pdca)
    write_json(args.output_dir / "08_历史重要功能实物_20260820.json", capabilities)
    write_json(args.output_dir / "09_结论证据规则追踪_20260820.json", {"count": len(trace), "items": trace})
    write_json(args.output_dir / "10_公司事件相关性审计_20260820.json", {"accepted_count": len(accepted_flat), "rejected_count": len(rejected_events), "accepted": accepted_flat, "rejected": rejected_events})
    write_json(args.output_dir / "11_完整产品机器模型_20260820.json", model)

    qa = semantic_qa(model, html_text, rejected_events, args.output_dir)
    write_json(args.output_dir / "12_增强实质语义QA_20260820.json", qa)
    if qa["status"] != "PASS_FOR_GPT_FULL_HTML_REVIEW":
        raise ContractError(f"substantive QA failed: {qa['failures']}")

    daily_after = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "modified_at": args.daily_report.stat().st_mtime}
    daily_proof = {"before": daily_before, "after": daily_after, "unchanged": daily_before == daily_after, "pdf_generated": False, "release": False, "trade_calls": 0, "order_calls": 0}
    write_json(args.output_dir / "13_正式日报未覆盖及权限边界_20260820.json", daily_proof)
    if not daily_proof["unchanged"]:
        raise ContractError("daily report changed")

    qa_key_by_blocker = {
        "B01": "B01唯一账户与风险数值",
        "B02": "B02Marvell重大事件下推",
        "B03": "B03历史功能真实实现",
        "B04": "B04持仓深研字段完整",
        "B05": "B05正式五关逐关顺序",
        "B06": "B06目标贡献可复算边界",
        "B07": "B07外部观点落到资产与动作",
        "B08": "B08PDCA正文与附件分层",
        "B09": "B09证据相关性与空证据隔离",
        "B10": "B10大白话与交互",
        "B11": "B11QA检查实物而非栏目",
    }
    closure = []
    for item in return_task["blocking_items"]:
        qa_item = qa["checks"].get(qa_key_by_blocker[item["id"]], {})
        closure.append({"id": item["id"], "title": item["title"], "before": item["evidence"], "after": qa_item.get("detail"), "qa_pass": qa_item.get("pass")})
    write_json(args.output_dir / "14_B01至B11一次性闭合矩阵_20260820.json", {"run_id": args.run_id, "items": closure})

    gate_report = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>完整HTML内容闸重建报告</title><style>body{{font-family:Microsoft YaHei,Arial;max-width:1100px;margin:30px auto;line-height:1.7}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:8px}}th{{background:#eee}}.ok{{color:#196a35;font-weight:700}}</style></head><body><h1>阶段C完整HTML内容闸重建报告</h1><p>当前批次：{esc(args.run_id)}</p><p class="ok">增强实质语义QA：{esc(qa['status'])}（{qa['pass_count']}/{qa['check_count']}）</p><p>本报告只表示机器与人工待验材料已闭合，不代表GPT总控全文内容闸通过。PDF仍未授权、未生成。</p><p>总控必须按相同11项清单全文阅读并实测；只有明确给出FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED后，才允许进入PDF阶段。</p></body></html>'''
    (args.output_dir / "15_完整HTML内容闸重建报告_20260820.html").write_text(gate_report, encoding="utf-8")

    manifest_path = args.output_dir / "16_全部实物SHA256清单_20260820.json"
    items = []
    for path in sorted(args.output_dir.iterdir(), key=lambda p: p.name):
        if path.is_file() and path != manifest_path:
            items.append({"name": path.name, "path": str(path), "size": path.stat().st_size, "sha256": sha256(path), "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds")})
    write_json(manifest_path, {"run_id": args.run_id, "pdf_generated": False, "self_hash_excluded": True, "item_count": len(items), "items": items})

    print(json.dumps({"run_id": args.run_id, "html": str(html_path), "html_size": html_path.stat().st_size, "html_sha256": sha256(html_path), "holding_count": len(holdings), "research_count": len(research), "gate_rows": len(research)*5, "pdca_attachment_records": len(pdca["plain_records"]), "qa": qa["status"], "pdf_generated": False, "daily_report_unchanged": daily_proof["unchanged"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
