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


def fetch_fred_dgs2() -> float | None:
    """真 2 年美债收益率 FRED DGS2（keyless·派工单§3 替换3月^IRX代理）。
    DGS2 是日频大文件·易超时→用 cosd 限近90天缩小文件、重试3次、逐次加长超时。全失败→None(由调用方统一标待接)。"""
    from datetime import date as _date
    try:
        cosd = (datetime.now(JST).date() - timedelta(days=90)).isoformat()
    except Exception:
        cosd = "2026-01-01"
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2&cosd={cosd}"
    for to in (12, 20, 30):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            text = urllib.request.urlopen(req, timeout=to).read().decode("utf-8")
        except Exception:
            continue
        for line in reversed(text.strip().splitlines()[1:]):
            _, _, v = line.partition(",")
            v = v.strip()
            if v and v != ".":
                try:
                    return float(v)
                except ValueError:
                    continue
        return None
    return None


def ok_payload(date: str, us10y: float, us3m: float, us2y: float | None = None) -> dict[str, Any]:
    spread = round(us10y - us3m, 3)
    spread_2y = round(us10y - us2y, 3) if us2y is not None else None
    if us2y is not None:
        note = "短端已接真2年美债(FRED DGS2)；同时保留3月(^IRX)作对照"
    else:
        note = "短端用3个月(^IRX)，非2年；真2年(FRED DGS2)今日抓取失败·待接"
    return {
        "task_id": "2b-1",
        "generated_at": now_jst(),
        "date": date,
        "connection": {"ok": True, "reason": ""},
        "source": "Yahoo ^TNX / ^IRX + FRED DGS2",
        "short_end_note": note,
        "us10y": us10y,
        "us3m": us3m,
        "us2y": us2y,
        "spread_10y_3m": spread,
        "spread_10y_2y": spread_2y,
        "inverted": (spread_2y < 0) if spread_2y is not None else (spread < 0),
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

    us2y = fetch_fred_dgs2()  # 真2年美债(FRED)·失败则回退3月代理
    payload = ok_payload(args.date, us10y, us3m, us2y)
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
