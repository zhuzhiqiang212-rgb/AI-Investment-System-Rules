#!/usr/bin/env python3
"""当日涨跌真源（董事局工单2026-07-17）· 只读不下单

现有 stock_change_*.json 只覆盖美股(Yahoo)、且不含日股 → 日股"今天跌了多少"没有真源。
本模块直接从 OpenD 快照取 last_price / prev_close_price，算当日涨跌%，覆盖全持仓+参照指数。
缺真源(取不到)→标待接、不编。

产物：data/market/day_change_{date}.json
用法：python scripts/day_change_scan.py --date 20260717
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

# 参照物(给"今天大盘怎么样"当锚·不是持仓)
BENCH = {
    "JP.1321": "日经225ETF",
    "US.SOXX": "半导体指数ETF",
    "US.SPY": "标普500ETF",
    "HK.800000": "恒生指数",
    "JP.285A": "铠侠(日本存储龙头)",
}


def scan(date: str) -> dict:
    try:
        from futu import OpenQuoteContext, RET_OK
    except Exception as e:
        return {"error": f"futu SDK 不可用：{e}", "changes": {}}
    prod = ROOT / "data" / "reports" / f"production_{date}.json"
    try:
        holds = json.loads(prod.read_text(encoding="utf-8")).get("holdings", [])
    except Exception as e:
        return {"error": f"production_{date}.json 缺：{e}", "changes": {}}
    codes = [str(h["symbol"]) for h in holds if not str(h["symbol"]).startswith("CC.")]
    name_by = {str(h["symbol"]): str(h.get("name") or h["symbol"]) for h in holds}
    out: dict = {}
    q = None
    try:
        q = OpenQuoteContext(host="127.0.0.1", port=11111)
        for batch in [codes[i:i + 20] for i in range(0, len(codes), 20)] + [list(BENCH)]:
            r, d = q.get_market_snapshot(batch)
            if r != RET_OK:
                continue
            for _i, x in d.iterrows():
                c = str(x["code"])
                lp, pc = x.get("last_price"), x.get("prev_close_price")
                if lp is None or not pc:
                    out[c] = {"status": "待接·无价或无昨收", "name": name_by.get(c, BENCH.get(c, c))}
                    continue
                out[c] = {"name": name_by.get(c, BENCH.get(c, c)),
                          "price": float(lp), "prev_close": float(pc),
                          "change_pct": round((float(lp) - float(pc)) / float(pc) * 100, 2),
                          "update_time": str(x.get("update_time") or ""),
                          "is_bench": c in BENCH, "status": "OK"}
    except Exception as e:
        return {"error": f"OpenD 连不上或取数失败：{e}", "changes": out}
    finally:
        if q is not None:
            try:
                q.close()
            except Exception:
                pass
    return {"error": "", "changes": out}


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="当日涨跌真源(OpenD)")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    r = scan(a.date)
    doc = {"_说明": "当日涨跌%=（OpenD last_price − prev_close_price）÷ prev_close_price。"
                   "覆盖全持仓+参照指数(日经ETF/SOXX/SPY/恒生/铠侠)。取不到→标待接、不编。",
           "date": a.date, "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "source": "OpenD get_market_snapshot(last_price vs prev_close_price)",
           "error": r.get("error", ""), "changes": r.get("changes", {})}
    p = ROOT / "data" / "market" / f"day_change_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for v in doc["changes"].values() if v.get("status") == "OK")
    print(f"wrote {p.name} · 取到 {ok}/{len(doc['changes'])} 只" + (f" · 错误：{doc['error']}" if doc["error"] else ""))
    for c, v in sorted(doc["changes"].items(), key=lambda x: x[1].get("change_pct", 0)):
        if v.get("status") == "OK":
            print(f"   {v['name'][:12]:14s}{c:12s}{v['change_pct']:+7.2f}%{'  ←参照' if v.get('is_bench') else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
