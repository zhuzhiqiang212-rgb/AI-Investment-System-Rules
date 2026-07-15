#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build true MA50/MA200 levels for current holdings from Futu OpenD.

Read-only quote context only. The script pulls K_DAY history via
request_history_kline and computes moving averages from close prices.
It never estimates, interpolates, or falls back to stale values.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from realtime_price import (  # noqa: E402
    classify_failure,
    connect_quote_context,
    get_realtime_price,
    records_from_frame,
)


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
    reread = path.read_text(encoding="utf-8")
    if reread != text + "\n":
        raise RuntimeError(f"UTF-8 write/read mismatch: {path}")
    if "\ufffd" in reread:
        raise RuntimeError(f"U+FFFD detected after write: {path}")


def unique_holdings(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in reviews:
        symbol = item.get("symbol")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append({
            "symbol": symbol,
            "name": item.get("name"),
        })
    return out


def null_item(symbol: str, name: str | None, status: str, reason: str | None) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "name": name,
        "realtime_price": None,
        "price_field": None,
        "price_status": "FAIL",
        "price_reason": reason,
        "ma50": None,
        "ma200": None,
        "kline_count": 0,
        "status": status,
        "reason": reason,
    }


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 6)


def get_kline_closes(ctx: Any, symbol: str) -> tuple[list[float], int, str | None]:
    from futu import AuType, KLType, RET_OK

    try:
        ret, data, page_req_key = ctx.request_history_kline(
            symbol,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ,
            max_count=1000,
        )
    except Exception as exc:
        return [], 0, str(exc)

    if ret != RET_OK:
        return [], 0, str(data)

    rows = records_from_frame(data)
    while page_req_key is not None and len(rows) < 300:
        try:
            ret, data, page_req_key = ctx.request_history_kline(
                symbol,
                ktype=KLType.K_DAY,
                autype=AuType.QFQ,
                max_count=1000,
                page_req_key=page_req_key,
            )
        except Exception as exc:
            return [], len(rows), str(exc)
        if ret != RET_OK:
            return [], len(rows), str(data)
        rows.extend(records_from_frame(data))

    closes: list[float] = []
    for row in rows:
        close = to_float(row.get("close"))
        if close is not None:
            closes.append(close)
    return closes, len(rows), None


def build_item(ctx: Any, symbol: str, name: str | None) -> dict[str, Any]:
    quote = get_realtime_price(symbol, ctx=ctx, max_retries=1, wait_seconds=0)
    price = quote.get("price") if quote.get("status") == "OK" else None
    price_field = quote.get("used_field")
    price_status = quote.get("status")
    price_reason = quote.get("reason")

    if symbol.startswith("CC."):
        return {
            "symbol": symbol,
            "name": name,
            "realtime_price": price,
            "price_field": price_field,
            "price_status": price_status,
            "price_reason": price_reason,
            "ma50": None,
            "ma200": None,
            "kline_count": 0,
            "status": "待拉·该类不支持均线",
            "reason": "OpenD 加密代码暂不跑 K_DAY 均线；不使用估算或旧值",
        }

    closes, kline_count, kline_reason = get_kline_closes(ctx, symbol)
    ma20 = compute_average(closes, 20)     # 派工单20260715:20日均线(短期)
    ma50 = compute_average(closes, 50)
    ma200 = compute_average(closes, 200)
    # 低吸价=回踩50日均线位、止损价=跌破200日年线位(工单口径·缺K线则None不编)
    low_buy = ma50
    stop_loss = ma200

    status_parts: list[str] = []
    reason_parts: list[str] = []
    if kline_reason:
        status_parts.append("待拉·K线读取失败")
        reason_parts.append(kline_reason)
    else:
        if ma50 is None:
            status_parts.append("待拉·历史不足")
            reason_parts.append("MA50 历史K线不足50根")
        if ma200 is None:
            status_parts.append("待拉·历史不足")
            reason_parts.append("MA200 历史K线不足200根")
    if price_status != "OK":
        reason_parts.append(f"realtime_price FAIL: {price_reason}")

    status = "OK" if not status_parts else "；".join(dict.fromkeys(status_parts))
    return {
        "symbol": symbol,
        "name": name,
        "realtime_price": price,
        "price_field": price_field,
        "price_status": price_status,
        "price_reason": price_reason,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "low_buy_price": low_buy,       # 低吸价=MA50位(回踩50日)·缺则None不编
        "stop_loss_price": stop_loss,   # 止损价=MA200位(跌破年线)·缺则None不编
        "kline_count": kline_count,
        "status": status,
        "reason": None if not reason_parts else "；".join(reason_parts),
    }


def build_disconnected(date: str, holdings: list[dict[str, Any]], attempts: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    items = [
        null_item(item["symbol"], item.get("name"), "待拉·OpenD未连", reason)
        for item in holdings
    ]
    return {
        "task_id": "D3-1",
        "generated_at": now_jst(),
        "date": date,
        "connection": {"ok": False, "reason": reason, "attempts": attempts},
        "source_kline": "request_history_kline K_DAY",
        "holdings": items,
        "summary": {"total": len(items), "ok": 0, "pending": len(items)},
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
        },
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Build holdings MA50/MA200 levels from Futu OpenD.")
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{args.date}.json"
    output_path = ROOT / "data" / "holdings" / f"ma_levels_{args.date}.json"
    holdings_doc = read_json(holdings_path)
    holdings = unique_holdings(holdings_doc.get("reviews", []))

    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    if ctx is None:
        reason = "OpenD quote connection failed"
        payload = build_disconnected(args.date, holdings, attempts, reason)
        write_json(output_path, payload)
        print(json.dumps({
            "output": str(output_path),
            "exit_code": 2,
            "connection_ok": False,
            "reason": reason,
            "summary": payload["summary"],
        }, ensure_ascii=False, indent=2))
        return 2

    items: list[dict[str, Any]] = []
    try:
        for item in holdings:
            try:
                items.append(build_item(ctx, item["symbol"], item.get("name")))
            except Exception as exc:
                items.append(null_item(
                    item["symbol"],
                    item.get("name"),
                    "待拉·单只失败",
                    f"{classify_failure(str(exc))}: {exc}",
                ))
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    ok = sum(1 for item in items if item.get("status") == "OK")
    pending = len(items) - ok
    payload = {
        "task_id": "D3-1",
        "generated_at": now_jst(),
        "date": args.date,
        "connection": {"ok": True, "reason": "", "attempts": attempts},
        "source_kline": "request_history_kline K_DAY",
        "holdings": items,
        "summary": {"total": len(items), "ok": ok, "pending": pending},
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
        },
    }
    write_json(output_path, payload)
    print(json.dumps({
        "output": str(output_path),
        "exit_code": 0,
        "connection_ok": True,
        "summary": payload["summary"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
