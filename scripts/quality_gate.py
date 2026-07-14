#!/usr/bin/env python3
"""基本面质量关（试行·尺=基本面质量关框架.html）· 只读不下单

漏斗新增一关，放【硬性闸之后、均线/估值/护城河之前】。专看"账本硬不硬"：
毛利率/自由现金流/订价权/资产负债表/订单可见度——分行业门槛，不一刀切。

出【三档·不是过/杀两档】(核心=不误杀趋势标的)：
  ① 优质·通过     达标无硬伤 → 正常往下
  ② 趋势观察·不杀  某项未达标但趋势向上/属当日激活趋势节点/试行期缺数从宽 → 不淘汰·标黄·附缺哪项
  ③ 硬伤·淘汰     账本明确硬伤且无改善趋势 → 硬筛淘汰

防误杀三条(必须生效)：
  1) 看方向不只看水平：指标看趋势(环比/同比)，改善中即使未达标→②不③
  2) 与硬性闸联动：属"当日激活趋势节点"(硬性闸已认定方向)→ 只降到②、绝不③
  3) 试行期从宽：缺数/边界一律②、绝不③；门槛试行中校准

铁律：缺数不编，标"待接/待评/NA"；只锚指标定义+门槛尺+趋势判定法，不锚死名单(哪只落①②③是数据算出来的)。
输入：data/valuation/quality_inputs.json(理解岗填真财务·缺→null)。本关不入世界观·试行·重大改动经董事长。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = "00_请先看这里/基本面质量关框架.html"   # 本关依据的尺(试行·改尺走董事长)
sys.path.insert(0, str(ROOT / "scripts"))
try:
    from security_classifier import classify
except Exception:
    def classify(symbol: Any, name: Any = "") -> dict:  # type: ignore[misc]
        return {"type": "", "model": "", "model_disp": ""}

# 类型 → industry_bucket(尺§四门槛表的4行业·派工单②)：分行业门槛不一刀切
INDUSTRY_BUCKET = {
    "成长股": "制造软件品牌", "周期股": "半导体设备", "保险": "金融", "券商": "金融",
    "综合商社": "金融", "控股公司": "金融", "资产": "资产",
}

# 门槛按 industry_bucket 分行业·不一刀切(尺§四)。门槛数值=【试行初值·待董事长终审】。None=该桶豁免/NA·不卡此项。
# industry_bucket 每只可由 data/fundamentals 显式覆盖(如丰田汽车→低毛利制造)，缺则由类型 INDUSTRY_BUCKET 默认推。
BUCKET_THRESHOLDS = {
    "制造软件品牌": {"gross_margin_min": 0.45, "fcf_positive": True, "backlog_applies": True,
                     "note": "毛利率≥45%(试行初值·待终审)、FCF为正、订单看指引/递延/续约"},
    "半导体设备": {"gross_margin_min": None, "fcf_positive": True, "backlog_applies": True,
                   "note": "毛利率按代工/设备结构(台积50-66%正常·不卡45%)、FCF为正(周期底部可入②)、订单看backlog/book-to-bill"},
    "低毛利制造": {"gross_margin_min": 0.12, "fcf_positive": True, "backlog_applies": False,
                   "note": "低毛利制造(汽车/量产硬件/分销)·毛利率≥12%【试行初值·待终审】·不用45%线·重看trend+FCF+资产负债表"},
    "零售分销": {"gross_margin_min": None, "fcf_positive": True, "backlog_applies": False,
                 "note": "零售分销天生低毛利·毛利率豁免→看净利率/周转、FCF为正"},
    "金融": {"gross_margin_min": None, "fcf_positive": None, "roe_min": 0.10, "backlog_applies": False,
             "note": "金融/券商/控股/商社豁免毛利率/FCF→核心看ROE(≥10%试行初值·待终审)、资本充足/杠杆/NAV；订单NA"},
    "资产": {"gross_margin_min": None, "fcf_positive": None, "backlog_applies": False,
             "note": "无财报资产·质量关NA(只按仓位纪律+币价)"},
}


def bucket_for(typ: str, override: Any = None) -> str:
    """定 industry_bucket：显式覆盖(fundamentals) 优先；否则按类型默认推。"""
    b = str(override or "").strip()
    if b in BUCKET_THRESHOLDS:
        return b
    return INDUSTRY_BUCKET.get(typ, "制造软件品牌")
IND_NAMES = {"gross_margin": "毛利率", "fcf": "自由现金流", "pricing_power": "订价权",
             "balance_sheet": "资产负债表", "order_visibility": "订单可见度", "roe": "ROE净资产收益率"}


def _load_inputs() -> dict[str, dict]:
    # 结构化财报源(派工单③)：优先 data/fundamentals/fundamentals.json；兼容旧 data/valuation/quality_inputs.json
    for p in (ROOT / "data" / "fundamentals" / "fundamentals.json",
              ROOT / "data" / "valuation" / "quality_inputs.json"):
        if p.exists():
            try:
                return (json.loads(p.read_text(encoding="utf-8")) or {}).get("holdings", {}) or {}
            except Exception:
                continue
    return {}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _improving(trend: Any) -> bool:
    """趋势向上=改善中(环比/同比向好)。识别 改善/向上/转正/回升/up/improving。"""
    return any(k in str(trend or "") for k in ("改善", "向上", "转正", "回升", "提升", "up", "improv"))


def _deteriorating(trend: Any) -> bool:
    return any(k in str(trend or "") for k in ("恶化", "下滑", "走弱", "下降", "转差", "down", "deterior"))


def _fcf_positive(raw: dict):
    """FCF 是否为正：数值→>0；字符串→含'正'不含'负'为True、含'负'为False；否则 None(待接)。
    (Cowork 常把 FCF 填成'US$96.7B(正·…)'这类描述串·不硬编数)。"""
    val = raw.get("value")
    n = _num(val)
    if n is not None:
        return n > 0
    s = str(val or "")
    if not s:
        return None
    if "负" in s:
        return False
    if "正" in s:
        return True
    return None


def grade_one(symbol: str, name: str, indicators: dict, is_active_node: bool, industry_bucket: Any = None) -> dict:
    """给一只判三档。核心硬账指标(毛利率/FCF·按行业门槛)驱动①；定性项(订价权/订单)缺不阻止①、只标待评。
    防误杀三条内建：缺数从宽(②)、激活节点封顶②、改善趋势不③。industry_bucket 可由 fundamentals 覆盖。"""
    cls = classify(symbol, name)
    typ = cls.get("type", "")
    bucket = bucket_for(typ, industry_bucket)
    th = BUCKET_THRESHOLDS.get(bucket, {})
    indicators = indicators or {}

    if typ == "资产" or bucket == "资产":
        return {"tier": "NA", "tier_label": "资产口径·质量关NA", "industry_bucket": bucket, "type": typ,
                "missing": [], "why": "无财报资产·质量关不适用(只按仓位纪律)", "flags": []}

    def _raw(vk):
        v = indicators.get(vk)
        return v if isinstance(v, dict) else {"value": v}

    missing_core: list[str] = []   # 缺核心硬账指标(毛利/FCF·按行业适用)→②
    missing_aux: list[str] = []    # 缺定性/辅助(订价权/资产负债表/订单)→只标待评·不阻止①
    hard: list[str] = []           # 真硬伤(③候选)
    improving: list[str] = []      # 未达标但改善中(②)
    ok: list[str] = []
    core_ok: list[str] = []        # 通过的【核心硬账指标】(毛利达标/FCF为正)——①必须至少有一项(治金融桶靠辅助项虚升①)

    # 毛利率(核心·按行业门槛；None=该行业豁免不卡)
    gm_th = th.get("gross_margin_min")
    if gm_th is not None:
        gm = _num(_raw("gross_margin").get("value")); gm_tr = _raw("gross_margin").get("trend")
        if gm is None:
            missing_core.append("毛利率")
        elif gm >= gm_th:
            ok.append(f"毛利率{gm:.0%}≥门槛{gm_th:.0%}"); core_ok.append("毛利率")
        elif _improving(gm_tr):
            improving.append("毛利率(未达门槛但改善中)")
        elif _deteriorating(gm_tr):
            hard.append("毛利率(持续低于门槛且下滑)")
        else:
            improving.append("毛利率(未达门槛·趋势未知·试行从宽按观察)")

    # ROE(金融/券商/控股桶核心·豁免毛利/FCF后用它·尺:金融不与科技比毛利)。roe负/文本待接→留②·绝不③
    roe_th = th.get("roe_min")
    if roe_th is not None:
        rv = _num(_raw("roe").get("value"))
        if rv is None:                       # 文本(待接/负-描述串)→②不硬③
            missing_core.append("ROE·待接")
        elif rv >= roe_th:
            ok.append(f"ROE{rv:.0%}≥门槛{roe_th:.0%}"); core_ok.append("ROE")
        elif rv < 0:                         # ROE为负→留②观察·不硬判③(尺·派工单)
            improving.append(f"ROE为负({rv:.0%})·留观察不杀(不硬③)")
        else:
            improving.append(f"ROE{rv:.0%}未达门槛{roe_th:.0%}·观察")

    # 自由现金流(核心·按行业；None=豁免)
    if th.get("fcf_positive"):
        fr = _raw("fcf"); fpos = _fcf_positive(fr); ftr = fr.get("trend")
        if fpos is None:
            missing_core.append("自由现金流")
        elif fpos:
            ok.append("自由现金流为正"); core_ok.append("自由现金流")
        elif _improving(ftr):
            improving.append("FCF(为负但改善/有转正路径)")
        else:
            hard.append("FCF(长期为负且无改善)")

    # 资产负债表(辅助·仅明确恶化才算硬伤·否则缺=待接不阻止①)
    bs = _raw("balance_sheet"); bsv = bs.get("value")
    if bsv in (None, ""):
        missing_aux.append("资产负债表·待接")
    elif _deteriorating(bs.get("trend")) and str(bsv).strip() in ("弱", "差", "恶化", "资不抵债"):
        hard.append("资产负债表(明确恶化/资不抵债)")
    else:
        ok.append("资产负债表")

    # 订价权(辅助·定性·缺=待评不阻止①)
    pp = _raw("pricing_power").get("value")
    if pp in (None, ""):
        missing_aux.append("订价权·待评")
    else:
        ok.append(f"订价权{pp}")

    # 订单可见度(辅助·部分行业NA·缺=待接不阻止①)
    if th.get("backlog_applies", True):
        ov = _raw("order_visibility").get("value")
        if ov in (None, ""):
            missing_aux.append("订单可见度·待接")
        else:
            ok.append("订单可见度")

    flags: list[str] = []
    # ③ 硬伤·淘汰：真硬伤 且 无改善 且 非激活节点(防误杀三条)
    if hard and not is_active_node and not improving:
        return {"tier": "③", "tier_label": "硬伤·淘汰", "industry_bucket": bucket, "type": typ,
                "missing": missing_core + missing_aux, "why": "、".join(hard) + "·账本明确硬伤且无改善趋势",
                "flags": ["硬筛淘汰"]}
    if is_active_node and hard:
        flags.append("防误杀②:属当日激活趋势节点·只降到②不淘汰")
    if improving:
        flags.append("防误杀②:未达标但趋势改善·不杀")
    if missing_core:
        flags.append("试行从宽:缺核心真数据·标待接·按②观察不杀")

    # ① 优质：须有【核心硬账指标】达标(毛利达标或FCF为正)·且无缺核心/无硬伤/无未达标。
    # 定性 aux 缺不阻止；但核心全豁免(金融/控股·毛利FCF都不适用)→无核心可证→不虚升①·留②观察(账本待接金融口径ROE/资本充足)。
    if core_ok and not missing_core and not hard and not improving:
        why = "核心达标无硬伤：" + "、".join(ok)
        if missing_aux:
            why += "（辅助项待补：" + "、".join(missing_aux) + "，不影响优质判定）"
        return {"tier": "①", "tier_label": "优质·通过", "industry_bucket": bucket, "type": typ,
                "missing": missing_aux, "why": why, "flags": []}

    # 其余 → ② 趋势观察·不杀
    why_bits = []
    if improving:
        why_bits.append("；".join(improving))
    if missing_core:
        why_bits.append("缺核心(待接)：" + "、".join(missing_core))
    if not core_ok and not missing_core:   # 核心全豁免(金融/控股)·无硬账核心可证优质→观察
        why_bits.append("本行业毛利/FCF豁免·暂无核心硬账指标可证优质(账本待接金融口径:净利率/ROE/资本充足)")
    if missing_aux:
        why_bits.append("辅助(待评/待接)：" + "、".join(missing_aux))
    if is_active_node:
        why_bits.append("属当日激活趋势节点")
    return {"tier": "②", "tier_label": "趋势观察·不杀", "industry_bucket": bucket, "type": typ,
            "missing": missing_core + missing_aux, "why": "；".join(why_bits) or "试行期数据待接·按观察不杀", "flags": flags}


def grade_holdings(holdings: list[dict]) -> dict[str, dict]:
    """给全部持仓判质量关三档。holdings=[{symbol,name,matched_node_classes_effective 或 hard_filter}]。"""
    inputs = _load_inputs()
    out: dict[str, dict] = {}
    for h in holdings or []:
        sym = str(h.get("symbol") or "")
        if not sym:
            continue
        name = h.get("name", "")
        # 与硬性闸联动：effective 匹配到激活节点 或 hard_filter==符合 → 当日激活趋势节点
        eff = h.get("matched_node_classes_effective") or []
        is_active = bool(eff) or (h.get("hard_filter") == "符合")
        rec = inputs.get(sym) or inputs.get(sym.split(".")[-1]) or {}
        ind = rec.get("indicators", {})
        r = grade_one(sym, name, ind, is_active, rec.get("industry_bucket"))  # fundamentals 可覆盖 industry_bucket
        r["rule_source"] = RULE_SOURCE                                                  # 依据尺
        r["is_active_node"] = is_active                                                 # 是否当日激活趋势节点(防误杀联动)
        out[sym] = r
    return out


def summarize(graded: dict[str, dict]) -> dict[str, int]:
    c = {"①": 0, "②": 0, "③": 0, "NA": 0}
    for r in graded.values():
        c[r.get("tier", "②")] = c.get(r.get("tier", "②"), 0) + 1
    return c
