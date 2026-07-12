#!/usr/bin/env python3
"""
opportunity_valuation_gate.py
TASK-2026-07-02-029

Second valuation gate on chain-driven opportunity pool.
- Reads daily chain opportunity pool.
- Uses Futu OpenD quote-side get_stock_filter only.
- No trade context, no order, no publish.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
OPPORTUNITY_DIR = ROOT / "data" / "opportunities"
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 reread mismatch: {path}")
    if chr(63) in reread or chr(0xFFFD) in reread:
        raise RuntimeError(f"Garble marker found: {path}")


def base_code(code: str) -> str:
    value = str(code or "").strip()
    if "." in value:
        value = value.split(".")[-1]
    return value.upper()


def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def build_financial_filters():
    from futu import FinancialFilter, FinancialQuarter, SimpleFilter, StockField

    pe = SimpleFilter()
    pe.stock_field = StockField.PE_TTM
    pe.is_no_filter = True

    pb = SimpleFilter()
    pb.stock_field = StockField.PB_RATE
    pb.is_no_filter = True

    net_profit = FinancialFilter()
    net_profit.stock_field = StockField.NET_PROFIT
    net_profit.quarter = FinancialQuarter.ANNUAL
    net_profit.is_no_filter = True

    return [pe, pb, net_profit]


def records_from_filter_result(data: Any) -> list[Any]:
    if isinstance(data, tuple) and len(data) >= 3:
        return list(data[2] or [])
    if isinstance(data, tuple) and len(data) >= 2:
        return list(data[1] or [])
    return list(data or [])


def financial_record_from_item(item: Any) -> dict[str, Any]:
    raw = dict(getattr(item, "__dict__", {}))
    code = str(raw.get("stock_code") or "")
    annual_key = ("net_profit", "annual")
    return {
        "code": code,
        "base": base_code(code),
        "pe": safe(raw.get("pe_ttm")),
        "pb": safe(raw.get("pb_rate")),
        "net_profit": safe(raw.get(annual_key)),
        "raw_keys": [str(key) for key in raw.keys()],
    }


def fetch_financials_for_plate(ctx: Any, market: str, plate_code: str) -> tuple[dict[str, dict[str, Any]], str]:
    from futu import Market, RET_OK

    market_value = getattr(Market, market)
    ret, data = ctx.get_stock_filter(
        market_value,
        filter_list=build_financial_filters(),
        plate_code=plate_code,
        begin=0,
        num=200,
    )
    if ret != RET_OK:
        return {}, str(data)
    result: dict[str, dict[str, Any]] = {}
    for item in records_from_filter_result(data):
        record = financial_record_from_item(item)
        result[record["base"]] = record
    return result, ""


def classify_candidate(candidate: dict[str, Any], financial: dict[str, Any] | None, error: str) -> dict[str, Any]:
    market = str(candidate.get("market") or "")
    pe_limit = 40
    pe = to_float(financial.get("pe") if financial else None)
    pb = to_float(financial.get("pb") if financial else None)
    net_profit = to_float(financial.get("net_profit") if financial else None)
    positive_profit = None if net_profit is None else net_profit > 0

    category = "C类财务待补"
    reason = "财务数据待补"
    if error:
        reason = "财务数据待补：" + error
    elif pe is not None and positive_profit is not None:
        if positive_profit and 0 < pe < pe_limit:
            category = "A类趋势加估值合理"
            reason = "正盈利且PE在合理区间"
        else:
            category = "B类趋势但贵或无盈利"
            reason = "PE为负、无盈利或PE超过上限"

    return {
        "code": candidate.get("code"),
        "name": candidate.get("name"),
        "node_class": candidate.get("node_class"),
        "plate_code": candidate.get("plate_code"),
        "plate_name": candidate.get("plate_name"),
        "market": market,
        "pe": pe,
        "pb": pb,
        "positive_profit": positive_profit,
        "net_profit": net_profit,
        "category": category,
        "reason": reason,
    }


def load_pool(date_text: str) -> tuple[dict[str, Any], Path]:
    path = OPPORTUNITY_DIR / f"chain_opportunities_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError("需先跑链驱动机会发现: " + str(path))
    return json.loads(path.read_text(encoding="utf-8")), path


def run_gate(date_text: str) -> dict[str, Any]:
    from futu import OpenQuoteContext

    pool, source_path = load_pool(date_text)
    candidates = pool.get("candidates", [])
    plate_cache: dict[tuple[str, str], tuple[dict[str, dict[str, Any]], str]] = {}
    classified = []

    ctx = OpenQuoteContext(host=HOST, port=PORT)
    try:
        for candidate in candidates:
            market = str(candidate.get("market") or "")
            plate_code = str(candidate.get("plate_code") or "")
            cache_key = (market, plate_code)
            if cache_key not in plate_cache:
                plate_cache[cache_key] = fetch_financials_for_plate(ctx, market, plate_code)
                time.sleep(3.2)
            records, error = plate_cache[cache_key]
            financial = records.get(base_code(str(candidate.get("code") or "")))
            classified.append(classify_candidate(candidate, financial, error))
    finally:
        ctx.close()

    groups = {
        "A类趋势加估值合理": [],
        "B类趋势但贵或无盈利": [],
        "C类财务待补": [],
    }
    for item in classified:
        groups[item["category"]].append(item)

    source_fp = pool.get("fingerprint", {})
    return {
        "task_id": "TASK-2026-07-02-029",
        "mode": "FORMAL_VALUATION_GATE_READ_ONLY",
        "generated_at": now_jst(),
        "fingerprint": {
            "source_pool_file": str(source_path),
            "total_gate": source_fp.get("total_gate"),
            "activated_node_classes": source_fp.get("activated_node_classes"),
            "source_scope": source_fp.get("scope"),
            "generated_at": now_jst(),
            "mode": "FORMAL_VALUATION_GATE_READ_ONLY",
        },
        "safety": {
            "read_only": True,
            "quote_context_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "deep_valuation": False,
        },
        "criteria": {
            "A": "正盈利且0<PE<40",
            "B": "PE为负、无盈利或PE超过上限",
            "C": "财务数据取不到，待补",
        },
        "counts": {key: len(value) for key, value in groups.items()},
        "groups": groups,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Valuation gate on chain-driven opportunity pool.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = parser.parse_args()
    try:
        output = run_gate(args.date)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    output_path = OPPORTUNITY_DIR / f"opportunity_gated_{args.date}.json"
    write_json_utf8(output_path, output)
    print(f"OUTPUT_PATH={output_path}")
    print(f"COUNTS={json.dumps(output['counts'], ensure_ascii=False)}")
    for item in output["groups"]["A类趋势加估值合理"]:
        print(f"A={item.get('code')} {item.get('name')} NODE={item.get('node_class')} PE={item.get('pe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
