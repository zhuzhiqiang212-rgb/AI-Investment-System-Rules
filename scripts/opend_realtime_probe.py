#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenD realtime quote deep probe.

Read-only probe for TASK-2026-07-02-054.
It uses subscribe with SubType.QUOTE and get_stock_quote. It also reads
query_subscription, get_global_state, get_market_state, and get_market_snapshot.
It does not call historical K-line APIs, trade APIs, order APIs, or publish.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))
QMARK = chr(63)
REPL = chr(0xFFFD)


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


def sanitize_text(value: str) -> str:
    return value.replace(QMARK, "[question_mark]").replace(REPL, "[replacement_char]")


def sanitize_tree(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_tree(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_tree(item) for key, item in value.items()}
    return value


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


def frame_or_value(obj: Any) -> Any:
    records = records_from_frame(obj)
    if records:
        return records
    return json_safe(obj)


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


def call_api(label: str, func, *args, **kwargs) -> dict[str, Any]:
    from futu import RET_OK

    try:
        ret, data = func(*args, **kwargs)
        return {
            "label": label,
            "ret": int(ret) if isinstance(ret, int) else str(ret),
            "success": ret == RET_OK,
            "data": frame_or_value(data),
            "failure_type": None if ret == RET_OK else classify_failure(str(data)),
            "failure_reason": None if ret == RET_OK else str(data),
            "called_at": now_jst(),
        }
    except Exception as exc:
        return {
            "label": label,
            "ret": "exception",
            "success": False,
            "data": None,
            "failure_type": classify_failure(str(exc)),
            "failure_reason": str(exc),
            "called_at": now_jst(),
        }


def connect_quote_context(max_retries: int, wait_seconds: int):
    from futu import OpenQuoteContext, RET_OK

    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_retries + 1):
        ctx = None
        try:
            ctx = OpenQuoteContext(host=HOST, port=PORT)
            ret, data = ctx.get_global_state()
            attempts.append({
                "attempt": attempt,
                "ret": int(ret) if isinstance(ret, int) else str(ret),
                "success": ret == RET_OK,
                "data": frame_or_value(data),
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


def subscribe_quote(ctx: Any, code: str, extended_time: bool) -> dict[str, Any]:
    from futu import SubType

    return call_api(
        f"subscribe_quote_extended_{extended_time}",
        ctx.subscribe,
        [code],
        [SubType.QUOTE],
        is_first_push=True,
        subscribe_push=False,
        extended_time=extended_time,
    )


def quote_snapshot(ctx: Any, code: str, extended_time: bool = False) -> dict[str, Any]:
    sub = subscribe_quote(ctx, code, extended_time)
    quote = call_api("get_stock_quote", ctx.get_stock_quote, [code])
    rows = quote.get("data") if isinstance(quote.get("data"), list) else []
    row = rows[0] if rows else {}
    extracted = {
        "code": code,
        "extended_time_subscribe": extended_time,
        "subscribe": sub,
        "quote": quote,
        "fields_of_interest": extract_quote_fields(row),
        "raw": row,
    }
    return extracted


def extract_quote_fields(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "code", "name", "data_date", "data_time", "last_price",
        "open_price", "high_price", "low_price", "prev_close_price",
        "pre_price", "pre_high_price", "pre_low_price",
        "after_price", "after_high_price", "after_low_price",
        "overnight_price", "overnight_high_price", "overnight_low_price",
        "sec_status", "suspension", "dark_status",
    ]
    out = {key: row.get(key) for key in keys if key in row}
    for key, value in row.items():
        low = str(key).lower()
        if any(token in low for token in ["status", "state", "time", "date"]) and key not in out:
            out[str(key)] = value
    return out


def infer_us_cause(nvda_probe: dict[str, Any], market_state: dict[str, Any], subscription: dict[str, Any]) -> dict[str, Any]:
    normal = nvda_probe.get("normal_quote", {})
    ext = nvda_probe.get("extended_quote", {})
    row = normal.get("raw") or {}
    ext_row = ext.get("raw") or {}
    last_price = row.get("last_price")
    after_price = row.get("after_price")
    overnight_price = row.get("overnight_price")
    ext_last = ext_row.get("last_price")
    data_date = row.get("data_date")
    data_time = row.get("data_time")
    quote_has_extended = after_price not in (None, "N/A") or overnight_price not in (None, "N/A")
    explicit_delay_flag = find_delay_like_fields([row, ext_row, market_state, subscription])

    if quote_has_extended:
        reason = "last_price_is_regular_session_field_extended_fields_available"
        detail = "last_price is regular-session quote; use after_price or overnight_price during extended sessions when present"
    elif explicit_delay_flag:
        reason = "permission_or_delay_flag_seen"
        detail = "API returned fields that look like delay or permission status; inspect raw permission fields"
    elif data_date and data_time:
        reason = "no_explicit_permission_flag_seen_time_or_session_field_likely"
        detail = "quote returned dated snapshot but no explicit RT or DELAY permission flag in accessible methods"
    else:
        reason = "undetermined"
        detail = "quote returned too few fields for cause inference"

    return {
        "target": "US.NVDA",
        "last_price": last_price,
        "after_price": after_price,
        "overnight_price": overnight_price,
        "extended_subscribe_last_price": ext_last,
        "data_date": data_date,
        "data_time": data_time,
        "quote_has_extended_fields": quote_has_extended,
        "explicit_delay_or_permission_flag": explicit_delay_flag,
        "inferred_reason": reason,
        "inference_detail": detail,
        "permission_probe_note": "SDK exposes get_global_state and query_subscription here; no direct quote-right method name was available in OpenQuoteContext",
    }


def find_delay_like_fields(items: list[Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for item in items:
        scan_delay_fields(item, found, path="")
    return found


def scan_delay_fields(value: Any, found: list[dict[str, Any]], path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            child_text = str(child).lower()
            child_path = f"{path}.{key}" if path else str(key)
            if any(token in low for token in ["delay", "right", "permission", "quota", "status"]):
                found.append({"path": child_path, "value": json_safe(child)})
            elif any(token in child_text for token in ["delay", "permission", "quota", "realtime", "real-time"]):
                found.append({"path": child_path, "value": json_safe(child)})
            scan_delay_fields(child, found, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            scan_delay_fields(child, found, f"{path}[{idx}]")


def probe_crypto_code_formats(ctx: Any) -> dict[str, Any]:
    candidates = {
        "BTC": [
            "BTC", "BTC.USD", "BTC-USD", "BTC_USD", "CC.BTCUSD",
            "CRYPTO.BTCUSD", "US.BTCUSD", "US.BTC-USD", "HK.BTCUSD",
        ],
        "ETH": [
            "ETH", "ETH.USD", "ETH-USD", "ETH_USD", "CC.ETHUSD",
            "CRYPTO.ETHUSD", "US.ETHUSD", "US.ETH-USD", "HK.ETHUSD",
        ],
    }
    output: dict[str, Any] = {}
    for coin, codes in candidates.items():
        trials = []
        success = None
        for code in codes:
            snap = quote_snapshot(ctx, code, extended_time=False)
            row = snap.get("raw") or {}
            ok = bool((snap.get("quote") or {}).get("success") and row.get("last_price") is not None)
            trial = {
                "code": code,
                "success": ok,
                "last_price": row.get("last_price"),
                "data_date": row.get("data_date"),
                "data_time": row.get("data_time"),
                "failure_type": (snap.get("quote") or {}).get("failure_type") or (snap.get("subscribe") or {}).get("failure_type"),
                "failure_reason": (snap.get("quote") or {}).get("failure_reason") or (snap.get("subscribe") or {}).get("failure_reason"),
                "fields_of_interest": snap.get("fields_of_interest"),
            }
            trials.append(trial)
            if ok and success is None:
                success = trial
        output[coin] = {
            "found_working_format": success is not None,
            "first_success": success,
            "trials": trials,
        }
    return output


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_payload = sanitize_tree(payload)
    text = json.dumps(clean_payload, ensure_ascii=False, indent=2) + "\n"
    if QMARK in text or REPL in text:
        raise RuntimeError(f"garble marker found before write: {path}")
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 roundtrip mismatch: {path}")
    if QMARK in reread or REPL in reread:
        raise RuntimeError(f"garble marker found after write: {path}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Deep probe OpenD realtime quote capability.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--wait-seconds", type=int, default=3)
    args = parser.parse_args()

    ctx, attempts = connect_quote_context(args.max_retries, args.wait_seconds)
    payload: dict[str, Any] = {
        "task_id": "TASK-2026-07-02-054",
        "mode": "READ_ONLY_REALTIME_DEEP_PROBE",
        "generated_at": now_jst(),
        "date": args.date,
        "connection": {
            "host": HOST,
            "port": PORT,
            "max_retries": args.max_retries,
            "wait_seconds": args.wait_seconds,
            "connected": ctx is not None,
            "attempts": attempts,
        },
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "history_kline_called": False,
            "quote_api": "subscribe QUOTE + get_stock_quote",
            "extra_read_only_calls": ["get_global_state", "query_subscription", "get_market_state", "get_market_snapshot"],
        },
    }

    if ctx is None:
        payload["error"] = "OpenD quote connection failed"
    else:
        try:
            global_state = call_api("get_global_state", ctx.get_global_state)
            subscription_before = call_api("query_subscription_before", ctx.query_subscription, True)
            us_market_state = call_api("get_market_state_US_NVDA", ctx.get_market_state, ["US.NVDA"])
            us_market_snapshot = call_api("get_market_snapshot_US_NVDA", ctx.get_market_snapshot, ["US.NVDA"])
            nvda_normal = quote_snapshot(ctx, "US.NVDA", extended_time=False)
            nvda_extended = quote_snapshot(ctx, "US.NVDA", extended_time=True)
            subscription_after = call_api("query_subscription_after", ctx.query_subscription, True)
            crypto_probe = probe_crypto_code_formats(ctx)
            payload.update({
                "us_nvda_deep_probe": {
                    "global_state": global_state,
                    "subscription_before": subscription_before,
                    "market_state": us_market_state,
                    "market_snapshot": us_market_snapshot,
                    "normal_quote": nvda_normal,
                    "extended_quote": nvda_extended,
                    "subscription_after": subscription_after,
                },
                "us_realtime_cause_inference": infer_us_cause(
                    {
                        "normal_quote": nvda_normal,
                        "extended_quote": nvda_extended,
                    },
                    us_market_state,
                    subscription_after,
                ),
                "crypto_code_format_probe": crypto_probe,
            })
        finally:
            ctx.close()

    out_path = ROOT / "data" / "market" / f"opend_realtime_deep_probe_{args.date}.json"
    write_json_utf8(out_path, payload)

    summary = {
        "output": str(out_path),
        "connected": payload["connection"]["connected"],
        "us_cause": payload.get("us_realtime_cause_inference"),
        "crypto_success": {
            coin: data.get("first_success")
            for coin, data in (payload.get("crypto_code_format_probe") or {}).items()
        },
        "safety": payload["safety"],
    }
    print(json.dumps(sanitize_tree(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
