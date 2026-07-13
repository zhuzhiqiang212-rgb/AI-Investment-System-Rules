#!/usr/bin/env python3
"""机会层候选行情抓取（模板卡2026-07-13§3·接候选行情源）· 只读不下单

抓 watchlist 候选(海力士/美光/东京电子)的当日现价(Yahoo chart·keyless)，写
data/market/candidate_prices_{当日}.json，供 full_product_render 的⑧机会池填"什么价买"的现价。
抓不到→该候选标 status=待接、price=null，render 据实标"待接真源"、不编价。只读、不下单。
候选的"合理买点/估值"另需估值源(候选无 valuation 实例)，本脚本只接现价、买点仍待接。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

# 候选→Yahoo代码+币种(只锚定义·可迭代·与 OPP_WATCHLIST 对应)
CANDIDATES = [
    {"name": "海力士(SK Hynix)", "yahoo": "000660.KS", "currency": "₩"},
    {"name": "美光(Micron·MU)", "yahoo": "MU", "currency": "$"},
    {"name": "东京电子", "yahoo": "8035.T", "currency": "¥"},
]


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="候选行情抓取·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    sys.path.insert(0, str(ROOT / "scripts"))
    from yield_curve_fetch import fetch_regular_market_price  # 复用 Yahoo chart 取价

    out = {"generated_at": datetime.now(JST).isoformat(), "source": "Yahoo chart(keyless)", "prices": {}}
    for c in CANDIDATES:
        try:
            p = fetch_regular_market_price(c["yahoo"])
            out["prices"][c["name"]] = {"price": round(float(p), 2), "currency": c["currency"],
                                        "yahoo": c["yahoo"], "status": "OK"}
        except Exception as exc:  # 抓不到→待接·不编价
            out["prices"][c["name"]] = {"price": None, "currency": c["currency"],
                                        "yahoo": c["yahoo"], "status": "待接", "reason": str(exc)[:80]}
    path = ROOT / "data" / "market" / f"candidate_prices_{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for v in out["prices"].values() if v.get("status") == "OK")
    print(f"wrote {path} · 候选现价 {ok}/{len(CANDIDATES)} 接通")
    for n, v in out["prices"].items():
        print(f"  {n}: {v.get('currency')}{v.get('price')} ({v.get('status')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
