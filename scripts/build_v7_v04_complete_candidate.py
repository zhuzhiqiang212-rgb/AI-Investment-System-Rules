#!/usr/bin/env python3
"""Build the V7 complete investment-research candidate v0.4.

This is a presentation/assembly step. Business judgments are copied from the
GPT control order; the script does not invent trade actions or portfolio sizes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
PRODUCT_DATE = "2026-08-17"
CRITICAL_RUN = "V7-V04-CRITICAL-EVIDENCE-20260817-003853-JST"
CRITICAL = ROOT / "output/decision_inputs/2026-08-17" / CRITICAL_RUN
BUSINESS_INPUT = ROOT / "output/decision_inputs/2026-08-16/V7-V04-BUSINESS-INPUT-20260816-092343-JST"
BLUEPRINT = ROOT / "output/candidates/2026-08-15/V7-BLUEPRINT-DATA-CLOSE-20260816-015526-JST"
EDINET = ROOT / "output/candidates/2026-08-15/V7-BLUEPRINT-EDINET-REFRESH-20260816-002610-JST"
FUTU = ROOT / "data/accounts/futu_positions_20260817.json"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"
USDJPY = 159.304993


HOLDING_JUDGMENTS = {
    "US.MSFT": "核心持有，当前不追增；重点核查Azure增长、资本开支和自由现金流能否继续支撑年度目标。",
    "JP.9984": "持有、暂停增加；作为AI代理敞口加强压力测试。同一驱动风险恶化或出现更高胜率替代机会时，列入优先调整对象。",
    "US.NVDA": "核心持有、不追高；只有在明显回落且数据中心需求与利润率逻辑未破坏时才重新考虑增加。",
    "JP.6857": "持有、暂停增加；等待订单、利润率和半导体设备周期验证。",
    "JP.4568": "持有；重点跟踪核心管线、监管节点和商业化进度。",
    "JP.7974": "持有；新增仓位必须由硬件销量、软件装机和利润兑现支持。",
    "JP.4063": "持有，作为组合分散项；旧账户日期下不产生当日交易动作。",
    "US.MSTR": "不补仓；在COIN、CRCL、MSTR的保留顺序中处于最后，是第一顺位替换或压缩对象。",
    "BTC": "风险管理持有，不进入年度目标贡献计算；旧数据不产生当日交易动作。",
    "ETH": "风险管理持有，不进入年度目标贡献计算；旧数据不产生当日交易动作。",
    "US.SNDK": "持有但不增加；价格、拆股和财报已闭合，但券商盈亏率与成本计算仍不一致。券商市值用于账户风险，券商盈亏率不得支持估值或动作。",
    "US.AVGO": "持有、不追高；等待AI收入、利润率和指引继续兑现。",
    "US.META": "持有；IBKR不做目标管理，但必须进入逐只审查、集中度、回撤和风险管理。",
    "JP.8766": "仍持有；作为非AI及利率相关分散项继续观察。",
    "US.COIN": "在三项加密相关持仓中优先保留；目前不新增。",
    "US.CRCL": "次于Coinbase、优先于MSTR；小仓观察，不新增。",
    "JP.6758": "持有；必须正确区分持续经营利润和包含终止经营后的总体结果。",
    "JP.6954": "持有观察；等待自动化需求和订单恢复，旧数据不产生当日动作。",
    "JP.7203": "持有观察；关注汇率、关税、销量与利润率。",
    "JP.8001": "持有观察，作为业务和驱动分散项。",
    "US.SPCX": "只保留小型跟踪仓位，不增加；流动性、估值和公开财务证据不足。",
    "KRX.005930": "小仓持有观察；韩元价格、韩元市值、美元报告值和汇率日期必须分列。",
    "US.IBKR": "小仓持有观察；旧账户日期下不产生当日动作。",
    "US.TSM": "跟踪持有、不追高；优先等待估值回落或下一次财报确认后再决定是否增加。",
}

TIER_1 = ["US.ETN", "US.CEG", "JP.8306", "US.TSM", "US.VRT", "JP.8316", "JP.8411", "US.ASML"]
TIER_2 = ["US.CRDO", "US.MU", "US.WDC", "US.XOM", "US.CVX"]
TIER_3 = ["US.SNDK", "US.NVDA", "US.AVGO", "US.PLTR", "US.ON", "US.COHR", "US.LITE", "US.NRG"]
CORE_BAND = {"US.MSFT", "US.NVDA", "US.AVGO", "US.TSM", "JP.4568"}
NO_PRICE_ACTION = {"BTC", "ETH", "US.SPCX", "US.SNDK"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_html(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def esc(value: Any) -> str:
    if value is None:
        return "未取得"
    return html.escape(str(value), quote=True)


def money(value: Any, currency: str | None = None) -> str:
    if value is None:
        return "未取得"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    prefix = {"USD": "$", "JPY": "JPY ", "KRW": "KRW "}.get(currency or "", "")
    return f"{prefix}{number:,.2f}"


def compact(value: Any, currency: str = "") -> str:
    if value is None:
        return "未取得"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    unit = ""
    for divisor, suffix in ((1e12, "万亿"), (1e8, "亿"), (1e4, "万")):
        if abs(number) >= divisor:
            number /= divisor
            unit = suffix
            break
    label = {"USD": "美元", "JPY": "日元", "KRW": "韩元", "TWD": "新台币"}.get(currency, currency)
    return f"{number:,.2f}{unit}{label}"


def table(headers: list[str], rows: list[list[Any]], cls: str = "") -> str:
    head = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{x if isinstance(x, Safe) else esc(x)}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="{esc(cls)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


class Safe(str):
    pass


def source_link(url: str | None, label: str = "查看原文") -> Safe:
    if not url:
        return Safe("未取得直接链接")
    return Safe(f'<a href="{esc(url)}">{esc(label)}</a>')


def extract_price(candidate: dict[str, Any]) -> tuple[float | None, str]:
    text = str((candidate.get("gates") or [{}, {}, {}])[2].get("input", ""))
    match = re.search(r"价格=([0-9,.]+).*?（([^）]+)）", text)
    if not match:
        return None, "未取得"
    return float(match.group(1).replace(",", "")), match.group(2)


def observation_band(code: str, price: float | None, data_current: bool, candidate: bool = False) -> dict[str, Any]:
    if price is None or (not data_current and not candidate) or code in NO_PRICE_ACTION:
        return {
            "type": "研究触发条件",
            "base_price": price,
            "lower": None,
            "upper": None,
            "plain": "数据陈旧、非上市、加密或仍有口径限制，不给可执行价格区间；只列财报、估值或风险触发条件。",
        }
    if code in CORE_BAND:
        low, high, kind = price * 0.85, price * 1.15, "核心质量公司临时观察带"
        plain = f"基准价的85%以下（约{low:,.2f}）才重新评估增加；约{low:,.2f}至{high:,.2f}持有观察；超过约{high:,.2f}须复核盈利上修是否足以支持价格。"
    else:
        low, high, kind = price * 0.80, price * 1.10, "高波动/周期/高估值公司临时观察带"
        plain = f"基准价的80%以下（约{low:,.2f}）才重新评估增加；约{low:,.2f}至{high:,.2f}持有观察；超过约{high:,.2f}加强反向质疑。"
    return {"type": kind, "base_price": price, "lower": round(low, 4), "upper": round(high, 4), "plain": plain + " 这是观察区间，不是订单或精确内在价值。"}


def overlay_futu(accounts: dict[str, Any], holdings: dict[str, Any], futu: dict[str, Any]) -> None:
    old_non_futu = [row for row in accounts["account_rows"] if row["account"] != "富途"]
    fresh = []
    for pos in futu["futu_positions"]:
        currency = "JPY" if pos["symbol"].startswith("JP.") else "USD"
        fresh.append({
            "account": "富途",
            "account_property": "个人/公司属性未由OpenD字段确认",
            "instrument": pos["name"],
            "code": pos["symbol"],
            "quantity": pos["quantity"],
            "cost": pos["cost_price"],
            "latest_price": pos["broker_nominal_price"],
            "market_value": pos["broker_market_val"],
            "profit_loss": None,
            "broker_pl_ratio": pos["pl_ratio"],
            "currency": currency,
            "data_date": futu["data_date"],
            "source": str(FUTU),
            "target_management": True,
            "risk_management": True,
            "production_day_data": True,
            "freshness": "本生产批次OpenD只读刷新",
            "chairman_statement": "不适用：接口账户已刷新",
        })
    for row in old_non_futu:
        row["chairman_statement"] = "董事长声明未交易，因此沿用最近截图；不是当日接口数据。"
        row["freshness"] = "最后已知状态；未交易，因此未更新"
    accounts["account_rows"] = fresh + old_non_futu
    accounts["futu_reconciliation"] = {
        "total_assets_usd": futu["futu_cash"]["total_assets"],
        "securities_market_value_usd": futu["futu_cash"]["market_val"],
        "cash_usd": futu["futu_cash"]["cash"],
        "other_net_assets_aggregate_usd": round(
            futu["futu_cash"]["total_assets"] - futu["futu_cash"]["market_val"] - futu["futu_cash"]["cash"], 4
        ),
        "closed_to_total": True,
        "boundary": "总额闭合；其他净资产仅有汇总，具体资产名称尚未由OpenD拆分。",
        "futu_run_id": futu["run_id"],
        "input_hash": futu["input_hash"],
    }
    fresh_by_code = {row["code"]: row for row in fresh}
    for item in holdings["items"]:
        facts = [fact for fact in item["account_facts"] if fact["account"] != "富途"]
        if item["code"] in fresh_by_code:
            facts.insert(0, fresh_by_code[item["code"]])
            item["current_price"] = fresh_by_code[item["code"]]["latest_price"]
            item["price_data_time"] = futu["generated_at"]
        item["account_facts"] = facts


def make_judgment_matrix(run_id: str, generated_at: str) -> dict[str, Any]:
    holdings = [
        {"conclusion_id": f"CON-HOLD-{code.replace('.', '-')}", "code": code, "judgment": judgment, "source": "GPT总控v0.4正式开工令"}
        for code, judgment in HOLDING_JUDGMENTS.items()
    ]
    candidates = []
    for tier, codes, conclusion in (
        (1, TIER_1, "重点等待触发条件，不代表现在买入"),
        (2, TIER_2, "继续研究，当前价格下吸引力不足"),
        (3, TIER_3, "当前不新增"),
    ):
        for code in codes:
            candidates.append({"conclusion_id": f"CON-CAND-{code.replace('.', '-')}", "code": code, "tier": tier, "judgment": conclusion, "executable_now": False})
    return {
        "run_id": run_id,
        "generated_at": generated_at,
        "today": {
            "conclusion": "不机械减仓、不因年度目标追高；当前可执行新机会为0。保留现金，等待估值、财报或波动改善风险收益比。",
            "executable_new_opportunity_count": 0,
            "boundary": "没有立即买入，是当前价格下风险收益比不足，不是系统没有找到机会。",
        },
        "holdings": holdings,
        "candidates": candidates,
        "ratio_rules": "单只15%/20%和同一驱动30%均不得机械产生交易动作。",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()
    now = datetime.now(JST)
    generated_at = now.isoformat(timespec="seconds")
    run_id = args.run_id or f"V7-V04-COMPLETE-{now.strftime('%Y%m%d-%H%M%S')}-JST"
    out = ROOT / "output/candidates/2026-08-17" / run_id
    out.mkdir(parents=True, exist_ok=False)

    accounts = read_json(CRITICAL / "01_全账户资产明细_20260817.json")
    holdings = read_json(CRITICAL / "02_24类持仓业务判断输入_20260817.json")
    candidates = read_json(CRITICAL / "03_21只候选五关输入_20260817.json")
    pdca = read_json(CRITICAL / "04_PDCA汇总及逐条记录_20260817.json")
    evidence = read_json(CRITICAL / "05_精确证据注册表_20260817.json")
    input_gaps = read_json(CRITICAL / "06_缺失与冲突清单_20260817.json")
    futu = read_json(FUTU)
    layers = read_json(EDINET / "04_七层因果链检查报告_20260815.json")
    external = read_json(EDINET / "11_老雷湖水EDINET接入与使用报告_20260815.json")
    further_source = read_json(EDINET / "12_仍需进一步了解清单_20260815.json")
    mother_source = read_json(EDINET / "13_母版功能及新增成果对照_20260815.json")
    blueprint_source = read_json(BLUEPRINT / "08_蓝图覆盖矩阵_20260815.json")
    daily_before = stamp(DAILY)

    overlay_futu(accounts, holdings, futu)
    judgments = make_judgment_matrix(run_id, generated_at)
    judgment_by_code = {x["code"]: x["judgment"] for x in judgments["holdings"]}
    candidate_tier = {x["code"]: x for x in judgments["candidates"]}
    evidence_by_entity = {}
    for row in evidence["items"]:
        entity = row.get("entity")
        if entity:
            evidence_by_entity.setdefault(entity, []).append(row)

    holding_matrix = []
    for item in holdings["items"]:
        fresh = any(fact.get("production_day_data") for fact in item["account_facts"])
        band = observation_band(item["code"], item.get("current_price"), fresh)
        item["gpt_control_judgment"] = judgment_by_code[item["code"]]
        item["observation_band"] = band
        item["valuation_classification"] = (
            "无法形成可执行价格动作" if band["lower"] is None else "临时观察带；不是精确内在价值"
        )
        item["pdca_next_check"] = "下一次正式财报、账户新实物或总控指定验证日"
        holding_matrix.append({
            "code": item["code"],
            "name": item["name"],
            "account_coverage": item["account_facts"],
            "financial_period": item.get("latest_formal_financial_period"),
            "financial_source": item.get("evidence_url"),
            "judgment": item["gpt_control_judgment"],
            "valuation": item.get("valuation_numbers_and_basis"),
            "observation_band": band,
            "catalyst": item.get("short_term_catalyst"),
            "reverse_risk": item.get("maximum_reverse_risk"),
            "invalidation": item.get("invalidation_condition"),
            "completeness": "COMPLETE_WITH_EXPLICIT_LIMITS" if not item.get("missing_fields") else "PARTIAL_EXPLICIT_GAPS",
        })

    candidate_matrix = []
    for item in candidates["items"]:
        price, price_time = extract_price(item)
        tier = candidate_tier[item["code"]]
        band = observation_band(item["code"], price, True, candidate=True)
        item["gpt_control_tier"] = tier["tier"]
        item["gpt_control_judgment"] = tier["judgment"]
        item["executable_now"] = False
        item["observation_band"] = band
        item["price_and_time"] = {"price": price, "time": price_time}
        candidate_matrix.append({
            "code": item["code"], "name": item["name"], "tier": tier["tier"], "judgment": tier["judgment"],
            "five_gates": item["gates"], "price_and_time": item["price_and_time"], "observation_band": band,
            "replacement_comparison": item.get("possible_replacement_comparison"), "executable_now": False,
            "evidence": item.get("official_evidence"),
        })

    account_matrix = {
        "run_id": run_id,
        "generated_at": generated_at,
        "futu_run_id": futu["run_id"],
        "futu_input_hash": futu["input_hash"],
        "futu_reconciliation": accounts["futu_reconciliation"],
        "rows": accounts["account_rows"],
        "truth_boundary": "富途为本批次OpenD只读数据；其余账户因董事长声明未交易而沿用最近截图。不同日期不得拼成同日净值。",
        "sbi_ownership": "个人/公司归属尚未闭合，保持状态不明。",
        "samsung_currency_reconciliation": accounts.get("samsung_currency_reconciliation"),
    }

    target_path = {
        "run_id": run_id,
        "actual_progress": "缺经确认的年初统一基准，不能给出精确年度完成度。",
        "goal_40": "在核心盈利兑现、替代机会以更好风险收益比落地且回撤受控时有条件实现。",
        "goal_100": "现有证据不足以宣称可达；不得用杠杆、补仓摊低或追高强行实现。",
        "scenarios": [
            {"scenario": "压力", "conditions": "AI和加密同向回撤、日元/利率不利、盈利指引下修", "impact": "+40%明显受阻；优先保留可恢复性", "today": "不追高，保留现金和替代方案"},
            {"scenario": "基准", "conditions": "核心盈利兑现、回撤受控、观察池等待更好价格", "impact": "+40%有条件可能；+100%证据不足", "today": "持有、核查和设置触发条件"},
            {"scenario": "积极", "conditions": "AI基础设施、存储和日本金融催化兑现且估值未过度扩张", "impact": "缩小+40%差距；仍不能据此承诺+100%", "today": "只在触发条件和替代价值更优时重新评估"},
        ],
        "bottlenecks": ["AI及同一驱动暴露较高", "主要候选估值普遍不低", "缺统一年初基准", "三个人工账户不是当日数据", "SNDK券商盈亏率口径未解释"],
        "current_executable_new_opportunities": 0,
    }

    pdca_separation = {
        "run_id": run_id,
        "independent_series": 5,
        "tracking_records": 57,
        "adjudicated_tracking_points": 29,
        "consistent_tracking_points": 28,
        "inconsistent_tracking_points": 1,
        "pending_tracking_points": 28,
        "tracking_point_consistency_rate": 96.552,
        "plain_language": "28/29只表示已判定跟踪点的一致率。5个独立系列样本过少；每个系列达到最终成功定义后只能结算一次。该比例不是投资胜率、交易胜率或系统预测能力。",
        "series": pdca.get("series", []),
        "records": pdca.get("records", []),
    }

    trace = []
    for item in holdings["items"]:
        evidences = evidence_by_entity.get(item["code"], [])
        trace.append({
            "conclusion_id": f"CON-HOLD-{item['code'].replace('.', '-')}",
            "conclusion": item["gpt_control_judgment"],
            "evidence_ids": [x["evidence_id"] for x in evidences] or ["EV-ACCOUNT-LOCAL"],
            "rule_id": "RULE-DYNAMIC-HOLDING-REVIEW",
            "evidence_date": evidences[0].get("data_date") if evidences else item.get("price_data_time"),
            "source_links": [x.get("url") for x in evidences] or [fact["source"] for fact in item["account_facts"]],
            "support": "支持事实与研究输入；动作由GPT总控批准",
            "reverse_evidence": item.get("maximum_reverse_risk"),
        })
    for item in candidates["items"]:
        evidences = evidence_by_entity.get(item["code"], [])
        trace.append({
            "conclusion_id": f"CON-CAND-{item['code'].replace('.', '-')}",
            "conclusion": item["gpt_control_judgment"],
            "evidence_ids": [x["evidence_id"] for x in evidences],
            "rule_id": "RULE-FIVE-GATE-NO-AUTO-BUY",
            "evidence_date": evidences[0].get("data_date") if evidences else item["price_and_time"]["time"],
            "source_links": [x.get("url") for x in evidences] or [item.get("official_evidence", {}).get("url")],
            "support": "支持五关研究，不等于当前可以买入",
            "reverse_evidence": item["gates"][4].get("input"),
        })
    for layer in layers["layers"]:
        trace.append({
            "conclusion_id": f"CON-LAYER-{layer['layer']}", "conclusion": layer["conclusion"],
            "evidence_ids": [f"EV-LAYER-{layer['layer']}"], "rule_id": "RULE-SEVEN-LAYER-TRANSMISSION",
            "evidence_date": layer["date"], "source_links": [], "support": "支持层间传导", "reverse_evidence": layer["block"],
        })
    trace.extend([
        {"conclusion_id": "CON-TODAY-001", "conclusion": judgments["today"]["conclusion"], "evidence_ids": ["EV-FUTU-20260817", "EV-CANDIDATE-SET"], "rule_id": "RULE-RISK-REWARD-FIRST", "evidence_date": PRODUCT_DATE, "source_links": [str(FUTU)], "support": "总控业务判断与账户事实共同支持", "reverse_evidence": "若价格大幅回落且盈利逻辑未破坏，需重新评估"},
        {"conclusion_id": "CON-TARGET-001", "conclusion": "目标只做条件管理，不伪造完成度", "evidence_ids": ["EV-ACCOUNT-MIXED-DATE", "EV-PDCA-LEDGER"], "rule_id": "RULE-NO-BASELINE-NO-PRECISE-PROGRESS", "evidence_date": PRODUCT_DATE, "source_links": [str(BUSINESS_INPUT)], "support": "缺统一年初基准", "reverse_evidence": "取得完整年初基准后可重算"},
    ])
    trace_doc = {"run_id": run_id, "generated_at": generated_at, "trace_count": len(trace), "items": trace}

    feature_diff = {
        "run_id": run_id,
        "items": [
            {"feature": "三层结构与七层因果链", "action": "保留并更新", "change": "第一屏改为当前可执行机会0和现金等待逻辑"},
            {"feature": "24类持仓逐只研究", "action": "更新", "change": "写入总控逐只判断、正式财务、观察带和SNDK双收益率"},
            {"feature": "21只候选五关", "action": "更新", "change": "按三层业务排序，全部当前不可执行"},
            {"feature": "PDCA", "action": "重做口径", "change": "5个系列与57个跟踪点分离；96.552%只称跟踪点一致率"},
            {"feature": "证据链", "action": "扩展", "change": "逐持仓、逐候选、七层和目标均建立结论-证据-规则关系"},
            {"feature": "固定仓位硬线", "action": "删除机械动作", "change": "15%、20%、30%不产生自动加减仓；实际权重和压力测试保留"},
            {"feature": "原始JSON和内部状态码", "action": "从正文删除", "change": "机器字段仅在附件；正文使用大白话"},
            {"feature": "HTML折叠", "action": "保留并增强", "change": "三层跳转和一键展开/折叠；PDF强制全部展开"},
        ],
    }

    gaps = {
        "run_id": run_id,
        "blocking_for_candidate_generation": [],
        "allowed_open_items": input_gaps["allowed_nonblocking_gaps"] + [
            {"id": "OPEN-SNDK-PL", "item": "SNDK券商收益率25.21%与现价/成本计算19.19%不一致", "impact": "券商收益率不进入估值或动作"},
            {"id": "OPEN-LITE-CF", "item": "LITE财年末公告未在本包摘录段落提供全年现金流", "impact": "不补数，等待正式文件"},
            {"id": "OPEN-YEAR-BASE", "item": "缺经确认年初统一基准", "impact": "不能计算精确年度完成度"},
        ],
        "candidate_boundary": "上述缺口不阻止生成送验候选，但会限制估值、目标完成度或动作。",
    }

    blueprint_matrix = {
        "run_id": run_id,
        "items": [
            {"requirement": "第一层今天怎么做", "source": "GPT总控v0.4正式开工令", "location": "第一屏与行动清单", "status": "COVERED"},
            {"requirement": "第二层为什么", "source": str(EDINET / "04_七层因果链检查报告_20260815.json"), "location": "市场、七层、账户、目标、压力测试", "status": "COVERED"},
            {"requirement": "第三层完整研究底稿", "source": CRITICAL_RUN, "location": "24类持仓、21只候选、证据追踪、进一步了解", "status": "COVERED"},
            {"requirement": "正文大白话", "source": "Current深度标准", "location": "全部正文", "status": "COVERED"},
            {"requirement": "状态边界", "source": "Current启动包", "location": "页首和末页", "status": "COVERED"},
        ] + blueprint_source.get("items", []),
    }

    external_rows = []
    for label, key in (("老雷", "laolei"), ("湖水", "hushui")):
        for row in external.get(key, []):
            external_rows.append([
                label, row.get("date", "未取得"), "已读取", row.get("support", "未形成直接支持"),
                row.get("challenge", "仍需与官方数据交叉"), row.get("use", "只作外部观点，不替代正式数据"),
            ])

    further_items = further_source.get("items", further_source if isinstance(further_source, list) else [])
    if not isinstance(further_items, list):
        further_items = []
    further_items = further_items + [
        {"id": "FURTHER-V04-01", "unknown": "SNDK券商收益率为何与现价/成本计算不一致", "importance": "影响账面收益解释", "missing": "券商成本口径说明", "impact": "不会改变市值，但可能改变收益归因", "method": "下一次OpenD字段说明或券商对账", "eta": "下次账户核查"},
        {"id": "FURTHER-V04-02", "unknown": "候选何时出现足够估值安全垫", "importance": "决定观察池能否转为可执行机会", "missing": "价格回落或盈利上修", "impact": "可能改变当前可执行机会0", "method": "财报与价格触发检查", "eta": "下一次财报/显著波动"},
    ]

    # Machine attachments are written before the human-facing product.
    for name, value in (
        ("03_GPT总控业务判断落地矩阵_20260817.json", judgments),
        ("04_24类持仓完整性矩阵_20260817.json", {"run_id": run_id, "count": len(holding_matrix), "items": holding_matrix}),
        ("05_21只候选五关轨迹_20260817.json", {"run_id": run_id, "count": len(candidate_matrix), "items": candidate_matrix}),
        ("06_全账户资产与日期矩阵_20260817.json", account_matrix),
        ("07_年度目标路径与三情景_20260817.json", target_path),
        ("08_PDCA系列与跟踪点分离表_20260817.json", pdca_separation),
        ("09_结论证据规则追踪表_20260817.json", trace_doc),
        ("10_原产品功能保留更新新增删除对照_20260817.json", feature_diff),
        ("11_数据缺口和失败项清单_20260817.json", gaps),
        ("12_蓝图覆盖矩阵_20260817.json", blueprint_matrix),
    ):
        write_json(out / name, value)

    account_rows = []
    for row in accounts["account_rows"]:
        account_rows.append([
            row["account"], row["code"], row["instrument"], row["quantity"], money(row.get("cost"), row.get("currency")),
            money(row.get("latest_price"), row.get("currency")), money(row.get("market_value"), row.get("currency")),
            row.get("data_date"), "是" if row.get("production_day_data") else "否", row.get("chairman_statement", ""),
            "目标+风险" if row.get("target_management") else "仅风险", row.get("freshness"),
        ])

    layer_rows = [[x["layer"], x["name"], x["date"], Safe("<br>".join(esc(y) for y in x["facts"])), x["conclusion"], x["next"], x["block"]] for x in layers["layers"]]
    news_rows = [
        ["美国7月零售销售", "2026-08-14", "环比下降0.6%，控制组下降0.4%；九个月来首次下降。", "盈利预期偏负面、折现率偏正面，属于混合影响。", "同比仍增长约5%，退款、油价和Prime Day时点会扰动单月数据。", source_link("https://www.reuters.com/business/us-retail-sales-unexpectedly-fall-july-2026-08-14/", "Reuters原文")],
        ["日本央行9月加息可能性", "2026-08-14", "来源报道，尚非日本央行正式决定。Reuters援引消息人士称最早可能在9月会议加息。", "银行保险可能受益；软银、任天堂等高久期或出口资产承受利率与汇率压力。", "增长约束可能令加息推迟，不能写成已经决定。", source_link("https://www.reuters.com/world/asia-pacific/boj-eyeing-september-rate-hike-faster-pace-tightening-sources-say-2026-08-14/", "Reuters原文")],
        ["NVIDIA相关AI基础设施融资", "2026-08-14", "融资安排潜在规模超过5000亿美元，NVIDIA潜在支持最高约1250亿美元；不是已经发生的现金支出。", "支持AI基础设施需求，也提高同一驱动和融资链风险。", "私募信贷、对手方和循环融资风险可能放大资本开支回撤。", source_link("https://www.reuters.com/legal/transactional/private-credit-roundup-nvidias-half-trillion-chips-financing-plus-others-2026-08-14/", "Reuters原文")],
    ]

    holding_sections = []
    for item in holdings["items"]:
        facts = item["account_facts"]
        account_text = "；".join(
            f"{x['account']}：{x['quantity']:,.6g}，{money(x.get('market_value'), x.get('currency'))}，数据日{x['data_date']}"
            for x in facts
        ) or "没有账户实物"
        detail = item.get("formal_financial_detail") or {}
        financial = (
            f"期间：{item.get('latest_formal_financial_period')}。收入{compact(item.get('revenue'), detail.get('currency',''))}；"
            f"营业利润{compact(item.get('operating_profit'), detail.get('currency',''))}；归母/净利润{compact(item.get('net_income_attributable_or_net_income'), detail.get('currency',''))}；"
            f"经营现金流{compact(item.get('operating_cash_flow'), detail.get('currency',''))}；自由现金流{compact(item.get('free_cash_flow'), detail.get('currency',''))}。"
        )
        if item["code"] in {"BTC", "ETH"}:
            financial = "这是数字资产，不适用企业收入、利润和现金流；用流动性、采用度、托管与监管风险评估。"
        sndk = ""
        if item["code"] == "US.SNDK":
            sndk = "<div class='callout risk'><b>SNDK双口径：</b>40股；现价1,641.11美元；券商市值65,644.40美元；成本1,376.88美元；自行计算收益率约19.19%；券商显示25.21%。两者尚未闭合。市值进入风险，券商收益率不进入估值或动作。</div>"
        band = item["observation_band"]
        holding_sections.append(f'''<details class="holding" open id="holding-{esc(item['code'].replace('.','-'))}"><summary>{esc(item['code'])}｜{esc(item['name'])}｜{esc(item['gpt_control_judgment'])}</summary><div class="asset-body">{sndk}<div class="facts"><p><b>账户事实：</b>{esc(account_text)}</p><p><b>公司/资产做什么：</b>{esc(item.get('business'))}</p><p><b>如何赚钱：</b>{esc(item.get('how_it_makes_money'))}</p><p><b>增长驱动：</b>{esc(item.get('main_business_and_growth_drivers'))}</p><p><b>正式财务：</b>{esc(financial)}</p><p><b>现金、债务与特殊项目：</b>现金{esc(compact(item.get('cash'), detail.get('currency','')))}；债务/融资义务{esc(compact(item.get('debt_and_financing_obligations'), detail.get('currency','')))}；{esc(item.get('one_off_and_accounting_basis'))}</p><p><b>护城河与竞争：</b>{esc(item.get('moat'))} 主要竞争者：{esc(item.get('main_competitors'))}</p><p><b>估值方法和当前判断：</b>{esc(item.get('valuation_method_input_only'))} {esc(item.get('valuation_numbers_and_basis'))}</p><p><b>便宜/合理/偏贵：</b>{esc(item['valuation_classification'])}</p><p><b>行动观察带：</b>{esc(band['plain'])}</p><p><b>短期与一年观察：</b>{esc(item.get('short_term_catalyst'))}；一年催化：{esc(item.get('one_year_catalyst'))}</p><p><b>反向质疑：</b>{esc(item.get('maximum_reverse_risk'))}</p><p><b>推翻条件：</b>{esc(item.get('invalidation_condition'))}</p><p><b>替代比较：</b>{esc(item.get('comparison_with_holdings_and_alternatives'))}</p><p><b>PDCA验证：</b>{esc(item['pdca_next_check'])}</p><p><b>总控结论：</b>{esc(item['gpt_control_judgment'])}</p><p><b>证据：</b>{source_link(item.get('evidence_url'), '正式原文')}</p></div><div class="trace-note">结论编号 CON-HOLD-{esc(item['code'].replace('.','-'))}｜规则：动态逐只审查，不用固定比例机械交易</div></div></details>''')

    candidate_sections = []
    for item in sorted(candidates["items"], key=lambda x: (x["gpt_control_tier"], (TIER_1 + TIER_2 + TIER_3).index(x["code"]))):
        gates = "".join(f"<li><b>第{g['gate']}关：</b>{esc(g.get('input'))}</li>" for g in item["gates"])
        candidate_sections.append(f'''<details class="candidate" open id="candidate-{esc(item['code'].replace('.','-'))}"><summary>第{item['gpt_control_tier']}层｜{esc(item['code'])}｜{esc(item['name'])}｜{esc(item['gpt_control_judgment'])}</summary><div class="asset-body"><p><b>板块与当日激活证据：</b>{esc(item.get('theme'))}</p><ol class="gates">{gates}</ol><p><b>与持仓比较：</b>{esc(item.get('possible_replacement_comparison'))}</p><p><b>观察原因：</b>{esc(item.get('observation_pool_reason'))}</p><p><b>行动观察带：</b>{esc(item['observation_band']['plain'])}</p><p><b>现在怎么办：</b>当前不新增，不生成订单；等待价格、财报或事件触发后由GPT总控重新判断。</p><p><b>正式证据：</b>{source_link((item.get('official_evidence') or {}).get('url'), '查看公司/监管原文')}</p><div class="trace-note">结论编号 CON-CAND-{esc(item['code'].replace('.','-'))}｜通过扫描不等于可以买入</div></div></details>''')

    trace_rows = []
    for row in trace:
        links = [source_link(url, "原文") for url in row["source_links"] if url]
        trace_rows.append([row["conclusion_id"], row["conclusion"], "、".join(row["evidence_ids"]), row["rule_id"], row["evidence_date"], Safe(" ".join(links)), row["support"], row["reverse_evidence"]])

    pdca_series_rows = []
    for row in pdca_separation["series"]:
        pdca_series_rows.append([row.get("series_id"), row.get("layer"), row.get("code"), row.get("operator"), row.get("tracking_count"), row.get("adjudicated_count"), row.get("pending_count"), row.get("series_final_status", "尚未最终结算")])

    account_summary = accounts["futu_reconciliation"]
    direct_ai_usd = sum(float(p["broker_market_val"]) for p in futu["futu_positions"] if p["symbol"] in {"US.NVDA", "US.MSFT", "US.AVGO", "US.TSM", "US.SNDK"})
    softbank_usd = next(float(p["broker_market_val"]) for p in futu["futu_positions"] if p["symbol"] == "JP.9984") / USDJPY
    direct_ai_pct = direct_ai_usd / futu["futu_cash"]["total_assets"] * 100
    broad_ai_pct = (direct_ai_usd + softbank_usd) / futu["futu_cash"]["total_assets"] * 100

    css = '''
:root{--ink:#17212b;--soft:#5a6772;--line:#c9d1d8;--paper:#fff;--band:#eef2f4;--nav:#24313a;--red:#a63a33;--green:#246746;--gold:#8a6718;--blue:#235f86}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#e8ecef;color:var(--ink);font-family:"Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;line-height:1.58;font-size:10.5pt;letter-spacing:0}.page{max-width:1180px;margin:0 auto;background:var(--paper);box-shadow:0 0 24px #0002}header{padding:28px 38px 20px;border-top:10px solid var(--nav)}h1{font-size:25pt;line-height:1.25;margin:0 0 10px}h2{font-size:17pt;border-bottom:2px solid var(--nav);padding-bottom:5px;margin:26px 0 12px}h3{font-size:13pt;margin:19px 0 8px}.meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.status{border:1px solid var(--line);padding:9px;background:#f7f8f9}.warn{color:var(--gold);font-weight:800}.bad{color:var(--red);font-weight:800}nav{position:sticky;top:0;z-index:8;background:var(--nav);padding:8px 16px;display:flex;gap:6px;flex-wrap:wrap}nav a,nav button{color:white;background:transparent;border:1px solid #ffffff70;padding:5px 8px;text-decoration:none;font:inherit;cursor:pointer;border-radius:4px}main{padding:0 38px 54px}.screen{min-height:72vh}.callout{border-left:5px solid var(--blue);background:#f2f6f8;padding:11px 14px;margin:10px 0}.action{border-left-color:var(--green);background:#f2f8f4}.risk{border-left-color:var(--red);background:#fff4f3}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.panel{border:1px solid var(--line);padding:12px;background:#fff}.panel h3{margin-top:0}.metric{font-size:18pt;font-weight:800}.table-wrap{overflow-x:auto;margin:8px 0 18px}table{border-collapse:collapse;width:100%;table-layout:auto}th,td{border:1px solid var(--line);padding:6px 7px;text-align:left;vertical-align:top;font-size:9pt;overflow-wrap:anywhere}th{background:#e8edf0}tr:nth-child(even) td{background:#fafbfc}details{border:1px solid var(--line);margin:10px 0;background:#fff}summary{font-weight:800;padding:10px 12px;background:#e9eef1;cursor:pointer}.asset-body{padding:7px 12px 12px}.facts{columns:2;column-gap:24px}.facts p{break-inside:avoid;margin:7px 0}.gates{padding-left:22px}.gates li{margin:6px 0}.trace-note{font-size:8.6pt;color:var(--soft);border-top:1px dashed var(--line);padding-top:5px}.small{font-size:9pt;color:var(--soft)}.page-break{break-before:page}.avoid{break-inside:avoid}.bar{height:14px;background:#dce4e9;margin:4px 0}.bar>span{display:block;height:100%;background:var(--blue)}code{font-family:Consolas,monospace;font-size:.9em;overflow-wrap:anywhere}a{color:#155a84}
@media(max-width:760px){header,main{padding-left:16px;padding-right:16px}.meta,.grid{grid-template-columns:1fr}.facts{columns:1}h1{font-size:20pt}}
@page{size:A4 portrait;margin:13mm 11mm 15mm}@media print{body{background:#fff;font-size:10.2pt}.page{box-shadow:none;max-width:none}nav{display:none}header,main{padding-left:0;padding-right:0}.screen{min-height:0}details{break-inside:auto}details>summary{break-after:avoid}.facts{columns:1}th,td{font-size:9pt;padding:4px 5px}a{color:#000;text-decoration:none}}
'''

    html_doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2026-08-17完整投研产品候选v0.4</title><style>{css}</style></head><body><div class="page"><header><h1>★2026-08-17完整投研产品候选 v0.4</h1><p>产品生成日：2026-08-17 JST｜生成时间：{esc(generated_at)}｜run_id：<code>{esc(run_id)}</code></p><div class="meta"><div class="status"><b>业务复验</b><br><span class="warn">等待独立复验</span><div class="small">business_pass=PENDING_INDEPENDENT_REVIEW</div></div><div class="status"><b>最终产品复验</b><br><span class="warn">等待独立复验</span><div class="small">final_product_pass=PENDING_INDEPENDENT_REVIEW</div></div><div class="status"><b>发布状态</b><br><span class="bad">未授权</span><div class="small">release_status=NOT_AUTHORIZED</div></div><div class="status"><b>当前可执行</b><br><span class="bad">否</span><div class="small">current_executable=false</div></div></div><p class="small">完整候选，不是正式产品；不构成交易授权。未登记Release，未覆盖正式日报，未生成订单。</p></header><nav><a href="#layer1">第一层 今天怎么做</a><a href="#layer2">第二层 为什么</a><a href="#layer3">第三层 研究底稿</a><a href="#accounts">全账户</a><a href="#holdings">24类持仓</a><a href="#candidates">21只候选</a><a href="#target">目标</a><a href="#pdca">PDCA</a><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">全部展开</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">全部折叠</button></nav><main>
<section id="layer1" class="screen"><h2>第一层｜今天怎么做</h2><div class="callout action"><h3>一句话结论</h3><p><b>不机械减仓，不为年度目标追高，今天没有需要立即执行的新买入。</b>不是系统没找到机会，而是主要候选当前价格下风险收益比不够好。保留现金，等待估值回落、财报确认或市场波动给出更好条件。</p></div><div class="grid"><div class="panel"><div class="metric">0</div><b>当前可执行新机会</b><p>21只观察池继续有效；没有一只被写成“现在可以买”。</p></div><div class="panel"><div class="metric">{direct_ai_pct:.3f}% / {broad_ai_pct:.3f}%</div><b>AI直接 / 含软银广义暴露</b><p>按本批次富途总资产和8月14日USD/JPY估算；用于风险观察，不是固定硬线。</p></div><div class="panel"><div class="metric">$68,150.64</div><b>富途现金</b><p>本批次OpenD只读刷新；保留现金等待更好的风险收益比。</p></div><div class="panel"><div class="metric">5 / 57</div><b>独立预测系列 / 连续跟踪点</b><p>已判定29点，其中28点一致、1点不一致；样本很少。</p></div></div><h3>今日做什么</h3><ol><li>核心持仓继续持有，但新增AI仓位前先比较同一驱动暴露与替代价值。</li><li>保留现金，等待重点候选触发更有利的估值、财报或事件条件。</li><li>加密相关保留顺序为COIN、CRCL、MSTR；MSTR不补仓，是第一顺位替换或压缩对象。</li><li>SNDK市值继续计入风险，券商收益率不用于估值；持有但不增加。</li><li>继续核对Azure、AI资本开支、日本利率、存储周期和三个人工账户的新实物。</li></ol><h3>今日不做什么</h3><p>不因15%、20%或30%固定比例自动交易；不追高，不补仓摊低，不把观察池写成买入清单，不用旧截图冒充当日数据，不生成订单。</p><div class="callout risk"><b>主要瓶颈：</b>AI及同一驱动暴露较高；候选估值普遍不低；缺统一年初基准；三个人工账户不是当日数据；SNDK券商收益率口径未解释。</div><h3>全账户覆盖状态</h3>{table(['账户','标的','数量','成本','最新价','市值','数据日','当日数据','董事长声明','用途','限制'],account_rows)}</section>
<section id="layer2" class="page-break"><h2>第二层｜为什么这样做</h2><h3>当日市场、宏观与重大新闻</h3><p class="small">市场与新闻事实沿用优先输入中的最新可核材料；每项均显示原始日期，不把8月14/15材料冒充8月17新事件。</p>{table(['事件','发布日期','事实','对组合影响','反向风险','来源'],news_rows)}<h3>七层因果链</h3>{table(['层','名称','证据日期','事实','结论','传给下一层','边界'],layer_rows)}<h3>完整传导</h3>{table(['链路','事实到行动'],[[x['chain_id'],x['path']] for x in layers['complete_chains']])}<h3>全账户、现金和同一驱动</h3><p>富途总资产{money(account_summary['total_assets_usd'],'USD')}，证券市值{money(account_summary['securities_market_value_usd'],'USD')}，现金{money(account_summary['cash_usd'],'USD')}，其他净资产汇总{money(account_summary['other_net_assets_aggregate_usd'],'USD')}。总额闭合，但其他净资产没有逐项名称。</p><div class="bar"><span style="width:{min(100,direct_ai_pct):.3f}%"></span></div><p>AI直接暴露约{direct_ai_pct:.3f}%；加入软银代理暴露约{broad_ai_pct:.3f}%。这不是30%硬线，不自动触发交易。</p><h3>压力测试</h3>{table(['口径','AI直接跌20%','AI直接跌35%','AI广义跌20%','AI广义跌35%'],[['含SNDK券商市值','组合损失约9.630%','约16.852%','约12.295%','约21.516%'],['不含SNDK敏感性','约8.500%','约14.875%','约11.166%','约19.540%']])}<div class="grid"><div class="panel"><h3>共同估值收缩</h3><p>NVDA、MSFT、AVGO和软银若同时估值收缩，组合损失不是单只风险相加那么简单。</p></div><div class="panel"><h3>资本开支放缓</h3><p>AI需求或资产利用率不达预期，会同时压低芯片、网络、电力、散热和数据中心估值。</p></div><div class="panel"><h3>出口限制与自研芯片</h3><p>出口限制或客户自研加速会削弱GPU、先进制程和互连收入预期。</p></div><div class="panel"><h3>日本利率与日元</h3><p>银行保险可能受益，但软银、任天堂等高久期或出口资产可能承压。</p></div></div><h3>外部观点如何使用</h3>{table(['来源','日期','是否读取','支持内容','反对/风险','采用方式'],external_rows or [['老雷/湖水','见附件','已读取','支持主题与资金流观察','不替代官方数据','只作外部观点']])}</section>
<section id="layer3" class="page-break"><h2>第三层｜完整研究底稿</h2><div class="callout"><b>阅读顺序：</b>先看全账户，再看24类持仓、21只候选五关、目标和PDCA，最后核对证据链与仍需了解。</div><section id="accounts"><h2>全账户资产与日期</h2><p>富途为2026-08-17 OpenD只读刷新。SBI、IBKR、bitFlyer因董事长声明未交易而沿用最近截图，必须写成“最后已知状态”。SBI个人/公司归属仍不明，不自行拆分。</p>{table(['账户','代码','标的','数量','成本','最新价','市值','数据日','当日','未交易声明','用途','新鲜度'],account_rows)}<h3>Samsung币种分列</h3>{table(['项目','数值','日期'],[['韩元报价','242,500 KRW','2026-08-04'],['韩元持仓市值','3,637,500 KRW','2026-08-04'],['IBKR美元折算市值','$2,560.00','2026-08-04'],['隐含汇率','1,420.8984375 KRW/USD','2026-08-04']])}</section><section id="holdings" class="page-break"><h2>24类持仓逐只研究</h2><p>每只均包含业务、赚钱方式、正式财务、现金债务、护城河、估值方法、观察带、催化剂、反向质疑、失效条件、替代比较、PDCA与总控结论。</p>{''.join(holding_sections)}</section><section id="candidates" class="page-break"><h2>21只候选五关轨迹</h2><p><b>第一层：</b>重点等待触发条件；<b>第二层：</b>继续研究但当前吸引力不足；<b>第三层：</b>当前不新增。PLTR和ON通过基础扫描不等于可以买入。</p>{''.join(candidate_sections)}</section><section id="target" class="page-break"><h2>＋40%／＋100%目标路径</h2><div class="callout"><b>真实边界：</b>缺经确认年初统一基准，不能给出精确年度完成度。</div>{table(['情景','成立条件','目标影响','今天怎么办'],[[x['scenario'],x['conditions'],x['impact'],x['today']] for x in target_path['scenarios']])}<p><b>＋40%：</b>{esc(target_path['goal_40'])}</p><p><b>＋100%：</b>{esc(target_path['goal_100'])}</p><p><b>当前组合瓶颈：</b>{esc('；'.join(target_path['bottlenecks']))}</p></section><section id="pdca" class="page-break"><h2>PDCA：系列和跟踪点分开</h2><div class="grid"><div class="panel"><div class="metric">5</div><b>独立预测系列</b></div><div class="panel"><div class="metric">57</div><b>连续跟踪记录</b></div><div class="panel"><div class="metric">29</div><b>已判定跟踪点</b></div><div class="panel"><div class="metric">28 / 1 / 28</div><b>一致 / 不一致 / 待验证</b></div></div><div class="callout risk"><b>96.552%的准确说法：</b>已判定跟踪点的一致率28/29。5个独立系列样本过少；每个系列只有达到最终成功定义后才能结算一次。这个比例不是投资胜率、交易胜率或系统预测能力。</div>{table(['系列ID','层','标的','判定方式','跟踪数','已判定','待验证','系列结算'],pdca_series_rows)}</section><section class="page-break"><h2>结论—证据—规则追踪</h2><p>技术编号放在本附录，正文仍用大白话。每项重要持仓、候选、七层和目标判断都能追到证据和规则。</p>{table(['结论ID','结论','证据ID','规则ID','证据日期','原文','支持程度','反向证据'],trace_rows,'trace')}</section><section><h2>仍需进一步了解</h2>{table(['ID','还不知道什么','为什么重要','缺什么','可能改变','验证方法','时间'],[[x.get('id'),x.get('unknown'),x.get('importance'),x.get('missing'),x.get('impact'),x.get('method'),x.get('eta')] for x in further_items])}</section><section><h2>原产品功能对照与蓝图覆盖</h2>{table(['功能','处理','变化'],[[x['feature'],x['action'],x['change']] for x in feature_diff['items']])}{table(['蓝图要求','来源','产品落点','状态'],[[x.get('requirement'),x.get('source',x.get('current_evidence','上一蓝图材料')),x.get('location',x.get('product_location','本产品')),x.get('status')] for x in blueprint_matrix['items']])}</section><section><h2>数据缺口和失败项</h2>{table(['编号','仍未闭合','对本产品影响'],[[x.get('id'),x.get('item'),x.get('impact')] for x in gaps['allowed_open_items']])}<p>这些缺口不阻止形成送验候选，但会限制估值、年度完成度或交易动作；本候选没有越过这些限制。</p></section><section class="page-break"><h2>候选状态与停止边界</h2><ul><li>业务复验：等待独立复验。</li><li>最终产品复验：等待独立复验。</li><li>发布：未授权；当前不可执行。</li><li>未登记Release，未覆盖00_今日日报.pdf。</li><li>未调用交易接口，未生成或执行订单。</li><li>完成后交GPT总控全量核对，再交原GPT终验线程独立验收。</li></ul></section></section></main></div><script>document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{{const x=document.querySelector(a.getAttribute('href'));if(x&&x.tagName==='DETAILS')x.open=true}}));</script></body></html>'''

    product_html = out / "★2026-08-17完整投研产品候选_v0.4.html"
    write_html(product_html, html_doc)
    construction = {
        "run_id": run_id,
        "generated_at": generated_at,
        "task": "V7完整投研产品候选v0.4一次性生成",
        "inputs_in_priority_order": [
            "Current启动包/总索引/蓝图/验收与深度标准",
            "董事长截至2026-08-17正式裁定",
            str(CRITICAL), str(BUSINESS_INPUT), str(BLUEPRINT), str(EDINET),
        ],
        "input_hashes": {str(path): sha256(path) for path in [FUTU, CRITICAL / "02_24类持仓业务判断输入_20260817.json", CRITICAL / "03_21只候选五关输入_20260817.json", CRITICAL / "04_PDCA汇总及逐条记录_20260817.json"]},
        "daily_before": daily_before,
        "modifications": [
            "新建独立v0.4候选目录，未覆盖旧候选",
            "富途使用本生产批次OpenD只读快照",
            "落实24类持仓总控判断和21只候选三层判断",
            "加入临时行动观察带并明确不是订单或精确内在价值",
            "PDCA按5个系列与57个跟踪点分离，96.552%只称跟踪点一致率",
            "重建逐持仓、逐候选、七层和目标的证据追踪",
        ],
        "prohibitions": {"release": False, "daily_overwrite": False, "trade_api": False, "orders": False, "current_rules_modified": False},
    }
    write_json(out / "15_完整施工日志和修改前后清单_20260817.json", construction)
    write_html(out / "15_完整施工日志和修改前后清单_20260817.html", "<!doctype html><meta charset='utf-8'><title>施工日志</title><style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}li{margin:6px}</style><h1>v0.4完整施工日志和修改前后清单</h1><p>新建独立候选，不覆盖旧产品。富途接入本批次只读快照；24类持仓、21只候选、目标、PDCA和证据链按总控裁定更新。</p><ul>" + "".join(f"<li>{esc(x)}</li>" for x in construction["modifications"]) + "</ul><p>未Release、未覆盖正式日报、未调用交易接口、未生成订单。</p>")
    print(json.dumps({"run_id": run_id, "output_dir": str(out), "html": str(product_html), "daily_before": daily_before, "holding_count": len(holding_matrix), "candidate_count": len(candidate_matrix), "trace_count": len(trace)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
