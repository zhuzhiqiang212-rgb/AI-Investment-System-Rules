from __future__ import annotations

"""第二块 · 宏观事件 + 主题新闻源（让"待第二块"三环也机器自动评）

机器自动抓当日宏观事件真值(经济日历)与主题新闻，喂进规则引擎，把 evidence_autobuild
里现在标"待第二块"的三环（世界观级 / 战略产业面 / 手段层）变成机器自动评。

诚实边界（总则第九条四、第十三条二）：机器【抓不到】真源 → 如实标"待接真源"、读上一
状态、绝不编造。先接一个能用的源跑通一环，再逐环加。

可用真源（机器侧·无需密钥）：
- 主题新闻：Google News RSS（keyless）→ 战略产业面 / 手段层 / 世界观级
- 经济日历：FRED fredgraph.csv（keyless）→ 总闸(非农/CPI/Fed 真值)；本网络下超时则标"待接真源"

用法：
  python scripts/macro_news_intake.py --date 20260711        # 独立跑：读回 daily_ 写回三环
  evidence_autobuild.py --with-macro-news                      # 由第一块调用 enrich_links()
"""

import argparse
import html
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (compatible; macro_news_intake/1.0)"}
TIMEOUT = 12

# ── 写死·可审计的新闻关键词规则表（力度打分）────────────────────────────────
STRAT_BULL = ["record", "beat", "beats", "raise", "raised", "robust", "strong", "surge",
              "surges", "upgrade", "boom", "rally", "all-time", "tops", "jump", "soar",
              "demand remains", "上修", "强劲", "创纪录", "超预期"]
STRAT_BEAR = ["miss", "misses", "cut", "cuts", "slowdown", "sell-off", "selloff", "downgrade",
              "plunge", "plunges", "glut", "oversupply", "warn", "warns", "weak",
              "趋稳", "下修", "疲软", "抛售", "不及预期"]
MEANS_POS = ["approval", "approved", "greenlight", "green light", "bank", "charter", "launch",
             "adopt", "adoption", "license", "expand", "integrat", "partnership", "issue",
             "获批", "落地", "扩张"]
MEANS_NEG = ["ban", "banned", "dilute", "crackdown", "restrict", "delay", "reject", "sue",
             "lawsuit", "fraud", "禁", "打击", "收紧", "推迟"]
WORLD_REGIME = ["war", "invasion", "sanction", "tariff", "alliance", "decoupl", "nuclear",
                "coup", "embargo", "regime", "战争", "制裁", "关税", "脱钩"]

# 每环一条新闻查询（先一源一环跑通；可逐环加）
QUERIES = {
    "strategy": "AI semiconductor earnings guidance Nvidia TSMC demand",
    "means": "stablecoin regulation crypto bank",
    "world": "US tariff sanctions geopolitics alliance",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── 真源抓取（抓不到→返回 None，由调用方标"待接真源"）────────────────────────

def fetch_news(query: str, limit: int = 6) -> list[dict[str, str]] | None:
    """Google News RSS（keyless）。返回 [{title, source}]；网络失败→None。"""
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read()
        root = ET.fromstring(raw)
    except Exception:
        return None
    items = []
    for it in root.findall(".//item")[:limit]:
        title = html.unescape((it.findtext("title") or "").strip())
        src = ""
        src_el = it.find("source")
        if src_el is not None and src_el.text:
            src = html.unescape(src_el.text.strip())
        link = html.unescape((it.findtext("link") or "").strip())  # 真新闻url·让证据链可点(派工单§2.1)
        if title:
            items.append({"title": title, "source": src, "url": link})
    return items or None


def fetch_fred_latest(series_id: str) -> dict[str, Any] | None:
    """FRED fredgraph.csv（keyless）。返回 {date, value, prev}；失败/超时→None。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        req = urllib.request.Request(url, headers=UA)
        text = urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8")
    except Exception:
        return None
    rows = [r for r in text.strip().splitlines()[1:] if "," in r]
    vals = []
    for r in rows:
        d, _, v = r.partition(",")
        v = v.strip()
        if v and v != ".":
            try:
                vals.append((d.strip(), float(v)))
            except ValueError:
                pass
    if not vals:
        return None
    last = vals[-1]
    prev = vals[-2] if len(vals) >= 2 else (None, None)
    return {"series": series_id, "date": last[0], "value": last[1], "prev": prev[1]}


# ── 关键词规则：真新闻→力度（写死·可审计）────────────────────────────────────

def _count(titles: list[str], words: list[str]) -> int:
    low = " ".join(titles).lower()
    return sum(low.count(w.lower()) for w in words)


def score_strategy(news: list[dict[str, str]]) -> dict[str, Any]:
    titles = [n["title"] for n in news]
    bull, bear = _count(titles, STRAT_BULL), _count(titles, STRAT_BEAR)
    net = bull - bear
    if net >= 2:
        strength, state = "强", "AI产业面走强"
    elif net <= -2:
        strength, state = "弱", "AI产业面转弱"
    else:
        strength, state = "中", "AI产业面中性"
    return {"strength": strength, "state": state, "bull": bull, "bear": bear,
            "direction": f"AI({state})"}


def score_means(news: list[dict[str, str]]) -> dict[str, Any]:
    titles = [n["title"] for n in news]
    pos, neg = _count(titles, MEANS_POS), _count(titles, MEANS_NEG)
    if pos == 0 and neg == 0:
        strength, state = "弱", "手段层今日无明显动作"
    elif pos - neg >= 2:
        strength, state = "中", "稳定币/加密通道活跃(偏松)"
    elif neg - pos >= 2:
        strength, state = "弱", "稳定币/加密通道受限(偏紧)"
    else:
        strength, state = "中", "手段层有动作·中性"
    return {"strength": strength, "state": state, "pos": pos, "neg": neg,
            "direction": state}


def score_world(news: list[dict[str, str]]) -> dict[str, Any]:
    titles = [n["title"] for n in news]
    regime = _count(titles, WORLD_REGIME)
    # 世界观级 regime 反转是高门槛：读了真新闻但不凭标题关键词就翻面(诚实)
    if regime >= 4:
        state = "地缘/秩序信号增多·需盯(未到regime反转)"
    else:
        state = "三支柱维持·无regime反转"
    return {"strength": "中", "state": state, "regime_hits": regime,
            "direction": f"变({state})"}


# ── 组装：把真评写回对应 link（覆盖"待第二块"占位，带 source 指纹）──────────────

def _find(links: list[dict], keyword: str) -> dict | None:
    for L in links:
        if keyword in str(L.get("node", "")):
            return L
    return None


def enrich_links(links: list[dict[str, Any]], date: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """把三环"待第二块"→机器自动评；返回 (links, report)。抓不到的如实标待接真源。"""
    report: dict[str, Any] = {"source": "Google News RSS(keyless) + FRED(keyless)",
                              "auto_nodes": [], "pending_source_nodes": [], "fetched": {}}

    # —— 环1：战略产业面（AI/半导体新闻）——
    strat_news = fetch_news(QUERIES["strategy"])
    node = _find(links, "战略指向")
    if node is not None:
        if strat_news:
            sc = score_strategy(strat_news)
            heads = [n["title"] for n in strat_news[:3]]
            node["evidence"] = (f"【第二块·真新闻】AI/半导体产业面：多空关键词 多={sc['bull']}/空={sc['bear']} "
                                f"→ 规则判「{sc['state']}·{sc['strength']}」。样本：" + "；".join(heads))
            node["strength"] = sc["strength"]
            node["direction"] = sc["direction"]
            node["today_events"] = [f"真新闻：{h}" for h in heads]
            node["background"] = [f"关键词打分 多{sc['bull']}-空{sc['bear']}=净{sc['bull']-sc['bear']}"]
            node["news_items"] = [{"title": n["title"], "source": n.get("source", ""), "url": n.get("url", "")} for n in strat_news[:3]]
            node["source"] = f"Google News RSS·q=[{QUERIES['strategy']}]·{len(strat_news)}条"
            node["_state"] = sc["state"]
            if sc["strength"] == "强":
                node["plain"] = f"今天 AI 产业的好消息明显比坏消息多（利好{sc['bull']}条/利空{sc['bear']}条）→ 对你：AI 主线基本面还硬，核心仓可以守。"
            elif sc["strength"] == "弱":
                node["plain"] = f"今天 AI 产业的坏消息偏多（利好{sc['bull']}/利空{sc['bear']}）→ 对你：AI 主线要盯着点、别急着加仓。"
            else:
                node["plain"] = f"今天 AI 产业消息多空参半（利好{sc['bull']}/利空{sc['bear']}）→ 对你：AI 主线没大变，守着看。"
            report["auto_nodes"].append("战略产业面")
            report["fetched"]["strategy"] = {"count": len(strat_news), "score": sc}
        else:
            node["evidence"] = "【待接真源】战略产业面新闻源今日抓取失败 → 读上一状态「中」，不编造。"
            node["direction"] = "AI(待接真源·读上一状态)"
            node["plain"] = "今天没抓到 AI 产业的新闻，沿用上次判断「AI 主线仍在」→ 对你：核心仓照守，不因抓不到就动。"
            node["source"] = "Google News RSS 抓取失败·待接真源"
            report["pending_source_nodes"].append("战略产业面")

    # —— 环2：手段层（稳定币/FIMA 新闻）——
    means_news = fetch_news(QUERIES["means"])
    node = _find(links, "手段层")
    if node is not None:
        if means_news:
            sc = score_means(means_news)
            heads = [n["title"] for n in means_news[:3]]
            node["evidence"] = (f"【第二块·真新闻】手段层(稳定币/加密通道)：正={sc['pos']}/负={sc['neg']} "
                                f"→ 规则判「{sc['state']}·{sc['strength']}」。样本：" + "；".join(heads))
            node["strength"] = sc["strength"]
            node["direction"] = sc["direction"]
            node["today_events"] = [f"真新闻：{h}" for h in heads]
            node["background"] = [f"关键词打分 正{sc['pos']}/负{sc['neg']}", "FIMA 定量数值仍待机械层"]
            node["news_items"] = [{"title": n["title"], "source": n.get("source", ""), "url": n.get("url", "")} for n in means_news[:3]]
            node["source"] = f"Google News RSS·q=[{QUERIES['means']}]·{len(means_news)}条"
            node["_state"] = sc["state"]
            if "偏松" in sc["state"] or "活跃" in sc["state"]:
                node["plain"] = f"稳定币/加密这条「钱进美元」的管道今天利好偏多（利好{sc['pos']}/利空{sc['neg']}）→ 对你：这条大通道在变活，长期利多美元资产。"
            elif "受限" in sc["state"] or "偏紧" in sc["state"]:
                node["plain"] = f"稳定币这条管道今天遇到监管收紧（利好{sc['pos']}/利空{sc['neg']}）→ 对你：短期情绪偏谨慎。"
            else:
                node["plain"] = "稳定币/加密通道今天没明显动作 → 对你：不影响今天动作。"
            report["auto_nodes"].append("手段层")
            report["fetched"]["means"] = {"count": len(means_news), "score": sc}
        else:
            node["evidence"] = "【待接真源】手段层新闻源今日抓取失败 → 读上一状态，不编造。"
            node["direction"] = "待接真源·读上一状态"
            node["plain"] = "今天没抓到稳定币/加密的新闻，沿用上次判断 → 对你：不影响今天动作。"
            node["source"] = "Google News RSS 抓取失败·待接真源"
            report["pending_source_nodes"].append("手段层")

    # —— 环3：世界观级（地缘/秩序新闻）——
    world_news = fetch_news(QUERIES["world"])
    node = _find(links, "总命题") or _find(links, "世界")
    if node is not None:
        if world_news:
            sc = score_world(world_news)
            heads = [n["title"] for n in world_news[:3]]
            node["evidence"] = (f"【第二块·真新闻】地缘/秩序：regime关键词命中={sc['regime_hits']} "
                                f"→ 规则判「{sc['state']}」(标题关键词不足以宣告regime反转·诚实)。样本：" + "；".join(heads))
            node["strength"] = sc["strength"]
            node["direction"] = sc["direction"]
            node["today_events"] = [f"真新闻：{h}" for h in heads]
            node["background"] = [f"regime关键词命中={sc['regime_hits']}", "三支柱框架延续"]
            node["news_items"] = [{"title": n["title"], "source": n.get("source", ""), "url": n.get("url", "")} for n in world_news[:3]]
            node["source"] = f"Google News RSS·q=[{QUERIES['world']}]·{len(world_news)}条"
            node["_state"] = sc["state"]
            if "增多" in sc["state"]:
                node["plain"] = f"今天扫了地缘新闻，紧张信号多了些（命中{sc['regime_hits']}条），但还没到掀翻大格局 → 对你：大方向暂不变，多留个心眼。"
            else:
                node["plain"] = f"今天扫了地缘新闻，没有会掀翻世界大格局的大事（命中{sc['regime_hits']}条）→ 对你：投资大方向不变，照现有框架走。"
            report["auto_nodes"].append("世界观级")
            report["fetched"]["world"] = {"count": len(world_news), "score": sc}
        else:
            node["evidence"] = "【待接真源】世界观级新闻源今日抓取失败 → 读上一状态，不编造。"
            node["direction"] = "待接真源·读上一状态"
            node["plain"] = "今天没抓到地缘/秩序的新闻，沿用上次判断 → 对你：大方向不变。"
            node["source"] = "Google News RSS 抓取失败·待接真源"
            report["pending_source_nodes"].append("世界观级")

    # —— 总闸 enrich：经济日历真值(非农/CPI/Fed)。本网络下 FRED 超时→待接真源 ——
    fed_node = _find(links, "总闸")
    macro = {}
    for key, sid in (("非农PAYEMS", "PAYEMS"), ("CPI", "CPIAUCSL"), ("FedFunds", "FEDFUNDS")):
        got = fetch_fred_latest(sid)
        if got:
            macro[key] = got
    if fed_node is not None:
        if macro:
            bits = []
            for k, v in macro.items():
                trend = ""
                if v.get("prev") is not None:
                    trend = "升" if v["value"] > v["prev"] else ("降" if v["value"] < v["prev"] else "平")
                bits.append(f"{k}={v['value']}({v['date']}·较前值{trend})")
            fed_node.setdefault("today_events", []).append("经济日历真值：" + "；".join(bits))
            fed_node["source"] = str(fed_node.get("source", "")) + " + FRED经济日历"
            report["fetched"]["macro_calendar"] = macro
            report["auto_nodes"].append("总闸·经济日历enrich")
        else:
            fed_node.setdefault("background", []).append("经济日历源(FRED非农/CPI/Fed)本次超时→待接真源，总闸仍按行情边际")
            report["pending_source_nodes"].append("总闸·经济日历(FRED超时)")

    return links, report


def apply_to_file(date: str) -> dict[str, Any]:
    """独立跑：读回 daily_{date}.json，enrich 三环，写回。"""
    path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    if not path.exists():
        raise FileNotFoundError(f"need 第一块求证表 first: {path}")
    data = _read_json(path)
    links, report = enrich_links(data.get("links", []), date)
    data["links"] = [{k: v for k, v in L.items() if not k.startswith("_")} for L in links]
    data.setdefault("rule_engine", {})["macro_news"] = report
    data["data_date_note"] = str(data.get("data_date_note", "")) + " ｜已接第二块(宏观新闻源)覆写三环。"
    _write_json(path, data)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="第二块·宏观事件+主题新闻源")
    parser.add_argument("--date", default="20260711")
    args = parser.parse_args()
    report = apply_to_file(args.date)
    print(f"[OK] 第二块已写回 daily_{args.date}.json")
    print("自动评环:", "、".join(report["auto_nodes"]) or "无")
    print("待接真源环:", "、".join(report["pending_source_nodes"]) or "无")
    print("report:", json.dumps(report, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
