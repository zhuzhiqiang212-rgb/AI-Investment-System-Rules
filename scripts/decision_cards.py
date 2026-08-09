# -*- coding: utf-8 -*-
"""★轮129 D2/PI1:左栏图文决策卡。每张卡四段固定：①今日事件(引用证据ID·来源·as_of)→②对照哪把尺→
③判定(印证绿/动摇红)→④一句话依据(大白话·G14)。★迷你图=SVG内联(不外链)近20日走势。★卡显provenance。
★PI1-4 未填层不出卡(不造壳)·标『待判断』。★PI2 守G14大白话:不许只写守/观察·必带『错了看什么信号』(证伪信号)。
★Code不填判断·只把 evidence_map/判断工单/价格序列 搬成卡·术语加大白话旁注。"""
import json, html as _h
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(x):
    return _h.escape(str(x)) if x is not None else ""


# ★PI2-3 术语→大白话旁注(G14:术语必须大白话)
GLOSSARY = {
    "边际转松": "钱没那么紧了，但只是今天这一下·不是趋势反转",
    "印证": "今天的事验证了原来的判断",
    "动摇": "今天的事跟原判断相反·要警惕",
    "可能动摇": "今天的事可能跟原判断相反·方向还要 Opus5 定",
    "受损": "对它不利",
    "受益": "对它有利",
    "普跌": "都在跌",
    "抗跌": "跌得比别人少",
    "紧档": "利率还在高位·钱贵",
    "客观空": "今天真没这类事·不是漏填",
    "状态延续": "沿用昨天的判断·今天没新变化",
}


def _plain(text):
    """给术语加大白话旁注(命中GLOSSARY的词后加括注·只加一次)。"""
    t = str(text or ""); added = set()
    for k, v in GLOSSARY.items():
        if k in t and k not in added:
            t = t.replace(k, "%s（＝%s）" % (k, v), 1); added.add(k)
    return t


def _sparkline(symbol, w=150, h=36):
    """★PI1-2:近20日收盘 SVG 内联迷你图(不外链·不依赖CDN)。涨绿跌红。取不到→标『无价格序列』。"""
    d = _rj(ROOT / "data/prices" / f"daily_{symbol}.json")
    series = d.get("series") or []
    closes = [x.get("close") for x in series[-20:] if isinstance(x.get("close"), (int, float))]
    if len(closes) < 2:
        return '<span style="font-size:10px;color:#999">（无近20日价格序列·迷你图略）</span>'
    lo, hi = min(closes), max(closes)
    rng = (hi - lo) or 1
    n = len(closes)
    pts = " ".join("%.1f,%.1f" % (i * (w / (n - 1)), h - 2 - (c - lo) / rng * (h - 4)) for i, c in enumerate(closes))
    up = closes[-1] >= closes[0]
    col = "#0f7b3f" if up else "#c0392b"
    pct = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] else 0
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle">'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6"/>'
            f'<circle cx="{w:.0f}" cy="{h-2-(closes[-1]-lo)/rng*(h-4):.1f}" r="2.2" fill="{col}"/></svg>'
            f'<span style="font-size:10px;color:{col}">近20日 {pct:+.1f}%</span>')


def _verdict_style(kind):
    """判定→红绿底色(印证绿/动摇红/延续灰蓝/待判断灰)。"""
    if "动摇" in kind:
        return "#fdecea", "#c0392b", "★动摇"
    if "印证" in kind:
        return "#e9f7ef", "#0f7b3f", "印证"
    if "延续" in kind or "客观空" in kind:
        return "#eef2f7", "#42607a", "状态延续"
    return "#f2f2f2", "#888", "待判断"


def _card(事件, 证据ID, 来源, as_of, 尺, 判定文, 判定kind, 一句话, 错了看, prov, svg):
    bg, bd, badge = _verdict_style(判定kind)
    err = f'<div style="font-size:11.5px;color:#7a3b00;margin-top:3px">🔎 <b>错了看什么信号</b>：{esc(错了看)}</div>' if 错了看 else \
          '<div style="font-size:11px;color:#a00;margin-top:3px">🔎 错了看什么信号：★待 Opus5 给证伪信号</div>'
    return (f'<div style="border:1px solid {bd};border-left:6px solid {bd};border-radius:8px;background:{bg};padding:9px 12px;margin:8px 0">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="font-size:12px;color:#555">① 今日事件 <span style="background:#12324e;color:#fff;border-radius:3px;padding:0 5px;font-size:10px">{esc(证据ID)}</span></span>{svg}</div>'
            f'<div style="font-size:13px;font-weight:600;margin:2px 0">{esc(事件)}</div>'
            f'<div style="font-size:11px;color:#666">来源 {esc(来源)}·{esc(as_of)}</div>'
            f'<div style="font-size:12px;margin-top:4px">② 对照尺：<b>{esc(尺)}</b> ｜ ③ 判定：<b style="color:{bd}">{esc(badge)}·{esc(判定文)}</b></div>'
            f'<div style="font-size:12.5px;margin-top:4px">④ <b>一句话依据</b>：{esc(一句话)}</div>'
            f'{err}'
            f'<div style="font-size:10.5px;color:#88a;margin-top:4px">provenance：{esc(prov)}</div></div>')


_LAYER_KEY = {"③资金流动": "③资金流动", "④板块轮动": "④板块轮动", "⑥持仓比较": "⑥持仓比较"}


def _downstream_judgment(dc, 下游层):
    """取该证据下游层已填判断(证伪信号=错了看什么)。未填→None。"""
    try:
        from judgment_slots_build import read_layer_output as _rlo
        k = _LAYER_KEY.get(下游层)
        return _rlo(dc, k) if k else None
    except Exception:
        return None


def layer1_cards(dc):
    """★册1:①层动摇/可能动摇事件→决策卡(PI3-1)。判定=印证/动摇(机器)·错了看=下游已填层证伪信号。"""
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    cards = []
    for e in em.get("路1_对6尺持续验证(★动摇置顶)", []):
        kind = str(e.get("印证动摇") or "")
        if "动摇" not in kind:   # 只出动摇/可能动摇(册1动摇条)
            continue
        下游 = e.get("下游层")
        j = _downstream_judgment(dc, 下游)
        错了看 = (j or {}).get("证伪信号")
        一句 = _plain("%s（%s）——%s" % (e.get("维度") or "", e.get("方向") or "", "跟原判断相反·要警惕" if "★动摇" in kind else "可能跟原判断相反·方向待Opus5定"))
        # 迷你图:第一三共等个股给个股图;板块/宏观无个股→略
        sym = "JP.4568" if "第一三共" in str(e.get("证据")) else None
        svg = _sparkline(sym) if sym else '<span style="font-size:10px;color:#999">（宏观/板块·无单一标的迷你图）</span>'
        cards.append(_card(str(e.get("证据"))[:90], e.get("id"), e.get("来源"), e.get("as_of"),
                           e.get("对应尺"), kind, kind, 一句, 错了看,
                           "①证据映射器→%s%s" % (下游, ("·下游%s已填判断" % 下游) if j else "·下游待判断"), svg))
    return cards


def holding_cards(dc):
    """★册2a/2b:持仓判断卡。★PI1-4:⑥复核已填→出卡;⑥未填→不出卡·标『待判断』(不造壳)。"""
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    sl = (js.get("②~⑦层工单", {}) or {}).get("⑥持仓比较", {}) or {}
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    name_by = {p.get("symbol"): p.get("name") for p in ep.get("三只", [])}
    cards = []; pending = []
    for r in sl.get("★须复核既有判断(NV3)", []):
        cs = r.get("★复核槽位(Opus5填)", {}) or {}
        concl = cs.get("维持原判/修正/撤回")
        sym = r.get("标的")
        if concl:   # ⑥复核已填→出卡
            kind = "★动摇" if ("修正" in str(concl) or "撤回" in str(concl)) else "印证"
            svg = _sparkline(sym) if sym and sym.startswith(("JP.", "US.")) else ""
            cards.append(_card("%s 复核：%s" % (name_by.get(sym, sym), concl), r.get("动摇证据ID"),
                               "⑥持仓判断工单(Opus5)", "复核", "⑥持仓档案", concl, kind,
                               _plain(str(cs.get("理由"))[:120]), cs.get("新证伪信号"),
                               "⑥持仓比较·复核·引用%s" % cs.get("★引用证据ID"), svg))
        else:       # ★未填→不出卡·记待判断(不造壳)
            pending.append(name_by.get(sym, sym))
    return cards, pending


def build_all(dc):
    return {"层1卡": layer1_cards(dc), "持仓卡_pending": holding_cards(dc)}
