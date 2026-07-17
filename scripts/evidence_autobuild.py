from __future__ import annotations

"""第一块 · 求证表自生成器（规则引擎·行情驱动）

机器读当日行情（latest_market_snapshot / yield_curve / sector_flow），按写死的
可审计规则自评各环力度，自动拼 derived(方向/口径/约束)，写 data/evidence_chain/
daily_{date}.json（字段对齐现结构，让 production_pipeline / full_product_render 不改就能读）。

边界（派工单）：本块只做"行情能算的环"。经济日历(非农/CPI)+新闻源=第二块；
缺数据的环如实标"待第二块/待定"，不硬推、不编（总则第十三条二）。
"""

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ── 写死·可审计的规则阈值（可在此常量表调参，不散落在逻辑里）─────────────
RULES = {
    # 总闸·美联储：US10Y 较昨(change_percent)变动
    "US10Y_EASE_PCT": -0.15,   # 降>0.15% → 边际松
    "US10Y_TIGHT_PCT": 0.15,   # 升>0.15% → 偏紧
    # 资金轮动：VIX 较昨(change_percent)
    "VIX_SPIKE_PCT": 5.0,      # 升>5% → 避险
    # 板块轮动：SOXX 较昨(change_percent)
    "SOXX_STRONG_PCT": 1.0,    # 涨>1% → 走强
    "SOXX_WEAK_PCT": -1.0,     # 跌>1% → 走弱
}

# 标准 AI 承接节点（写进 today_direction，供 production_pipeline 激活筛选）
ACTIVE_NODES = ["算力", "半导体设备", "代工", "存储", "盟友链"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "待定"


# ── 输入装载（缺文件→返回 None，由各环如实标"待定/待第二块"）──────────────

def load_snapshot() -> dict[str, Any] | None:
    path = ROOT / "data" / "market" / "latest_market_snapshot.json"
    if not path.exists():
        return None
    data = read_json(path)
    by_symbol = {}
    for asset in data.get("assets", []):
        by_symbol[str(asset.get("symbol"))] = asset
    return {"raw": data, "by_symbol": by_symbol, "file": path.name}


def load_dated(subdir: str, prefix: str, date: str) -> dict[str, Any] | None:
    """读 {prefix}_{date}.json；当日缺→回退到最近可得的一份，如实标注非当日。"""
    folder = ROOT / "data" / subdir
    exact = folder / f"{prefix}_{date}.json"
    if exact.exists():
        data = read_json(exact)
        return {"data": data, "file": exact.name, "is_today": True, "used_date": date}
    candidates = sorted(folder.glob(f"{prefix}_*.json"))
    if not candidates:
        return None
    latest = candidates[-1]
    used = latest.stem.replace(f"{prefix}_", "")
    data = read_json(latest)
    return {"data": data, "file": latest.name, "is_today": False, "used_date": used}


# ── 规则引擎：每环一个判定函数，返回对齐现结构的 link 字典 ──────────────────

def rule_world(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """总命题·世界观：行情层不判 regime 级反转，读上一状态、待第二块。"""
    return {
        "node": "总命题·世界是否真变",
        "evidence": "【待第二块】世界观级(三支柱是否 regime 反转)需宏观/新闻判断，行情层不硬推；"
                    "默认读上一状态：三支柱(美国优先·阵营化·AI国力)维持、无级别反转。",
        "strength": "中",
        "direction": "待第二块(读上一状态·变)",
        "plain": "今天没有会掀翻世界大格局（美国优先·阵营化·AI国力）的大事 → 对你：投资的大方向不变，照现有框架走。",
        "today_events": ["行情驱动块不判世界观级反转 → 待第二块(新闻/宏观事件源)"],
        "background": ["三支柱框架延续(上一状态)"],
        "source": "规则引擎·本块不含世界观判据(待第二块)",
    }


def rule_fed(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """总闸·美联储：US10Y 较昨变动。无当日Fed/非农事件→读行情边际，宏观事件待第二块。"""
    if not snapshot or "US10Y" not in snapshot["by_symbol"]:
        return {
            "node": "总闸·美联储是否美国优先",
            "evidence": "【数据缺】latest_market_snapshot 无 US10Y → 力度待定、不硬推(总则十三条二)。",
            "strength": "待定",
            "direction": "待定",
            "plain": "今天没拿到美国国债利率的新数据 → 对你：总闸这层沿用上次判断，不瞎猜、不动仓。",
            "today_events": ["US10Y 数据缺 → 待定"],
            "background": ["宏观事件(Fed/非农)源=待第二块"],
            "source": "latest_market_snapshot.json(缺 US10Y)",
        }
    a = snapshot["by_symbol"]["US10Y"]
    chg = a.get("change_percent")
    val = a.get("close", a.get("price"))
    chg_f = float(chg) if isinstance(chg, (int, float)) else None
    if chg_f is None:
        state, strength, direction = "维持(变动缺)", "待定", "待定"
    elif chg_f <= RULES["US10Y_EASE_PCT"]:
        state, strength, direction = "边际松", "中", "松·美国优先未证伪"
    elif chg_f >= RULES["US10Y_TIGHT_PCT"]:
        state, strength, direction = "偏紧", "弱", "偏紧·收水"
    else:
        state, strength, direction = "维持", "中", "维持"
    evidence = (
        f"【行情·主】US10Y={val}、较昨{fmt_pct(chg)}"
        f"（阈值±{RULES['US10Y_TIGHT_PCT']}%）→ 规则判「{state}」。"
        "【诚实】今日无新 Fed/非农事件判据(宏观事件源=第二块)，此处只读行情边际、不假装宏观。"
    )
    if state == "偏紧":
        plain = f"美国国债利率今天涨了一点（到 {val}%），市场觉得钱还要收着、不会放水 → 对你：别等放水行情，守核心、不追高。"
    elif state == "边际松":
        plain = f"美国国债利率今天降了点（到 {val}%），钱有一点点松的苗头、但还没到大放水 → 对你：环境略友好，仍守核心、别激进。"
    elif state == "维持":
        plain = f"美国国债利率今天基本没动（{val}%），钱的松紧维持原样 → 对你：按原计划守，不因总闸调仓。"
    else:
        plain = f"美国国债利率今天读数不全（{val}%）→ 对你：总闸这层沿用上次判断，不瞎猜。"
    return {
        "node": "总闸·美联储是否美国优先",
        "evidence": evidence,
        "strength": strength,
        "direction": direction,
        "plain": plain,
        "today_events": [
            f"行情：US10Y={val}、较昨{fmt_pct(chg)} → 规则判「{state}」",
            "宏观事件(Fed议息/非农)=待第二块，本块不判",
        ],
        "background": [f"data_date={a.get('data_date')}"],
        "source": f"latest_market_snapshot.json·US10Y.change_percent={fmt_pct(chg)}",
        "_state": state,
    }


def rule_strategy(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """战略·AI：行情无法直接判产业面→默认读上一状态'中'、标待新闻(第二块)。"""
    return {
        "node": "战略指向·AI/安全/能源",
        "evidence": "【诚实】产业面(AI基建需求/龙头盈利预期/政策)行情层无法直接判 → "
                    "默认读上一状态「中」，产业面新闻=待第二块，不假装。",
        "strength": "中",
        "direction": "AI(待产业面新闻·第二块)",
        "plain": "今天没接到 AI 产业的新消息，沿用上次判断「AI 主线仍在」→ 对你：核心仓照守，不因今天没新闻就动。",
        "today_events": ["产业面新闻(AI/半导体/政策) = 待第二块，本块不判"],
        "background": ["上一状态：AI 国力主线仍强(读上一状态)"],
        "source": "规则引擎·本块不含产业面新闻判据(待第二块)",
    }


def rule_means(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """手段层·FIMA/稳定币/加密：数值待机械层+新闻源，行情层不判力度。"""
    bg = ["FIMA/稳定币数值=待机械层+第二块"]
    if snapshot:
        parts = []
        for sym in ("IBIT", "BITQ"):
            a = snapshot["by_symbol"].get(sym)
            if a:
                parts.append(f"{sym} 较昨{fmt_pct(a.get('change_percent'))}")
        if parts:
            bg.append("行情佐证(非判据)：" + "、".join(parts))
    return {
        "node": "手段层·FIMA/稳定币/加密",
        "evidence": "【待第二块】手段层力度需稳定币/FIMA 数值(机械层)+新闻，行情层不硬推力度。",
        "strength": "待定",
        "direction": "待第二块",
        "plain": "今天这层（稳定币/加密这条「钱进美元」的管道）没有新数据/新闻，沿用上次判断 → 对你：不影响今天动作。",
        "today_events": ["手段层判据(稳定币/FIMA) = 待第二块，本块不判"],
        "background": bg,
        "source": "规则引擎·本块不含手段层判据(待第二块)",
    }


def rule_capital(snapshot: dict[str, Any] | None, curve: dict[str, Any] | None) -> dict[str, Any]:
    """资金轮动：VIX + 曲线是否倒挂。VIX↓且曲线不倒挂→不避险·中；VIX↑>5%或倒挂→避险·弱。"""
    vix = snapshot["by_symbol"].get("^VIX") if snapshot else None
    if vix is None and curve is None:
        return {
            "node": "资金轮动",
            "evidence": "【数据缺】VIX 与收益率曲线均缺 → 力度待定、不硬推。",
            "strength": "待定", "direction": "待定",
            "plain": "今天没拿到市场情绪(VIX)和利率曲线的新数据 → 对你：这层沿用上次判断，不动仓。",
            "today_events": ["VIX/曲线数据缺 → 待定"],
            "background": [], "source": "缺 VIX + yield_curve",
        }
    vix_chg = vix.get("change_percent") if vix else None
    vix_chg_f = float(vix_chg) if isinstance(vix_chg, (int, float)) else None
    inverted = None
    curve_note = "曲线数据缺"
    curve_src = "yield_curve 缺"
    if curve:
        inverted = bool(curve["data"].get("inverted"))
        # 口径统一：优先真2年美债(10Y-2Y·FRED DGS2/Yahoo备源)，与宏观表一致；无2年才退回3月^IRX
        spread_2y = curve["data"].get("spread_10y_2y")
        if spread_2y is not None:
            curve_note = f"曲线{'倒挂' if inverted else '未倒挂'}(10Y-2Y={spread_2y})"
        else:
            spread = curve["data"].get("spread_10y_3m")
            curve_note = f"曲线{'倒挂' if inverted else '未倒挂'}(10Y-3M={spread}·2年待接)"
        curve_src = curve["file"] + ("" if curve["is_today"] else f"(最近可得 {curve['used_date']}·非当日)")

    spike = vix_chg_f is not None and vix_chg_f > RULES["VIX_SPIKE_PCT"]
    if spike or inverted:
        strength, direction, state = "弱", "避险", "避险"
    elif vix_chg_f is not None and vix_chg_f <= 0 and inverted is False:
        strength, direction, state = "中", "不避险·钱没撤离风险资产", "不避险"
    elif inverted is None or vix_chg_f is None:
        strength, direction, state = "待定", "部分数据缺·待定", "待定"
    else:
        strength, direction, state = "中", "中性", "中性"
    vix_txt = f"VIX 较昨{fmt_pct(vix_chg)}" if vix else "VIX 缺"
    vix_move = "降了" if (vix_chg_f is not None and vix_chg_f <= 0) else "升了"
    if state == "不避险":
        plain = f"市场恐慌指标(VIX)今天{vix_move}({fmt_pct(vix_chg)})、利率曲线也没倒挂，大家没在逃跑、钱还留在股市 → 对你：不用慌着减仓。"
    elif state == "避险":
        plain = f"市场今天在往避风港躲（VIX 蹿高 {fmt_pct(vix_chg)} 或利率曲线倒挂）→ 对你：降点风险、多留现金垫。"
    elif state == "中性":
        plain = f"市场情绪今天不温不火（VIX {fmt_pct(vix_chg)}）→ 对你：按原计划，不因情绪调仓。"
    else:
        plain = "今天市场情绪/曲线数据不全 → 对你：这层沿用上次判断。"
    # ══ 乙[层间阻尼]：资金层同理——2~3读数(VIX/曲线/高收益利差)，翻状态需连2日或超2倍阈值 ══
    _rd = [{"name": "VIX", "value": vix_chg_f, "threshold": RULES["VIX_SPIKE_PCT"]},
           {"name": "曲线", "value": (1.0 if inverted else 0.0) if inverted is not None else None,
            "threshold": 1.0}]
    _hy = (snapshot or {}).get("by_symbol", {}).get("HYG") if snapshot else None
    if _hy and isinstance(_hy.get("change_percent"), (int, float)):
        _rd.append({"name": "高收益利差(HYG)", "value": float(_hy["change_percent"]), "threshold": 1.0})
    else:
        _rd.append({"name": "高收益利差", "value": None, "threshold": None})   # 缺→标待接·不编
    d = _damp("资金轮动", state, [r for r in _rd if r.get("value") is not None], _DATE[0])
    if d.get("damped"):
        state = d["state"]
        strength, direction = {"避险": ("弱", "避险"), "不避险": ("中", "不避险·钱没撤离风险资产"),
                               "中性": ("中", "中性")}.get(state, ("中", state))
        plain = (f"市场情绪今天的读数（{vix_txt}、{curve_note}）按老规矩会翻成「{d['raw_state']}」；"
                 f"但只动了这一天、也没到两倍幅度 → <b>先不翻</b>，维持「{state}」（治天天变卦）。")
    return {
        "node": "资金轮动",
        "evidence": (f"【行情·主】{vix_txt}、{curve_note}（阈值 VIX>+{RULES['VIX_SPIKE_PCT']}%或倒挂→避险）"
                     f"→ 规则判「{state}」。【阻尼】{d.get('why','')}"),
        "strength": strength,
        "direction": direction,
        "plain": plain,
        "today_events": [f"行情：{vix_txt}、{curve_note} → 规则判「{state}」"],
        "background": [f"VIX data_date={vix.get('data_date') if vix else '缺'}",
                       f"层间阻尼：{d.get('rule') or '不涉及翻转'}",
                       "读数：VIX + 曲线" + ("+ 高收益利差(HYG)" if _hy else " + 高收益利差<待接·无HYG真源·不编>")],
        "source": f"latest_market_snapshot.json·^VIX + {curve_src}",
        "_state": state,
        "_damping": d,
    }


def rule_sector(snapshot: dict[str, Any] | None, sector: dict[str, Any] | None) -> dict[str, Any]:
    """板块轮动：SOXX 当日涨>1%→走强；跌>1%→走弱；否则中性。"""
    soxx = snapshot["by_symbol"].get("SOXX") if snapshot else None
    if soxx is None:
        return {
            "node": "板块轮动",
            "evidence": "【数据缺】snapshot 无 SOXX → 力度待定、不硬推。",
            "strength": "待定", "direction": "待定",
            "plain": "今天没拿到半导体板块(SOXX)的新数据 → 对你：这层沿用上次判断，不动仓。",
            "today_events": ["SOXX 数据缺 → 待定"],
            "background": [], "source": "缺 SOXX",
        }
    chg = soxx.get("change_percent")
    chg_f = float(chg) if isinstance(chg, (int, float)) else None
    if chg_f is None:
        strength, direction, state = "待定", "待定", "待定"
    elif chg_f > RULES["SOXX_STRONG_PCT"]:
        strength, direction, state = "强", "半导体走强·资金回流", "走强"
    elif chg_f < RULES["SOXX_WEAK_PCT"]:
        strength, direction, state = "弱", "半导体走弱", "走弱"
    else:
        strength, direction, state = "中", "中性", "中性"
    bg = ["板块各承接节点结构化个股级拉数 = 待建"]
    src = f"latest_market_snapshot.json·SOXX.change_percent={fmt_pct(chg)}"
    if sector:
        src += f" (+ {sector['file']}" + ("" if sector["is_today"] else f"·最近可得 {sector['used_date']}·非当日") + ")"
    if state == "走弱":
        plain = f"半导体板块今天跌了点（SOXX {fmt_pct(chg)}）、资金在流出 → 对你：AI 硬件短期偏弱，别这时候追高加仓。"
    elif state == "走强":
        plain = f"半导体板块今天涨了（SOXX {fmt_pct(chg)}）、资金在回流 → 对你：AI 硬件短期有劲，核心仓可安心守。"
    elif state == "中性":
        plain = f"半导体板块今天涨跌不大（SOXX {fmt_pct(chg)}）→ 对你：AI 硬件没明显方向，守着看、不追。"
    else:
        plain = "今天半导体板块读数不全 → 对你：这层沿用上次判断。"
    # ══ 乙[层间阻尼·董事长2026-07-17拍板]：翻状态需【连续2日同向】或【超2倍阈值】，否则维持上一状态 ══
    #   治的就是"SOXX 今天±1%就翻、明天又翻回来"的天天变卦。
    d = _damp("板块轮动", state, [{"name": "SOXX", "value": chg, "threshold": RULES["SOXX_STRONG_PCT"]}], _DATE[0])
    if d.get("damped"):
        state = d["state"]
        strength, direction = _sector_words(state)
        plain = (f"半导体板块今天读数是 SOXX {fmt_pct(chg)}，按老规矩会翻成「{d['raw_state']}」；"
                 f"但只动了这一天、也没到两倍幅度 → <b>先不翻</b>，维持「{state}」。"
                 f"要么明天还这样、要么动静再大一倍才算数（治天天变卦）。")
    return {
        "node": "板块轮动",
        "evidence": (f"【行情·主】SOXX 较昨{fmt_pct(chg)}（阈值±{RULES['SOXX_STRONG_PCT']}%）→ 规则判「{state}」。"
                     + f"【阻尼】{d.get('why','')}"),
        "strength": strength,
        "direction": direction,
        "plain": plain,
        "today_events": [f"行情：SOXX 较昨{fmt_pct(chg)} → 规则判「{state}」"],
        "background": bg + [f"层间阻尼：{d.get('rule') or '不涉及翻转'}"],
        "source": src,
        "_state": state,
        "_damping": d,
    }


def _sector_words(state: str) -> tuple:
    return {"走强": ("强", "半导体走强·资金回流"), "走弱": ("弱", "半导体走弱"),
            "中性": ("中", "中性")}.get(state, ("中", state))


_DATE = [""]          # build 起手写入当日日期，供阻尼器往回读历史
_DAMP_LOG: dict = {}


def _damp(layer: str, state: str, readings: list, date: str) -> dict:
    try:
        from layer_damping import damp
        r = damp(layer, state, readings, date)
    except Exception as e:
        r = {"state": state, "flipped": False, "damped": False, "why": f"阻尼器不可用({e})→按裸状态", "rule": ""}
    _DAMP_LOG[layer] = r
    return r


# ── derived 三字段自动拼（各环力度→方向/口径/约束）─────────────────────────

def build_derived(fed: dict, strategy: dict, capital: dict, sector: dict, macro_news_on: bool = False) -> dict[str, str]:
    fed_s = fed.get("strength")
    fed_state = fed.get("_state", fed.get("direction"))
    cap_state = capital.get("_state", capital.get("direction"))
    sec_state = sector.get("_state", sector.get("direction"))
    # 战略环力度：接了第二块(新闻)就读真评，否则读上一状态"中·待第二块"
    strat_s = strategy.get("strength", "中")
    strat_state = strategy.get("_state", "维持" if not macro_news_on else str(strategy.get("direction", "维持")))

    # today_direction：各环力度 + 激活节点
    today_direction = (
        f"总闸(美联储)「{fed_state}·{fed_s}」({_short(fed)})；"
        f"战略AI「{strat_state}·{strat_s}」({_short(strategy)})；"
        f"资金「{cap_state}·{capital.get('strength')}」({_short(capital)})；"
        f"板块半导体「{sec_state}·{sector.get('strength')}」({_short(sector)})。"
    )
    if fed_s == "弱":
        today_direction += "今天整体：总闸偏紧转弱→守核心、机会口径收口、不追高、控AI集中。"
        action_short = "守核心、别追高、控AI集中、机会口径收口"
    elif fed_s == "待定":
        today_direction += "今天整体：总闸数据待定→保守读上一状态、不放宽。"
        action_short = "按上一状态保守、不放宽"
    else:
        today_direction += "今天整体：总闸中档→守核心、不追高、控AI集中。"
        action_short = "守核心、不追高、控AI集中"
    # 结尾不加句号：避免渲染层再接"；"时出现"。；"标点错(治#20)
    today_direction += "激活承接节点：" + "、".join(ACTIVE_NODES)

    # 短版"一句话方向"：页头用它当主句，长版折叠(治#21 超长run-on)
    today_direction_short = f"今天：总闸{fed_state}、板块半导体{sec_state}→{action_short}"

    # opportunity_scope：随总闸力度自动收口/切备用
    node_txt = "AI承接节点(" + "/".join(ACTIVE_NODES) + ")"
    if fed_s == "弱":
        opportunity_scope = f"总闸偏紧转弱→机会口径【自动收口】：只在{node_txt}内严筛，不放宽口径、不切普通AI牛市备用逻辑。"
    elif fed_s == "证伪":
        opportunity_scope = f"总闸证伪→【切备用逻辑】：暂停主线口径，只保防御/非AI分散，等总闸修复。"
    elif fed_s == "待定":
        opportunity_scope = f"总闸数据待定→口径按上一状态保守，只在{node_txt}内筛、不放宽；宏观事件待第二块。"
    else:
        opportunity_scope = f"总闸中档→只在{node_txt}内筛，口径不放宽、不切备用逻辑。"

    # decision_constraint：板块+资金力度拼约束
    parts = ["不追高、控AI集中。"]
    if sector.get("strength") == "弱":
        parts.append(f"板块半导体今日走弱({_short(sector)})→承接节点内偏谨慎、不追强势股。")
    elif sector.get("strength") == "强":
        parts.append(f"板块半导体今日走强({_short(sector)})→主线资金回流、可在节点内正常筛。")
    if capital.get("strength") == "弱":
        parts.append(f"资金转避险({_short(capital)})→降风险暴露、抬现金垫。")
    if macro_news_on and strat_s == "弱":
        parts.append(f"战略产业面转弱({_short(strategy)})→AI主线降注意力、盯下修风险。")
    elif macro_news_on and strat_s == "强":
        parts.append(f"战略产业面走强({_short(strategy)})→AI主线支撑、节点内正常筛。")
    tail = "个股级持仓上限/减仓名单=其它模块，本表只给行情+新闻驱动的方向与口径。" if macro_news_on \
        else "个股级持仓上限/减仓名单=其它模块，本表只给行情驱动的方向与口径；宏观事件(非农/CPI)+新闻面=待第二块。"
    parts.append(tail)
    decision_constraint = "".join(parts)

    # 甲4：当日派生状态词全部在此定稿·全册只许引用这里的取值(出厂lint校验"同一状态词全文唯一")
    return {
        "today_direction": today_direction,
        "today_direction_short": today_direction_short,
        "opportunity_scope": opportunity_scope,
        "decision_constraint": decision_constraint,
        # 状态词唯一取值区(渲染层只读不改)
        "state_words": {
            "fed_gate": fed_state,            # 总闸档
            "fed_strength": fed_s,            # 总闸力度
            "sector": sec_state,              # 板块方向
            "strategy": strat_state,          # 战略方向
            "capital": cap_state,             # 资金方向
            "opportunity_scope": opportunity_scope,   # 机会口径·全篇唯一
        },
    }


def _short(link: dict) -> str:
    """从 today_events 抽第一条'行情：...'做简短指纹。"""
    for ev in link.get("today_events", []):
        if ev.startswith("行情"):
            return ev.split("→")[0].replace("行情：", "").strip()
    return link.get("strength", "")


def macro_cal_from_report(mr: dict | None) -> dict:
    """从 macro_news 富集报告里取宏观日历(含FEDFUNDS)·缺→空(→无Fed事件·沿用/基线)。"""
    if not mr:
        return {}
    return (mr.get("fetched", {}) or {}).get("macro_calendar", {}) or {}


def fed_gate_state_machine(date: str, macro_cal: dict, us10y_val, us10y_chg) -> dict[str, Any]:
    """R2 总闸状态机(事件驱动)：Fed事件=FEDFUNDS变动(决议/加降息)。无事件→沿用上一状态+第N天。
    US10Y/VIX 只作边际注脚·绝不翻闸。同日重跑幂等(不重复+第N天)。治 B2 单日噪声翻面。"""
    import json as _json
    from pathlib import Path as _P
    sp = ROOT / "data" / "evidence_chain" / "fed_gate_state.json"
    prev = None
    if sp.exists():
        try:
            prev = _json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            prev = None
    ff = (macro_cal or {}).get("FedFunds") or (macro_cal or {}).get("FEDFUNDS") or {}
    v, pv = ff.get("value"), ff.get("prev")
    fed_event = (v is not None and pv is not None and float(v) != float(pv))
    footnote = f"边际注脚(仅参考·不翻闸)：US10Y={us10y_val}、较昨{fmt_pct(us10y_chg)}"
    if prev and prev.get("date") == date:                 # 同日重跑→幂等(不改状态、不+天)
        st = dict(prev); st["footnote"] = footnote; st["fed_event_today"] = fed_event
        return st
    if fed_event:                                          # 有Fed决议事件→重定状态
        if float(v) > float(pv):
            state, strength, direction = "偏紧·加息", "中", "偏紧·收水(加息事件)"
        else:
            state, strength, direction = "偏松·降息", "中", "偏松(降息事件)"
        day_n, last_event = 1, ff.get("date")
    elif prev:                                             # 无事件→沿用昨日状态+第N天
        state, strength, direction = prev["state"], prev["strength"], prev["direction"]
        day_n, last_event = int(prev.get("day_n", 1)) + 1, prev.get("last_event")
    else:                                                  # 首次·无事件·无prev→基线
        state, strength, direction = "维持·观察", "中", "总闸维持(无新Fed事件·基线)"
        day_n, last_event = 1, ff.get("date")
    st = {"date": date, "state": state, "strength": strength, "direction": direction,
          "day_n": day_n, "last_event": last_event, "fed_funds": v, "fed_event_today": fed_event,
          "footnote": footnote}
    try:
        sp.write_text(_json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return st


def build(date: str, with_macro_news: bool = False) -> dict[str, Any]:
    _DATE[0] = date                      # 乙[层间阻尼]：供阻尼器往回读该层的真实历史状态
    _DAMP_LOG.clear()
    snapshot = load_snapshot()
    curve = load_dated("market", "yield_curve", date)
    sector = load_dated("sector", "sector_flow", date)

    fed = rule_fed(snapshot)
    strategy = rule_strategy(snapshot)
    capital = rule_capital(snapshot, curve)
    sector_link = rule_sector(snapshot, sector)
    links = [
        rule_world(snapshot),
        fed,
        strategy,
        rule_means(snapshot),
        capital,
        sector_link,
    ]

    # 第二块：宏观事件+新闻源(macro_news_intake) 把"待第二块"三环变机器自动评
    macro_report = None
    if with_macro_news:
        import macro_news_intake  # 同目录
        links, macro_report = macro_news_intake.enrich_links(links, date)
        # enrich 后重取被更新的环，供 derived 读真评
        strategy = next((L for L in links if "战略指向" in str(L.get("node"))), strategy)
        fed = next((L for L in links if "总闸" in str(L.get("node"))), fed)

    # R2：用事件驱动状态机【覆盖】总闸(不再由US10Y日波动定状态)。US10Y=注脚。
    _us = (snapshot or {}).get("by_symbol", {}).get("US10Y", {}) if snapshot else {}
    _sm = fed_gate_state_machine(date, macro_cal_from_report(macro_report), _us.get("close", _us.get("price")), _us.get("change_percent"))
    _day_tag = f"（事件日）" if _sm.get("fed_event_today") else f"（无新Fed事件·沿用第{_sm.get('day_n')}天）"
    fed["strength"] = _sm["strength"]
    fed["direction"] = _sm["direction"]
    fed["_state"] = _sm["state"]
    fed["evidence"] = (f"【状态机·事件驱动】总闸={_sm['state']}{_day_tag}·据美联储事件(FEDFUNDS/决议)"
                       f"，非单日行情噪声(治B2)。{_sm['footnote']}。上次事件={_sm.get('last_event')}")
    fed["plain"] = (f"美联储姿态今天{_sm['state']}{_day_tag}——按'有Fed事件才翻、没事件就沿用'判，"
                    f"不被国债利率一天涨跌牵着走 → 对你：总闸维持，不因单日行情调仓。")
    fed["today_events"] = [f"总闸状态机={_sm['state']}{_day_tag}", _sm["footnote"]]
    for L in links:
        if "总闸" in str(L.get("node")):
            L.update({"strength": fed["strength"], "direction": fed["direction"], "_state": fed["_state"],
                      "evidence": fed["evidence"], "plain": fed["plain"], "today_events": fed["today_events"]})

    derived = build_derived(fed, strategy, capital, sector_link, macro_news_on=with_macro_news)

    # 剥掉内部辅助字段 _state（不落盘）
    clean_links = [{k: v for k, v in link.items() if not k.startswith("_")} for link in links]

    inputs_used = {
        "latest_market_snapshot": snapshot["file"] if snapshot else "缺",
        "snapshot_data_date": snapshot["raw"].get("generated_at") if snapshot else None,
        "yield_curve": (curve["file"] + ("" if curve["is_today"] else f"·非当日({curve['used_date']})")) if curve else "缺",
        "sector_flow": (sector["file"] + ("" if sector["is_today"] else f"·非当日({sector['used_date']})")) if sector else "缺",
    }

    note = "行情驱动的自动求证表：力度按写死规则从当日行情算出(可回溯到文件/字段)。"
    if with_macro_news:
        note += "已接第二块(宏观事件+新闻源)：三环由机器读真新闻/宏观自动评，抓不到的如实标'待接真源'、读上一状态。"
    else:
        note += "经济日历(非农/CPI)+新闻源=第二块，缺的环如实标'待第二块/待定'、不硬推。"

    rule_engine = {"thresholds": RULES, "inputs_used": inputs_used}
    if macro_report is not None:
        rule_engine["macro_news"] = macro_report
    # 乙[层间阻尼]：落台账(每层裸状态/读数/是否真翻/为什么)——可回溯、可复核
    if _DAMP_LOG:
        try:
            from layer_damping import log as _damp_log
            _damp_log(date, _DAMP_LOG)
        except Exception:
            pass
        rule_engine["layer_damping"] = {
            "_说明": "翻状态需【连续2日同向】或【超2倍阈值】，否则维持上一状态(治单日噪声天天翻)。"
                     "董事长2026-07-17拍板采纳。",
            "layers": {k: {"state": v.get("state"), "raw_state": v.get("raw_state"),
                           "damped": v.get("damped"), "rule": v.get("rule")}
                       for k, v in _DAMP_LOG.items()}}

    return {
        "date": date,
        "source": "机器自生成·evidence_autobuild.py·规则引擎"
                  + ("+第二块(宏观新闻源)" if with_macro_news else ""),
        "data_date_note": note,
        "rule_engine": rule_engine,
        "derived": derived,
        "links": clean_links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="第一块·求证表自生成器(规则引擎·行情驱动)")
    parser.add_argument("--date", default="20260711")
    parser.add_argument("--with-macro-news", action="store_true",
                        help="接第二块：抓当日宏观事件+主题新闻，把待第二块三环变机器自动评")
    args = parser.parse_args()

    result = build(args.date, with_macro_news=args.with_macro_news)
    out_path = ROOT / "data" / "evidence_chain" / f"daily_{args.date}.json"
    write_json(out_path, result)
    print(f"[OK] 写出 {out_path}")
    d = result["derived"]
    print("today_direction:", d["today_direction"])
    print("opportunity_scope:", d["opportunity_scope"])
    print("decision_constraint:", d["decision_constraint"])
    if result["rule_engine"].get("macro_news"):
        print("macro_news:", json.dumps(result["rule_engine"]["macro_news"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
