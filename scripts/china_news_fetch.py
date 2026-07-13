#!/usr/bin/env python3
"""中国支线·稀土/自主可控真新闻抓取（派工单2026-07-13⑤）· 只读不下单

抓 Google News RSS(keyless) 稀土出口管制/自主可控/国产替代 真新闻，写
data/evidence_chain/china_news_{当日}.json（每条 title/source/url/summary），供 render 的中国支线用。
港股行情待 OpenD 港股（本脚本不接·render 另标待接）。抓不到→status=待接，render 据实标、不编。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

QUERIES = [
    ("稀土/出口管制", "稀土 出口管制 rare earth export control China"),
    ("自主可控/国产替代", "半导体 国产替代 自主可控 China chip localization"),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="中国支线新闻抓取·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    sys.path.insert(0, str(ROOT / "scripts"))
    from macro_news_intake import fetch_news  # 复用 Google News RSS(含 title/source/url/summary)

    out = {"generated_at": datetime.now(JST).isoformat(), "source": "Google News RSS(keyless)",
           "topics": {}, "hk_quote": {"status": "待接", "note": "港股行情待 OpenD 港股/指数源"}}
    total_ok = 0
    for label, q in QUERIES:
        news = fetch_news(q, limit=4)
        if news:
            out["topics"][label] = {"status": "OK", "items": [
                {"title": n.get("title"), "source": n.get("source", ""),
                 "url": n.get("url", ""), "summary": n.get("summary", "")} for n in news[:3]]}
            total_ok += 1
        else:
            out["topics"][label] = {"status": "待接", "items": [], "reason": "RSS 今日未抓到·待接真源"}
    path = ROOT / "data" / "evidence_chain" / f"china_news_{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path} · 主题接通 {total_ok}/{len(QUERIES)}（港股行情待接）")
    for lb, v in out["topics"].items():
        print(f"  {lb}: {v.get('status')}·{len(v.get('items', []))}条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
