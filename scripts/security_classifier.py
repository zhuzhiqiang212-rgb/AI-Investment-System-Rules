#!/usr/bin/env python3
"""标的类型分类器 → 自动选估值模型（尺=右栏_估值方法学.html §1）· 只读不下单

董事长定：估值模型【由类型自动定】，不手工每只指定(见尺铁律)。本模块把标的按【生意模式/行业】
归类，再按尺的"类型→模型"表自动映射估值模型；持仓与候选池新标的都走同一分类。

分类来源(依次)：
  ① CC.* → 资产(无财报·不做企业估值)
  ② data/valuation/security_types.json 登记的行业事实(可迭代·非模型死名单·补登=数据)
  ③ 名称/代码关键词规则(兜底·新候选也能自动归类)
  ④ 都不中 → 默认"成长股"并标"默认分类·请核"(不静默、供PDCA纠偏)

类型→模型映射即"尺"，改它=改尺·走董事长。缺真财务输入的由估值引擎标"待接真源"、不硬编。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# 类型 → 模型（尺·右栏_估值方法学§1）。改此=改尺·走董事长。
TYPE_MODEL: dict[str, dict[str, str]] = {
    "成长股":   {"model": "growth_dcf",    "model_disp": "两段式EPS-DCF",     "why_type": "盈利稳定增长·EPS≈可分配现金"},
    "控股公司": {"model": "nav",           "model_disp": "净资产法(NAV)",     "why_type": "价值=手里一堆资产"},
    "周期股":   {"model": "mid_cycle",     "model_disp": "中周期盈利法(不用峰值)", "why_type": "盈利大起大落(半导体设备/存储/代工/汽车等)"},
    "保险":     {"model": "pbv",           "model_disp": "PB/内含价值法",     "why_type": "利润≠可分配现金"},
    "综合商社": {"model": "nav",           "model_disp": "NAV/PB(按主业·商社偏资产→NAV)", "why_type": "多业务持股·按主业归类"},
    "券商":     {"model": "normalized_pe", "model_disp": "正常化PE",          "why_type": "证券/交易所·盈利随市况波动·用正常化盈利"},
    "资产":     {"model": "asset_none",    "model_disp": "不做企业估值(仓位纪律)", "why_type": "无财报的资产·只按仓位纪律+币价管"},
}

# 关键词规则(兜底·按生意模式非死名单)：命中词 → 类型。顺序=优先级。
_KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    (("保险", "海上", "insurance", "assurance"), "保险"),
    (("软银", "softbank", "控股", "holding", "holdings", "投资公司"), "控股公司"),
    (("商社", "伊藤忠", "三菱商事", "三井物产", "丸红", "trading", "itochu"), "综合商社"),
    (("证券", "券商", "交易所", "exchange", "brokers", "interactive", "ibkr",
      "coinbase", "coin", "circle", "crcl", "银行", "bank"), "券商"),
    (("存储", "闪迪", "sandisk", "sndk", "美光", "micron", "海力士", "hynix", "内存", "dram", "nand", "hbm",
      "半导体设备", "设备", "东京电子", "tokyo electron", "爱德万", "advantest", "应用材料", "asml", "lam",
      "代工", "foundry", "台积", "tsmc", "tsm", "晶圆",
      "汽车", "丰田", "toyota", "本田", "整车"), "周期股"),
]


def _load_table() -> dict[str, Any]:
    p = ROOT / "data" / "valuation" / "security_types.json"
    if not p.exists():
        return {}
    try:
        return (json.loads(p.read_text(encoding="utf-8")) or {}).get("securities", {}) or {}
    except Exception:
        return {}


def classify(symbol: Any, name: Any = "") -> dict[str, str]:
    """把标的归类→自动选模型。返回 {type,type_reason,model,model_disp,source}。"""
    sym = str(symbol or "")
    nm = str(name or "")
    # ① 加密/无财报资产
    if sym.upper().startswith("CC."):
        tm = TYPE_MODEL["资产"]
        return {"type": "资产", "type_reason": tm["why_type"], "model": tm["model"],
                "model_disp": tm["model_disp"], "source": "规则·加密无财报"}
    # ② 登记表(行业事实·可迭代)
    table = _load_table()
    rec = table.get(sym) or table.get(sym.split(".")[-1]) or table.get(nm)
    if rec and rec.get("type") in TYPE_MODEL:
        t = rec["type"]; tm = TYPE_MODEL[t]
        return {"type": t, "type_reason": rec.get("why") or tm["why_type"], "model": tm["model"],
                "model_disp": tm["model_disp"], "source": "登记表(行业事实)"}
    # ③ 关键词规则兜底
    hay = (sym + " " + nm).lower()
    for words, t in _KEYWORD_RULES:
        if any(w.lower() in hay for w in words):
            tm = TYPE_MODEL[t]
            return {"type": t, "type_reason": tm["why_type"], "model": tm["model"],
                    "model_disp": tm["model_disp"], "source": "关键词规则"}
    # ④ 默认成长股(不静默·标请核)
    tm = TYPE_MODEL["成长股"]
    return {"type": "成长股", "type_reason": tm["why_type"], "model": tm["model"],
            "model_disp": tm["model_disp"], "source": "默认分类·请核类型"}


# 各模型所需真财务输入(供"待接"提示与卡片说明)
MODEL_INPUTS: dict[str, str] = {
    "growth_dcf": "forward EPS + 增长/年限/永续/折现",
    "nav": "各资产真估值合计 − 净负债 ÷ 股本(±控股折价)",
    "mid_cycle": "正常年景EPS×中周期PE，或 中周期EBITDA×EV/EBITDA",
    "pbv": "每股净资产×目标PB，或 内含价值/股×倍数",
    "normalized_pe": "正常化EPS × 正常化PE",
    "asset_none": "(不适用·按仓位纪律≤12%+币价管)",
}
