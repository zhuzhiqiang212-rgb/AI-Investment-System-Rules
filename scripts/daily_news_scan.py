#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日新闻扫描接口（派工单G2·2026-07-22）：扫持仓+候选标的当日新闻/公告→data/news/daily_{date}.json。
每条:标题/链接/发布日期/原文片段/来源。供第3关短期归因挂真实来源(防编造)。
源=Google News RSS(keyless·复用macro_news_intake.fetch_news)·真新闻·取不到标『当日无新闻』不编造。
用法：python scripts/daily_news_scan.py --date 20260722 [--fresh-days 3]"""
import argparse, json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
JST = timezone(timedelta(hours=9))
from macro_news_intake import fetch_news  # Google News RSS·title/source_raw/url/summary/pub_dt/pub_date

# 候选15只名(据gate3)·英文查询更准
CAND_NAME = {"US.CDNS": "Cadence Design", "US.COHR": "Coherent", "US.CRDO": "Credo Technology",
             "US.D": "Dominion Energy", "US.DGX": "Quest Diagnostics", "US.GSK": "GSK",
             "US.HII": "Huntington Ingalls", "US.INCY": "Incyte", "US.KLAC": "KLA Corp",
             "US.LITE": "Lumentum", "US.P": "US.P stock", "US.PEG": "Public Service Enterprise",
             "US.PLTR": "Palantir", "US.STX": "Seagate", "US.WDC": "Western Digital"}


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--fresh-days", type=int, default=3)
    ap.add_argument("--limit", type=int, default=4)
    a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    today = datetime.strptime(d, "%Y%m%d").replace(tzinfo=JST)

    # 目标 = 持仓20 + 候选15
    hold = json.loads((ROOT / "data/accounts/holdings_true_20260720.json").read_text(encoding="utf-8"))["holdings"]
    targets = {}
    for h in hold:
        c = h["symbol"]
        if c.startswith("CC."):
            continue
        targets[c] = {"code": c, "name": h.get("name"), "类别": "持仓"}
    # SpaceX(第20只持仓·未上市·0720台账缺·须显式纳入新闻扫描)
    if "US.SPCX" not in targets:
        targets["US.SPCX"] = {"code": "US.SPCX", "name": "SpaceX", "类别": "持仓(未上市)"}
    for c, nm in CAND_NAME.items():
        if c in targets:
            targets[c]["类别"] = "持仓+候选"
        else:
            targets[c] = {"code": c, "name": nm, "类别": "候选"}

    # 查询词:美股用英文名·日股用中文名
    EN = dict(CAND_NAME)
    EN.update({"US.NVDA": "Nvidia", "US.MSFT": "Microsoft", "US.MSTR": "Strategy MicroStrategy",
               "US.COIN": "Coinbase", "US.AVGO": "Broadcom", "US.CRCL": "Circle stock", "US.SNDK": "SanDisk",
               "US.TSM": "TSMC", "US.META": "Meta Platforms", "US.IBKR": "Interactive Brokers", "US.SPCX": "SpaceX"})

    rows = {}
    no_news = []
    for c, meta in targets.items():
        q = EN.get(c) or meta["name"] or c
        try:
            items = fetch_news(str(q), limit=a.limit, lang=("en" if c.startswith("US.") else "zh"))
        except Exception as e:
            items = None
            rows[c] = {**meta, "查询": q, "新闻": [], "状态": f"抓取异常:{e}"}
            continue
        news = []
        for it in (items or []):
            pd = it.get("pub_dt")
            fresh = None
            if isinstance(pd, datetime):
                days = (today - pd.astimezone(JST)).days
                fresh = (0 <= days <= a.fresh_days)
            news.append({"标题": it.get("title"), "链接": it.get("url"), "发布日期": it.get("pub_date"),
                         "原文片段": it.get("summary"), "来源": it.get("source_raw"),
                         "近{}日内".format(a.fresh_days): fresh})
        # 优先保留近N日内的
        news.sort(key=lambda x: (x.get("近{}日内".format(a.fresh_days)) is True), reverse=True)
        rows[c] = {**meta, "查询": q, "新闻条数": len(news), "新闻": news,
                   "状态": ("有新闻" if news else "当日无新闻·未编造")}
        if not news:
            no_news.append(c)
        time.sleep(0.5)

    doc = {
        "_说明": "每日新闻扫描接口(G2)·持仓+候选当日新闻/公告·供第3关短期归因挂真实来源(防编造)。源=Google News RSS(keyless)。",
        "date": d, "generated_at": now(), "源": "Google News RSS(keyless·复用macro_news_intake.fetch_news)",
        "新鲜窗口天数": a.fresh_days, "扫描标的数": len(targets), "无新闻标的数": len(no_news),
        "无新闻标的": no_news, "cards": rows,
    }
    p = ROOT / "data" / "news" / f"daily_{d}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("扫描", len(targets), "标的·无新闻", len(no_news), "只:", no_news)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
