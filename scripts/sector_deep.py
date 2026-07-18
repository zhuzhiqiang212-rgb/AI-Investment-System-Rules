#!/usr/bin/env python3
"""板块深度尺（董事局工单 2026-07-18·架构师产出3份子板块深度研究后渲入）

读架构师3份研究：
  data/valuation/sector_research_power_infra.json     （AI电力/能源 + AI基础设施外延）
  data/valuation/sector_research_health_software.json （AI医疗健康 + AI软件应用）
  data/valuation/sector_research_defense_semi.json    （军工国防 + 半导体设备/存储）

三份 schema 各异（英文键 / 中文键板块一二 / sector_1_2）→ 这里归一化成统一结构：
  subsector = {key, name, tag, data_date, disclaimer,
               static:{what, chain, long},
               dynamic:{past, now, next, drivers},
               leaders:[{title, w(为什么是他·业务+技术), f(财报), v(估值贵不贵),
                         vs(对比持仓), rec(决策建议), cls(前瞻分类), rel(可靠度), sources}],
               forward:{rec:[可推荐·下轮且价合理], wait:[好公司但贵·等回调]}}

硬边界（总则）：全部是【架构师研究·非权威·非富途实时价】；只读不改任何持仓动作；
缺可靠数据处（如 Leidos 实时价、ServiceNow 价格口径）照 JSON 里的标注写「待接·不编」。
龙头名单=动·季度级更新（非死名单·非日变）。

只读不产出文件；deep_render.py import 它渲染。
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VDIR = ROOT / "data" / "valuation"

# 机会池要收的「下轮可推荐·现价还合理」5只（董事长工单点名）
POOL_PICKS = ["VST", "CEG", "LHX", "RTX", "VEEV"]

DISCLAIMER = ("架构师研究·非权威·非富途实时价——股价/估值为架构师 2026-07 中旬网络快照，"
              "非 OpenD 当日实时；下单价以 OpenD 实时为准。龙头名单季度级更新，非死名单。")


def _rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fin_str(f: Any) -> str:
    """财报：dict→拼成一句；str→原样。"""
    if isinstance(f, dict):
        return "；".join(f"{k}：{v}" for k, v in f.items() if v)
    return str(f or "")


def _val_str(v: Any) -> str:
    if isinstance(v, dict):
        bits = []
        for k in ("price_jul2026", "market_cap", "pe_trailing", "pe_forward", "assessment"):
            if v.get(k):
                bits.append(str(v[k]))
        return "；".join(bits)
    return str(v or "")


def _leader_power(c: dict) -> dict:
    biz = str(c.get("business") or "")
    tech = str(c.get("tech") or "")
    w = biz + (("　技术门槛：" + tech) if tech else "")
    return {
        "title": f'{c.get("name","")}（{c.get("ticker","")}）',
        "ticker": str(c.get("ticker") or ""),
        "w": w,
        "f": _fin_str(c.get("financials")),
        "v": _val_str(c.get("valuation")),
        "vs": str(c.get("vs_holdings") or ""),
        "rec": str(c.get("recommendation") or ""),
        "cls": str(c.get("forward_class") or ""),
        "rel": str(c.get("reliability") or ""),
        "sources": c.get("sources") or [],
    }


def _leader_cn(c: dict) -> dict:
    """health/defense 的龙头小研报（键为 标的/名称_代码 + ①..⑤，可能带后缀）。"""
    def g(*names):
        for n in names:
            for k, v in c.items():
                if k == n or k.startswith(n):
                    return str(v or "")
        return ""
    title = g("标的", "名称_代码", "名称")
    return {
        "title": title,
        "ticker": _ticker_from(title),
        "w": g("①业务与技术", "①为什么是它", "①为什么是他"),
        "f": g("②财报真数据", "②财报"),
        "v": g("③估值贵不贵", "③估值"),
        "vs": g("④对比董事长持仓", "④对比", "④"),
        "rec": g("⑤决策建议", "⑤"),
        "cls": "",
        "rel": "",
        "sources": [],
    }


def _ticker_from(title: str) -> str:
    """从『礼来 Eli Lilly (LLY)』『RTX(雷神…)』『L3Harris(LHX)』抽 ticker。"""
    import re
    m = re.findall(r"\(([A-Z]{1,5})\)", title or "")
    if m:
        return m[-1]
    m2 = re.match(r"\s*([A-Z]{2,5})\b", title or "")
    return m2.group(1) if m2 else ""


def _forward_from_power(companies: list) -> dict:
    rec, wait = [], []
    for c in companies:
        fc = str(c.get("forward_class") or "")
        line = f'{c.get("name","")}（{c.get("ticker","")}）：{c.get("recommendation") or fc}'
        if fc.startswith("可推荐"):
            rec.append(line)
        elif "贵" in fc or "等回调" in fc:
            wait.append(line)
    return {"rec": rec, "wait": wait}


def _forward_from_cn(fwd: dict) -> dict:
    if not isinstance(fwd, dict):
        return {"rec": [], "wait": []}
    rec = fwd.get("合理的_可推荐") or fwd.get("合理的·可推荐") or []
    wait = fwd.get("贵的_等好价") or fwd.get("贵的·等好价") or []
    return {"rec": [str(x) for x in rec], "wait": [str(x) for x in wait]}


def load() -> list:
    """归一化3份研究 → 统一 subsector 列表（按板块地图顺序：先军工/电力硬分散，后半导体/软件/医疗）。"""
    out = []

    # ── 1) power_infra（英文键） ──
    p = _rj(VDIR / "sector_research_power_infra.json")
    dd = (p.get("_meta") or {}).get("data_date", "")
    for key, sv in (p.get("estimates") or {}).items():
        st = sv.get("static") or {}
        dy = sv.get("dynamic") or {}
        out.append({
            "key": key, "name": sv.get("name_cn", key), "tag": "AI电力能源＋基础设施",
            "data_date": dd, "disclaimer": DISCLAIMER,
            "static": {"what": st.get("what", ""), "chain": st.get("chain_position", ""),
                       "long": st.get("long_logic", "")},
            "dynamic": {"past": dy.get("past_quarter", ""), "now": dy.get("this_week", ""),
                        "next": dy.get("next_quarter", ""), "drivers": dy.get("drivers_numbers")},
            "leaders": [_leader_power(c) for c in (sv.get("companies") or [])],
            "forward": _forward_from_power(sv.get("companies") or []),
        })

    # ── 2) defense_semi（sector_1_/sector_2_） ── 军工排最前（进板块地图）
    d = _rj(VDIR / "sector_research_defense_semi.json")
    dd2 = (d.get("_meta") or {}).get("研究日期") or (d.get("_meta") or {}).get("data_date", "")
    ds = []
    for key in [k for k in d if k.startswith("sector_")]:
        sv = d[key]
        lk = next((k for k in sv if "龙头" in k), None)
        ds.append({
            "key": key, "name": _sub_name(key, sv), "tag": "军工国防＋设备存储",
            "data_date": dd2, "disclaimer": DISCLAIMER,
            "static": {"what": sv.get("静_是什么", ""), "chain": sv.get("静_在AI链哪一环", ""),
                       "long": sv.get("静_长期逻辑", "")},
            "dynamic": {"past": _g(sv, "动_过去"), "now": _g(sv, "动_现在"),
                        "next": _g(sv, "动_未来"), "drivers": None},
            "leaders": [_leader_cn(c) for c in (sv.get(lk) or [])] if lk else [],
            "forward": _forward_from_cn(sv.get("前瞻分类") or sv.get("前瞻分两类")),
        })
    # 军工放最前
    out = [x for x in ds if "军工" in x["name"]] + out + [x for x in ds if "军工" not in x["name"]]

    # ── 3) health_software（板块一_/板块二_） ──
    h = _rj(VDIR / "sector_research_health_software.json")
    dd3 = (h.get("_meta") or {}).get("data_date", "")
    for key in [k for k in h if k.startswith("板块")]:
        sv = h[key]
        lk = next((k for k in sv if "龙头" in k), None)
        out.append({
            "key": key, "name": _sub_name(key, sv), "tag": "AI医疗＋AI软件",
            "data_date": dd3, "disclaimer": DISCLAIMER,
            "static": {"what": sv.get("静_是什么", ""), "chain": sv.get("静_在AI链哪一环", ""),
                       "long": sv.get("静_长期逻辑", "")},
            "dynamic": {"past": _g(sv, "动_过去"), "now": _g(sv, "动_现在"),
                        "next": _g(sv, "动_未来"), "drivers": None},
            "leaders": [_leader_cn(c) for c in (sv.get(lk) or [])] if lk else [],
            "forward": _forward_from_cn(sv.get("前瞻分两类") or sv.get("前瞻分类")),
        })

    return out


def _g(sv: dict, prefix: str) -> str:
    for k, v in sv.items():
        if k.startswith(prefix):
            return str(v or "")
    return ""


def _sub_name(key: str, sv: dict) -> str:
    # 从 key 去掉 sector_1_/板块一_ 前缀留中文名
    import re
    nm = re.sub(r"^(sector_\d+_|板块[一二三四]_)", "", key)
    return nm or key


def pool_picks() -> list:
    """机会池要收的5只（VST/CEG/LHX/RTX/VEEV）——从统一结构里按 ticker 捞出，带来源+非权威标注。"""
    subs = load()
    idx = {}
    for s in subs:
        for L in s["leaders"]:
            if L["ticker"]:
                idx[L["ticker"]] = (s, L)
    picks = []
    for tk in POOL_PICKS:
        hit = idx.get(tk)
        if not hit:
            picks.append({"ticker": tk, "found": False,
                          "note": f"{tk}：架构师研究里未定位到龙头卡·待接"})
            continue
        s, L = hit
        picks.append({"ticker": tk, "found": True, "title": L["title"],
                      "sector": s["name"], "v": L["v"], "rec": L["rec"], "vs": L["vs"],
                      "sources": L["sources"], "disclaimer": DISCLAIMER})
    return picks


_TK_STOP = {"PE", "AI", "US", "EPS", "PS", "ACV", "ADC", "RNA", "DOE", "SEC", "IR",
            "GAAP", "TTM", "EV", "EBITDA", "DRAM", "NAND", "HBM", "EUV", "MAC", "IT",
            "PJM", "SMR", "PPA", "GPU", "CPU", "Q1", "Q2", "Q3", "Q4", "FY", "YOY"}


def _tickers_in(text: str) -> list:
    # ASCII-only 边界(中文在 Python 里算 \w，\b 在"RTX前"处不断词→漏抽)：用 negative lookaround
    import re
    got = re.findall(r"\(([A-Z]{1,5})\)", text or "")
    got += re.findall(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])", text or "")
    return [t for t in got if t not in _TK_STOP]


def arch_verdict_map() -> dict:
    """架构师对各龙头的【forward P/E 贵贱判定】查询表（供估值引擎/CI用）。
    返回 {ticker: {"verdict":"合理"|"合理偏上"|"贵·等回调"|"", "pe_text":..., "sector":...}}
    判定来源(权威·非机械)：
      · power 龙头的 forward_class 字段(可推荐→合理·好公司但贵→贵)
      · health/defense 的『前瞻分两类』(合理的_可推荐→合理·贵的_等好价→贵·等回调)
    只覆盖架构师研究里出现过的票；没出现的→不在表里(估值引擎据此标待接·不硬套正常化)。"""
    subs = load()
    out = {}
    for s in subs:
        for L in s["leaders"]:
            tk = L.get("ticker")
            if not tk:
                continue
            cls = str(L.get("cls") or "")
            verdict = ""
            if cls.startswith("可推荐"):
                verdict = "合理"
            elif "贵" in cls or "等回调" in cls:
                verdict = "贵·等回调"
            out[tk] = {"verdict": verdict, "pe_text": L.get("v", ""), "sector": s["name"]}
        f = s.get("forward") or {}
        for line in f.get("rec", []):
            for tk in set(_tickers_in(line)):
                out.setdefault(tk, {"verdict": "", "pe_text": line, "sector": s["name"]})
                if not out[tk].get("verdict"):
                    out[tk]["verdict"] = "合理"
        for line in f.get("wait", []):
            for tk in set(_tickers_in(line)):
                out.setdefault(tk, {"verdict": "", "pe_text": line, "sector": s["name"]})
                if not out[tk].get("verdict"):
                    out[tk]["verdict"] = "贵·等回调"
    return out


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    subs = load()
    print(f"归一化子板块 {len(subs)} 个：")
    for s in subs:
        print(f"  · {s['name']}（{s['tag']}·{s['data_date']}）龙头{len(s['leaders'])}只 "
              f"可推荐{len(s['forward']['rec'])}/等回调{len(s['forward']['wait'])}")
        for L in s["leaders"]:
            miss = [k for k in ("w", "f", "v", "vs", "rec") if not L[k]]
            print(f"      {L['ticker'] or '?':<6}{L['title'][:22]:<24}五维缺{miss or '无'}")
    print("\n机会池5只：")
    for p in pool_picks():
        print(f"  {p['ticker']}: {'✓ '+p.get('sector','') if p['found'] else '✗ '+p['note']}")
