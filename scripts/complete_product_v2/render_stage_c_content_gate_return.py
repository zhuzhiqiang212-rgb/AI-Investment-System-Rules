from __future__ import annotations

import argparse
import copy
import html
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.complete_product_v2 import render_stage_c_capability_closed_html as previous
JST = timezone(timedelta(hours=9))

ACCOUNT_SOURCE: dict[str, Any] = {}
FUTU_SNAPSHOT: dict[str, Any] = {}
MARKET_FACTS: dict[str, Any] = {}
REFRESHED_ACCOUNT: dict[str, Any] = {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def market_record(asset_id: str) -> dict[str, Any] | None:
    return next((row for row in MARKET_FACTS["records"] if row.get("asset_id") == asset_id), None)


def quote_value(asset_id: str) -> tuple[float, str, str]:
    row = market_record(asset_id)
    if not row:
        raise RuntimeError(f"missing refreshed quote: {asset_id}")
    if row.get("last_price") is not None:
        price = float(row["last_price"])
        raw_time = str(row.get("update_time") or MARKET_FACTS["evidence_cutoff_jst"])
        zone = "JST" if asset_id.startswith("JP.") else "ET（富途市场时间）"
        return price, f"{raw_time} {zone}", str(row["source"])
    return float(row["price"]), str(row["market_time_jst"]), str(row["source"])


def rebuild_account_source() -> dict[str, Any]:
    source = copy.deepcopy(ACCOUNT_SOURCE)
    usd_jpy, usd_jpy_time, usd_source = quote_value("USDJPY")
    krw_jpy, krw_jpy_time, krw_source = quote_value("KRWJPY")
    futu_map = {row["symbol"]: row for row in FUTU_SNAPSHOT["futu_positions"]}
    rows: list[dict[str, Any]] = []
    for old in source["positions"]:
        row = copy.deepcopy(old)
        symbol = row["asset_id"]
        price, price_time, price_source = quote_value(symbol)
        if row["account"] == "FUTU":
            position = futu_map[symbol]
            row["quantity"] = float(position["quantity"])
            row["quantity_evidence_date"] = "2026-08-21"
            row["quantity_evidence_status"] = "8月21日OpenD只读接口实测"
            row["source"] = "Futu OpenD只读持仓接口；未调用交易解锁或订单功能"
        row["price"] = price
        row["price_time_jst"] = price_time
        row["price_source"] = price_source
        if row["currency"] == "JPY":
            value = row["quantity"] * price
        elif row["currency"] == "USD":
            value = row["quantity"] * price * usd_jpy
        elif row["currency"] == "KRW":
            value = row["quantity"] * price * krw_jpy
        else:
            raise RuntimeError(f"unsupported currency: {row['currency']}")
        row["market_value_jpy"] = round(value, 2)
        row["fx_used"] = (
            {"pair": "USD/JPY", "value": usd_jpy, "time": usd_jpy_time, "source": usd_source}
            if row["currency"] == "USD" else
            {"pair": "KRW/JPY", "value": krw_jpy, "time": krw_jpy_time, "source": krw_source}
            if row["currency"] == "KRW" else
            {"pair": "不需要换汇", "value": 1.0, "time": price_time, "source": "日元原币计价"}
        )
        rows.append(row)

    futu_total_jpy = float(FUTU_SNAPSHOT["futu_cash"]["total_assets"]) * usd_jpy
    futu_positions_jpy = sum(row["market_value_jpy"] for row in rows if row["account"] == "FUTU")
    futu_cash_and_other_jpy = futu_total_jpy - futu_positions_jpy
    broker = FUTU_SNAPSHOT["futu_cash"]
    cash_rows = copy.deepcopy(source["cash_and_unknown_fields"])
    futu_cash = next(row for row in cash_rows if row["account"] == "FUTU")
    futu_cash.update({
        "name": "现金及尚未拆分的其他净资产",
        "market_value_jpy": round(futu_cash_and_other_jpy, 2),
        "data_date": "2026-08-21",
        "status": "8月21日OpenD实测；账户总额已闭合，内部构成仍有未拆分项",
        "components": {
            "cash_usd": broker["cash"],
            "account_market_value_usd": broker["market_val"],
            "total_assets_usd": broker["total_assets"],
            "other_net_assets_usd": round(broker["total_assets"] - broker["market_val"] - broker["cash"], 4),
            "usd_jpy": usd_jpy,
            "usd_jpy_time_jst": usd_jpy_time,
        },
    })
    ibkr_cash = next(row for row in cash_rows if row["account"] == "IBKR")
    ibkr_cash["market_value_jpy"] = round(2056.28 * usd_jpy, 2)
    ibkr_cash["status"] = "8月4日最后确认现金，董事长8月19日确认其后无交易；按8月21日汇率重估，利息和费用变化仍未知"

    account_totals: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        account_totals[row["account"]] += row["market_value_jpy"]
    for row in cash_rows:
        account_totals[row["account"]] += float(row["market_value_jpy"])
    account_totals["FUTU"] = round(futu_total_jpy, 2)
    known_total = round(sum(account_totals.values()), 2)

    combined: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"quantity_by_account": {}, "market_value_jpy": 0.0, "name": ""}
    )
    for row in rows:
        item = combined[row["asset_id"]]
        item["asset_id"] = row["asset_id"]
        item["name"] = row["name"]
        item["quantity_by_account"][row["account"]] = row["quantity"]
        item["market_value_jpy"] += row["market_value_jpy"]
    combined_rows = sorted(
        ({**value, "market_value_jpy": round(value["market_value_jpy"], 2)} for value in combined.values()),
        key=lambda row: row["market_value_jpy"], reverse=True,
    )
    combined_map = {row["asset_id"]: row for row in combined_rows}

    def risk(symbols: set[str]) -> dict[str, Any]:
        value = sum(combined_map[symbol]["market_value_jpy"] for symbol in symbols if symbol in combined_map)
        return {
            "symbols": sorted(symbols), "market_value_jpy": round(value, 2),
            "known_total_ratio_pct": round(value / known_total * 100.0, 6),
            "denominator": "8月21日已知资产观察总额；手工账户仍保留各自证据日期",
        }

    ai_direct = {"US.AVGO", "US.MSFT", "US.NVDA", "US.SNDK", "US.TSM"}
    crypto_direct = {"BTC", "ETH"}
    source.update({
        "known_assets_total_jpy": known_total,
        "account_known_values_jpy": {key: round(value, 2) for key, value in account_totals.items()},
        "unknowns": [
            "SBI个人与公司账户归属未闭合；2026-08-19 18:50 JST交易后截图已读取，数量按8月21日价格重估。",
            "SBI买付余力不等同于完整现金、融资及应计利息拆分。",
            "IBKR使用2026-08-04最后截图；董事长于8月19日确认其后无交易，利息、费用、负现金和融资仍不是生产日实物。",
            "bitFlyer使用2026-08-11最后截图；董事长于8月19日确认其后无交易。",
            "不同账户证据日期不同，已知资产合计不是四账户同日完整净值。",
        ],
        "positions": rows,
        "combined_positions": combined_rows,
        "cash_and_unknown_fields": cash_rows,
        "risk": {
            "ai_direct": risk(ai_direct),
            "ai_broad_with_softbank_proxy": risk(ai_direct | {"JP.9984"}),
            "crypto_direct": risk(crypto_direct),
            "crypto_broad_with_related_equities": risk(crypto_direct | {"US.MSTR", "US.COIN", "US.CRCL"}),
        },
        "forward_observation_baselines": {
            "FUTU": {"baseline_jpy": account_totals["FUTU"], "plus_40_target_jpy": round(account_totals["FUTU"] * 1.4, 2), "plus_100_target_jpy": round(account_totals["FUTU"] * 2.0, 2), "boundary": "8月21日OpenD当日实测前瞻观察基线，不是1月1日年度收益基线。"},
            "SBI账户归属尚未确认": {"baseline_jpy": account_totals["SBI账户归属尚未确认"], "plus_40_target_jpy": round(account_totals["SBI账户归属尚未确认"] * 1.4, 2), "plus_100_target_jpy": round(account_totals["SBI账户归属尚未确认"] * 2.0, 2), "boundary": "8月19日交易后数量按8月21日收盘价重估；账户归属仍未闭合。"},
        },
        "annual_performance_boundary": "缺少2026年1月1日完整净值及全年净入出金，不能计算年度实际累计收益或精确目标差额。",
        "refresh_audit": {
            "futu_snapshot_run_id": FUTU_SNAPSHOT["run_id"],
            "futu_collected_at_jst": FUTU_SNAPSHOT["generated_at"],
            "market_cutoff_jst": MARKET_FACTS["evidence_cutoff_jst"],
            "usd_jpy": usd_jpy, "usd_jpy_time_jst": usd_jpy_time,
            "topix_status": "自动行情源失败，未写成没有TOPIX行情",
        },
    })
    return source


def refresh_capability(capability: dict[str, Any]) -> None:
    global REFRESHED_ACCOUNT
    if not REFRESHED_ACCOUNT:
        REFRESHED_ACCOUNT = rebuild_account_source()
    combined = {row["asset_id"]: row for row in REFRESHED_ACCOUNT["combined_positions"]}
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    for cap in capability["holdings_24"]:
        symbol = cap["symbol"]
        combined_row = combined[symbol]
        price, price_time, source = quote_value(symbol)
        cap["market_value_jpy"] = combined_row["market_value_jpy"]
        cap["known_asset_weight_pct"] = round(combined_row["market_value_jpy"] / total * 100.0, 6)
        cap["quantity_by_account"] = combined_row["quantity_by_account"]
        cap["current_price"] = {"value": price, "time": price_time, "source": source}
    research_quotes = {}
    for item in capability["research_18"]:
        price, price_time, source = quote_value(item["asset_id"])
        old = market_record(item["asset_id"]) or {}
        item["current_quote"] = {
            "last_price": price, "update_time": price_time, "source": source,
            "pe_ratio": old.get("pe_ratio"), "pb_ratio": old.get("pb_ratio"),
        }
        research_quotes[item["asset_id"]] = item["current_quote"]
    capability["quote_refresh"] = {
        "records": [{"code": key, **value} for key, value in research_quotes.items()],
        "log": {"status": "FETCH_OK", "started_at_jst": MARKET_FACTS["started_at_jst"], "finished_at_jst": MARKET_FACTS["finished_at_jst"], "api": "OpenD只读行情及公开行情补足", "trade_calls": 0, "requested": 18, "received": 18},
    }
    capability["evidence_cutoff_jst"] = MARKET_FACTS["evidence_cutoff_jst"]


def weighted_scenario(decision: dict[str, Any], current: float) -> dict[str, float]:
    values = decision["scenario_values"]
    probs = decision["scenario_probability_pct"]
    weighted = sum(float(values[key]) * float(probs[key]) / 100.0 for key in ("bear", "base", "bull"))
    expected = (weighted / current - 1.0) * 100.0
    return {"weighted_value": weighted, "expected_return_pct": expected}


def apply_holdings(old_holdings: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]) -> list[dict[str, Any]]:
    refresh_capability(capability)
    rows = ORIGINAL_APPLY_HOLDINGS(old_holdings, capability, final)
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    for item in rows:
        decision = decision_map[item["asset_id"]]
        if decision["target_contribution_included"]:
            current = float(cap_map[item["asset_id"]]["current_price"]["value"])
            calc = weighted_scenario(decision, current)
            weight = float(cap_map[item["asset_id"]]["known_asset_weight_pct"])
            contribution = weight * calc["expected_return_pct"] / 100.0
            item["scenario_decision"]["expected_return_pct"] = round(calc["expected_return_pct"], 6)
            item["scenario_decision"]["target_contribution_pp"] = round(contribution, 6)
            item["scenario_decision"]["current_price_used"] = current
            item["scenario_decision"]["current_price_time"] = cap_map[item["asset_id"]]["current_price"]["time"]
            item["scenario_decision"]["weighted_scenario_value"] = round(calc["weighted_value"], 6)
            item["action"]["target_contribution"] = f"按8月21日账户权重机械复算：{contribution:+.4f}个百分点。"
    return rows


def apply_research(old_research: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]) -> list[dict[str, Any]]:
    refresh_capability(capability)
    return ORIGINAL_APPLY_RESEARCH(old_research, capability, final)


def build_target_bridge(capability: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    refresh_capability(capability)
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    rows = []
    contribution = 0.0
    quantified_weight = 0.0
    scenario_totals = {"bear": 0.0, "base": 0.0, "bull": 0.0}
    usd_jpy, usd_jpy_time, _ = quote_value("USDJPY")
    for symbol, cap in cap_map.items():
        decision = decision_map[symbol]
        current = float(cap["current_price"]["value"])
        row = {
            "asset_id": symbol, "name": cap["name"],
            "known_weight_pct": float(cap["known_asset_weight_pct"]),
            "current_price": current, "current_price_time": cap["current_price"]["time"],
            "current_price_source": cap["current_price"]["source"],
            "fx_value": usd_jpy if symbol.startswith("US.") else 1.0,
            "fx_time": usd_jpy_time if symbol.startswith("US.") else cap["current_price"]["time"],
            "fx_pair": "USD/JPY" if symbol.startswith("US.") else "原币为日元或本期不需要换汇",
            "target_contribution_included": decision["target_contribution_included"],
            "unique_action": decision["unique_action"],
            "scenario_values": decision.get("scenario_values"),
            "scenario_probability_pct": decision.get("scenario_probability_pct"),
            "probability_band": "悲观{bear}%／基准{base}%／乐观{bull}%".format(**decision["scenario_probability_pct"]) if decision.get("scenario_probability_pct") else "本期没有数值概率",
        }
        if decision["target_contribution_included"]:
            calc = weighted_scenario(decision, current)
            row.update(calc)
            row["target_contribution_pp"] = row["known_weight_pct"] * calc["expected_return_pct"] / 100.0
            row["formula"] = "概率加权价值=悲观值×悲观概率+基准值×基准概率+乐观值×乐观概率；预期收益=概率加权价值÷当前价−1；组合贡献=账户权重×预期收益"
            if symbol == "JP.4568":
                row["zero_explanation"] = "上一版恰好为0，是因为当时概率加权价值2,867.50日元与当时当前价2,867.50日元完全相同；8月21日价格刷新后按新价重新计算，不再强行保留0。"
            contribution += row["target_contribution_pp"]
            quantified_weight += row["known_weight_pct"]
            for key in scenario_totals:
                scenario_return = (float(decision["scenario_values"][key]) / current - 1.0) * 100.0
                scenario_totals[key] += row["known_weight_pct"] * scenario_return / 100.0
        else:
            row.update({"weighted_value": None, "expected_return_pct": None, "target_contribution_pp": None, "formula": "本期没有可靠数值情景，不按0计入目标桥。"})
        rows.append(row)
    unquantified = 100.0 - quantified_weight
    residual_40 = (40.0 - contribution) / (unquantified / 100.0)
    residual_100 = (100.0 - contribution) / (unquantified / 100.0)
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    portfolio = final["portfolio_target_judgment"]
    return {
        "boundary": "这是8月21日已知资产前瞻观察桥，不是2026年1月1日起的实际年度收益；手工账户仍保留各自证据日期。",
        "known_assets_jpy": total, "plus_40_observation_target_jpy": round(total * 1.4, 2),
        "plus_100_observation_target_jpy": round(total * 2.0, 2),
        "quantified_asset_count": 9, "quantified_weight_pct": round(quantified_weight, 6),
        "unquantified_weight_pct": round(unquantified, 6),
        "probability_weighted_contribution_pp": round(contribution, 6),
        "scenario_contribution_pp": {**{key: round(value, 6) for key, value in scenario_totals.items()}, "probability_weighted": round(contribution, 6)},
        "plus_40_status": "NOT_PROVEN", "plus_100_status": "NOT_FEASIBLE_UNDER_CURRENT_EVIDENCE",
        "plain_language_reason": f"9项数值情景按8月21日当前价、账户权重和汇率重算后，概率加权贡献约{contribution:+.2f}个百分点。其余资产和现金没有被当成0，但缺少可复算收益输入，因此当前仍不能证明＋40%路径成立，＋100%也没有可信可执行路径。",
        "residual_required_average_return_pct": {"for_plus_40": round(residual_40, 6), "for_plus_100": round(residual_100, 6)},
        "required_monthly_compound_pct": portfolio["required_monthly_compound_from_august_18_pct"],
        "cash_role": portfolio["cash_opportunity_cost"], "fallback_route": portfolio["fallback_route"],
        "monthly_milestones": portfolio["monthly_milestones"], "next_review": portfolio["next_full_review_jst"],
        "asset_rows": rows, "unquantified_is_zero": False,
        "fx": {"USD/JPY": usd_jpy, "time_jst": usd_jpy_time},
    }


def apply_pdca(model: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    audit = previous.legacy.rebuild_pdca_quality(model)
    all_new = copy.deepcopy(final["pdca_new_predictions"])
    process_qa = [row for row in all_new if row["prediction_id"] == "P-20260821-02"]
    investment = [row for row in all_new if row["prediction_id"] != "P-20260821-02"]
    summary = model["pdca"]["body_summary"]
    summary["new_predictions"] = all_new
    summary["investment_predictions"] = investment
    summary["process_quality_checks"] = process_qa
    summary["new_quality_baseline_count"] = len(investment)
    summary["probability_policy"] = copy.deepcopy(final["probability_policy"])
    audit.update({"investment_prediction_count": len(investment), "process_qa_count": len(process_qa), "all_records": all_new})
    layer7 = next(row for row in model["layers"] if row["layer"] == 7)
    layer7.update({
        "final_judgment": "本期建立5条投资预测基线，另有1条产品流程QA；两者分开统计。57条历史记录逐条展示其可验证性、结果、归因和改进。",
        "portfolio_transmission": "只有投资预测进入未来概率校准；流程QA用于检查产品有没有把媒体预期写成正式决定。",
        "reversal": "到验证日没有独立外部证据时，记录退出统计分母，不追溯补造。",
        "facts": [
            {
                "title": "57条历史记录的本期处理",
                "publisher": "本产品第三层PDCA正文",
                "fact": "57条历史记录逐条保留；缺少独立外部成功标准的记录明确列为无法验证并退出统计分母。",
                "supports": "支持把历史错误、归因、相反选择和改进直接交给董事长阅读。",
                "cannot_prove": "不能据此公布投资预测胜率。",
                "url": "#pdca",
            },
            {
                "title": "本期新记录分组",
                "publisher": "本产品第三层PDCA正文",
                "fact": "本期新建5条投资预测和1条产品流程QA；流程QA不进入投资预测校准。",
                "supports": "支持以后分别检查投资判断和产品表述质量。",
                "cannot_prove": "尚未到验证日，不能提前登记判对。",
                "url": "#pdca",
            },
        ],
    })
    return audit


def build_news(model: dict[str, Any]) -> None:
    old_records = [row for row in model["news"].get("records", []) if row.get("event_id") not in {"NEWS-20260820-MARKET-SNAPSHOT"}]
    macro = {row["name"]: row for row in MARKET_FACTS["macro_records"]}
    cutoff = MARKET_FACTS["evidence_cutoff_jst"]
    records = old_records + [
        {
            "event_id": "NEWS-20260821-GLOBAL-MARKETS", "title": "8月21日全球股市、长债、油价和美元出现相互拉扯",
            "publisher": "Reuters报道的可读取转载页；AP交叉核验；行情由公开图表接口复核",
            "published_at": "2026-08-21", "data_date": "2026-08-21盘中", "retrieved_at_jst": cutoff,
            "url": "https://ae.marketscreener.com/news/global-stocks-set-for-biggest-weekly-fall-since-mid-july-dollar-on-the-defensive-ce7858dadb89ff26",
            "independent_url": "https://apnews.com/article/96ef9586e1288e50843b4d2b1ccebc32",
            "fact": f"截至{macro['S&P 500']['market_time_jst']}的盘中快照：标普500较前收盘约{macro['S&P 500']['change_pct']:.2f}%，纳指约{macro['Nasdaq Composite']['change_pct']:.2f}%；美国10年期收益率约{macro['US 10Y yield']['price']:.2f}%，30年期约{macro['US 30Y yield']['price']:.2f}%；WTI约{macro['WTI crude']['price']:.2f}美元，布伦特约{macro['Brent crude']['price']:.2f}美元；USD/JPY约{macro['USD/JPY']['price']:.2f}。",
            "portfolio_impact": "增长资产下跌而长端收益率与油价走高，说明增长担忧和融资压力可同时存在。能源股短期受油价支持，高估值科技受折现率压制，现金选择权上升。",
            "boundary": "美股仍在盘中，不冒充收盘；Reuters原站无法由当前执行环境直接打开，事实由可读取转载页、AP和独立行情交叉核验。",
        },
        {
            "event_id": "NEWS-20260820-AVGO-AI-DEBT", "title": "Broadcom据报洽谈超过600亿美元AI芯片融资",
            "publisher": "Reuters报道，原始信息援引Bloomberg；可读取Reuters转载页", "published_at": "2026-08-20", "data_date": "2026-08-20", "retrieved_at_jst": cutoff,
            "url": "https://jackfmfargo.com/2026/08/20/broadcom-seeks-more-than-60-billion-in-latest-ai-debt-deal-bloomberg-news-reports/",
            "independent_url": "https://www.boursorama.com/bourse/actualites-amp/broadcom-cherche-a-lever-plus-de-60000-millions-pour-accord-de-puces-ia-rapporte-bloomberg-news-ece3781d853613b3798258ad1a917d60",
            "fact": "报道指Broadcom正与贷款方讨论为AI芯片安排筹集超过600亿美元债务，受益方包括Anthropic等；这是洽谈和报道，不是Broadcom已经完成融资或已经发生现金支出。",
            "portfolio_impact": "需求融资规模支持AI基础设施需求仍强，但把客户需求与大额债务绑定，会提高融资链、对手方和集中度风险。AVGO继续持有但不新增，AI同一驱动不扩大。",
            "boundary": "Broadcom、Apollo和Blackstone未就报道向Reuters置评；不能把报道金额当成公司已确认收入、负债或现金流。",
        },
        {
            "event_id": "NEWS-20260820-NVDA-CHINA-LPU-DENIAL", "title": "NVIDIA否认中国专用LPU已在路线图中",
            "publisher": "Reuters报道的可读取转载页；NVIDIA发言人回应", "published_at": "2026-08-20", "data_date": "2026-08-20", "retrieved_at_jst": cutoff,
            "url": "https://www.boursorama.com/bourse/actualites/nvidia-dement-les-informations-selon-lesquelles-elle-s-appreterait-a-lancer-une-puce-d-ia-en-chine-d-ici-la-fin-de-l-annee-71e3f8cec411a06e3c88bc2f4bfa83d2",
            "independent_url": "https://jackfmfargo.com/2026/08/20/nvidia-to-ship-ai-chip-for-china-by-year-end-the-information-reports/",
            "fact": "NVIDIA发言人否认将于年内推出面向中国客户的专用LPU，并称当前没有在中国销售LPU，路线图中也没有中国专用LPU。",
            "portfolio_impact": "这撤回了把未确认LPU传闻当作中国业务增量的依据；但没有消除出口限制、产品准入和本地竞争风险。NVDA核心持有、财报前不追价的动作不变。",
            "boundary": "公司否认只针对LPU报道，不能外推为NVIDIA全部中国业务或出口限制已经解决。",
        },
    ]
    model["news"] = {
        "run_id": model["run_id"], "search_started_at_jst": MARKET_FACTS["started_at_jst"],
        "search_finished_at_jst": cutoff, "evidence_cutoff_jst": cutoff,
        "search_scope": ["全球市场", "全球债券与美元", "油价与霍尔木兹", "AI融资", "NVDA中国业务", "24类持仓与18只观察股"],
        "queries": ["2026-08-21 global markets bonds oil dollar", "Broadcom more than 60 billion AI debt", "NVIDIA China LPU denial", "8月21日持仓与观察股公司公告增量"],
        "records": records,
        "failed_sources": ["Reuters原站三个指定页面均无法由当前执行环境直接打开；使用可读取Reuters转载页、AP与独立行情交叉核验。", "TOPIX自动行情源返回空结果；未写成没有TOPIX行情。"],
        "excluded": ["截止时间之后发布的事实", "只有标题且无可核内容的线索", "不能影响七层、账户、持仓或动作的低影响消息"],
    }


def inject_content(model: dict[str, Any]) -> dict[str, Any]:
    model["single_portfolio_source"] = copy.deepcopy(REFRESHED_ACCOUNT)
    model["evidence_cutoff_jst"] = MARKET_FACTS["evidence_cutoff_jst"]
    model["judgment_formed_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
    build_news(model)
    risk = REFRESHED_ACCOUNT["risk"]
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    layer_map = {row["layer"]: row for row in model["layers"]}
    layer_map[1].update({"final_judgment": "AI基础设施长期需求仍在，但8月21日出现股弱、长债收益率和油价偏高的组合；这不是无条件宽松环境。", "direction": "长期支持AI基础设施，短期压制高估值和高融资依赖资产", "strength": "中等偏强", "confidence": "中高", "transmission": "提高自由现金流、融资结构和估值安全边际要求；能源只作事件性研究。", "reversal": "油价、通胀和长端收益率持续回落，或AI资本开支被正式下调。"})
    layer_map[3].update({"final_judgment": "8月21日美股盘中走弱、美元走软，但美国长债收益率维持高位、油价上涨，资金并未转为单向宽松。", "direction": "中性偏紧", "strength": "中等偏强", "confidence": "中高", "transmission": "高估值科技不追价；现金保留选择权；能源价格受益不能直接等于能源股通过第五关。", "reversal": "股债同时企稳、油价回落且通胀预期连续下降。"})
    layer_map[4].update({"final_judgment": "Broadcom大额AI融资报道验证需求规模，也放大债务融资和对手方风险；NVIDIA否认中国专用LPU，不能再把该传闻当作增量。", "direction": "AI基础设施仍活跃，但融资与竞争风险上升；能源短期偏强", "strength": "中等", "confidence": "中高", "transmission": "AVGO、NVDA维持原持有边界但不新增；18只观察对象没有因此自动通过第五关。", "reversal": "融资安排被正式否认或需求取消，或NVDA发布正式中国专用产品并取得监管许可。"})
    layer_map[5]["final_judgment"] = "18只研究观察对象继续按唯一五关源管理；本轮新增新闻没有使任何对象形成可执行机会。"
    layer_map[5]["transmission"] = "研究卡、五关表、影子组合和行动栏全部从证券代码唯一源生成；当前可执行机会仍为0。"
    layer_map[6].update({"final_judgment": f"8月21日已知资产观察总额约{total:,.0f}日元；AI直接暴露{risk['ai_direct']['known_total_ratio_pct']:.2f}%，含软银代理后{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%；广义加密暴露{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%。", "transmission": "富途使用8月21日OpenD实测；SBI、IBKR、bitFlyer保留各自证据日。比例只用于风险观察，不是机械交易线。", "reversal": "取得手工账户更新现金、融资和应计字段后，重新计算已知分母和风险比例。"})
    layer_map[7].update({"final_judgment": "本期建立5条投资预测基线，另有1条产品流程QA；两者分开统计。57条历史记录逐条展示其可验证性、结果、归因和改进。", "transmission": "只有投资预测进入未来概率校准；流程QA用于检查产品有没有把媒体预期写成正式决定。", "reversal": "到验证日没有独立外部证据时，记录退出统计分母，不追溯补造。"})
    news_map = {row["event_id"]: row for row in model["news"]["records"]}
    for number, event_ids in {1: ["NEWS-20260821-GLOBAL-MARKETS"], 3: ["NEWS-20260821-GLOBAL-MARKETS"], 4: ["NEWS-20260820-AVGO-AI-DEBT", "NEWS-20260820-NVDA-CHINA-LPU-DENIAL"], 5: ["NEWS-20260820-AVGO-AI-DEBT"], 6: ["NEWS-20260821-GLOBAL-MARKETS"]}.items():
        layer_map[number].setdefault("facts", []).extend({
            **copy.deepcopy(news_map[event_id]),
            "supports": news_map[event_id]["portfolio_impact"],
            "cannot_prove": news_map[event_id]["boundary"],
        } for event_id in event_ids)
    research_map = {row["asset_id"]: row for row in model["research_gates"]}
    model["capabilities"]["shadow_portfolio"] = [{
        "asset_id": symbol, "name": item["name"], "capital_allocated": 0,
        "identity": "影子观察，不是真实持仓", "current_gate_stop": item["formal_gate_stop"],
        "comparison": item["replacement_target"], "trigger": item["executable_condition"],
        "next_review": item["next_review"],
    } for symbol, item in research_map.items()]
    for issue in model["capabilities"].get("issue_ledger", []):
        issue["owner"] = "数据证据由系统更新；投资判断由投研主脑统一裁定"
        if "全产品HTML必须恢复" in issue.get("issue", ""):
            issue["issue"] = "完整产品必须持续保留三层导航、证据追踪、替换比较、风险穿透、影子观察和问题台账。"
            issue["owner"] = "产品生成与内容闸复核"
    return {"status": "UPDATED_TO_2026-08-21_CUTOFF", "cutoff": model["evidence_cutoff_jst"]}


def apply_first_layer(model: dict[str, Any], final: dict[str, Any]) -> None:
    ORIGINAL_APPLY_FIRST_LAYER(model, final)
    action = model["judgment"]["today_action"]
    action["headline"] = "今天不强行新增仓位；先管理AI融资和长端利率风险，18只研究对象继续等待第五关真实触发。"
    action["priority"] = [
        "8月21日富途账户已通过OpenD只读刷新；手工账户继续显著保留原证据日期，不拼成同日净值。",
        "全球股市盘中偏弱、长债收益率和油价偏高，现金选择权上升；能源受益与科技折现压力同时存在。",
        "Broadcom大额AI融资报道既验证需求也提高融资链风险；AVGO持有、不新增。",
        "NVIDIA否认中国专用LPU，相关传闻不再作为增量依据；NVDA持有、财报前不追价。",
        "9项条件情景按8月21日价格、权重和汇率重算；＋40%路径仍未证明，＋100%仍无可信可执行路径。",
    ]


def render_target_bridge(target: dict[str, Any], base: Any) -> str:
    rows = []
    for row in target["asset_rows"]:
        if row["target_contribution_included"]:
            values = row["scenario_values"]
            probs = row["scenario_probability_pct"]
            calc = (
                f"当前价{row['current_price']:,.2f}（{row['current_price_time']}） → "
                f"概率加权价值{row['weighted_value']:,.2f} → 预期收益{row['expected_return_pct']:+.2f}% → "
                f"已知资产权重{row['known_weight_pct']:.2f}% → 组合贡献{row['target_contribution_pp']:+.4f}个百分点"
            )
            scenario = f"悲观{values['bear']:,.2f}×{probs['bear']}%＋基准{values['base']:,.2f}×{probs['base']}%＋乐观{values['bull']:,.2f}×{probs['bull']}%"
            note = row.get("zero_explanation") or ""
        else:
            calc = "没有可靠数值情景，不按0计入目标贡献，也不支持精确动作。"
            scenario = "使用非价格风险框架"
            note = ""
        rows.append(f"<tr data-target-row='{base.esc(row['asset_id'])}'><td>{base.esc(row['asset_id'])}<br>{base.esc(row['name'])}</td><td>{base.esc(scenario)}</td><td>{base.esc(calc)}<br><span class='muted'>汇率：{base.esc(row['fx_pair'])} {row['fx_value']:.4f}；{base.esc(row['fx_time'])}</span>{('<br><span class=\"boundary\">'+base.esc(note)+'</span>') if note else ''}</td><td>{base.esc(row['unique_action'])}</td></tr>")
    checkpoints = "".join(f"<tr><td>{base.esc(row['check_date'])}</td><td>{base.esc(row['check'])}</td></tr>" for row in target["monthly_milestones"])
    return f"""
    <div class="target-bars"><div><b>8月21日已知资产观察总额</b><span>¥{base.fmt_num(target['known_assets_jpy'])}</span><i style="width:50%"></i></div>
    <div><b>＋40%前瞻观察目标</b><span>¥{base.fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div>
    <div><b>＋100%压力目标</b><span>¥{base.fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{base.esc(target['boundary'])}</p>
    <div class="metric-grid"><article class="metric"><b>数值情景覆盖</b><strong>{target['quantified_weight_pct']:.2f}%</strong><small>9项条件情景</small></article>
    <article class="metric"><b>概率加权贡献</b><strong>{target['probability_weighted_contribution_pp']:+.2f}个百分点</strong><small>按8月21日价格和权重重算</small></article>
    <article class="metric"><b>＋40%路径</b><strong>尚未证明</strong><small>未量化部分平均仍需{target['residual_required_average_return_pct']['for_plus_40']:.2f}%</small></article>
    <article class="metric"><b>＋100%路径</b><strong>当前不可行</strong><small>未量化部分平均仍需{target['residual_required_average_return_pct']['for_plus_100']:.2f}%</small></article></div>
    <p>{base.esc(target['plain_language_reason'])}</p><p><b>现金机会成本：</b>{base.esc(target['cash_role'])}</p><p><b>替代路线：</b>{base.esc(target['fallback_route'])}</p>
    {base.details('24类资产可见计算桥', '<table><thead><tr><th>资产</th><th>情景输入</th><th>当前价到组合贡献</th><th>唯一动作</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>', attrs="data-visible-target-bridge='1'")}
    <h4>复核里程碑</h4><table><thead><tr><th>日期</th><th>检查内容</th></tr></thead><tbody>{checkpoints}</tbody></table><p><b>下一次全量复核：</b>{base.esc(target['next_review'])}</p>
    """


def render_pdca(pdca: dict[str, Any], base: Any) -> str:
    summary = pdca["body_summary"]
    investment = summary["investment_predictions"]
    process = summary["process_quality_checks"]
    investment_rows = "".join(f"<tr data-investment-prediction='1'><td>{index}</td><td>{base.esc(row['statement'])}</td><td>{row['probability_pct']}%</td><td>{base.esc(row['success_definition'])}</td><td>{base.esc(row['counterfactual'])}</td><td>{base.esc(row['verification_date'])}</td></tr>" for index, row in enumerate(investment, 1))
    process_rows = "".join(f"<tr data-process-qa='1'><td>{base.esc(row['statement'])}</td><td>{base.esc(row['success_definition'])}</td><td>{base.esc(row['verification_date'])}</td></tr>" for row in process)
    history_rows = []
    for row in pdca["plain_records"]:
        evidence = str(row.get("external_evidence") or "未取得").replace("source=", "证据来源：")
        history_rows.append(
            f"<tr data-pdca-history='1'><td>{row['record_number']}</td><td>{base.esc(row.get('prediction_date'))}<br>{base.esc(row.get('prediction'))}</td><td>{base.esc(row.get('success_definition'))}</td><td>{base.esc(row.get('actual_result'))}<br>{base.esc(evidence)}</td><td>{base.esc(row.get('verdict'))}</td><td>{base.esc(row.get('lesson'))}<br><b>相反选择：</b>{base.esc(row.get('counterfactual'))}</td></tr>"
        )
    changes = "".join(f"<li>{base.esc(value)}</li>" for value in summary.get("system_changes", []))
    return f"""
    <p><b>投资预测：</b>本期5条，只有这些记录进入未来概率校准。<b>产品流程QA：</b>1条，用来检查产品有没有把媒体预期写成正式决定，不计入投资预测。</p>
    <table><thead><tr><th>序号</th><th>投资预测</th><th>概率</th><th>成功标准</th><th>相反结果</th><th>验证时间</th></tr></thead><tbody>{investment_rows}</tbody></table>
    <h4>产品流程QA</h4><table><thead><tr><th>检查内容</th><th>通过标准</th><th>检查时间</th></tr></thead><tbody>{process_rows}</tbody></table>
    <h4>本期从历史错误中改变了什么</h4><ul>{changes}</ul>
    {base.details('57条历史记录：预测、实际、判定、归因和改进', '<p class="boundary">历史记录逐条保留；没有独立外部成功标准的记录退出统计分母，不追溯补造。</p><table><thead><tr><th>编号</th><th>当时预测</th><th>成功标准</th><th>实际与证据</th><th>判定</th><th>教训与相反选择</th></tr></thead><tbody>'+''.join(history_rows)+'</tbody></table>', attrs="data-pdca-ledger='57'")}
    """


def semantic_qa(model: dict[str, Any], html_text: str, capability: dict[str, Any], final: dict[str, Any], output_dir: Path, attachment_rows: list[dict[str, Any]], decision_hash: str) -> dict[str, Any]:
    visible = previous.visible_text(html_text)
    research = {row["asset_id"]: row for row in model["research_gates"]}
    shadow = {row["asset_id"]: row for row in model["capabilities"]["shadow_portfolio"]}
    gate_conflicts = [symbol for symbol in research if shadow.get(symbol, {}).get("current_gate_stop") != research[symbol]["formal_gate_stop"]]
    target_errors = []
    for row in model["target_bridge"]["asset_rows"]:
        if row["target_contribution_included"]:
            decision = next(item for item in final["holdings_judgments"] if item["asset_id"] == row["asset_id"])
            calc = weighted_scenario(decision, row["current_price"])
            expected_contribution = row["known_weight_pct"] * calc["expected_return_pct"] / 100.0
            if abs(expected_contribution - row["target_contribution_pp"]) > 1e-6 or not row["current_price_time"] or not row["fx_time"]:
                target_errors.append(row["asset_id"])
    forbidden = {term: visible.count(term) for term in ["Codex取证", "Codex施工", "全产品HTML必须恢复", "本期判断判断", "详见机器附件", "等待GPT总控", "总控必须决定"] if visible.count(term)}
    futu_rows = [row for row in model["single_portfolio_source"]["positions"] if row["account"] == "FUTU"]
    account_dates = {row["account"]: row["quantity_evidence_date"] for row in model["single_portfolio_source"]["positions"] if row["account"] != "FUTU"}
    news_ids = {row["event_id"] for row in model["news"]["records"]}
    new_news_ids = {"NEWS-20260821-GLOBAL-MARKETS", "NEWS-20260820-AVGO-AI-DEBT", "NEWS-20260820-NVDA-CHINA-LPU-DENIAL"}
    new_layer_facts = [fact for layer in model["layers"] for fact in layer.get("facts", []) if fact.get("event_id") in new_news_ids]
    new_layer_facts_complete = bool(new_layer_facts) and all(fact.get("supports") and fact.get("cannot_prove") for fact in new_layer_facts)
    news_window_ok = model["news"]["search_started_at_jst"] < model["news"]["search_finished_at_jst"] == model["news"]["evidence_cutoff_jst"] == model["evidence_cutoff_jst"]
    html_counts = {
        "holdings": len(re.findall(r"data-holding=['\"]", html_text)),
        "research": len(re.findall(r"data-research=['\"]", html_text)),
        "gates": len(re.findall(r"data-gate-row=['\"]1['\"]", html_text)),
        "target": len(re.findall(r"data-target-row=['\"]", html_text)),
        "investment_predictions": len(re.findall(r"data-investment-prediction=['\"]1['\"]", html_text)),
        "process_qa": len(re.findall(r"data-process-qa=['\"]1['\"]", html_text)),
        "pdca_history": len(re.findall(r"data-pdca-history=['\"]1['\"]", html_text)),
    }
    checks = {
        "Q01新闻窗口与增量事件": {"pass": news_window_ok and new_news_ids.issubset(news_ids) and new_layer_facts_complete, "detail": {"window_ok": news_window_ok, "new_event_count": len(news_ids & new_news_ids), "layer_transmission_complete": new_layer_facts_complete}},
        "Q02富途8月21日账户实测": {"pass": len(futu_rows) == 12 and all(row["quantity_evidence_date"] == "2026-08-21" for row in futu_rows) and model["single_portfolio_source"]["refresh_audit"]["futu_snapshot_run_id"].startswith("FUTU-RO-20260821"), "detail": {"positions": len(futu_rows), "snapshot": model["single_portfolio_source"]["refresh_audit"]}},
        "Q03手工账户日期边界": {"pass": account_dates.get("SBI账户归属尚未确认") == "2026-08-19 18:50 JST" and account_dates.get("IBKR") == "2026-08-04" and account_dates.get("bitFlyer") == "2026-08-11" and all(term in visible for term in ["2026-08-19 18:50 JST", "2026-08-04最后截图", "2026-08-11最后截图"]), "detail": account_dates},
        "Q04跨章节五关唯一": {"pass": len(research) == 18 and len(shadow) == 18 and not gate_conflicts, "detail": {"research": len(research), "shadow": len(shadow), "conflicts": gate_conflicts}},
        "Q05目标贡献可见复算": {"pass": len([row for row in model["target_bridge"]["asset_rows"] if row["target_contribution_included"]]) == 9 and not target_errors and "上一版恰好为0" in visible and html_counts["target"] == 24, "detail": {"errors": target_errors, "html_rows": html_counts["target"]}},
        "Q06PDCA分类与全文": {"pass": len(model["pdca"]["plain_records"]) == 57 and len(model["pdca"]["body_summary"]["investment_predictions"]) == 5 and len(model["pdca"]["body_summary"]["process_quality_checks"]) == 1 and html_counts["pdca_history"] == 57 and html_counts["investment_predictions"] == 5 and html_counts["process_qa"] == 1 and "三条新质量基线" not in visible and "新建3条预测基线" not in visible, "detail": html_counts},
        "Q07完整HTML自足": {"pass": all(term in visible for term in ["8月21日富途账户已通过富途只读账户接口只读刷新", "可见计算桥", "57条历史记录", "产品流程QA"]) and "详见机器附件" not in visible, "detail": {"required_visible": True}},
        "Q08内部施工语言": {"pass": not forbidden, "detail": forbidden},
        "Q09结构与冻结边界": {"pass": html_counts["holdings"] == 24 and html_counts["research"] == 18 and html_counts["gates"] == 90 and not list(output_dir.glob("*.pdf")) and model["status"] == previous.STATUS, "detail": html_counts},
        "Q10UTF8与本地路径": {"pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8") and not re.search(r"(?i)(?:[A-Z]:\\|file://)", visible), "detail": {"replacement": html_text.encode("utf-8").count(b"\xef\xbf\xbd")}},
    }
    failures = [key for key, result in checks.items() if not result["pass"]]
    return {"schema_version": "V7-STAGEC-RETURN-SEMANTIC-QA-2.0", "run_id": model["run_id"], "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"), "checks": checks, "pass_count": len(checks) - len(failures), "check_count": len(checks), "failures": failures, "status": "INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_CONTENT_GATE" if not failures else "FAIL", "self_declared_content_gate_pass": False, "pdf_render_authorized": False}


ORIGINAL_APPLY_HOLDINGS = previous.apply_holdings
ORIGINAL_APPLY_RESEARCH = previous.apply_research
ORIGINAL_APPLY_FIRST_LAYER = previous.apply_first_layer
ORIGINAL_INJECT = previous.legacy.inject_market_reversal
ORIGINAL_WRITE_ATTACHMENT = previous.write_attachment


def write_attachment(path: Path, value: Any, purpose: str) -> dict[str, Any]:
    if path.name == "01_PDCA历史57条及新预测.json":
        purpose = "57条历史记录、5条投资预测与1条产品流程QA"
    elif path.name == "12_PDCA概率校准规则.json":
        purpose = "固定概率档位、5条投资预测与1条产品流程QA"
    return ORIGINAL_WRITE_ATTACHMENT(path, value, purpose)


def main() -> int:
    global ACCOUNT_SOURCE, FUTU_SNAPSHOT, MARKET_FACTS
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-renderer", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--capability-input", required=True, type=Path)
    parser.add_argument("--final-judgment", required=True, type=Path)
    parser.add_argument("--previous-account-source", required=True, type=Path)
    parser.add_argument("--futu-snapshot", required=True, type=Path)
    parser.add_argument("--market-facts", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()
    ACCOUNT_SOURCE = load_json(args.previous_account_source)["data"]
    FUTU_SNAPSHOT = load_json(args.futu_snapshot)
    MARKET_FACTS = load_json(args.market_facts)
    previous.apply_holdings = apply_holdings
    previous.apply_research = apply_research
    previous.build_target_bridge = build_target_bridge
    previous.apply_pdca = apply_pdca
    previous.apply_first_layer = apply_first_layer
    previous.render_target_bridge = render_target_bridge
    previous.render_pdca = render_pdca
    previous.semantic_qa = semantic_qa
    previous.write_attachment = write_attachment
    previous.legacy.inject_market_reversal = inject_content
    previous.legacy.VISIBLE_TERM_MAP.update({
        "Codex取证，本期判断判断": "数据证据由系统更新，投资判断由投研主脑统一裁定",
        "Codex施工，本期判断全读验收": "产品生成后由总控执行全文内容闸",
        "全产品HTML必须恢复": "完整产品必须持续保留",
        "未由Codex取得原文": "本批次未直接取得原文",
    })
    sys.argv = [
        sys.argv[0], "--base-renderer", str(args.base_renderer), "--base-model", str(args.base_model),
        "--capability-input", str(args.capability_input), "--final-judgment", str(args.final_judgment),
        "--output-dir", str(args.output_dir), "--run-id", args.run_id,
        "--daily-report", str(args.daily_report),
    ]
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
