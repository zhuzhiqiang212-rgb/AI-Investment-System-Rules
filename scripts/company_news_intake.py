#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★MAIN-02 甲A2 公司层机械新闻feed（Code3 轮建·2026-08-09）。

现行管道 layer_pipeline.py 的设计：新闻全部在①层证据映射器进场，②~⑦是判断层。
③层已旁取利率/FOMC 机器观测、④层已旁取 sector_rotation——【公司层无任何机器新闻feed】。
本模块补这一环：按持仓20只逐只抓公司新闻(财报/指引/订单/诉讼/业绩/收购)，
【只接事件+日期+来源+可点链接+归到哪只】，★意义判断=待Opus5（丁铁律：Code不解读、不编造、不硬凑）。

与 ③FOMC(macro_news_intake.fetch_fed_fomc)/④sector 同型：机器出观测，Opus5填意义。
★只读·不下单。复用 macro_news_intake 的源白名单+时效闸（不另造一套尺）。

用法:
  python scripts/company_news_intake.py --date 20260808
输出: data/news/company_news_{date}.json（json.dump覆盖+写后json.loads自校验）
"""
import sys, os, json, glob, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import macro_news_intake as M   # 复用抓取+白名单+时效(不另造尺)

# 公司事件查询词（中文源优先）：财报/指引/订单/诉讼/业绩/并购
EVENT_TERMS = "财报 OR 业绩 OR 指引 OR 订单 OR 诉讼 OR 收购 OR 并购 OR 增资 OR 融资"
KEEP_AGE_HOURS = 168   # 公司事件窗口=7天(覆盖本财报周)；每条仍标精确 pub_date，不含糊
TOP_N = 3              # 每只最多留3条(按新鲜度)，其余进 dropped 计数


def _latest_holdings(date: str):
    """读 production_{date}.json 持仓；无则取最新一份。返回 [(symbol, name), ...] 去掉 CC.（加密对）。"""
    p = ROOT / "data" / "reports" / f"production_{date}.json"
    if not p.exists():
        cands = sorted(glob.glob(str(ROOT / "data" / "reports" / "production_*.json")))
        if not cands:
            return [], None
        p = Path(cands[-1])
    d = json.load(open(p, encoding="utf-8"))
    hs = []
    for h in d.get("holdings", []) or []:
        sym = str(h.get("symbol", ""))
        if sym.startswith("CC."):
            continue
        hs.append((sym, str(h.get("name") or sym)))
    return hs, p.name


def _age_hours(pub_dt, ref):
    if pub_dt is None:
        return None
    try:
        return (ref - pub_dt.astimezone(timezone.utc)).total_seconds() / 3600.0
    except Exception:
        return None


def _name_tokens(sym, name):
    """公司名归属核对用的匹配token：中文全名 + 英文ticker/别名。★防把别家新闻误贴到本只。"""
    toks = set()
    if name:
        toks.add(name)
    base = sym.split(".")[-1] if "." in sym else sym    # US.NVDA→NVDA
    if base:
        toks.add(base)
    # 少数需要英文别名(中文名在中文源里常见·英文名在混合源里出现)
    ALIAS = {"US.TSM": ["台积电", "TSMC", "台積電"], "JP.9984": ["软银", "SoftBank", "軟銀"],
             "US.SNDK": ["闪迪", "SanDisk", "SNDK"], "JP.6857": ["爱德万", "Advantest", "愛德萬"],
             "US.AVGO": ["博通", "Broadcom"], "JP.6758": ["索尼", "Sony"], "JP.7203": ["丰田", "Toyota"],
             "JP.4568": ["第一三共", "Daiichi"], "JP.7974": ["任天堂", "Nintendo"],
             "JP.8001": ["伊藤忠", "Itochu"], "JP.8766": ["东京海上", "Tokio Marine"],
             "US.NVDA": ["英伟达", "英偉達", "Nvidia"], "US.MSFT": ["微软", "Microsoft"],
             "US.META": ["Meta", "脸书"], "US.COIN": ["Coinbase"], "US.MSTR": ["MicroStrategy", "Strategy"],
             "US.CRCL": ["Circle"], "US.IBKR": ["盈透", "Interactive Brokers", "IBKR"], "US.SPCX": ["SpaceX"]}
    for a in ALIAS.get(sym, []):
        toks.add(a)
    return {t.lower() for t in toks if t}


def _qualify_company(items, ref, name_toks):
    """公司新闻合格判据（复用 macro 的白名单/剔除/重要性，不另造尺）：
    保留条件 = ★标题/摘要命中本公司名token(防误贴) 且 有真实发布时间 且 age<=7天
             且 (来源在白名单 或 标题命中重要性词) 且 不命中剔除模式。
    返回 (kept[按新鲜度], n_fetched, dropped_reasons)。★不硬凑：合格0条如实返回。"""
    kept, dropped = [], []
    for it in items or []:
        title = it.get("title", "")
        src_raw = it.get("source_raw", "") or ""
        pub_dt = it.get("pub_dt")
        blob = (title + " " + it.get("summary", "")).lower()
        if not any(t in blob for t in name_toks):        # ★归属核对:非本公司→丢(防误贴)
            dropped.append("标题/摘要未命中本公司名·非本只新闻")
            continue
        if M.SOURCE_BLOCK_PAT.search(src_raw) or M.SOURCE_BLOCK_PAT.search(title):
            dropped.append("剔除源/内容农场")
            continue
        age = _age_hours(pub_dt, ref)
        if age is None:
            dropped.append("无真实发布时间")
            continue
        if age > KEEP_AGE_HOURS:
            dropped.append("超7天旧闻")
            continue
        tier = M._src_tier(src_raw)                      # 白名单规范名 或 None
        important = bool(M.IMPORTANT_PAT.search(title))
        if tier is None and not important:
            dropped.append("非白名单源且标题无重大事件词")
            continue
        kept.append({
            "title": title,
            "source": tier or src_raw or "来源待接",
            "source_tier": "白名单" if tier else "非白名单·标题命中重大词",
            "pub_date": it.get("pub_date", "发布日待接"),
            "age_hours": round(age, 1),
            "url": it.get("url", ""),
            "lang": it.get("lang", "zh"),
        })
    kept.sort(key=lambda x: x["age_hours"])              # 越新越靠前
    return kept[:TOP_N], len(items or []), dropped


def build(date: str) -> dict:
    ref = datetime.now(timezone.utc)
    holds, used_file = _latest_holdings(date)
    out_holdings = []
    for sym, name in holds:
        q = f"{name} {EVENT_TERMS}"
        items = M.fetch_news(q, limit=10, lang="zh")
        if items is None:                                # 网络失败→如实标待接真源(不编)
            out_holdings.append({
                "symbol": sym, "name": name, "events": [],
                "n_fetched": 0, "n_kept": 0, "客观空": False,
                "★状态": "待接真源·抓取失败(网络)·读上一状态·不编",
                "★意义判断": "待Opus5判(Code只接事件·不解读)",
            })
            continue
        kept, n_fetched, dropped = _qualify_company(items, ref, _name_tokens(sym, name))
        out_holdings.append({
            "symbol": sym, "name": name, "events": kept,
            "n_fetched": n_fetched, "n_kept": len(kept),
            "客观空": (len(kept) == 0),
            "★状态": (f"抓{n_fetched}条→合格{len(kept)}条(白名单+7天内+重大事件词)"
                       if kept else f"抓{n_fetched}条→合格0条·今日无够格公司事件·客观空(不硬凑)"),
            "dropped_reasons_sample": dropped[:4],
            "★意义判断": "待Opus5判(Code只接事件+链接+归层·财报好坏/对持仓影响属Opus5·丁铁律)",
        })
    n_hit = sum(1 for h in out_holdings if h["n_kept"] > 0)
    return {
        "_说明": ("★公司层机械新闻feed(MAIN-02甲A2·Code只接事件+日期+来源+链接+归到哪只)·"
                   "★意义/财报好坏/对持仓影响=待Opus5(丁铁律:不解读不编造不硬凑)·"
                   "与③FOMC/④sector同型:机器出观测·Opus5填意义"),
        "date": date,
        "data_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
        "generated_at": ref.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Google News RSS(keyless·中文源优先) + 源白名单 + 时效≤7天 + 重要性词闸",
        "source_holdings_file": used_file,
        "window_hours": KEEP_AGE_HOURS,
        "n_holdings": len(holds),
        "n_holdings_with_events": n_hit,
        "holdings": out_holdings,
    }


def _write_self_validate(obj: dict, date: str) -> Path:
    """★铁律：json.dump覆盖(不用'a'模式)+写后立即 json.loads 自校验(失败抛错不静默)。"""
    outp = ROOT / "data" / "news" / f"company_news_{date}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=2)
    json.loads(txt)                                      # 写前先自校验字符串可解析
    with open(outp, "w", encoding="utf-8") as f:
        f.write(txt)
    json.loads(open(outp, encoding="utf-8").read())     # 写后再从盘读回自校验
    return outp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    a = ap.parse_args()
    obj = build(a.date)
    p = _write_self_validate(obj, a.date)
    print(f"[company_news] 写出 {p}")
    print(f"[company_news] 持仓{obj['n_holdings']}只·有公司事件{obj['n_holdings_with_events']}只")
    for h in obj["holdings"]:
        print(f"  {h['symbol']:<9} {h['name'][:8]:<9} {h['★状态']}")


if __name__ == "__main__":
    main()
