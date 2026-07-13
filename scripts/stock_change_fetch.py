#!/usr/bin/env python3
"""板块细分代表标的·个股当日涨跌抓取（派工单2026-07-13④）· 只读不下单

把 ⑥b 板块趋势的"冷热"从 SOXX 板块级代理，换成各细分代表标的的个股当日涨跌%。
抓 Yahoo chart(keyless) 的现价与前收，算涨跌%，写 data/market/stock_change_{当日}.json；
抓不到的标 status=待接，render 据实标"待接真源"、不编。只读、不下单。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

# 细分代表标的 base ticker → Yahoo 代码(只锚定义·与 SECTOR_SUBS 对应·可迭代)
PROXY_YAHOO = {
    "NVDA": "NVDA", "AVGO": "AVGO", "MSFT": "MSFT", "META": "META", "TSM": "TSM",
    "SNDK": "SNDK", "6857": "6857.T", "9984": "9984.T",
}


def fetch_change_pct(yahoo: str) -> tuple[float, float] | None:
    """返回 (现价, 当日涨跌%)；失败→None。"""
    import urllib.parse
    import urllib.request
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(yahoo, safe='')}?interval=1d&range=2d"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=8).read()
        meta = (json.loads(raw).get("chart", {}).get("result") or [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None or prev in (None, 0):
            return None
        return float(price), round((float(price) - float(prev)) / float(prev) * 100.0, 2)
    except Exception:
        return None


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="个股当日涨跌·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    out = {"generated_at": datetime.now(JST).isoformat(), "source": "Yahoo chart(keyless)", "changes": {}}
    for base, yahoo in PROXY_YAHOO.items():
        r = fetch_change_pct(yahoo)
        if r is not None:
            out["changes"][base] = {"price": r[0], "change_pct": r[1], "yahoo": yahoo, "status": "OK"}
        else:
            out["changes"][base] = {"price": None, "change_pct": None, "yahoo": yahoo, "status": "待接"}
    path = ROOT / "data" / "market" / f"stock_change_{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for v in out["changes"].values() if v.get("status") == "OK")
    print(f"wrote {path} · 个股涨跌 {ok}/{len(PROXY_YAHOO)} 接通")
    for b, v in out["changes"].items():
        print(f"  {b}: {v.get('change_pct')}% ({v.get('status')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
