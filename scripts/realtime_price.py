#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unified realtime quote helper.

Read-only. Uses OpenD quote APIs only:
subscribe with SubType.QUOTE, get_stock_quote, and get_market_state.
No historical K-line, trade context, order API, or publishing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any


HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def records_from_frame(obj: Any) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if hasattr(obj, "to_dict"):
        return [{str(k): json_safe(v) for k, v in row.items()} for row in obj.to_dict(orient="records")]
    if isinstance(obj, list):
        out = []
        for row in obj:
            if isinstance(row, dict):
                out.append({str(k): json_safe(v) for k, v in row.items()})
            else:
                out.append({"raw": json_safe(row)})
        return out
    if isinstance(obj, dict):
        return [{str(k): json_safe(v) for k, v in obj.items()}]
    return [{"raw": json_safe(obj)}]


def classify_failure(message: str) -> str:
    text = str(message).lower()
    if any(token in text for token in ["permission", "right", "quota", "authority"]):
        return "permission_or_quota"
    if any(token in text for token in ["subscribe", "subscription"]):
        return "need_subscription"
    if any(token in text for token in ["connect", "disconnect", "timeout", "connection", "socket"]):
        return "connection_problem"
    if any(token in text for token in ["invalid", "unknown", "security", "stock code", "market", "format of code"]):
        return "unsupported_code_or_market"
    return "api_failure"


def connect_quote_context(max_retries: int = 3, wait_seconds: int = 3):
    from futu import OpenQuoteContext, RET_OK

    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_retries + 1):
        ctx = None
        try:
            ctx = OpenQuoteContext(host=HOST, port=PORT)
            ret, data = ctx.get_global_state()
            attempts.append({
                "attempt": attempt,
                "success": ret == RET_OK,
                "ret": int(ret) if isinstance(ret, int) else str(ret),
                "data": records_from_frame(data),
                "time": now_jst(),
            })
            if ret == RET_OK:
                return ctx, attempts
        except Exception as exc:
            attempts.append({
                "attempt": attempt,
                "success": False,
                "exception": str(exc),
                "failure_type": classify_failure(str(exc)),
                "time": now_jst(),
            })
        try:
            if ctx is not None:
                ctx.close()
        except Exception:
            pass
        if attempt < max_retries:
            time.sleep(wait_seconds)
    return None, attempts


def get_market_state_value(ctx: Any, code: str) -> tuple[str | None, dict[str, Any]]:
    from futu import RET_OK

    try:
        ret, data = ctx.get_market_state([code])
        rows = records_from_frame(data)
        if ret == RET_OK and rows:
            return rows[0].get("market_state"), {"success": True, "raw": rows[0]}
        return None, {"success": False, "failure_type": classify_failure(str(data)), "failure_reason": str(data), "raw": rows}
    except Exception as exc:
        return None, {"success": False, "failure_type": classify_failure(str(exc)), "failure_reason": str(exc), "raw": None}


def is_us_code(code: str) -> bool:
    return code.startswith("US.")


def is_crypto_code(code: str) -> bool:
    return code.startswith("CC.")


def choose_price_field(code: str, market_state: str | None) -> tuple[str, str]:
    state = (market_state or "").upper()
    if is_crypto_code(code):
        return "last_price", "crypto_last_price"
    if code.startswith("JP.") or code.startswith("HK."):
        return "last_price", "cash_market_last_price"
    if is_us_code(code):
        if "PRE" in state:
            return "pre_price", "us_pre_market"
        if "AFTER" in state:
            return "after_price", "us_after_hours"
        if "OVERNIGHT" in state:
            return "overnight_price", "us_overnight"
        if any(token in state for token in ["NORMAL", "TRADING", "MORNING", "AFTERNOON", "OPEN"]):
            return "last_price", "us_regular_session"
        return "last_price", "us_state_unknown_default_regular_field"
    return "last_price", "default_last_price"


def is_missing_price(value: Any) -> bool:
    return value is None or value == "" or value == "N/A"


def get_realtime_price(code: str, ctx: Any | None = None, max_retries: int = 3, wait_seconds: int = 3) -> dict[str, Any]:
    """Return one realtime quote decision for code.

    The function never downgrades to a stale fallback field. If the field
    selected for the current market state has no value, status is FAIL.
    """

    from futu import RET_OK, SubType

    own_ctx = False
    attempts: list[dict[str, Any]] = []
    if ctx is None:
        ctx, attempts = connect_quote_context(max_retries=max_retries, wait_seconds=wait_seconds)
        own_ctx = True

    result: dict[str, Any] = {
        "code": code,
        "price": None,
        "data_date": None,
        "data_time": None,
        "market_state": None,
        "used_field": None,
        "status": "FAIL",
        "reason": None,
        "field_policy": None,
        "connection_attempts": attempts,
        "raw_fields": None,
        "generated_at": now_jst(),
    }

    if ctx is None:
        result["reason"] = "OpenD quote connection failed"
        return result

    try:
        market_state, market_state_raw = get_market_state_value(ctx, code)
        result["market_state"] = market_state
        result["market_state_raw"] = market_state_raw

        extended_time = is_us_code(code)
        try:
            ret, data = ctx.subscribe(
                [code],
                [SubType.QUOTE],
                is_first_push=True,
                subscribe_push=False,
                extended_time=extended_time,
            )
        except Exception as exc:
            result["reason"] = str(exc)
            result["failure_type"] = classify_failure(str(exc))
            return result

        if ret != RET_OK:
            result["reason"] = str(data)
            result["failure_type"] = classify_failure(str(data))
            return result

        ret, data = ctx.get_stock_quote([code])
        if ret != RET_OK:
            result["reason"] = str(data)
            result["failure_type"] = classify_failure(str(data))
            return result

        rows = records_from_frame(data)
        row = rows[0] if rows else {}
        field, policy = choose_price_field(code, market_state)
        value = row.get(field)
        result.update({
            "data_date": row.get("data_date"),
            "data_time": row.get("data_time"),
            "used_field": field,
            "field_policy": policy,
            "raw_fields": {
                "last_price": row.get("last_price"),
                "pre_price": row.get("pre_price"),
                "after_price": row.get("after_price"),
                "overnight_price": row.get("overnight_price"),
                "sec_status": row.get("sec_status"),
                "suspension": row.get("suspension"),
            },
        })
        if is_missing_price(value):
            result["status"] = "FAIL"
            result["price"] = None
            result["reason"] = f"selected field {field} has no value for market_state {market_state}"
            return result

        result["status"] = "OK"
        result["price"] = value
        result["reason"] = None
        return result
    finally:
        if own_ctx:
            try:
                ctx.close()
            except Exception:
                pass


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Test unified realtime price helper.")
    parser.add_argument("codes", nargs="*", default=[
        "US.NVDA",
        "US.MSFT",
        "JP.6857",
        "JP.9984",
        "CC.BTCUSD",
        "CC.ETHUSD",
    ])
    args = parser.parse_args()

    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    output = {
        "task_id": "TASK-2026-07-02-055",
        "mode": "READ_ONLY_REALTIME_PRICE_TEST",
        "connection": {"connected": ctx is not None, "attempts": attempts},
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "history_kline_called": False,
        },
        "results": [],
    }
    try:
        for code in args.codes:
            output["results"].append(get_realtime_price(code, ctx=ctx))
    finally:
        if ctx is not None:
            ctx.close()

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
