#!/usr/bin/env python3
"""Build the V13 incremental event-window research supplement."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V13_DIR = ROOT / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST"
V12_SOURCE = ROOT / "output/candidates/2026-08-28/V12-CHAIRMAN-DECISION-20260828181431-JST/V12结构化产品源.json"
LOCKED = ROOT / "output/decision_inputs/2026-08-26/V7-V20-FORECAST-LOCK-20260826175555-JST/84份正式预测_LOCKED.json"
V11 = ROOT / "output/candidates/2026-08-28/V7-V20-PREDICTIVE-FULL-HTML-V11-20260828113325-JST/★2026-08-27完整投研产品候选_v2.0_预测型完整HTML_v11.html"
V12 = ROOT / "output/candidates/2026-08-28/V12-CHAIRMAN-DECISION-20260828181431-JST/V12董事长投资决策产品.html"
EXPECTED = {
    "v11": "3FCCD3E4F3978C87DDC18C6E80D570EE61427BA1A8052BBDD651C4477EB83E78",
    "v12": "C3D56CA6D3FE2624E396428515A916F66DE81336920A9815CD720C4DE4537494",
}
UA = "AI-Investment-System event-window research local-research@example.com"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_json(url: str) -> Any:
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(attempt + 1)
    raise RuntimeError(f"{url}: {last}")


def yahoo_symbol(asset_id: str) -> str | None:
    if asset_id in {"BTC", "ETH"}:
        return asset_id + "-USD"
    if asset_id.startswith("JP."):
        return asset_id.split(".", 1)[1] + ".T"
    if asset_id.startswith("KRX."):
        return asset_id.split(".", 1)[1] + ".KS"
    if asset_id.startswith("US."):
        return asset_id.split(".", 1)[1]
    return None


def yahoo_prices(symbol: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(symbol, safe="")
    start = int(datetime(2017, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2027, 12, 31, tzinfo=timezone.utc).timestamp())
    doc = fetch_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={start}&period2={end}&interval=1d&events=history"
    )
    result = ((doc.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
    adjusted = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    closes = quote.get("close") or []
    rows = []
    for index, stamp in enumerate(timestamps):
        value = adjusted[index] if index < len(adjusted) and adjusted[index] is not None else (
            closes[index] if index < len(closes) else None
        )
        if value is not None:
            rows.append({"date": datetime.fromtimestamp(stamp, timezone.utc).date().isoformat(), "close": float(value)})
    return rows


def sec_ticker_map() -> dict[str, dict[str, Any]]:
    raw = fetch_json("https://www.sec.gov/files/company_tickers.json")
    return {item["ticker"].upper(): item for item in raw.values()}


def sec_result_dates(ticker: str, ticker_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    item = ticker_map.get(ticker.upper())
    if not item:
        return []
    cik = int(item["cik_str"])
    recent = (fetch_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").get("filings") or {}).get("recent") or {}
    keys = ["form", "filingDate", "accessionNumber", "primaryDocument"]
    if not all(key in recent for key in keys):
        return []
    rows = []
    for form, filing_date, accession, primary_document in zip(*(recent[key] for key in keys)):
        if form not in {"10-Q", "10-K"}:
            continue
        compact = accession.replace("-", "")
        rows.append({
            "event_date": filing_date,
            "event_type": form,
            "source_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{compact}/{primary_document}",
            "source_quality": "A",
            "source_role": "正式季度或年度财务申报日",
        })
    return rows


def nasdaq_result_dates(ticker: str) -> list[dict[str, Any]]:
    try:
        doc = fetch_json(f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise")
    except Exception:
        return []
    rows = ((((doc.get("data") or {}).get("earningsSurpriseTable") or {}).get("rows")) or [])
    result = []
    for row in rows:
        try:
            event_date = datetime.strptime(row.get("dateReported"), "%m/%d/%Y").date().isoformat()
        except (TypeError, ValueError):
            continue
        result.append({
            "event_date": event_date,
            "event_type": "正式业绩公布",
            "source_url": f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise",
            "source_quality": "B",
            "source_role": "Nasdaq历史业绩公布日",
        })
    return result


def reaction(event: dict[str, Any], prices: list[dict[str, Any]]) -> dict[str, Any] | None:
    dates = [row["date"] for row in prices]
    closes = [row["close"] for row in prices]
    anchor_index = None
    for index, trading_date in enumerate(dates):
        if trading_date < event["event_date"]:
            anchor_index = index
        else:
            break
    if anchor_index is None or anchor_index + 60 >= len(prices):
        return None
    anchor = closes[anchor_index]
    path = closes[anchor_index : anchor_index + 61]
    peak, max_drawdown = path[0], 0.0
    for value in path:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return {
        **event,
        "anchor_trading_date": dates[anchor_index],
        "anchor_close": anchor,
        "return_5d": closes[anchor_index + 5] / anchor - 1,
        "return_20d": closes[anchor_index + 20] / anchor - 1,
        "return_60d": closes[anchor_index + 60] / anchor - 1,
        "max_drawdown_60d": max_drawdown,
        "calculation_rule": "事件日前最后一个交易日收盘至其后第5/20/60个交易日收盘；最大回撤按后续60个交易日路径计算",
    }


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return values[low]
    return values[low] * (high - position) + values[high] * (position - low)


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not samples:
        return None
    result: dict[str, Any] = {"sample_count": len(samples)}
    for days in (5, 20, 60):
        values = [row[f"return_{days}d"] for row in samples]
        result[f"return_{days}d"] = {
            "median": statistics.median(values),
            "p25": percentile(values, 0.25),
            "p75": percentile(values, 0.75),
            "worst": min(values),
            "best": max(values),
        }
    drawdowns = [row["max_drawdown_60d"] for row in samples]
    result["max_drawdown_60d"] = {"median": statistics.median(drawdowns), "worst": min(drawdowns)}
    return result


def risk_factor(asset_id: str) -> str:
    groups = {
        "AI算力与半导体资本开支": {"US.NVDA", "US.AVGO", "US.AMD", "US.TSM", "US.ASML", "JP.6857", "JP.8035", "JP.7735", "US.TER"},
        "AI高速互联": {"US.CRDO", "US.ALAB", "US.ANET", "US.COHR"},
        "存储价格与HBM周期": {"US.MU", "US.SNDK", "KRX.000660", "KRX.005930", "JP.4063", "JP.3436"},
        "数据中心电力与建设": {"US.ETN", "US.GEV", "US.PWR", "US.VRT", "US.MOD"},
        "云资本开支与AI变现": {"US.MSFT", "US.META", "US.ORCL"},
        "加密流动性与监管": {"BTC", "ETH", "US.COIN", "US.CRCL", "US.MSTR"},
        "日本资产价值与融资": {"JP.9984", "JP.8001", "JP.8766"},
        "消费与制造业周期": {"JP.6758", "JP.6954", "JP.7203", "JP.7974"},
    }
    for name, members in groups.items():
        if asset_id in members:
            return name
    return {"JP.4568": "临床与审批", "US.IBKR": "交易活跃度与利率", "US.SPCX": "商业航天里程碑与估值"}.get(asset_id, "公司特定经营事件")


def specific(asset: dict[str, Any]) -> bool:
    text = " ".join(str(asset.get(key) or "") for key in ("short_catalyst", "short_upgrade_condition", "short_downgrade_condition"))
    return len(text) >= 80 and not any(word in text for word in ("好于预期就升级", "弱于预期就降级", "尚未取得"))


def research_one(asset: dict[str, Any], ticker_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    asset_id, symbol = asset["asset_id"], yahoo_symbol(asset["asset_id"])
    prices, price_error = [], None
    try:
        prices = yahoo_prices(symbol) if symbol else []
    except Exception as exc:
        price_error = str(exc)
    ticker = asset_id.split(".", 1)[1] if asset_id.startswith("US.") else ""
    formal = []
    if ticker and ticker not in {"ASML", "TSM", "SPCX"}:
        try:
            formal = sec_result_dates(ticker, ticker_map)
        except Exception:
            formal = []
    if len(formal) < 5 and ticker:
        existing = {row["event_date"] for row in formal}
        formal.extend(row for row in nasdaq_result_dates(ticker) if row["event_date"] not in existing)
    formal.sort(key=lambda row: row["event_date"], reverse=True)
    samples = []
    for event in formal:
        row = reaction(event, prices)
        if row:
            samples.append(row)
        if len(samples) >= 8:
            break
    stats = summarize(samples)
    is_specific = specific(asset)
    if stats and stats["sample_count"] >= 5 and is_specific:
        grade, grade_reason = "A", "有明确公司验证事件、至少5次正式财务申报日和完整5/20/60交易日价格统计。"
    elif is_specific and (stats or prices):
        grade, grade_reason = "B", "方向和事件可以核对，但历史样本不足5次、事件口径不完全一致，或正式事件日期仍需补强。"
    else:
        grade, grade_reason = "C", "目前只有方向性故事或缺少足够可比事件，不能可靠量化一次波段收益。"
    return {
        "asset_id": asset_id,
        "asset_name": asset["asset_name"],
        "grade": grade,
        "grade_reason": grade_reason,
        "future_12m_event_window": {
            "event": asset.get("short_catalyst"),
            "expected_window": asset.get("short_event"),
            "entry_observation_condition": asset.get("short_upgrade_condition"),
            "exit_or_realization_condition": "正式事件披露后核对经营事实和价格反应；若逻辑兑现，则结束该窗口，不把一年预测当作继续等待理由。",
            "failure_condition": asset.get("short_downgrade_condition") or asset.get("short_risk"),
            "estimated_holding_window": "事件前后约5至60个交易日" if grade == "A" else "等待关键证据后再确定，当前不作收益量化",
        },
        "historical_comparable_event_type": "正式季度或年度财务申报窗口" if formal else "未取得足够可核历史事件",
        "historical_sample_count": len(samples),
        "historical_samples": samples,
        "historical_price_statistics": stats,
        "price_source": {
            "symbol": symbol,
            "source": "Yahoo Finance daily adjusted close chart",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "row_count": len(prices),
            "error": price_error,
        },
        "event_source": "SEC正式10-Q/10-K申报日；不足时以Nasdaq业绩公布日补充并明确B级来源",
        "current_vs_history": {
            "why_comparable": "当前和历史都围绕正式经营结果、公司指引或其后的市场重新定价窗口。" if formal else "当前尚缺同口径历史事件，不能声称可比。",
            "important_difference": asset.get("short_risk") or asset.get("downside"),
        },
        "risk_factor": risk_factor(asset_id),
        "can_enter_plus100_calculation": grade == "A",
        "why_not_one_year_target": "统计只使用事件前后5/20/60个交易日真实价格，不引用一年期Bull、Bear或概率加权收益。",
        "source_evidence": asset.get("short_evidence_reference") or [],
    }


def overlap_and_risk(rows: list[dict[str, Any]]) -> dict[str, Any]:
    a_rows = [row for row in rows if row["grade"] == "A"]
    factors: dict[str, list[str]] = defaultdict(list)
    for row in a_rows:
        factors[row["risk_factor"]].append(row["asset_id"])
    overlap = []
    if a_rows:
        overlap.append({
            "window": "当前验证日至未来约60个交易日",
            "assets": [row["asset_id"] for row in a_rows],
            "sequential_reuse_allowed": False,
            "reason": "正式业绩和验证窗口大面积重叠；前一窗口明确结束前，不能假设同一笔资金依次复用。",
        })
    return {
        "a_grade_count": len(a_rows),
        "time_overlap_groups": overlap,
        "common_risk_groups": [{
            "risk_factor": factor,
            "assets": assets,
            "independent_success_count_allowed": 1 if len(assets) > 1 else len(assets),
            "reason": "同组资产依赖相同盈利或资金变量，不能机械当成多次独立成功机会。",
        } for factor, assets in sorted(factors.items())],
        "overlapping_wave_false_sequential_reuse_count": 0,
    }


def annual_paths(rows: list[dict[str, Any]]) -> dict[str, Any]:
    a_rows = [row for row in rows if row["grade"] == "A"]
    blocker = (
        "A级事件窗口存在，但没有获批的资金分配、独立成功概率和不重叠全年顺序；不能把历史中位数直接串联成年度复利。"
        if a_rows else "没有达到A级的事件窗口，无法建立年度量化路径。"
    )
    paths = []
    for name, meaning in (
        ("保守路径", "基础组合正常表现，同时允许部分事件窗口失败。"),
        ("中性路径", "只把历史中位反应当研究参照，不把它当获批成功率。"),
        ("激进路径", "多个A级窗口成功，但必须先解决时间重叠与共同风险。"),
    ):
        paths.append({
            "path": name,
            "meaning": meaning,
            "baseline_portfolio_contribution": {
                "FUTU": 0.33614149,
                "SBI": 0.17835622,
                "source": "冻结目标桥，只作基础组合背景",
            },
            "wave_contribution": None,
            "failure_loss": None,
            "maximum_drawdown": None,
            "capital_reuse": "NOT_CALCULATED",
            "status": "CALCULATION_NOT_SUPPORTED",
            "reason": blocker,
        })
    return {
        "paths": paths,
        "plus100_reliably_supported": False,
        "conclusion": "42项资产已全量研究。当前虽有可量化事件窗口，但数量、独立性、时间排序和资金复用证据仍不足以建立可靠的+100%实现路径。",
        "what_is_missing": [
            "不重叠的A级事件窗口顺序",
            "经GPT批准的每个窗口资金占用比例",
            "基于同口径历史样本的成功与失败概率",
            "共同风险发生时的组合最大回撤约束",
        ],
        "chairman_questions": {
            "a_grade_count": len(a_rows),
            "a_grade_assets_and_events": [
                {"asset_id": row["asset_id"], "asset_name": row["asset_name"], "event": row["future_12m_event_window"]["event"]}
                for row in a_rows
            ],
            "historical_normal_move_and_risk": [
                {"asset_id": row["asset_id"], "statistics": row["historical_price_statistics"]} for row in a_rows
            ],
            "gap_to_plus100": blocker,
            "next_validation_events": [
                {"asset_id": row["asset_id"], "event": row["future_12m_event_window"]["event"], "condition": row["future_12m_event_window"]["entry_observation_condition"]}
                for row in rows if row["grade"] in {"A", "B"}
            ][:12],
        },
    }


def main() -> None:
    if sha(V11) != EXPECTED["v11"] or sha(V12) != EXPECTED["v12"]:
        raise SystemExit("frozen V11/V12 fingerprint mismatch")
    source, locked = load(V12_SOURCE), load(LOCKED)
    assets = source.get("all_assets_ranked") or []
    if len(assets) != 42 or len(locked.get("contracts") or []) != 84:
        raise SystemExit("frozen count mismatch")
    ticker_map = sec_ticker_map()
    rows = []
    for index, asset in enumerate(assets, 1):
        print(f"[{index:02d}/42] {asset['asset_id']} {asset['asset_name']}", flush=True)
        rows.append(research_one(asset, ticker_map))
    counts = {grade: sum(row["grade"] == grade for row in rows) for grade in "ABC"}
    overlap, paths = overlap_and_risk(rows), annual_paths(rows)
    common = {
        "run_id": "PLUS100-EVENT-WINDOW-RESEARCH-20260829-JST",
        "status": "RESEARCH_COMPLETE_NOT_GPT_APPROVED",
        "generated_at_jst": datetime.now().astimezone().isoformat(),
        "source_v11_sha256": sha(V11),
        "source_v12_sha256": sha(V12),
        "locked_forecast_sha256": sha(LOCKED),
        "locked_forecast_changed_count": 0,
        "asset_count": 42,
        "grade_counts": counts,
    }
    supplement = {
        **common,
        "supplement_id": "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT",
        "identity": "INCREMENTAL_RESEARCH_LAYER / DOES_NOT_REWRITE_V11_V12_OR_LOCKED_FORECASTS",
        "method": {
            "event_anchor": "事件日前最后一个交易日收盘",
            "price_windows": [5, 20, 60],
            "required_statistics": ["median", "p25", "p75", "worst", "max_drawdown"],
            "a_grade_rule": "明确资产事件 + 至少5次可比正式事件 + 完整5/20/60日真实价格反应",
            "no_one_year_scenario_as_wave_return": True,
            "no_fake_probability": True,
            "no_target_backsolve": True,
        },
        "asset_scan": rows,
        "grade_pools": {grade: [row for row in rows if row["grade"] == grade] for grade in "ABC"},
        "overlap_and_risk": overlap,
        "annual_paths": paths,
    }
    dump(V13_DIR / "42项资产事件窗口扫描结果.json", {**common, "assets": rows})
    dump(V13_DIR / "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT.json", supplement)
    dump(V13_DIR / "A_B_C三级波段池.json", {**common, "pools": supplement["grade_pools"]})
    dump(V13_DIR / "A级机会历史样本.json", {**common, "assets": supplement["grade_pools"]["A"]})
    dump(V13_DIR / "时间重叠与风险相关性检查.json", {**common, **overlap})
    dump(V13_DIR / "保守_中性_激进年度路径.json", {**common, **paths})
    print(json.dumps({"status": "PASS", "grade_counts": counts, "plus100_supported": paths["plus100_reliably_supported"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
