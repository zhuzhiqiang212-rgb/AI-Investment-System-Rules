#!/usr/bin/env python3
"""迷你趋势图·每日行情快照存储（派工单2026-07-13⑦）· 只读不下单

迷你趋势图需要历史数据才画得出——从今天起每天存一份行情快照(市场快照+持仓现价)，开始攒。
写 data/market/history/snap_{当日}.json；不覆盖历史。产品里该处标"趋势图·攒数据中(现N天)"、不编假图。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="每日行情快照存储·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    hist_dir = ROOT / "data" / "market" / "history"
    hist_dir.mkdir(parents=True, exist_ok=True)

    snap = {}
    mkt = ROOT / "data" / "market" / "latest_market_snapshot.json"
    if mkt.exists():
        snap["market"] = {a.get("symbol"): a.get("price") for a in json.loads(mkt.read_text(encoding="utf-8")).get("assets", [])}
    prod = ROOT / "data" / "reports" / f"production_{date}.json"
    if prod.exists():
        snap["holdings"] = {h.get("symbol"): h.get("price") for h in json.loads(prod.read_text(encoding="utf-8")).get("holdings", [])}
    out_path = hist_dir / f"snap_{date}.json"
    out_path.write_text(json.dumps({"date": date, "generated_at": datetime.now(JST).isoformat(), "snapshot": snap},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(list(hist_dir.glob("snap_*.json")))
    print(f"wrote {out_path} · 历史快照现有 {n} 天（迷你趋势图攒数据中）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
