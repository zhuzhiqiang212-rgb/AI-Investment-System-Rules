# -*- coding: utf-8 -*-
"""★轮120 NZ:查清 08-03 到底有没有当日新闻被抓到——★逐条给数据·不推测·结果落盘。
NZ1-1 raw 按发布日期分组(08-03/02/01/07-31/更早/无日期)。NZ1-2 08-03条目卡在哪段(白名单/相关性/时效)+样例。
NZ2-1 白名单域名清单。NZ3 结果写 data/logs/news_chain_diagnose_{date}.json。★不改任何过滤逻辑(NZ4)。"""
import sys, json, argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import macro_news_intake as M
import worldview_layer as W
import national_strategy_layer as NSL


def _bucket(d, today):
    if d is None:
        return "无日期"
    delta = (today - d).days
    if delta <= 0:
        return "08-03及以后(当日)"
    return {1: "08-02", 2: "08-01", 3: "07-31"}.get(delta, "07-30及更早")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    now = datetime.now(timezone.utc); today = now.date()
    tw_monday = M._trading_week_monday(now)

    seen, raw_all = set(), []
    for layer, cats, ring in [("①世界观", W.CATEGORIES, "世界观"), ("②国家战略", NSL.CATEGORIES, "国家战略")]:
        _ring = M.RING_ALIAS.get(ring, ring)
        for name, qs in cats:
            for q in (qs if isinstance(qs, list) else [qs]):
                items = M.fetch_news(q, limit=12, lang=("en" if any(c.isascii() and c.isalpha() for c in q[-8:]) else "zh"))
                if items is None:
                    continue
                for n in items:
                    key = (n.get("title", "")[:60])
                    if key in seen:
                        continue
                    seen.add(key)
                    dt = n.get("pub_dt")
                    pd = dt.astimezone(timezone.utc).date() if dt else None
                    blob = (n.get("title", "") + " " + n.get("summary", ""))
                    tier = M._src_tier(n.get("source_raw", ""))
                    rescued = bool(not tier and M.IMPORTANT_PAT.search(blob) and not M.SOURCE_BLOCK_PAT.search(str(n.get("source_raw", "")).lower()))
                    rel = any(w.lower() in blob.lower() for w in M.RELEVANCE.get(_ring, []))
                    age_h = (now - dt.astimezone(timezone.utc)).total_seconds() / 3600.0 if dt else None
                    is_major = bool(M.MAJOR_EVENT_PAT.search(blob)); in_week = (pd >= tw_monday) if pd else False
                    time_ok = (age_h is not None and (age_h <= M.MAX_AGE_HOURS or (is_major and in_week)))
                    raw_all.append({"标题": n.get("title", "")[:70], "源": n.get("source_raw", ""),
                                    "pub_date": pd.strftime("%Y-%m-%d") if pd else None, "bucket": _bucket(pd, today),
                                    "ring": ring, "过白名单": bool(tier or rescued), "过相关性": rel, "过时效": time_ok,
                                    "卡在": ("白名单" if not (tier or rescued) else ("时效" if not time_ok else ("相关性" if not rel else "合格")))})

    # NZ1-1 按日期分组
    by_date = Counter(r["bucket"] for r in raw_all)
    # NZ1-2 当日(08-03)条目卡在哪段
    today_items = [r for r in raw_all if r["bucket"] == "08-03及以后(当日)"]
    today_stuck = Counter(r["卡在"] for r in today_items)
    # 各段存活
    stage = {"raw": len(raw_all), "过白名单": sum(r["过白名单"] for r in raw_all),
             "过白名单+时效": sum(1 for r in raw_all if r["过白名单"] and r["过时效"]),
             "过白名单+时效+相关性(=合格)": sum(1 for r in raw_all if r["过白名单"] and r["过时效"] and r["过相关性"])}
    # NZ2-3 归因
    if today_items:
        n_wl = sum(1 for r in today_items if not r["过白名单"])
        if any(r["卡在"] == "合格" for r in today_items):
            attr = "★数据异常:当日有合格条(与内存跑0命中不符·见样例)"
        elif n_wl == len(today_items):
            attr = "A 白名单太窄——★当日新闻【存在】但源全不在权威名单(见当日卡白名单域名)"
        elif any(r["卡在"] == "相关性" for r in today_items):
            attr = "B 白名单源今日有发·但非①层主题(卡相关性)——零命中在①层主题口径下【部分正确】"
        else:
            attr = "混合:当日有条·卡白名单/相关性混合(见样例)"
    else:
        attr = "C 源本身取不到当日——★raw 里【一条 08-03 都没有】(源问题·非过滤)"

    out = {
        "_说明": "★轮120 NZ 查清08-03有无当日新闻被抓·逐条数据·不推测·落盘。★本轮不改过滤(NZ4)。★RSS实时·结果随抓取时刻波动。",
        "date": dh, "诊断时刻(UTC)": now.strftime("%Y-%m-%d %H:%M"), "本交易周起点": tw_monday.strftime("%Y-%m-%d"), "MAX_AGE_HOURS": M.MAX_AGE_HOURS,
        "★NZ1-1 raw按发布日期分组": dict(by_date), "raw总数": len(raw_all),
        "★NZ1-2 当日(08-03)条目数": len(today_items), "★当日条目卡在哪段": dict(today_stuck),
        "★当日条目样例(前8)": [{"标题": r["标题"], "源": r["源"][:40], "卡在": r["卡在"]} for r in today_items[:8]],
        "各段存活": stage,
        "★NZ2-1 白名单域名/源清单": sorted(set(M.SOURCE_WHITELIST.values())),
        "★NZ2-3 归因(A/B/C)": attr,
        "★卡白名单的当日源(域名·NZ1-2)": sorted(set(r["源"][:50] for r in today_items if r["卡在"] == "白名单"))[:15],
        "★卡相关性的当日标题样例": [r["标题"] for r in today_items if r["卡在"] == "相关性"][:6],
    }
    op = ROOT / "data/logs" / f"news_chain_diagnose_{dc}.json"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[news诊断] 落盘", op.name)
    print("★NZ1-1 raw按日期:", dict(by_date), "· raw总", len(raw_all))
    print("★NZ1-2 当日08-03条目:", len(today_items), "· 卡在:", dict(today_stuck))
    print("★NZ2-3 归因:", attr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
