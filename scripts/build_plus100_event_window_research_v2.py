#!/usr/bin/env python3
"""Rebuild only the V13 +100% event-window research method."""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import build_plus100_event_window_research as v1

ROOT = Path(__file__).resolve().parents[1]
V13_DIR = v1.V13_DIR
OLD_SUPPLEMENT = V13_DIR / "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT.json"
EXPECTED_LOCKED_SHA = "FFA84D49E20CFB0D15A5220E33A94547BA16683B2B4D8C4C731E549635F382B8"
ET = ZoneInfo("America/New_York")
JST = ZoneInfo("Asia/Tokyo")

BENCHMARKS = {
    "US.MU": ("SOXX", "美国半导体行业ETF"), "US.SNDK": ("SOXX", "美国半导体行业ETF"),
    "US.NVDA": ("SOXX", "美国半导体行业ETF"), "US.CRDO": ("SOXX", "美国半导体行业ETF"),
    "US.AVGO": ("SOXX", "美国半导体行业ETF"), "US.ASML": ("SOXX", "美国半导体行业ETF"),
    "US.TER": ("SOXX", "美国半导体行业ETF"), "US.COHR": ("SOXX", "美国半导体行业ETF"),
    "US.ALAB": ("SOXX", "美国半导体行业ETF"), "US.AMD": ("SOXX", "美国半导体行业ETF"),
    "US.TSM": ("SOXX", "美国半导体行业ETF"),
    "US.ORCL": ("QQQ", "纳斯达克100ETF"), "US.MSFT": ("QQQ", "纳斯达克100ETF"),
    "US.META": ("QQQ", "纳斯达克100ETF"), "US.ANET": ("QQQ", "纳斯达克100ETF"),
    "US.VRT": ("XLI", "美国工业行业ETF"), "US.ETN": ("XLI", "美国工业行业ETF"),
    "US.MOD": ("XLI", "美国工业行业ETF"), "US.PWR": ("XLI", "美国工业行业ETF"),
    "US.GEV": ("XLI", "美国工业行业ETF"), "US.SPCX": ("XLI", "美国工业行业ETF"),
    "US.IBKR": ("XLF", "美国金融行业ETF"),
    "US.COIN": ("BTC-USD", "比特币现货价格"), "US.CRCL": ("BTC-USD", "比特币现货价格"),
    "US.MSTR": ("BTC-USD", "比特币现货价格"),
    "BTC": ("SPY", "标普500ETF"), "ETH": ("BTC-USD", "比特币现货价格"),
}

OFFICIAL_IR = {
    "US.MU": "https://investors.micron.com/", "US.COIN": "https://investor.coinbase.com/",
    "US.CRCL": "https://investor.circle.com/", "US.ORCL": "https://investor.oracle.com/",
    "JP.9984": "https://group.softbank/en/ir", "US.SNDK": "https://investor.sandisk.com/",
    "US.NVDA": "https://investor.nvidia.com/", "US.MSFT": "https://www.microsoft.com/en-us/Investor/",
    "JP.7735": "https://www.screen.co.jp/ir", "US.META": "https://investor.atmeta.com/",
    "US.ETN": "https://www.eaton.com/us/en-us/company/investor-relations.html",
    "US.CRDO": "https://investors.credosemi.com/", "US.VRT": "https://investors.vertiv.com/",
    "JP.6758": "https://www.sony.com/en/SonyInfo/IR/", "JP.6857": "https://www.advantest.com/investors/",
    "US.ANET": "https://investors.arista.com/", "US.MSTR": "https://www.strategy.com/investor-relations",
    "JP.7974": "https://www.nintendo.co.jp/ir/en/", "JP.4568": "https://www.daiichisankyo.com/investors/",
    "JP.4063": "https://www.shinetsu.co.jp/en/ir/", "JP.7203": "https://global.toyota/en/ir/",
    "JP.8035": "https://www.tel.com/ir/", "US.TSM": "https://investor.tsmc.com/english",
    "JP.6954": "https://www.fanuc.co.jp/en/ir/", "ETH": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "US.SPCX": "https://ir.spacex.com/", "BTC": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "US.AVGO": "https://investors.broadcom.com/", "US.MOD": "https://investors.modine.com/",
    "US.PWR": "https://investors.quantaservices.com/", "US.ASML": "https://www.asml.com/en/investors",
    "JP.8766": "https://www.tokiomarinehd.com/en/ir/", "US.IBKR": "https://investors.interactivebrokers.com/",
    "US.TER": "https://investors.teradyne.com/", "KRX.000660": "https://www.skhynix.com/ir/UI-FR-IR01/",
    "JP.8001": "https://www.itochu.co.jp/en/ir/", "US.GEV": "https://www.gevernova.com/investors",
    "JP.3436": "https://www.sumcosi.com/english/ir/", "US.COHR": "https://investors.coherent.com/",
    "US.ALAB": "https://investors.asteralabs.com/", "US.AMD": "https://ir.amd.com/",
    "KRX.005930": "https://www.samsung.com/global/ir/",
}

FUTURE_OVERRIDES = {
    "US.MU": ("Micron 2026财年第四季度正式业绩和下一财年指引", "2026-09-30 16:30 ET（收盘后）", "确定日期", "https://investors.micron.com/news/press-release/2026/Micron-Technology-to-Report-Fiscal-Fourth-Quarter-Results-on-September-30-2026/default.aspx", "公司2026年8月26日正式公告。"),
    "US.AVGO": ("Broadcom 2026财年第三季度业绩和业务展望", "2026-09-02 17:00 ET（收盘后）", "确定日期", "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announce-third-quarter-fiscal-year-2026-financial", "公司2026年8月3日正式公告。"),
    "US.ORCL": ("Oracle 2027财年第一季度业绩", "2026年9月中旬", "确定月份/季度", "https://investor.oracle.com/faq/default.aspx", "公司投资者关系FAQ明确为9月中旬，尚未给日期。"),
    "JP.9984": ("软银1万亿日元新债最终利率与资金用途核对", "2026-09-04", "确定日期", "https://group.softbank/en/news/press", "公司正式债券资料已给最终利率确定日。"),
    "US.CRDO": ("Credo 2027财年第一季度业绩与67.9%毛利率指引核对", "2026年9月上旬", "确定月份/季度", "https://investors.credosemi.com/news-events/news/default.aspx", "公司IR已发布业绩电话会安排，当前页面摘要未稳定返回确切日期。"),
    "US.NVDA": ("NVIDIA 2027财年第三季度业绩，核对1080亿美元收入和74%毛利率指引", "2026年11月下旬", "确定月份/季度", "https://investor.nvidia.com/", "公司尚未公告确切日期；按正式季度报告周期定位。"),
    "US.MSFT": ("Microsoft 2027财年第一季度业绩，核对Azure、AI收入、资本开支和现金流", "2026年10月下旬", "确定月份/季度", "https://www.microsoft.com/en-us/Investor/", "公司明确下一次业绩日期尚待公告；按季度节奏定位。"),
    "KRX.005930": ("Samsung 2026年第三季度业绩指引与正式结果，核对HBM和利润率", "2026年10月", "确定月份/季度", "https://www.samsung.com/global/ir/financial-information/earnings-release/", "公司IR按季度披露，确切日期尚未公告。"),
    "KRX.000660": ("SK hynix 2026年第三季度业绩与HBM4认证、出货核对", "2026年10月", "确定月份/季度", "https://www.skhynix.com/ir/UI-FR-IR01/", "公司季度披露窗口可定位到10月，确切日期尚未公告。"),
    "BTC": ("美联储利率决定及经济预测，核对实际利率和风险资金环境", "2026-09-16 14:00 ET", "确定日期", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "美联储正式FOMC日历。"),
    "ETH": ("美联储利率决定后核对资金环境，并结合链上活动和竞争链份额", "2026-09-16 14:00 ET", "确定日期", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "美联储正式FOMC日历；链上验证本身没有单一事件日。"),
}

TRIGGER_FAMILY = {
    "US.MSTR": "NAV_FINANCING", "JP.9984": "NAV_FINANCING", "US.COIN": "CRYPTO_OPERATING",
    "US.CRCL": "CRYPTO_OPERATING", "BTC": "MACRO_LIQUIDITY", "ETH": "MACRO_LIQUIDITY",
    "JP.4568": "CLINICAL_REGULATORY", "JP.7974": "PRODUCT_CYCLE", "US.SPCX": "PRODUCT_MILESTONE",
    "JP.7203": "QUALITY_AND_VOLUME", "JP.6954": "ORDER_CYCLE",
    "JP.4063": "MEMORY_CYCLE", "JP.3436": "MEMORY_CYCLE", "US.MU": "MEMORY_CYCLE",
    "US.SNDK": "MEMORY_CYCLE", "KRX.000660": "MEMORY_CYCLE", "KRX.005930": "MEMORY_CYCLE",
}


def benchmark_for(asset_id: str) -> tuple[str, str]:
    if asset_id in BENCHMARKS:
        return BENCHMARKS[asset_id]
    if asset_id.startswith("JP."):
        return "^TOPX", "日本TOPIX指数"
    if asset_id.startswith("KRX."):
        return "^KS11", "韩国综合股价指数"
    return "SPY", "标普500ETF"


def trigger_family(asset_id: str) -> str:
    return TRIGGER_FAMILY.get(asset_id, "EARNINGS_GROWTH_MARGIN")


def future_event(asset: dict[str, Any]) -> dict[str, Any]:
    asset_id = asset["asset_id"]
    if asset_id in FUTURE_OVERRIDES:
        event, window, confidence, source, basis = FUTURE_OVERRIDES[asset_id]
    elif asset_id.startswith("US."):
        event, window, confidence = asset.get("short_catalyst"), "2026年10月至12月的下一次季度披露窗口", "确定月份/季度"
        source, basis = OFFICIAL_IR.get(asset_id), "公司尚未公告确切日期；只按正式季度报告节奏定位，不补造统一日期。"
    elif asset_id.startswith("JP."):
        event, window, confidence = asset.get("short_catalyst"), "2026年10月至11月的日本企业季度披露窗口", "确定月份/季度"
        source, basis = OFFICIAL_IR.get(asset_id), "确切日期尚未公告；按日本季度披露节奏定位，不能当作确定日。"
    elif asset_id.startswith("KRX."):
        event, window, confidence = asset.get("short_catalyst"), "2026年10月的韩国企业季度披露窗口", "确定月份/季度"
        source, basis = OFFICIAL_IR.get(asset_id), "确切日期尚未公告；按韩国季度披露节奏定位。"
    else:
        event, window, confidence = asset.get("short_catalyst"), "当前无法确定单一事件日", "当前无法确定"
        source, basis = OFFICIAL_IR.get(asset_id), "只有方向性验证条件，没有可核定的单一事件日。"
    return {
        "asset_id": asset_id, "asset_name": asset["asset_name"], "event": event,
        "time": window, "time_confidence": confidence, "source": source, "basis": basis,
        "entry_observation_condition": asset.get("short_upgrade_condition"),
        "exit_or_realization_condition": "事件披露后核对触发条件与市场反应；经营事实兑现或被证伪时结束该窗口。",
        "failure_condition": asset.get("short_downgrade_condition") or asset.get("short_risk"),
    }


def sec_earnings_events(ticker: str, ticker_map: dict[str, dict[str, Any]]) -> tuple[int | None, list[dict[str, Any]]]:
    item = ticker_map.get(ticker.upper())
    if not item:
        return None, []
    cik = int(item["cik_str"])
    recent = (v1.fetch_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").get("filings") or {}).get("recent") or {}
    fields = ["form", "filingDate", "acceptanceDateTime", "accessionNumber", "primaryDocument", "items", "reportDate"]
    if not all(field in recent for field in fields):
        return cik, []
    events = []
    for values in zip(*(recent[field] for field in fields)):
        form, filing_date, accepted, accession, document, items, report_date = values
        if not ((form == "8-K" and "2.02" in (items or "")) or form == "6-K"):
            continue
        accepted_utc = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
        accepted_et = accepted_utc.astimezone(ET)
        if accepted_et.hour >= 16:
            relation, anchor_rule, candidate_day = "AFTER_MARKET_CLOSE", "下一交易日", accepted_et.date() + timedelta(days=1)
        elif (accepted_et.hour, accepted_et.minute) < (9, 30):
            relation, anchor_rule, candidate_day = "BEFORE_MARKET_OPEN", "当日交易日", accepted_et.date()
        else:
            relation, anchor_rule, candidate_day = "DURING_MARKET_HOURS", "当日交易日；日线统计以前一收盘为起点", accepted_et.date()
        compact = accession.replace("-", "")
        events.append({
            "event_timestamp": accepted_utc.isoformat(), "event_timestamp_et": accepted_et.isoformat(),
            "event_calendar_date": accepted_et.date().isoformat(), "candidate_trading_day": candidate_day.isoformat(),
            "market_session_relation": relation, "trading_day_anchor_rule": anchor_rule,
            "event_type": f"SEC {form}正式业绩披露", "form": form, "report_date": report_date,
            "accession_number": accession,
            "source": f"https://www.sec.gov/Archives/edgar/data/{cik}/{compact}/{document}",
            "source_quality": "A", "source_role": "SEC正式接收时间；若公司IR另有更早正式时间，应以前者替换",
            "filing_date": filing_date,
        })
    return cik, events


def nasdaq_surprises(ticker: str) -> dict[str, dict[str, Any]]:
    try:
        doc = v1.fetch_json(f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise")
    except Exception:
        return {}
    rows = ((((doc.get("data") or {}).get("earningsSurpriseTable") or {}).get("rows")) or [])
    result = {}
    for row in rows:
        try:
            event_date = datetime.strptime(row.get("dateReported"), "%m/%d/%Y").date().isoformat()
            surprise = float(str(row.get("percentageSurprise")).replace("%", ""))
        except (TypeError, ValueError):
            continue
        result[event_date] = {
            "eps_actual": row.get("eps"), "eps_consensus": row.get("consensusForecast"),
            "eps_surprise_pct": surprise, "source": f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise",
            "source_quality": "B", "source_role": "Nasdaq展示的一致预期与实际每股收益差异",
        }
    return result


def _fact_quarters(fact: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not fact:
        return {}
    entries = next(iter((fact.get("units") or {}).values()), [])
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        start, end = row.get("start"), row.get("end")
        if not start or not end or row.get("form") not in {"10-Q", "10-K", "20-F", "40-F"}:
            continue
        duration = (date.fromisoformat(end) - date.fromisoformat(start)).days
        if 70 <= duration <= 120:
            candidates[end].append(row)
    return {end: min(rows, key=lambda row: row.get("filed") or "9999") for end, rows in candidates.items()}


def company_quarter_metrics(cik: int | None) -> list[dict[str, Any]]:
    if cik is None:
        return []
    try:
        facts = v1.fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json").get("facts") or {}
    except Exception:
        return []
    taxonomy = facts.get("us-gaap") or facts.get("ifrs-full") or {}

    def merged(tags: list[str]) -> dict[str, dict[str, Any]]:
        merged_values: dict[str, dict[str, Any]] = {}
        for tag in tags:
            for period_end, value in _fact_quarters(taxonomy.get(tag)).items():
                merged_values.setdefault(period_end, value)
        return merged_values

    revenue = merged(["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "Revenue"])
    gross = merged(["GrossProfit"])
    operating = merged(["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"])
    rows = []
    for end in sorted(set(revenue) | set(gross) | set(operating)):
        rev, gp, op = revenue.get(end, {}).get("val"), gross.get(end, {}).get("val"), operating.get(end, {}).get("val")
        filed_values = [item.get("filed") for item in (revenue.get(end), gross.get(end), operating.get(end)) if item and item.get("filed")]
        rows.append({
            "period_end": end, "filed": min(filed_values) if filed_values else None,
            "revenue": rev, "gross_profit": gp, "operating_income": op,
            "gross_margin": gp / rev if isinstance(gp, (int, float)) and isinstance(rev, (int, float)) and rev else None,
            "operating_margin": op / rev if isinstance(op, (int, float)) and isinstance(rev, (int, float)) and rev else None,
        })
    for row in rows:
        end = date.fromisoformat(row["period_end"])
        prior = min(
            (candidate for candidate in rows if 320 <= (end - date.fromisoformat(candidate["period_end"])).days <= 410),
            key=lambda candidate: abs((end - date.fromisoformat(candidate["period_end"])).days - 365), default=None,
        )
        row["revenue_yoy"] = row["revenue"] / prior["revenue"] - 1 if prior and row.get("revenue") and prior.get("revenue") else None
        margin_name = "operating_margin" if row.get("operating_margin") is not None else "gross_margin"
        row["margin_metric"] = margin_name
        row["margin_yoy_change"] = row[margin_name] - prior[margin_name] if prior and row.get(margin_name) is not None and prior.get(margin_name) is not None else None
    return rows


def nearest_metric(event: dict[str, Any], metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    event_day = date.fromisoformat(event["event_calendar_date"])
    matches = []
    for row in metrics:
        if row.get("filed"):
            gap = abs((date.fromisoformat(row["filed"]) - event_day).days)
            if gap <= 7:
                matches.append((gap, row))
    return min(matches, key=lambda item: item[0])[1] if matches else None


def classify_similarity(asset_id: str, metric: dict[str, Any] | None, surprise: dict[str, Any] | None) -> dict[str, Any]:
    family = trigger_family(asset_id)
    incompatible = {"NAV_FINANCING", "MACRO_LIQUIDITY", "CRYPTO_OPERATING", "CLINICAL_REGULATORY", "PRODUCT_MILESTONE", "PRODUCT_CYCLE", "QUALITY_AND_VOLUME", "ORDER_CYCLE"}
    if family in incompatible:
        return {"trigger_similarity": "LOW", "reason": f"当前触发属于{family}，普通季度业绩不能替代该特定事件。", "inputs": {"financial_metric": metric, "earnings_surprise": surprise}}
    revenue = metric.get("revenue_yoy") if metric else None
    margin = metric.get("margin_yoy_change") if metric else None
    eps = surprise.get("eps_surprise_pct") / 100 if surprise else None
    known = [value for value in (revenue, margin, eps) if isinstance(value, (int, float))]
    positives, negatives = sum(value > 0 for value in known), sum(value < 0 for value in known)
    strong = (revenue is not None and revenue >= 0.10) or (eps is not None and eps >= 0.05)
    if len(known) >= 2 and negatives == 0 and positives >= 2 and strong:
        similarity, reason = "HIGH", "收入增长、利润率变化或每股收益惊喜中至少两项同向为正，并含一项较强改善。"
    elif known and negatives == 0 and positives >= 1:
        similarity, reason = "MEDIUM", "至少一项经营结果同向改善，但收入、利润率或一致预期信息不完整。"
    else:
        similarity, reason = "LOW", "经营结果与当前正向触发不一致，或缺少足以判断相似度的公司指标。"
    return {
        "trigger_similarity": similarity, "reason": reason,
        "inputs": {"revenue_yoy": revenue, "margin_metric": metric.get("margin_metric") if metric else None,
                   "margin_yoy_change": margin, "eps_surprise_pct": surprise.get("eps_surprise_pct") if surprise else None,
                   "financial_metric_source": "SEC XBRL companyfacts" if metric else None,
                   "earnings_surprise_source": surprise.get("source") if surprise else None},
    }


def next_index(prices: list[dict[str, Any]], candidate_day: str) -> int | None:
    return next((index for index, row in enumerate(prices) if row["date"] >= candidate_day), None)


def price_on_or_before(prices: list[dict[str, Any]], day: str) -> float | None:
    value = None
    for row in prices:
        if row["date"] <= day:
            value = row["close"]
        else:
            break
    return value


def reaction(event: dict[str, Any], prices: list[dict[str, Any]], benchmark: list[dict[str, Any]], benchmark_symbol: str, benchmark_name: str) -> dict[str, Any] | None:
    event_index = next_index(prices, event["candidate_trading_day"])
    if event_index is None or event_index == 0 or event_index + 59 >= len(prices):
        return None
    base_index, base = event_index - 1, prices[event_index - 1]["close"]
    base_day, event_day = prices[base_index]["date"], prices[event_index]["date"]
    benchmark_base = price_on_or_before(benchmark, base_day)
    if benchmark_base is None:
        return None
    absolute, benchmark_returns, excess = {}, {}, {}
    for days, index in {1: event_index, 5: event_index + 4, 20: event_index + 19, 60: event_index + 59}.items():
        endpoint = prices[index]
        benchmark_end = price_on_or_before(benchmark, endpoint["date"])
        if benchmark_end is None:
            return None
        absolute[str(days)] = endpoint["close"] / base - 1
        benchmark_returns[str(days)] = benchmark_end / benchmark_base - 1
        excess[str(days)] = absolute[str(days)] - benchmark_returns[str(days)]
    path = [row["close"] for row in prices[base_index:event_index + 60]]
    peak, max_drawdown = path[0], 0.0
    for value in path:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return {
        **event, "trading_day_anchor": event_day, "pre_event_close_date": base_day, "pre_event_close": base,
        "absolute_return": absolute,
        "benchmark": {"symbol": benchmark_symbol, "name": benchmark_name, "return": benchmark_returns},
        "excess_return": excess, "max_upside_60d": max(value / base - 1 for value in path),
        "max_loss_from_entry_60d": min(value / base - 1 for value in path), "max_drawdown_60d": max_drawdown,
        "calculation_rule": "正式消息时间决定事件交易日；盘后锚定下一交易日，盘前锚定当日。收益从事件日前一收盘计算；超额收益=股票收益-同期基准收益。",
    }


def value_stats(values: list[float]) -> dict[str, Any]:
    return {"median": statistics.median(values), "p25": v1.percentile(values, 0.25), "p75": v1.percentile(values, 0.75),
            "worst": min(values), "best": max(values), "positive_count": sum(value > 0 for value in values),
            "total_count": len(values), "positive_ratio": sum(value > 0 for value in values) / len(values)}


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not samples:
        return None
    result: dict[str, Any] = {"sample_count": len(samples)}
    for days in (1, 5, 20, 60):
        key = str(days)
        result[f"absolute_return_{days}d"] = value_stats([row["absolute_return"][key] for row in samples])
        result[f"benchmark_return_{days}d"] = value_stats([row["benchmark"]["return"][key] for row in samples])
        result[f"excess_return_{days}d"] = value_stats([row["excess_return"][key] for row in samples])
    result["max_upside_60d"] = value_stats([row["max_upside_60d"] for row in samples])
    result["max_loss_from_entry_60d"] = value_stats([row["max_loss_from_entry_60d"] for row in samples])
    result["max_drawdown_60d"] = value_stats([row["max_drawdown_60d"] for row in samples])
    return result


def specific_trigger(asset: dict[str, Any]) -> bool:
    text = " ".join(str(asset.get(key) or "") for key in ("short_catalyst", "short_upgrade_condition", "short_downgrade_condition"))
    return len(text) >= 80 and not any(word in text for word in ("好于预期就升级", "弱于预期就降级", "尚未取得"))


def grade_asset(asset: dict[str, Any], calendar: dict[str, Any], samples: list[dict[str, Any]], primary: list[dict[str, Any]], stats: dict[str, Any] | None) -> tuple[str, list[str], list[str]]:
    failures, passes = [], []
    (failures if calendar["time_confidence"] == "当前无法确定" else passes).append(
        "未来事件窗口当前无法定位" if calendar["time_confidence"] == "当前无法确定" else "未来事件可定位到日期或月份/季度")
    (passes if specific_trigger(asset) else failures).append(
        "当前进入和降级条件为资产特定条件" if specific_trigger(asset) else "当前触发条件仍不够资产特定")
    high_count = sum(row["trigger_similarity"]["trigger_similarity"] == "HIGH" for row in primary)
    if len(primary) >= 5 and high_count >= 2:
        passes.append(f"有{len(primary)}个HIGH/MEDIUM相似样本，其中{high_count}个HIGH")
    else:
        failures.append(f"相似样本仅{len(primary)}个、HIGH仅{high_count}个；A级要求至少5个相似样本且至少2个HIGH")
    if not stats:
        failures.append("没有可用的相似样本超额收益统计")
    else:
        ex20, ex60 = stats["excess_return_20d"], stats["excess_return_60d"]
        if ex20["median"] > 0.03 and ex60["median"] > 0.05 and ex20["positive_ratio"] >= 0.60 and ex60["positive_ratio"] >= 0.60:
            passes.append("20日和60日超额收益中位数及正超额比例均达到重复性门槛")
        else:
            failures.append(f"超额优势不足：20日中位{ex20['median']:.2%}/正超额{ex20['positive_ratio']:.0%}，60日中位{ex60['median']:.2%}/正超额{ex60['positive_ratio']:.0%}")
        worst_drawdown, worst_excess = stats["max_drawdown_60d"]["worst"], ex60["worst"]
        edge_ratio = ex60["median"] / abs(worst_excess) if worst_excess < 0 else float("inf")
        if worst_drawdown >= -0.35 and edge_ratio >= 0.25:
            passes.append("历史最坏回撤和中位超额收益的关系未破坏风险收益结构")
        else:
            failures.append(f"下行风险过大：最坏60日最大回撤{worst_drawdown:.2%}，中位超额/最差超额比{edge_ratio:.2f}")
    if not failures:
        return "A", passes, failures
    if calendar["time_confidence"] != "当前无法确定" and specific_trigger(asset) and (samples or calendar.get("source")):
        return "B", passes, failures
    return "C", passes, failures


def risk_factor(asset_id: str) -> str:
    return v1.risk_factor(asset_id)


def research_one(asset: dict[str, Any], ticker_map: dict[str, dict[str, Any]], price_cache: dict[str, list[dict[str, Any]]], old_grades: dict[str, str]) -> dict[str, Any]:
    asset_id, symbol = asset["asset_id"], v1.yahoo_symbol(asset["asset_id"])
    benchmark_symbol, benchmark_name = benchmark_for(asset_id)
    prices = price_cache.get(symbol or "", [])
    benchmark = price_cache.get(benchmark_symbol, [])
    ticker = asset_id.split(".", 1)[1] if asset_id.startswith("US.") else ""
    cik, events = sec_earnings_events(ticker, ticker_map) if ticker else (None, [])
    metrics, surprises = company_quarter_metrics(cik) if events else [], nasdaq_surprises(ticker) if events else {}
    real_samples = []
    for event in events[:16]:
        metric = nearest_metric(event, metrics)
        surprise = surprises.get(event["event_calendar_date"])
        item = reaction(event, prices, benchmark, benchmark_symbol, benchmark_name)
        if item:
            item["trigger_similarity"] = classify_similarity(asset_id, metric, surprise)
            real_samples.append(item)
    primary = [row for row in real_samples if row["trigger_similarity"]["trigger_similarity"] in {"HIGH", "MEDIUM"}][:8]
    stats, calendar = summarize(primary), future_event(asset)
    grade, passes, failures = grade_asset(asset, calendar, real_samples, primary, stats)
    old_grade = old_grades.get(asset_id)
    transition = f"原{old_grade or '未评级'} → 新{grade}级"
    return {
        "asset_id": asset_id, "asset_name": asset["asset_name"],
        "old_method_status": "历史数据可量化候选" if old_grade == "A" else "旧方法待补证候选",
        "old_grade": old_grade, "new_grade": grade, "grade_transition": transition,
        "downgrade_reason": "；".join(failures) if old_grade == "A" and grade != "A" else None,
        "grade_passes": passes, "grade_failures": failures, "future_12m_event_window": calendar,
        "current_trigger_family": trigger_family(asset_id), "real_event_time_sample_count": len(real_samples),
        "condition_matched_sample_count": len(primary),
        "high_similarity_sample_count": sum(row["trigger_similarity"]["trigger_similarity"] == "HIGH" for row in primary),
        "medium_similarity_sample_count": sum(row["trigger_similarity"]["trigger_similarity"] == "MEDIUM" for row in primary),
        "low_similarity_excluded_count": sum(row["trigger_similarity"]["trigger_similarity"] == "LOW" for row in real_samples),
        "real_event_time_samples": real_samples, "condition_matched_samples": primary,
        "absolute_benchmark_excess_statistics": stats,
        "benchmark": {"symbol": benchmark_symbol, "name": benchmark_name, "selection_reason": "按资产所属市场或行业选择，用于剔除同期市场和板块共同涨跌。"},
        "risk_factor": risk_factor(asset_id), "can_enter_plus100_calculation": grade == "A",
        "a_grade_not_future_success_probability": True, "missing_for_upgrade": failures if grade == "B" else [],
        "price_source": {"asset_symbol": symbol, "benchmark_symbol": benchmark_symbol, "source": "Yahoo Finance daily adjusted close chart", "retrieved_at_utc": datetime.now(timezone.utc).isoformat()},
        "event_source_policy": "公司正式公告优先；未稳定取得IR发布时间时使用SEC 8-K/6-K正式接收时间。10-Q/10-K提交日不再作为事件日。",
    }


def rank_a(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for row in rows:
        if row["new_grade"] != "A":
            continue
        stats = row["absolute_benchmark_excess_statistics"]
        score = (stats["excess_return_20d"]["median"] * 35 + stats["excess_return_60d"]["median"] * 35
                 + stats["excess_return_60d"]["positive_ratio"] * 20 + stats["max_drawdown_60d"]["worst"] * 10)
        ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    result = []
    for index, (score, row) in enumerate(ranked, 1):
        stats = row["absolute_benchmark_excess_statistics"]
        result.append({
            "rank": index, "asset_id": row["asset_id"], "asset_name": row["asset_name"], "ranking_score": score,
            "why_ranked_here": f"20日超额中位{stats['excess_return_20d']['median']:.2%}、60日{stats['excess_return_60d']['median']:.2%}，正超额比例{stats['excess_return_60d']['positive_ratio']:.0%}，最坏最大回撤{stats['max_drawdown_60d']['worst']:.2%}。",
        })
    return result


def overlap_and_risk(rows: list[dict[str, Any]]) -> dict[str, Any]:
    a_rows = [row for row in rows if row["new_grade"] == "A"]
    times: dict[str, list[str]] = defaultdict(list)
    factors: dict[str, list[str]] = defaultdict(list)
    for row in a_rows:
        times[row["future_12m_event_window"]["time"]].append(row["asset_id"])
        factors[row["risk_factor"]].append(row["asset_id"])
    return {
        "a_grade_count": len(a_rows),
        "time_overlap_groups": [{"window": window, "assets": assets, "sequential_reuse_allowed": len(assets) == 1, "reason": "同一时间窗口内资金不能假装先后复用。"} for window, assets in times.items()],
        "common_risk_groups": [{"risk_factor": factor, "assets": assets, "independent_success_count_allowed": 1 if len(assets) > 1 else len(assets), "reason": "同组依赖同一经营或资金变量，不能机械当成多个独立成功事件。"} for factor, assets in sorted(factors.items())],
        "sequential_capital_reuse_supported": False,
        "reason": "未获批战术资金池，且多个事件只有月份/季度窗口，无法证明前一事件结束后资金已释放。",
    }


def annual_calculability(rows: list[dict[str, Any]], overlap: dict[str, Any]) -> dict[str, Any]:
    a_rows = [row for row in rows if row["new_grade"] == "A"]
    missing = []
    if len(a_rows) < 2:
        missing.append("足够数量且时间可排布的A级事件")
    missing.extend(["董事长批准的战术资金池比例", "每个A级窗口的资金释放规则", "剔除共同风险后的独立事件数", "基础组合和事件波段使用同一资金口径的贡献公式"])
    return {
        "plus100_calculable": False,
        "reason": "机会层已完成重新研究，但资金比例、释放机制和独立性没有获批，不能把历史超额收益串成组合收益。",
        "quantifiable_opportunity_ranges": [{
            "asset_id": row["asset_id"], "event": row["future_12m_event_window"]["event"],
            "20d_excess_iqr": [row["absolute_benchmark_excess_statistics"]["excess_return_20d"]["p25"], row["absolute_benchmark_excess_statistics"]["excess_return_20d"]["p75"]],
            "60d_excess_iqr": [row["absolute_benchmark_excess_statistics"]["excess_return_60d"]["p25"], row["absolute_benchmark_excess_statistics"]["excess_return_60d"]["p75"]],
            "worst_max_drawdown": row["absolute_benchmark_excess_statistics"]["max_drawdown_60d"]["worst"], "capital_weight": None,
        } for row in a_rows],
        "capital_weight_status": "NOT_AUTHORIZED / NOT_ASSUMED", "time_reuse_status": "NOT_PROVEN",
        "common_risk": overlap["common_risk_groups"], "maximum_portfolio_drawdown": None,
        "missing_variables": missing,
        "conclusion": "当前不能计算可靠的+100%路径。现在知道哪些事件可能有可重复超额收益，但还不知道获批资金比例、可否顺序复用，以及共同风险下组合会回撤多少。",
    }


def main() -> None:
    current = {"v11": v1.sha(v1.V11), "v12": v1.sha(v1.V12), "locked": v1.sha(v1.LOCKED)}
    expected = {"v11": v1.EXPECTED["v11"], "v12": v1.EXPECTED["v12"], "locked": EXPECTED_LOCKED_SHA}
    if current != expected:
        raise SystemExit(f"frozen source fingerprint mismatch: {current}")
    source, locked, old = v1.load(v1.V12_SOURCE), v1.load(v1.LOCKED), v1.load(OLD_SUPPLEMENT)
    assets = source.get("all_assets_ranked") or []
    if len(assets) != 42 or len(locked.get("contracts") or []) != 84:
        raise SystemExit("frozen count mismatch")
    old_grades = {row["asset_id"]: row.get("grade") for row in old.get("asset_scan") or []}
    ticker_map = v1.sec_ticker_map()
    symbols = {v1.yahoo_symbol(asset["asset_id"]) for asset in assets}
    symbols.update(benchmark_for(asset["asset_id"])[0] for asset in assets)
    symbols.discard(None)
    price_cache: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(v1.yahoo_prices, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            price_cache[futures[future]] = future.result()
    indexed_rows: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(research_one, asset, ticker_map, price_cache, old_grades): index for index, asset in enumerate(assets)}
        for future in as_completed(futures):
            index = futures[future]
            indexed_rows[index] = future.result()
            print(f"[{len(indexed_rows):02d}/42] {assets[index]['asset_id']} {assets[index]['asset_name']}", flush=True)
    rows = [indexed_rows[index] for index in range(len(assets))]
    counts = {grade: sum(row["new_grade"] == grade for row in rows) for grade in "ABC"}
    old_a_transitions = [{"asset_id": row["asset_id"], "asset_name": row["asset_name"], "transition": row["grade_transition"], "downgrade_reason": row["downgrade_reason"]} for row in rows if row["old_grade"] == "A"]
    ranking, overlap = rank_a(rows), overlap_and_risk(rows)
    annual = annual_calculability(rows, overlap)
    common = {
        "run_id": "PLUS100-EVENT-WINDOW-METHOD-V2-20260829-JST", "status": "WAITING_GPT_PLUS100_METHOD_REREVIEW",
        "generated_at_jst": datetime.now(JST).isoformat(), "source_v11_sha256": current["v11"], "source_v12_sha256": current["v12"],
        "locked_forecast_sha256": current["locked"], "locked_forecast_changed_count": 0, "v11_changed_count": 0,
        "v12_changed_count": 0, "asset_count": 42, "old_a_reinterpreted_as": "历史数据可量化候选", "old_a_count": 21,
        "new_grade_counts": counts,
    }
    supplement = {
        **common, "supplement_id": "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT_v2",
        "identity": "INCREMENTAL_RESEARCH_LAYER / DOES_NOT_REWRITE_V11_V12_OR_LOCKED_FORECASTS",
        "method": {
            "event_time": "公司正式公告时间优先；其次SEC 8-K/6-K正式接收时间。10-Q/10-K提交日禁止作为财报事件日。",
            "event_anchor": "盘后消息锚定下一交易日，盘前消息锚定当日，日线收益从事件日前一收盘起算。",
            "returns": [1, 5, 20, 60], "excess_return": "股票同期收益减合理市场或行业基准同期收益",
            "primary_samples": "只使用HIGH或MEDIUM相似样本；LOW仅留审计，不进A级统计。",
            "a_grade_rule": "事件可定位、触发具体、至少5个相似样本且至少2个HIGH、20/60日正向超额收益具有重复性、下行风险可接受。",
            "not_success_probability": "历史正超额比例不是未来成功概率。", "no_fake_event_date": True,
            "no_fake_probability": True, "no_target_backsolve": True,
        },
        "future_event_calendar": [row["future_12m_event_window"] for row in rows], "asset_scan": rows,
        "old_21_regrade": old_a_transitions, "grade_pools": {grade: [row for row in rows if row["new_grade"] == grade] for grade in "ABC"},
        "a_grade_ranking": ranking, "overlap_and_risk": overlap, "annual_path_calculability": annual,
        "priority_deep_review": [row for row in rows if row["asset_id"] in {"US.NVDA", "US.MU", "JP.9984", "US.ORCL", "US.MSFT", "US.AVGO", "US.CRDO", "US.ETN", "US.COIN", "KRX.000660", "KRX.005930"}],
    }
    outputs = {
        "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT_v2.json": supplement,
        "42项未来12个月事件日历.json": {**common, "events": supplement["future_event_calendar"]},
        "真实事件时间历史样本.json": {**common, "assets": [{"asset_id": row["asset_id"], "samples": row["real_event_time_samples"]} for row in rows]},
        "条件匹配历史事件样本.json": {**common, "assets": [{"asset_id": row["asset_id"], "samples": row["condition_matched_samples"]} for row in rows]},
        "股票与基准1_5_20_60日收益.json": {**common, "assets": [{"asset_id": row["asset_id"], "benchmark": row["benchmark"], "statistics": row["absolute_benchmark_excess_statistics"]} for row in rows]},
        "超额收益与最大回撤统计.json": {**common, "assets": [{"asset_id": row["asset_id"], "statistics": row["absolute_benchmark_excess_statistics"]} for row in rows]},
        "新A_B_C三级波段池.json": {**common, "ranking": ranking, "pools": supplement["grade_pools"], "old_21_regrade": old_a_transitions},
        "时间重叠与风险相关性v2.json": {**common, **overlap}, "年度路径可计算性报告.json": {**common, **annual},
    }
    for name, value in outputs.items():
        v1.dump(V13_DIR / name, value)
    print(json.dumps({"status": common["status"], "new_grade_counts": counts, "a_ranking": ranking, "plus100_calculable": annual["plus100_calculable"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
