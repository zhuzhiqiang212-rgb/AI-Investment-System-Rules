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

# 类型 → 门槛族(尺§四·分行业·不一刀切)。门槛数值=试行示例·待董事长校准。
BENCHMARK_FAMILY = {
    "成长股": "制造软件品牌", "周期股": "半导体设备工业", "保险": "金融",
    "券商": "金融", "综合商社": "控股金融", "控股公司": "控股金融", "资产": "资产",
}
# 各门槛族·五项口径(试行·待校准)。None=该族豁免/NA·不卡此项。
FAMILY_THRESHOLDS = {
    "制造软件品牌": {"gross_margin_min": 0.45, "fcf_positive": True, "backlog_applies": True,
                     "note": "毛利率≥45%(示例线·待校准)、FCF为正+现金转化、订单看指引/递延/续约"},
    "半导体设备工业": {"gross_margin_min": None, "fcf_positive": True, "backlog_applies": True,
                       "note": "毛利率按代工/设备结构(台积50-59%正常·不卡45%)、FCF为正(周期底部可入②)、订单看backlog/book-to-bill"},
    "金融": {"gross_margin_min": None, "fcf_positive": None, "backlog_applies": False,
             "note": "毛利率/FCF豁免→看净利率/ROE/坏账率、资本充足/拨备、杠杆口径；订单NA"},
    "控股金融": {"gross_margin_min": None, "fcf_positive": None, "backlog_applies": False,
                 "note": "控股/商社豁免毛利/FCF→看资产质量/NAV/杠杆；订单NA"},
    "资产": {"gross_margin_min": None, "fcf_positive": None, "backlog_applies": False,
             "note": "无财报资产·质量关NA(只按仓位纪律+币价)"},
}
IND_NAMES = {"gross_margin": "毛利率", "fcf": "自由现金流", "pricing_power": "订价权",
             "balance_sheet": "资产负债表", "order_visibility": "订单可见度"}


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


def grade_one(symbol: str, name: str, indicators: dict, is_active_node: bool) -> dict:
    """给一只判三档。缺数从宽(②/待接)、激活节点封顶②、改善趋势不③——防误杀三条内建。"""
    cls = classify(symbol, name)
    typ = cls.get("type", "")
    fam = BENCHMARK_FAMILY.get(typ, "制造软件品牌")
    th = FAMILY_THRESHOLDS.get(fam, {})
    indicators = indicators or {}

    # 资产口径：质量关NA
    if typ == "资产" or fam == "资产":
        return {"tier": "NA", "tier_label": "资产口径·质量关NA", "family": fam, "type": typ,
                "missing": [], "why": "无财报资产·质量关不适用(只按仓位纪律)", "flags": []}

    missing: list[str] = []
    hard_hits: list[str] = []       # 硬伤(真数据·达到③条件)
    improving_below: list[str] = []  # 未达标但改善中(→②)
    ok_hits: list[str] = []

    def _check(key, val_key, threshold, cmp_desc):
        """通用检查：缺→missing; 达标→ok; 未达标看趋势→硬伤 or 改善中。"""
        raw = indicators.get(val_key, {}) if isinstance(indicators.get(val_key), dict) else {"value": indicators.get(val_key)}
        val = _num(raw.get("value"))
        trend = raw.get("trend")
        disp = IND_NAMES[key]
        if threshold is None:      # 该族豁免此项
            return
        if val is None:
            missing.append(disp)
            return
        if key == "gross_margin":
            passed = val >= threshold
        elif key == "fcf":
            passed = val > 0
        else:
            passed = True
        if passed:
            ok_hits.append(disp)
        elif _improving(trend):
            improving_below.append(f"{disp}(未达标但改善中)")
        elif _deteriorating(trend):
            hard_hits.append(f"{disp}(低于门槛且下滑)")
        else:
            improving_below.append(f"{disp}(未达标·趋势未知·试行从宽按观察)")

    _check("gross_margin", "gross_margin", th.get("gross_margin_min"), "≥门槛")
    _check("fcf", "fcf", th.get("fcf_positive"), "为正")
    # 订价权/资产负债表/订单可见度：有明确硬伤标记才计③依据，否则缺→待评/待接
    for key, vk in (("pricing_power", "pricing_power"), ("balance_sheet", "balance_sheet"), ("order_visibility", "order_visibility")):
        raw = indicators.get(vk, {}) if isinstance(indicators.get(vk), dict) else {"value": indicators.get(vk)}
        val = raw.get("value")
        if val in (None, ""):
            if key == "order_visibility" and not th.get("backlog_applies", True):
                continue                       # 该族订单NA·不计缺
            missing.append(IND_NAMES[key] + ("·待评" if key == "pricing_power" else "·待接"))
        elif _deteriorating(raw.get("trend")) and str(val).strip() in ("弱", "差", "恶化"):
            hard_hits.append(f"{IND_NAMES[key]}(明确走弱)")
        else:
            ok_hits.append(IND_NAMES[key])

    flags: list[str] = []
    # ③ 硬伤·淘汰：真数据硬伤 且 无改善 且 非激活节点 且 非缺数从宽
    if hard_hits and not is_active_node and not improving_below:
        return {"tier": "③", "tier_label": "硬伤·淘汰", "family": fam, "type": typ,
                "missing": missing, "why": "、".join(hard_hits) + "·账本明确硬伤且无改善趋势",
                "flags": ["硬筛淘汰"]}
    # 防误杀：激活节点→封顶② / 改善中→② / 缺数→②(试行从宽)
    if is_active_node and hard_hits:
        flags.append("防误杀②:属当日激活趋势节点·只降到②不淘汰")
    if improving_below:
        flags.append("防误杀②:未达标但趋势改善·不杀")
    if missing:
        flags.append("试行从宽:缺真数据·标待接·按②观察不杀")

    # ① 优质：无缺、无硬伤、无未达标·且至少有实测达标项
    if not missing and not hard_hits and not improving_below and ok_hits:
        return {"tier": "①", "tier_label": "优质·通过", "family": fam, "type": typ,
                "missing": [], "why": "各项达标无硬伤：" + "、".join(ok_hits), "flags": []}
    # 其余 → ② 趋势观察·不杀
    why_bits = []
    if improving_below:
        why_bits.append("；".join(improving_below))
    if missing:
        why_bits.append("缺(待接/待评)：" + "、".join(missing))
    if is_active_node:
        why_bits.append("属当日激活趋势节点")
    return {"tier": "②", "tier_label": "趋势观察·不杀", "family": fam, "type": typ,
            "missing": missing, "why": "；".join(why_bits) or "试行期数据待接·按观察不杀", "flags": flags}


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
        ind = (inputs.get(sym) or inputs.get(sym.split(".")[-1]) or {}).get("indicators", {})
        r = grade_one(sym, name, ind, is_active)
        r["industry_bucket"] = INDUSTRY_BUCKET.get(r.get("type", ""), "制造软件品牌")  # 分行业门槛(派工单②)
        r["rule_source"] = RULE_SOURCE                                                  # 依据尺
        r["is_active_node"] = is_active                                                 # 是否当日激活趋势节点(防误杀联动)
        out[sym] = r
    return out


def summarize(graded: dict[str, dict]) -> dict[str, int]:
    c = {"①": 0, "②": 0, "③": 0, "NA": 0}
    for r in graded.values():
        c[r.get("tier", "②")] = c.get(r.get("tier", "②"), 0) + 1
    return c
