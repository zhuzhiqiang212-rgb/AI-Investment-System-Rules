#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fetch 10Y-3M Treasury curve from Yahoo Finance chart API.

Read-only public market data. No trading context, no order API, no publish.
Hard guardrail: if either endpoint fails, write all numeric values as null.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"write/read mismatch: {path}")
    if "\ufffd" in reread:
        raise RuntimeError(f"U+FFFD detected: {path}")


def fail_payload(date: str, reason: str) -> dict[str, Any]:
    return {
        "task_id": "2b-1",
        "generated_at": now_jst(),
        "date": date,
        "connection": {"ok": False, "reason": reason},
        "source": "Yahoo ^TNX / ^IRX",
        "short_end_note": "短端用3个月(^IRX)，非2年；真2年美债待FRED源",
        "us10y": None,
        "us3m": None,
        "spread_10y_3m": None,
        "inverted": None,
        "status": "待拉·源未连",
        "safety": {"read_only": True, "place_order_called": False, "published": False},
    }


def ok_payload(date: str, us10y: float, us3m: float) -> dict[str, Any]:
    spread = round(us10y - us3m, 3)
    return {
        "task_id": "2b-1",
        "generated_at": now_jst(),
        "date": date,
        "connection": {"ok": True, "reason": ""},
        "source": "Yahoo ^TNX / ^IRX",
        "short_end_note": "短端用3个月(^IRX)，非2年；真2年美债待FRED源",
        "us10y": us10y,
        "us3m": us3m,
        "spread_10y_3m": spread,
        "inverted": spread < 0,
        "status": "OK",
        "safety": {"read_only": True, "place_order_called": False, "published": False},
    }


def fetch_regular_market_price(symbol: str) -> float:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read().decode("utf-8")
    doc = json.loads(raw)
    result = doc.get("chart", {}).get("result") or []
    if not result:
        error = doc.get("chart", {}).get("error")
        raise RuntimeError(f"{symbol} missing result: {error}")
    price = result[0].get("meta", {}).get("regularMarketPrice")
    if price is None:
        raise RuntimeError(f"{symbol} missing meta.regularMarketPrice")
    return float(price)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fetch 10Y-3M yield curve.")
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    output_path = ROOT / "data" / "market" / f"yield_curve_{args.date}.json"
    try:
        us10y = fetch_regular_market_price("^TNX")
        us3m = fetch_regular_market_price("^IRX")
    except Exception as exc:
        payload = fail_payload(args.date, str(exc))
        write_json(output_path, payload)
        print(json.dumps({
            "output": str(output_path),
            "exit_code": 2,
            "connection_ok": False,
            "reason": str(exc),
            "status": payload["status"],
        }, ensure_ascii=False, indent=2))
        return 2

    payload = ok_payload(args.date, us10y, us3m)
    write_json(output_path, payload)
    print(json.dumps({
        "output": str(output_path),
        "exit_code": 0,
        "connection_ok": True,
        "us10y": payload["us10y"],
        "us3m": payload["us3m"],
        "spread_10y_3m": payload["spread_10y_3m"],
        "inverted": payload["inverted"],
        "status": payload["status"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
