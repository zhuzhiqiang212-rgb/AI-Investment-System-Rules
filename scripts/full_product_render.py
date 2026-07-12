from __future__ import annotations

import argparse
import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

try:
    from judgment_worldview_render import judgment_card
except Exception:  # 判断包消费方缺失时不破坏既有产品
    def judgment_card(date: str) -> str:  # type: ignore[misc]
        return ""

try:
    from stock_research_render import stock_research_card, stock_research_section, has_pack
except Exception:  # 个股研究消费方缺失时不破坏既有产品
    def has_pack(symbol: Any, name: Any) -> bool:  # type: ignore[misc]
        return False

    def stock_research_card(symbol: Any, name: Any) -> str:  # type: ignore[misc]
        return ""

    def stock_research_section(holdings: Any) -> str:  # type: ignore[misc]
        return ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def fmt_summary(value: Any) -> str:
    if isinstance(value, dict):
        return "、".join(f"{esc(k)}{esc(v)}" for k, v in value.items())
    return esc(value)


def find_link(daily: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    for link in daily.get("links", []):
        node = str(link.get("node", ""))
        if any(keyword in node for keyword in keywords):
            return link
    return {"node": "待填", "strength": "待填", "direction": "待填", "evidence": "待接入"}


def event_list(items: Any) -> str:
    if not items:
        return "<li>今日新事件待接入</li>"
    return "".join(f"<li>{esc(item)}</li>" for item in items)


def decision_badge(strength: Any) -> tuple[str, str, str]:
    if strength in ("强", "中"):
        return "支持", "#3ec38a", "🟢"
    if strength == "弱":
        return "转弱预警", "#ffd479", "🟡"
    if strength == "证伪":
        return "证伪·切备用逻辑", "#f0616d", "🔴"
    return "待填", "#9aa8b5", ""


def first_internal_event(link: dict[str, Any]) -> str:
    internal_events = link.get("internal_events")
    if isinstance(internal_events, list) and internal_events:
        return str(internal_events[0])
    return "今日无我持仓相关新事件"


def has_items(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def evidence_sufficient(link: dict[str, Any]) -> bool:
    if link.get("evidence_status") in ("不够", "待接入", "待补", "证据不足"):
        return False
    today_events = link.get("today_events")
    if today_events is None:
        external_events = link.get("external_events")
        internal_events = link.get("internal_events")
        has_event_support = has_items(external_events) or has_items(internal_events)
        if not has_event_support:
            return False
    else:
        has_event_support = has_items(today_events)
        if not has_event_support:
            return False
    evidence_text = str(link.get("evidence") or "")
    if not evidence_text:
        return False
    if any(token in evidence_text for token in ("待接入", "待补", "无证据", "无新证据")):
        return False
    if "今日无" in evidence_text and not has_event_support:
        return False
    return True


def evidence_event_sections(link: dict[str, Any]) -> str:
    if "today_events" in link or "background" in link:
        sections = f"""
        <section>
          <h3>今日事件</h3>
          <ul>{event_list(link.get('today_events'))}</ul>
        </section>
        <section>
          <h3>背景</h3>
          <ul>{event_list(link.get('background'))}</ul>
        </section>
        """
    else:
        sections = f"""
        <section>
          <h3>外部(大环境今日事件)</h3>
          <ul>{event_list(link.get('external_events'))}</ul>
        </section>
        <section>
          <h3>内部(我持仓相关今日事件)</h3>
          <ul>{event_list(link.get('internal_events'))}</ul>
        </section>
        """
    return f'<div class="event-grid">{sections}</div>'


def unify_strength_words(text: Any) -> str:
    """强弱标签统一一套词(治#27)：把「状态·力度」中的力度 强/中/弱、及独立(强)/(中)/(弱)
    归一到卡片同用的 很硬/一般/偏软；只动力度位，不动状态词(偏紧/走强/走弱/不避险)。"""
    s = str(text or "")
    for a, b in (("·强」", "·很硬」"), ("·中」", "·一般」"), ("·弱」", "·偏软」"),
                 ("(强)", "(很硬)"), ("(中)", "(一般)"), ("(弱)", "(偏软)")):
        s = s.replace(a, b)
    return s


def evidence_card(no: str, title: str, link: dict[str, Any], ruler_no: str, ruler_anchor: str) -> str:
    strength = link.get("strength")
    direction = link.get("direction")
    evidence = unify_strength_words(link.get("evidence"))
    # 大白话(事实→对你意味着什么)当主文放最显眼处；无 plain 则退回术语拼句(兼容旧数据)
    plain_main = link.get("plain") or (
        f"{title}：往「{direction}」方向，这层今天证据{plain_strength(strength)}。（今日无大白话·见下方系统依据）"
    )
    suff = evidence_sufficient(link)
    if suff:
        verdict, color, dot = decision_badge(strength)
        verdict_plain = {
            "支持": "这条判断今天站得住（有证据撑着）",
            "转弱预警": "这条判断在转弱（证据变软了·留意）",
            "证伪·切备用逻辑": "这条判断被事实推翻了·改走备用思路",
        }.get(verdict, verdict)
        dot_prefix = f"{dot} " if dot else ""
        badge = f'<span style="font-size:15px;font-weight:700;color:{color};">{dot_prefix}{esc(verdict_plain)}</span><small>（这层今天证据有多硬：{esc(plain_strength(strength))}）</small>'
    else:
        badge = '<span style="font-size:15px;font-weight:700;color:#9aa8b5;">⚠ 这层今天没有够硬的新证据，先不下新结论</span>'
    return f"""
    <details class="card" open>
      <summary><span>{esc(no)} {esc(title)}</span><b>{esc(plain_strength(strength))}</b></summary>
      <p class="macro-plain">{esc(plain_main)}</p>
      <p class="plain">今天这层怎么判：{badge}</p>
      <details class="term-fold">
        <summary>系统内部依据（读数 + 规则·想深究再看，可不看）</summary>
        <div class="meta">力度：{esc(plain_strength(strength))} ｜ 往哪个方向：{esc(direction)}</div>
        <div class="detail">{esc(evidence)}</div>
        {evidence_event_sections(link)}
        <div class="meta">这条对应哪把尺（判断依据规则）：<a href="#{esc(ruler_anchor)}" style="color:#8fd6ff;">右栏{esc(ruler_no)} 这把尺</a></div>
      </details>
    </details>
    """


def moat_text(moat: dict[str, Any]) -> str:
    score = moat.get("total_score")
    score_text = "待补" if score is None else str(score)
    return f"{moat.get('moat_grade', '待补护城河')} / 分数 {score_text} / 置信度 {moat.get('confidence', '待补')}"


def currency_for_symbol(symbol: str) -> str:
    if symbol.startswith("JP."):
        return "¥"
    if symbol.startswith("US.") or symbol.startswith("CC."):
        return "$"
    return ""


def fmt_level(value: Any) -> str:
    if value is None:
        return "待拉"
    try:
        return f"{float(value):.6f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def money(value: Any, cur: str = "$") -> str:
    try:
        return f"{cur}{float(value):,.0f}"
    except (TypeError, ValueError):
        return f"{cur}待补"


def pctf(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "待补"
    sign = "+" if number >= 0 else ""
    return f"{sign}{number:.2f}%"


def pnl_color(value: Any) -> str:
    try:
        return "#3ec38a" if float(value) >= 0 else "#f0616d"
    except (TypeError, ValueError):
        return "#9aa8b5"


def cost_pnl_cell(symbol: str, cost_by_ticker: dict[str, dict[str, Any]]) -> str:
    base = symbol.split(".")[-1]
    agg = cost_by_ticker.get(base)
    if not agg or agg.get("cost_coverage_status") == "PENDING":
        return '<span style="color:#9aa8b5;">成本待补·不显示假盈亏</span>'

    status = agg.get("cost_coverage_status")
    if status == "FULL" and agg.get("unrealized_pnl_pct") is not None:
        pct = agg.get("unrealized_pnl_pct")
        usd = agg.get("unrealized_pnl_usd")
        cost = agg.get("cost_basis_usd")
        return (
            f'<div><span style="font-size:15px;font-weight:700;color:{pnl_color(pct)};">浮盈亏 {pctf(pct)}</span>'
            f'（{money(usd, "$")}）</div>'
            f'<div style="color:#9aa8b5;font-size:12px;">成本 {money(cost, "$")}（USD折算）</div>'
        )
    if status == "PARTIAL" and agg.get("known_unrealized_pnl_pct") is not None:
        kpct = agg.get("known_unrealized_pnl_pct")
        return (
            f'<div><span style="font-size:14px;font-weight:700;color:{pnl_color(kpct)};">已知腿 {pctf(kpct)}</span></div>'
            f'<div style="color:#ffa657;font-size:12px;">另一账户成本待补·整只浮盈亏待全</div>'
            f'<div style="color:#9aa8b5;font-size:12px;">{esc(agg.get("cost_source_summary", ""))}</div>'
        )
    return '<span style="color:#9aa8b5;">成本待补·不显示假盈亏</span>'


def target_price_block(symbol: str, price: Any, target_by_base: dict[str, dict[str, Any]]) -> str:
    base = symbol.split(".")[-1]
    target = target_by_base.get(base) or target_by_base.get(symbol)
    if not target or target.get("take_profit") is None:
        return '<div style="color:#9aa8b5;">目标价：待估值中枢·DCF待做（不显示假目标）</div>'

    take_profit = target.get("take_profit")
    currency = target.get("currency")
    symbol_currency = "¥" if currency == "JPY" else "$" if currency == "USD" else currency_for_symbol(symbol)
    target_line = (
        f'<div>目标价(减仓线)：{esc(symbol_currency)}{esc(fmt_level(take_profit))}'
        f'　<span style="color:#ffa657;font-size:12px;">〔情景版·可信度B·非DCF〕</span></div>'
    )
    if price is None:
        return target_line
    try:
        price_num = float(price)
        target_num = float(take_profit)
    except (TypeError, ValueError):
        return target_line

    if price_num >= target_num:
        return target_line + '<div><span style="font-size:15px;font-weight:700;color:#ffa657;">🟠 已达目标价·考虑减仓</span></div>'
    return target_line + f'<div style="color:#9aa8b5;font-size:12px;">未到目标价（现价 {esc(symbol_currency)}{esc(fmt_level(price))}）</div>'


def price_level_cell(item: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]]) -> str:
    symbol = str(item.get("symbol") or "")
    ma = ma_by_symbol.get(symbol)
    price = None
    if ma:
        price = ma.get("realtime_price")
    if price is None:
        price = item.get("realtime_price") or item.get("price")

    if not ma or ma.get("ma50") is None or ma.get("ma200") is None:
        low_stop_block = '<span style="color:#9aa8b5;">待拉·无均线（不显示假价）</span>'
        return low_stop_block + target_price_block(symbol, price, target_by_base)

    ma50 = ma.get("ma50")
    ma200 = ma.get("ma200")
    symbol_currency = currency_for_symbol(symbol)

    try:
        price_num = float(price)
        ma50_num = float(ma50)
        ma200_num = float(ma200)
    except (TypeError, ValueError):
        low_stop_block = '<span style="color:#9aa8b5;">待拉·无均线（不显示假价）</span>'
        return low_stop_block + target_price_block(symbol, price, target_by_base)

    if price_num <= ma200_num:
        badge = '<span style="font-size:15px;font-weight:700;color:#f0616d;">🔴 跌破年线·止损区：考虑减/止损</span>'
    elif price_num <= ma50_num:
        badge = '<span style="font-size:15px;font-weight:700;color:#3ec38a;">🟢 回踩50日·低吸区：可考虑低吸/加</span>'
    else:
        badge = '<span style="font-size:15px;font-weight:700;color:#9ed8ff;">⚪ 在均线上方·持有观察（未到低吸/止损价）</span>'

    low_stop_block = (
        f'<div>低吸(回踩50日)：{esc(symbol_currency)}{esc(fmt_level(ma50))}</div>'
        f'<div>止损(跌破年线)：{esc(symbol_currency)}{esc(fmt_level(ma200))}</div>'
        f'<div>{badge}</div>'
        f'<div style="color:#9aa8b5;font-size:12px;">现价 {esc(symbol_currency)}{esc(fmt_level(price))}</div>'
    )
    return low_stop_block + target_price_block(symbol, price, target_by_base)


def holding_row(item: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]], cost_by_ticker: dict[str, dict[str, Any]]) -> str:
    return f"""
    <tr>
      <td>{esc(item.get('name'))}<br><span>{esc(item.get('symbol'))}</span></td>
      <td>{esc(item.get('hard_filter'))}</td>
      <td>{esc(item.get('soft_filter', {}).get('label'))}</td>
      <td>{esc(item.get('valuation', {}).get('label'))}</td>
      <td>{esc(moat_text(item.get('moat', {})))}</td>
      <td>{'<span style="color:#7ee0a0;">已研究·见下</span>' if has_pack(item.get('symbol'), item.get('name')) else '<span style="color:#9aa8b5;">待补个股研究</span>'}</td>
      <td>{price_level_cell(item, ma_by_symbol, target_by_base)}</td>
      <td>{cost_pnl_cell(str(item.get('symbol') or ''), cost_by_ticker)}</td>
      <td><b>{esc(item.get('action'))}</b><br>{esc(item.get('one_line_reason'))}</td>
    </tr>
    """


def _action_badge(action: Any) -> tuple[str, str, str]:
    """把上游 item.action 映射成"今日动词"徽章：动词永远明确、绝不造假买卖。
    本阶段无高确定性信号，默认走"守"家族(守·持有核心/守·观望/守·先别动)，
    不给决断买/卖。含"复核/受检"的试探值 → 守·先别动，把倾向大白话装进 caveat。
    返回 (今日动词, tone, caveat)：caveat 交给决策卡放进理由行小字，不进徽章。"""
    text = str(action or "").strip()
    tentative = ("复核" in text) or ("受检" in text)

    # 决断的"买/卖"只保留代码位（确定性够高才给，本阶段不触发，现不输出）：
    #   if not tentative and lead in ("买", "加"): return "买 · 加仓", "dc-good", ""
    #   if not tentative and lead in ("卖",):       return "卖 · 减仓", "dc-bad", ""

    if not text:
        return "守 · 观望", "dc-soft", ""

    # 含"复核"或"受检"的试探值 → 守 · 先别动（黄），倾向大白话放 caveat
    if tentative:
        caveat_map = {
            "减/复核": "看着像该减一点·还在复核",
            "等/复核低吸": "想等更便宜再买·还在复核",
            "等/受检": "还在检查方向对不对",
        }
        caveat = caveat_map.get(text)
        if caveat is None:
            if "减" in text:
                caveat = "看着像该减一点·还在复核"
            elif "复核低吸" in text or "低吸" in text:
                caveat = "想等更便宜再买·还在复核"
            elif "受检" in text:
                caveat = "还在检查方向对不对"
            else:
                caveat = "还在复核"
        return "守 · 先别动", "dc-hi", caveat

    parts = [p.strip() for p in text.split("/") if p.strip()]
    lead = parts[0] if parts else ""
    # 干净"守" → 守 · 持有核心
    if "守" in lead:
        return "守 · 持有核心", "dc-soft", ""
    # 干净"等"(无复核/受检) → 守 · 观望
    if "等" in lead:
        return "守 · 观望", "dc-soft", ""
    # 其余非试探未知值：本阶段一律回退到守家族，不擅自给买卖
    return "守 · 观望", "dc-soft", ""


def _ladder_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_range(text: Any) -> tuple[float | None, float | None]:
    """解析合理区字符串(如 "179.47 ~ 196.36" / "5,618.25 ~ 6,442.26")→ (下沿, 上沿)。
    解析不出数字返回 (None, None)；只有一个数时下沿=上沿。只读解析、不下单。"""
    if text is None:
        return None, None
    s = str(text)
    for token in ("～", "—", "－", "至", "到"):
        s = s.replace(token, "~")
    nums: list[float] = []
    for part in s.split("~"):
        cleaned = (
            part.replace(",", "").replace("$", "").replace("¥", "")
            .replace("日元", "").replace("元", "").strip()
        )
        val = _ladder_value(cleaned)
        if val is not None:
            nums.append(val)
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums), max(nums)


def _build_target_from_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """从估值样例(valuation_samples)构建 target：含合理区下沿/上沿、买点、止盈、止损、状态。
    这些是"能落地的动作价"来源；缺哪项就为 None，绝不拿均线冒充。"""
    fair_low, fair_high = _parse_range(sample.get("fair_value_range"))
    return {
        "take_profit": sample.get("take_profit_price"),
        "stop_loss": sample.get("stop_loss_price"),
        "buy_price": sample.get("buy_price"),
        "fair_low": fair_low,
        "fair_high": fair_high,
        "valuation_status": sample.get("valuation_status"),
        "currency": sample.get("currency"),
        "confidence": sample.get("confidence"),
    }


def _num_from_band(text: Any) -> float | None:
    """从估值实例 band 串(如 '$382-420'、'<$360'、'>$460')抽第一个数。"""
    if text is None:
        return None
    m = re.findall(r"[-+]?\d[\d,]*\.?\d*", str(text).replace(",", ""))
    return float(m[0]) if m else None


def targets_from_model_instances(inst_dir: Path) -> dict[str, dict[str, Any]]:
    """估值唯一来源=valuation 实例(model_instances)：把 valuation_bands 折成 target 价位。
    单一来源(治#5/6/8-12)：持仓卡价位阶梯与估值判断同源于此，非另一个 valuation_samples。
    take_profit=偏贵线(减仓)、buy_price=便宜线(低吸)、合理区=reasonable；标'相对估值·非精算'。"""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(inst_dir.glob("*.json")):
        try:
            d = read_json(path)
        except Exception:
            continue
        bands = d.get("valuation_bands", {}) or {}
        fair_low, fair_high = _parse_range(bands.get("reasonable"))
        cur = "¥" if str(d.get("symbol") or "").startswith("JP.") else "$"
        target = {
            "take_profit": _num_from_band(bands.get("expensive")),   # 偏贵/减仓线
            "stop_loss": None,                                        # 止损待DCF/纪律，不拿均线冒充
            "buy_price": _num_from_band(bands.get("cheap")),          # 便宜/低吸线
            "fair_low": fair_low if fair_low is not None else _num_from_band(bands.get("base")),
            "fair_high": fair_high,
            "valuation_status": "相对估值·非精算",
            "currency": cur,
            "confidence": d.get("confidence") or "C相对估值",
        }
        for key in (d.get("symbol"), _base_ticker(str(d.get("symbol") or "")), d.get("name")):
            if key:
                out[str(key)] = target
    return out


def holding_price_ladder(item: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """价位阶梯：返回 (一句大白话 now_line, 阶梯图 bar_html)。
    动作价一律来自估值(合理区/止盈/止损)，不再拿均线当止损/买点/防守价。
    · 有估值：便宜买点=合理区下沿、想卖=止盈价、危险=止损价，并说现价落在便宜/合理/贵哪档。
    · 缺估值(如MSTR/加密代理)：不给任何动作价，诚实说"估值还没做"，按仓位纪律控占比。
    均线只作一句"趋势背景"参考，绝不当买卖线/止损线。（依据《决策逻辑链·正确设计》四）"""
    symbol = str(item.get("symbol") or "")
    ma = ma_by_symbol.get(symbol)
    cur = currency_for_symbol(symbol)
    cur_e = esc(cur)

    price = None
    if ma:
        price = ma.get("realtime_price")
    if price is None:
        price = item.get("realtime_price") or item.get("price")
    price_num = _ladder_value(price)
    price_text = f'{cur_e}{esc(fmt_level(price))}' if price_num is not None else '待拉'

    # 动作价锚点：全部来自估值表(valuation_samples)——合理区下沿/上沿、止盈、止损
    base = symbol.split(".")[-1]
    target = target_by_base.get(base) or target_by_base.get(symbol)
    fair_low_num = _ladder_value(target.get("fair_low")) if target else None
    fair_high_num = _ladder_value(target.get("fair_high")) if target else None
    tp_num = _ladder_value(target.get("take_profit")) if target else None
    sl_num = _ladder_value(target.get("stop_loss")) if target else None
    has_val = any(v is not None for v in (fair_low_num, fair_high_num, tp_num, sl_num))

    # 趋势背景：均线只作一句方向参考，绝不当买卖线/止损线
    trend_note = ""
    if ma is not None:
        ma50v = _ladder_value(ma.get("ma50"))
        ma200v = _ladder_value(ma.get("ma200"))
        if ma50v is not None and ma200v is not None:
            if ma50v < ma200v:
                trend_note = '　<span style="color:#9db0c2;font-size:12px;">趋势背景：近两个月均价在近一年均价下方＝方向偏弱（仅参考，不当买卖线）。</span>'
            elif ma50v > ma200v:
                trend_note = '　<span style="color:#9db0c2;font-size:12px;">趋势背景：近两个月均价在近一年均价上方＝方向偏强（仅参考，不当买卖线）。</span>'
            else:
                trend_note = '　<span style="color:#9db0c2;font-size:12px;">趋势背景：两条均价线重合＝方向不明（仅参考，不当买卖线）。</span>'

    def _emptybar(msg: str) -> str:
        return (
            '<div class="dc-row"><div class="dc-lab">价位阶梯</div>'
            f'<div class="dc-val"><span style="color:#ffd479;">{msg}</span></div></div>'
        )

    # === 缺估值：诚实不给动作价（不拿均线冒充止损价/买卖价）===
    if not has_val:
        now_line = (
            '今天：先守着、别追高也别越跌越补 · <b>这只的估值还没做出来</b>'
            '（内在价值、合理区、止盈价、止损价都还没算），<b>所以不给你假的买卖价</b>——'
            '不会照均线硬编一个和现价差着十万八千里的价来骗你。现在能做的：'
            '按仓位纪律控制它的占比，不追高、不摊平；等它的估值和个股深研补出来，再定去留。'
            + trend_note
        )
        return now_line, _emptybar('这只估值还没做·先不给动作价·按仓位纪律控占比')

    # === 有估值：价位全部来自估值 ===
    cheap_txt = f'{cur_e}{esc(fmt_level(fair_low_num))}' if fair_low_num is not None else None
    high_txt = f'{cur_e}{esc(fmt_level(fair_high_num))}' if fair_high_num is not None else None
    tp_txt = f'{cur_e}{esc(fmt_level(tp_num))}' if tp_num is not None else None
    sl_txt = f'{cur_e}{esc(fmt_level(sl_num))}' if sl_num is not None else None

    # 现价落在便宜/合理/贵/危险哪一档（只描述位置，不给买卖决断）
    zone = ""
    zone_tone = "blue"
    if price_num is not None:
        if sl_num is not None and price_num <= sl_num:
            zone, zone_tone = "危险区（已跌破止损价）", "red"
        elif fair_low_num is not None and price_num < fair_low_num:
            zone, zone_tone = "便宜区（低于合理区下沿）", "green"
        elif fair_high_num is not None and price_num <= fair_high_num:
            zone, zone_tone = "合理区（不便宜也不贵）", "blue"
        elif fair_high_num is not None and price_num > fair_high_num:
            zone, zone_tone = "偏贵区（高于合理区上沿）", "blue"
        elif tp_num is not None and price_num >= tp_num:
            zone, zone_tone = "已到想卖的价（止盈价上方）", "blue"

    price_bits: list[str] = []
    if cheap_txt is not None:
        price_bits.append(f'想更便宜再买＝等回到 {cheap_txt}（合理区下沿）')
    if tp_txt is not None:
        price_bits.append(f'涨到 {tp_txt} 就想卖（止盈）')
    if sl_txt is not None:
        price_bits.append(f'跌破 {sl_txt} 算危险（止损·要认真复核去留）')
    zone_sentence = f'现价{price_text}落在【{esc(zone)}】。' if zone else f'现价{price_text}。'
    now_line = (
        '今天：先守着 · <b>价位按估值来（不看均线）</b>：'
        + '；'.join(price_bits) + '。' + zone_sentence + trend_note
    )

    # === 阶梯图：锚点全用估值（止损 ≤ 便宜买点 ＜ 想卖）===
    stop = sl_num          # 危险=止损价
    low_buy = fair_low_num  # 便宜买点=合理区下沿
    top = tp_num           # 想卖=止盈价
    badge = f'<span class="dc-zone dc-zone-{zone_tone}">现价落在：{esc(zone or "见阶梯")}</span>'

    if not (stop is not None and low_buy is not None and top is not None
            and stop <= low_buy < top):
        # 锚点不齐或次序异常：只给文字阶梯、不画会误导的矛盾图
        parts: list[str] = []
        if sl_txt is not None:
            parts.append(f'危险(跌破就止损){sl_txt}')
        if cheap_txt is not None:
            parts.append(f'便宜买点(合理区下沿){cheap_txt}')
        if high_txt is not None:
            parts.append(f'合理区上沿{high_txt}')
        parts.append(f'现价{price_text}')
        if tp_txt is not None:
            parts.append(f'想卖的价(止盈){tp_txt}')
        line = ' ＜ '.join(parts)
        bar_html = (
            '<div class="dc-row"><div class="dc-lab">价位阶梯</div>'
            f'<div class="dc-val"><div class="dc-ladder-line">{line}　{badge}</div></div></div>'
        )
        return now_line, bar_html

    span = top - stop
    pct = 0.0 if price_num is None else max(0.0, min(100.0, (price_num - stop) / span * 100.0))
    yellow_w = max(0.0, min(100.0, (low_buy - stop) / span * 100.0))
    green_w = max(0.0, 100.0 - yellow_w)
    marker = _ladder_value(pct) or 0.0
    bar = (
        '<div class="dc-ladder-bar">'
        f'<div class="dc-ladder-seg dc-lad-red" style="width:6%;"></div>'
        f'<div class="dc-ladder-seg dc-lad-yellow" style="width:{yellow_w:.1f}%;"></div>'
        f'<div class="dc-ladder-seg dc-lad-green" style="width:{green_w:.1f}%;"></div>'
        f'<div class="dc-ladder-mark" style="left:{marker:.1f}%;">▲</div>'
        '</div>'
    )
    line = (
        f'危险(跌破就止损){sl_txt} ＜ 便宜买点(合理区下沿){cheap_txt} '
        f'＜ 现价{price_text} ＜ 想卖的价(止盈){tp_txt}'
    )
    bar_html = (
        '<div class="dc-row"><div class="dc-lab">价位阶梯</div>'
        f'<div class="dc-val">{bar}'
        f'<div class="dc-ladder-line">{line}　{badge}</div></div></div>'
    )
    return now_line, bar_html


# ===================== 仓位集中度模块（结构化现算，不靠散文） =====================
# 仓位纪律尺（董事长2026-07-04确认沿用）：
#   单一标的 ≤15%（上限）｜AI主线 ≤45%（上限）｜防御 ≥15%（下限）
#   加密 ≤12%（上限）｜现金 ≥5%（下限）
# 本模块只做「结构化现算」：从 production.holdings 的 market_value 现算各类占比，
# 不写死具体标的死名单——只锚「定义」，标的由数据里的结构化字段现判（总则第六条）。
#
# 分类规则（只锚定义、不锚死名单）：
#  · 加密相关(CRYPTO_TICKERS/CC.前缀)：symbol 以 "CC." 开头，或 base ticker ∈ 加密敞口代理集。
#  · AI供应链(AI_SUPPLY_NODE_CLASSES)：holding 的 matched_node_classes_effective(缺则_raw)
#    与「广义AI供应链节点集」有交集。注：仓位纪律尺原文写"AI主线(算力+电力)"，此处取
#    **广义AI供应链**以对齐已知AI集中度口径——定义范围留架构师裁；要切窄，把
#    AI_SUPPLY_NODE_CLASSES 收成 {"算力","电力"} 即可（代码里已注明可切换点）。
#  · 防御(DEFENSIVE_SIGNALS)：非AI非加密，且 node_class/名称含防御类信号(保险/医药/公用/必需消费)。
#    判不出防御信号的非AI非加密持仓归"其它"，不硬塞防御。
#  · 单一标的：每只自身 market_value 占比。
#  · 现金：production/holdings 里若无结构化现金总额 → 标"待接入·无结构化现金数据"、不编数，
#    现金≥5%检查=待数据；分母口径=持仓 market_value 合计（无现金数据时）。

# 加密敞口代理集（base ticker，纯锚定义；CC.前缀自动归加密）
CRYPTO_TICKERS = {"MSTR", "COIN", "BTC", "ETH", "BTCUSD", "ETHUSD"}
# 广义AI供应链节点集（可切窄=改成 {"算力","电力"}；范围留架构师裁）
AI_SUPPLY_NODE_CLASSES = {"算力", "电力", "半导体设备", "存储", "代工", "盟友节点", "盟友", "盟友链", "AI软件应用"}

# 持仓→节点 分类映射（单一来源·治"当日闸弱时 matched_node_classes 为空→AI供应链算成0%"的bug）。
# 这是"我持仓本身属哪条链"的静态归类(风险集中度用)，非当日机会买卖名单(总则第六条区分)。
# 当持仓审查有当日 matched_node_classes(闸激活)时优先用它；为空时回退本映射，保证AI占比恒真。
# AI主线归类可迭代·范围留架构师裁(与上方 AI_SUPPLY_NODE_CLASSES 一致)。
HOLDING_NODE_MAP = {
    # AI 供应链
    "NVDA": "算力", "MSFT": "算力", "META": "AI软件应用",
    "AVGO": "半导体设备", "6857": "半导体设备", "TSM": "代工", "SNDK": "存储",
    "9984": "盟友链",
    # 加密
    "MSTR": "加密", "COIN": "加密", "CRCL": "加密", "BTC": "加密", "ETH": "加密",
    "BTCUSD": "加密", "ETHUSD": "加密",
    # 防御
    "4568": "防御·医药", "8766": "防御·保险",
    # 其它非AI
    "6758": "消费电子", "7974": "游戏", "7832": "消费", "7203": "汽车",
    "8001": "商社", "IBKR": "金融",
}
# 防御类名称/节点信号（只锚定义关键词，不锚死名单）
DEFENSIVE_SIGNALS = ("保险", "医药", "制药", "公用", "必需消费", "防御", "海上", "三共")

# 仓位纪律尺：上限类（超标才触发"别加"）+ 下限类（不足另出提示，不叫"别加"）
CONC_UPPER_LIMITS = {"AI供应链": 45.0, "单一标的": 15.0, "加密": 12.0}
CONC_LOWER_LIMITS = {"防御": 15.0, "现金": 5.0}
# 类名 → 大白话（只做展示层翻译，不改分类key/判定）
CONC_NAME_PLAIN = {
    "AI供应链": "AI供应链（押在AI这条产业链上的钱）",
    "加密": "加密（比特币等数字资产）",
    "防御": "防御（抗跌的保命仓·保险/医药/公用等）",
    "现金": "现金（随时能动用的钱）",
    "单一标的": "单一标的（单独一只股票）",
}


def _base_ticker(symbol: str) -> str:
    return symbol.split(".")[-1]


def _is_crypto(symbol: str) -> bool:
    if symbol.startswith("CC."):
        return True
    return _base_ticker(symbol).upper() in CRYPTO_TICKERS


def _holding_node(item: dict[str, Any]) -> str | None:
    """该持仓的节点归类：优先当日审查(闸激活时)的 matched_node_classes，为空则回退静态映射。"""
    classes = item.get("matched_node_classes_effective") or item.get("matched_node_classes_raw")
    if isinstance(classes, list) and classes:
        return str(classes[0])
    return HOLDING_NODE_MAP.get(_base_ticker(str(item.get("symbol") or "")))


# AI主线供应链持仓集(base ticker)：本单派工明列"NVDA/MSFT/AVGO/TSM/软银 都算进AI"。
# 要把设备/存储/软件(爱德万/SNDK/META)也折进AI主线口径→加进本集即可(范围留架构师裁·不改尺)。
AI_SUPPLY_HOLDINGS = {"NVDA", "MSFT", "AVGO", "TSM", "9984"}


def _is_ai_supply(item: dict[str, Any]) -> bool:
    classes = item.get("matched_node_classes_effective")
    if not classes:
        classes = item.get("matched_node_classes_raw")
    if isinstance(classes, list) and classes:
        return bool(set(str(c) for c in classes) & AI_SUPPLY_NODE_CLASSES)
    # 当日闸弱→matched 为空：回退到派工明列的AI主线持仓集，AI占比不再假成0%
    return _base_ticker(str(item.get("symbol") or "")) in AI_SUPPLY_HOLDINGS


def _is_defensive(item: dict[str, Any]) -> bool:
    text = f"{item.get('name') or ''} {item.get('node_class') or ''}"
    classes = item.get("matched_node_classes_effective") or item.get("matched_node_classes_raw") or []
    if isinstance(classes, list):
        text += " " + " ".join(str(c) for c in classes)
    return any(sig in text for sig in DEFENSIVE_SIGNALS)


def _mv(item: dict[str, Any]) -> float | None:
    try:
        v = item.get("market_value")
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


# 统一美元折算兜底汇率（快照与统一持仓都取不到时才用）
USDJPY_FALLBACK = 162.536


def resolve_usdjpy() -> tuple[float, str]:
    """统一美元折算汇率 USDJPY：优先市场快照，其次统一持仓 fx，最后兜底常数。
    返回 (rate, source_text)。只读文件、不下单。"""
    # 1) data/market/latest_market_snapshot.json 的 assets[symbol=USDJPY]
    snapshot_path = ROOT / "data" / "market" / "latest_market_snapshot.json"
    if snapshot_path.exists():
        try:
            snap = read_json(snapshot_path)
            for asset in snap.get("assets", []):
                if asset.get("symbol") == "USDJPY":
                    rate = asset.get("price")
                    if rate is None:
                        rate = asset.get("close")
                    if rate is not None and float(rate) > 0:
                        data_date = asset.get("data_date") or ""
                        return float(rate), f"latest_market_snapshot.json·USDJPY({data_date})"
        except (ValueError, TypeError, KeyError):
            pass
    # 2) data/accounts/unified_holdings_latest.json 的 fx.USDJPY
    cost_path = ROOT / "data" / "accounts" / "unified_holdings_latest.json"
    if cost_path.exists():
        try:
            cost = read_json(cost_path)
            rate = cost.get("fx", {}).get("USDJPY")
            if rate is not None and float(rate) > 0:
                return float(rate), "unified_holdings_latest.json·fx.USDJPY"
        except (ValueError, TypeError, KeyError):
            pass
    # 3) 兜底常数
    return USDJPY_FALLBACK, f"兜底常数{USDJPY_FALLBACK}（快照与统一持仓均取不到）"


def _mv_usd(item: dict[str, Any], usdjpy: float) -> tuple[float | None, str]:
    """把单只 market_value 折成统一美元。返回 (mv_usd, note)。
    · JP.* → market_value / USDJPY（日元折美元）
    · US./CC.* → 原值（已是美元）
    · 其它市场(如HK.) → 暂按原值、note='no_fx'（无汇率·在页面注明）
    · market_value 缺 → (None, 'missing')（如CC.BTC/ETH，不进分母）"""
    mv = _mv(item)
    if mv is None:
        return None, "missing"
    symbol = str(item.get("symbol") or "")
    if symbol.startswith("JP."):
        if usdjpy and usdjpy > 0:
            return mv / usdjpy, "jpy"
        return mv, "no_fx"
    if symbol.startswith("US.") or symbol.startswith("CC."):
        return mv, "usd"
    return mv, "no_fx"


def portfolio_concentration(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    """从 production.holdings 的 market_value 现算各类占比（结构化、不靠散文）。
    关键修正（货币混算 bug）：各持仓 market_value 币种不同——日股 JP.* 是日元、
    美股 US.* / 加密 CC.* 是美元。旧逻辑直接相加导致日元项被当美元、总额虚高、占比全错。
    现先把每只 market_value 统一折成美元（JP.* ÷ USDJPY）再算占比与超限判定。

    返回：
      total_mv / total_usd：全持仓折美元后之和（分母；无现金数据时=持仓合计）
      usdjpy / usdjpy_source：实际用的汇率与来源（快照→统一持仓fx→兜底常数）
      categories：{类名: {pct, limit, kind('upper'/'lower'), over(bool·仅上限), short(bool·仅下限), members}}
      singles：[{symbol, name, pct, over(bool)}]（每只自身美元占比 vs 单一标的上限15%）
      over_limit_symbols：属超标上限类(AI/单一/加密)的 symbol → {类名: 超限百分点} 映射
      cash_status：现金口径说明（无结构化现金数据 → 待接入）
      mv_missing：market_value 缺失(如CC.BTC/ETH)的 symbol 列表（不计入分母，另注明）
      no_fx_symbols：非JP/US/CC市场(如HK.)无汇率、暂按原值计入的 symbol 列表（页面注明）
    """
    usdjpy, usdjpy_source = resolve_usdjpy()

    priced: list[tuple[dict[str, Any], float]] = []
    mv_missing: list[str] = []
    no_fx_symbols: list[str] = []
    for h in holdings:
        mv_usd, note = _mv_usd(h, usdjpy)
        symbol = str(h.get("symbol") or "")
        if mv_usd is None:
            mv_missing.append(symbol)
            continue
        if note == "no_fx":
            no_fx_symbols.append(symbol)
        priced.append((h, mv_usd))

    total_mv = sum(mv for _, mv in priced)

    ai_mv = 0.0
    crypto_mv = 0.0
    defensive_mv = 0.0
    ai_members: list[str] = []
    crypto_members: list[str] = []
    defensive_members: list[str] = []
    singles: list[dict[str, Any]] = []

    for h, mv in priced:
        symbol = str(h.get("symbol") or "")
        pct = (mv / total_mv * 100.0) if total_mv > 0 else 0.0
        crypto = _is_crypto(symbol)
        ai = (not crypto) and _is_ai_supply(h)
        defensive = (not crypto) and (not ai) and _is_defensive(h)
        if crypto:
            crypto_mv += mv
            crypto_members.append(symbol)
        elif ai:
            ai_mv += mv
            ai_members.append(symbol)
        elif defensive:
            defensive_mv += mv
            defensive_members.append(symbol)
        singles.append({
            "symbol": symbol,
            "name": str(h.get("name") or symbol),
            "pct": pct,
            "over": pct > CONC_UPPER_LIMITS["单一标的"],
        })

    def _pct(v: float) -> float:
        return (v / total_mv * 100.0) if total_mv > 0 else 0.0

    categories: dict[str, Any] = {}
    ai_pct = _pct(ai_mv)
    crypto_pct = _pct(crypto_mv)
    defensive_pct = _pct(defensive_mv)
    categories["AI供应链"] = {
        "pct": ai_pct, "limit": CONC_UPPER_LIMITS["AI供应链"], "kind": "upper",
        "over": ai_pct > CONC_UPPER_LIMITS["AI供应链"], "short": False, "members": ai_members,
    }
    categories["加密"] = {
        "pct": crypto_pct, "limit": CONC_UPPER_LIMITS["加密"], "kind": "upper",
        "over": crypto_pct > CONC_UPPER_LIMITS["加密"], "short": False, "members": crypto_members,
    }
    categories["防御"] = {
        "pct": defensive_pct, "limit": CONC_LOWER_LIMITS["防御"], "kind": "lower",
        "over": False, "short": defensive_pct < CONC_LOWER_LIMITS["防御"], "members": defensive_members,
    }

    # 现金：无结构化现金总额 → 标待接入、不编数、检查=待数据
    cash_status = "待接入·无结构化现金数据（现金≥5%检查=待数据；分母口径=持仓market_value合计）"

    # over_limit_symbols：属超标上限类的 symbol → {类名: 超限百分点}
    over_limit_symbols: dict[str, dict[str, float]] = {}
    for cat_name in ("AI供应链", "加密"):
        cat = categories[cat_name]
        if cat["over"]:
            gap = cat["pct"] - cat["limit"]
            for symbol in cat["members"]:
                over_limit_symbols.setdefault(symbol, {})[cat_name] = gap
    for s in singles:
        if s["over"]:
            gap = s["pct"] - CONC_UPPER_LIMITS["单一标的"]
            over_limit_symbols.setdefault(s["symbol"], {})["单一标的"] = gap

    return {
        "total_mv": total_mv,
        "total_usd": total_mv,
        "usdjpy": usdjpy,
        "usdjpy_source": usdjpy_source,
        "no_fx_symbols": no_fx_symbols,
        "categories": categories,
        "singles": singles,
        "over_limit_symbols": over_limit_symbols,
        "cash_status": cash_status,
        "mv_missing": mv_missing,
        "upper_limits": CONC_UPPER_LIMITS,
        "lower_limits": CONC_LOWER_LIMITS,
    }


def concentration_dont_add_lines(symbol: str, conc: dict[str, Any] | None) -> list[str]:
    """若该 symbol 属某"超上限"的上限类(AI/单一/加密) → 生成"别加"大白话句子列表。
    多类超标就都返回。不改上游action、不自创买卖——只按仓位纪律尺加"别加"约束。"""
    if not conc:
        return []
    over = conc.get("over_limit_symbols", {}).get(symbol)
    if not over:
        return []
    lines: list[str] = []
    for cat_name, gap in over.items():
        if cat_name == "单一标的":
            singles = {s["symbol"]: s for s in conc.get("singles", [])}
            actual = singles.get(symbol, {}).get("pct", 0.0)
            limit = CONC_UPPER_LIMITS["单一标的"]
            # 超单一上限→动作统一为"守·可减回纪律"(治#7/#13 卡说守·研究说减 的打架)
            lines.append(f"这只单独一只已押太多（现在占 {actual:.1f}%，超单一上限 {limit:.0f}%）→ 守·可减回≤{limit:.0f}%纪律线（减到限内、不是清仓）")
        else:
            cat = conc.get("categories", {}).get(cat_name, {})
            actual = cat.get("pct", 0.0)
            limit = cat.get("limit", 0.0)
            lines.append(f"这类（{cat_name}）已经押得太多了，别再加了（现在占 {actual:.1f}%，超过了上限 {limit:.0f}%）")
    return lines


def concentration_summary_table(conc: dict[str, Any]) -> str:
    """顶部"仓位集中度摘要表"：各类占比 vs 限、超/不足标红绿。"""
    rows: list[str] = []

    def _upper_row(name: str) -> str:
        cat = conc["categories"][name]
        pct = cat["pct"]
        limit = cat["limit"]
        if cat["over"]:
            verdict = f'<span style="color:#f0616d;font-weight:700;">🔴 押太多了·超上限 +{pct - limit:.1f}pt（别再加）</span>'
        else:
            verdict = f'<span style="color:#3ec38a;font-weight:700;">🟢 还没押满（还能再放 {limit - pct:.1f}pt）</span>'
        members = "、".join(cat["members"]) if cat["members"] else "无"
        name_h = CONC_NAME_PLAIN.get(name, name)
        return (f"<tr><td>{esc(name_h)}</td><td>{pct:.1f}%</td><td>最多押 ≤{limit:.0f}%（上限）</td>"
                f"<td>{verdict}</td><td style='color:#8ea3b6;font-size:12px;'>{esc(members)}</td></tr>")

    def _lower_row(name: str) -> str:
        cat = conc["categories"][name]
        pct = cat["pct"]
        limit = cat["limit"]
        if cat["short"]:
            verdict = f'<span style="color:#ffd479;font-weight:700;">🟡 押得偏少 −{limit - pct:.1f}pt（不是"别加"·看整体配置再定）</span>'
        else:
            verdict = f'<span style="color:#3ec38a;font-weight:700;">🟢 够了·达标</span>'
        members = "、".join(cat["members"]) if cat["members"] else "无"
        name_h = CONC_NAME_PLAIN.get(name, name)
        return (f"<tr><td>{esc(name_h)}</td><td>{pct:.1f}%</td><td>至少留 ≥{limit:.0f}%（下限）</td>"
                f"<td>{verdict}</td><td style='color:#8ea3b6;font-size:12px;'>{esc(members)}</td></tr>")

    rows.append(_upper_row("AI供应链"))
    rows.append(_upper_row("加密"))
    rows.append(_lower_row("防御"))
    # 现金：待接入
    rows.append(
        f"<tr><td>{esc(CONC_NAME_PLAIN['现金'])}</td><td style='color:#9aa8b5;'>这项还没接进来</td><td>至少留 ≥5%（下限）</td>"
        f"<td><span style='color:#9aa8b5;'>⚪ 还没有现金数据·这项检查=等数据</span></td>"
        f"<td style='color:#8ea3b6;font-size:12px;'>{esc(conc.get('cash_status', ''))}</td></tr>"
    )

    # 单一标的超限（若有）
    over_singles = [s for s in conc.get("singles", []) if s["over"]]
    single_rows = ""
    if over_singles:
        parts = "、".join(f"{esc(s['name'])}({esc(s['symbol'])}) {s['pct']:.1f}%" for s in over_singles)
        single_rows = (
            f"<tr><td>{esc(CONC_NAME_PLAIN['单一标的'])}·押太多</td><td colspan='4' style='color:#f0616d;font-weight:700;'>"
            f"🔴 {parts} ＞15%上限（这几只押太多了·别再加）</td></tr>"
        )
    else:
        single_rows = (
            f"<tr><td>{esc(CONC_NAME_PLAIN['单一标的'])}</td><td colspan='4' style='color:#3ec38a;'>"
            "🟢 没有哪一只单独超过15%上限</td></tr>"
        )

    missing = conc.get("mv_missing", [])
    no_fx = conc.get("no_fx_symbols", [])
    note_parts: list[str] = []
    if missing:
        note_parts.append(
            f'{esc("、".join(missing))} 无结构化 market_value，不计入分母（占比按其余持仓合计算）。'
        )
    if no_fx:
        note_parts.append(
            f'{esc("、".join(no_fx))} 非JP/US/CC市场·无汇率，暂按原值计入分母（待补该市场汇率后重算）。'
        )
    note_parts.append(
        'AI供应链口径(Code自决)：本表取AI主线核心持仓 NVDA/MSFT/AVGO/TSM/软银 现算(USDJPY归一)；'
        '设备/存储/软件(爱德万/SNDK/META)暂未计入、要折进把其加进 AI_SUPPLY_HOLDINGS 即可(范围可迭代·代码一行可调)。'
        '此为全系统AI集中度的唯一现算来源，个股研究包不再各写死数字。'
    )
    missing_note = (
        f'<p class="plain" style="color:#9aa8b5;font-size:12px;">口径注：{"".join(note_parts)}</p>'
    )

    fx = conc.get("usdjpy")
    fx_src = conc.get("usdjpy_source", "")
    total_usd = conc.get("total_usd", conc.get("total_mv", 0.0))
    fx_line = (
        f'<p class="plain" style="margin-top:0;color:#ffcf6b;">'
        f'折算汇率 USDJPY=<b>{fmt_number(fx, 4)}</b>（来源：{esc(fx_src)}）'
        f'　｜　折美元总额 <b>{money(total_usd, "$")}</b>'
        f'（日股JP.*已÷USDJPY折美元，美股US.*／加密CC.*原为美元；占比与超限判定全部基于此美元口径）。</p>'
    )

    return f"""
    <section class="card" style="padding:14px 16px;margin:0 0 14px;border-color:#43627e;background:#13283a;">
      <h2 style="margin:0 0 8px;color:#9ed8ff;font-size:19px;">📐 仓位集中度摘要（看某一类是不是押太多了·对照我们的仓位规矩现算）</h2>
      <p class="plain" style="margin-top:0;">每一类占多少 = 这类持仓值多少钱 ÷ 全部持仓值多少钱（都先换算成美元再比；没有现金数据时，分母就用全部持仓合计）。哪一类押太多（超上限）→ 对应的持仓卡会自动写上"别加"；哪一类押太少（不足下限）→ 不是"别加"，看整体配置再定。</p>
      {fx_line}
      <table>
        <thead><tr><th>哪一类</th><th>现在占多少</th><th>我们的规矩（上限/下限）</th><th>判定</th><th>包含哪些</th></tr></thead>
        <tbody>{''.join(rows)}{single_rows}</tbody>
      </table>
      {missing_note}
    </section>
    """


# ===================== 大白话翻译器（只把给董事长看的字翻成人话，不改数据/判定） =====================
# 内部标签 → 人话。凡术语当场用人话解释一次。只做展示层翻译，不动上游判定。

def plain_hard(hard: Any) -> str:
    """硬性=方向对不对（在不在该押的方向上）。"""
    text = str(hard or "").strip()
    if text == "符合":
        return "方向对（在该押的方向上）"
    if text == "不符合":
        return "方向不对（不在该押的方向上）"
    if text == "受检":
        return "还在检查方向对不对"
    if text in ("待补", ""):
        return "方向还没核（待核）"
    return f"{esc(text)}(待核)"


def plain_soft(label: Any) -> str:
    """软性=位置贵不贵（现在这个价买进去，是高位还是回调到便宜位）。"""
    text = str(label or "").strip()
    mapping = {
        "位置好": "位置好·已回调到较便宜的位置",
        "位置中性": "位置一般·不算贵也不算便宜",
        "位置偏高": "在高位·不便宜（现在追着买容易吃套）",
        "低吸区": "已回调到便宜区（便宜时能买的位置）",
        "止损区": "跌破关键线·危险区（跌过头、该防守）",
        "均线上方": "在高位·不便宜",
        "在均线上方": "在高位·不便宜",
        "技术待补": "位置还没算（待补）",
    }
    if text in mapping:
        return mapping[text]
    return f"{esc(text)}（位置贵不贵·待解释）"


def plain_valuation(label: Any) -> str:
    """估值=价格值不值（这个价格是贵了还是划算）。"""
    text = str(label or "").strip()
    if not text:
        return "还没做估值（价格值不值·待算）"
    if "待DCF" in text or "待估" in text or text in ("估值待判", "估值待补"):
        return "还没做估值（价格值不值·待算）"
    mapping = {
        "便宜": "价格便宜（划算）",
        "合理偏便宜": "价格算合理、还略偏便宜",
        "合理": "价格算合理",
        "合理区附近": "价格算合理",
        "偏贵": "偏贵（价格有点高）",
        "贵": "偏贵（价格偏高）",
    }
    if text in mapping:
        return mapping[text]
    return esc(text)


def plain_moat_phrase(moat: dict[str, Any] | None) -> str:
    """护城河=靠什么长期赚钱、对手难抢。返回一句人话短语（放进句子里用）。"""
    grade = str((moat or {}).get("moat_grade") or "待补护城河").strip()
    if grade == "宽护城河":
        return "护城河宽·很能守（靠什么长期赚钱、对手难抢）"
    if grade == "窄护城河":
        return "护城河窄·一般（长期护城能力普通）"
    if grade == "无护城河":
        return "几乎没护城河（对手容易抢生意）"
    return "还没评护城河（靠什么长期赚钱·还没打分）"


def plain_moat(moat: dict[str, Any] | None) -> str:
    """护城河人话主句 + 分数/把握当小字附注（分数不当主角）。"""
    main = plain_moat_phrase(moat)
    score = (moat or {}).get("total_score")
    conf = str((moat or {}).get("confidence") or "").strip()
    note_bits: list[str] = []
    if score is not None:
        note_bits.append(f"打分{esc(str(score))}")
    if conf and conf != "待补":
        note_bits.append(f"把握{esc(conf)}")
    if note_bits:
        return main + f'<span style="color:#8ea3b6;font-size:12px;">（{"·".join(note_bits)}）</span>'
    return main


def plain_strength(strength: Any) -> str:
    """力度=这条判断今天的证据有多硬。强→很硬 中→一般 弱→偏软 证伪→被事实推翻了。
    返回纯人话文本（调用处自行 esc()）。"""
    text = str(strength or "").strip()
    mapping = {"强": "很硬", "中": "一般", "弱": "偏软", "证伪": "被事实推翻了"}
    if text in mapping:
        return mapping[text]
    if text in ("", "待填"):
        return "还没有够硬的新证据"
    return text


def plain_certainty(certainty: Any) -> str:
    """确定性=我们对这条判断的把握有多大。高→把握大 中→把握一般 弱→把握小 证伪→被事实推翻了。
    返回纯人话文本（调用处自行 esc()）。"""
    text = str(certainty or "").strip()
    if text == "强":  # 把握用高/中/弱标度；数据里漏进力度词"强"时按等价的"高"归一(治#15·与动作列一致)
        text = "高"
    mapping = {"高": "把握大", "中": "把握一般", "弱": "把握小", "证伪": "被事实推翻了"}
    if text in mapping:
        return mapping[text]
    if text in ("", "待填"):
        return "还在攒把握"
    return text


def plain_decision_quality(level: Any) -> str:
    """决策质量分=今天我们下手的底气有多足。高→底气足 中→底气一般 低→底气不足。"""
    text = str(level or "").strip()
    mapping = {"高": "底气足", "中": "底气一般", "低": "底气不足"}
    if text in mapping:
        return mapping[text]
    if text in ("", "待填"):
        return "底气还没算出来"
    return text


def holding_decision_card(item: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]], cost_by_ticker: dict[str, dict[str, Any]], concentration: dict[str, Any] | None = None) -> str:
    """每只持仓一张决策卡（display-only）。动作沿用上游 item.action，不自创买卖决策。
    concentration(可选)：portfolio_concentration() 结果。若该 holding 属某"超上限"的上限类
    (AI/单一/加密) → 在理由处自动追加"别加"句（红/黄提示），与"守·先别动"并存不矛盾。"""
    name = item.get("name")
    symbol = str(item.get("symbol") or "")
    badge_text, tone, caveat = _action_badge(item.get("action"))

    now_line, ladder = holding_price_ladder(item, ma_by_symbol, target_by_base)

    # 四道关全翻成人话（每关：这是在问啥 + 人话答案）
    hard_h = plain_hard(item.get("hard_filter"))
    soft_h = plain_soft(item.get("soft_filter", {}).get("label"))
    _val_label = str(item.get("valuation", {}).get("label") or "")
    if symbol.startswith("CC."):  # BTC/ETH等资产：大白话说清资产口径，不再笼统"估值没做"(治②)
        val_h = "资产·不做企业估值（比特币/以太坊是资产、没有财报，只看币价+仓位纪律，不给公司估值区间）"
    else:
        val_h = plain_valuation(_val_label)
        if _val_label and "待" not in _val_label:  # 有估值实例→标"相对估值·非精算"(治#5/③)
            val_h += '<span style="color:#8ea3b6;font-size:12px;">（相对估值·非精算·来源valuation实例）</span>'
        if _val_label in ("贵", "偏贵"):  # 估值偏贵→动作统一带"可择机减"(治#7/#13·卡与研究不打架)
            val_h += '<span style="color:#ffd479;font-size:12px;">→ 偏贵·可择机减回纪律</span>'
    moat_h = plain_moat(item.get("moat", {}))
    gate_block = (
        f'<div style="margin:2px 0;">· 方向对不对：{hard_h}</div>'
        f'<div style="margin:2px 0;">· 位置贵不贵：{soft_h}</div>'
        f'<div style="margin:2px 0;">· 价格值不值：{val_h}</div>'
        f'<div style="margin:2px 0;">· 生意硬不硬（护城河=靠什么长期赚钱、对手难抢）：{moat_h}</div>'
    )

    cost_html = cost_pnl_cell(symbol, cost_by_ticker)

    # 极小仓提示(治#25)：市值不足全组合0.2%的零头仓(如台积电1股$453·占约0.03%)→标"极小仓"，
    # 免小白把叙事上听着重要、实际是零头的仓当核心大仓。通用按占比判定，不硬编码单只、不写死行业叙事。
    tiny_html = ""
    _base = symbol.split(".")[-1]
    _agg = cost_by_ticker.get(_base) or {}
    _mv = _agg.get("market_value_usd")
    _total_mv = sum(float((v or {}).get("market_value_usd") or 0) for v in cost_by_ticker.values())
    if _mv and _total_mv and (float(_mv) / _total_mv) < 0.002:
        _pct = float(_mv) / _total_mv * 100
        tiny_html = (
            '<div class="dc-tiny" style="background:#2a2410;border:1px solid #6a5420;color:#ffe4a8;'
            'border-radius:8px;padding:6px 10px;margin:6px 0;font-size:12.5px;line-height:1.6;">'
            f'⚠ <b>极小仓</b>：这只只占约 {_pct:.2f}% 仓位（市值 {money(_mv, "$")}），是零头/象征性持仓——'
            '在叙事里可能听着重要，但你实际押注很小，<b>别当重仓理解</b>。</div>'
        )

    if has_pack(item.get("symbol"), item.get("name")):
        research = '<span style="color:#7ee0a0;">这只我们深研过了，见下方</span>'
    else:
        research = '<span style="color:#9aa8b5;">这只还没深研</span>'

    # 理由：给董事长看的是人话（caveat 或"照上面四关来"）；上游术语版 one_line_reason
    # 属数据、不改内容，降级成灰色小字"内部依据"，只留作可核对、不当主文案。
    reason_raw = esc(item.get("one_line_reason"))
    if caveat:
        reason_plain = esc(caveat)
    else:
        reason_plain = "综合上面这四道关，今天就按上面写的动作来（先守着、别急）。"
    reason_html = (
        f'{reason_plain}'
        f'<div style="color:#8ea3b6;font-size:12px;margin-top:3px;">系统内部依据（术语版·可不看）：{reason_raw}</div>'
    )

    # 仓位纪律尺：属超上限类(AI/单一/加密)→自动追加"别加"句（红/黄提示·大白话）
    # 不改上游action、不自创买卖，只加"别加"约束；多类超标就都追加。
    dont_add_lines = concentration_dont_add_lines(symbol, concentration)
    dont_add_html = ""
    if dont_add_lines:
        items = "".join(
            f'<div class="dc-dontadd">· {esc(line)}</div>' for line in dont_add_lines
        )
        dont_add_html = (
            f'<div class="dc-row dc-dontadd-row"><div class="dc-lab">别再加</div>'
            f'<div class="dc-val">{items}</div></div>'
        )

    # 基本面缺(护城河未评 或 无个股深研)→动作旁标"初判"，诚实说还没真正进决策
    moat_info = item.get("moat", {}) or {}
    moat_scored = moat_info.get("total_score") is not None
    has_research = has_pack(item.get("symbol"), item.get("name"))
    prelim_html = ""
    if (not moat_scored) or (not has_research):
        prelim_html = (
            '<div class="dc-prelim" style="color:#ffcf6b;font-size:12px;margin-top:5px;line-height:1.6;">'
            '（这是按方向/位置/估值的<b>初判</b>；护城河/深研还没做、还没真正进决策，待补全再定）</div>'
        )
    # "现在：…"翻译已含允许的 <b>…</b>，不整体转义；紧跟徽章、显眼一行
    now_row = f'<div class="dc-row dc-now"><div class="dc-lab">今天<br>该做啥</div><div class="dc-val">{now_line}{prelim_html}</div></div>'

    return f"""
    <div class="dc-card {tone}">
      <div class="dc-top">
        <div class="dc-title">{esc(name)}（{esc(symbol)}）</div>
        <div class="dc-badge {tone}">{badge_text}</div>
      </div>
      {tiny_html}
      {now_row}
      {ladder}
      <div class="dc-row"><div class="dc-lab">能不能<br>拿得住</div><div class="dc-val">{gate_block}</div></div>
      <div class="dc-row"><div class="dc-lab">我的成本·<br>现在赚还是亏</div><div class="dc-val">{cost_html}</div></div>
      <div class="dc-row"><div class="dc-lab">个股研究</div><div class="dc-val">{research}</div></div>
      <div class="dc-row dc-judge"><div class="dc-lab">为什么</div><div class="dc-val">{reason_html}</div></div>
      {dont_add_html}
    </div>
    """


def color_item(text: str, color: str) -> str:
    return f'<li style="color:{color};">{esc(text)}</li>'


def plain_items(items: list[str]) -> str:
    return "".join(f"<li>{esc(item)}</li>" for item in items)


def name_arrow(current: dict[str, Any], candidate: dict[str, Any]) -> str:
    return f"{current.get('name')}→{candidate.get('name')}"


def build_today_state(daily: dict[str, Any], production: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]]) -> dict[str, Any]:
    layer_strengths = {
        str(link.get("node")): link.get("strength")
        for link in daily.get("links", [])
        if link.get("node")
    }
    holding_levels: dict[str, str] = {}
    target_hits: dict[str, bool] = {}
    name_by_symbol: dict[str, str] = {}
    price_by_symbol: dict[str, Any] = {}
    ma50_by_symbol: dict[str, Any] = {}
    ma200_by_symbol: dict[str, Any] = {}
    target_by_symbol: dict[str, Any] = {}

    for item in production.get("holdings", []):
        symbol = str(item.get("symbol") or "")
        if not symbol:
            continue
        name_by_symbol[symbol] = str(item.get("name") or symbol)
        ma = ma_by_symbol.get(symbol)
        price = ma.get("realtime_price") if ma else None
        price_by_symbol[symbol] = price
        ma50_by_symbol[symbol] = ma.get("ma50") if ma else None
        ma200_by_symbol[symbol] = ma.get("ma200") if ma else None
        if not ma or ma.get("ma50") is None or ma.get("ma200") is None or price is None:
            level_key = "待拉"
        else:
            try:
                price_num = float(price)
                ma50_num = float(ma.get("ma50"))
                ma200_num = float(ma.get("ma200"))
            except (TypeError, ValueError):
                level_key = "待拉"
            else:
                if price_num <= ma200_num:
                    level_key = "止损"
                elif price_num <= ma50_num:
                    level_key = "低吸"
                else:
                    level_key = "均线上方"
        holding_levels[symbol] = level_key

        base = symbol.split(".")[-1]
        target = target_by_base.get(base) or target_by_base.get(symbol)
        take_profit = target.get("take_profit") if target else None
        target_by_symbol[symbol] = take_profit
        try:
            target_hits[symbol] = bool(take_profit is not None and price is not None and float(price) >= float(take_profit))
        except (TypeError, ValueError):
            target_hits[symbol] = False

    opp = production.get("opportunity_pool", {})
    opp_ch1 = [
        name_arrow(comp.get("current_holding", {}), comp.get("candidate", {}))
        for comp in opp.get("channel_1_swap_comparisons", []) or []
    ]
    opp_ch2 = [
        str(item.get("name"))
        for item in opp.get("channel_2_new_opportunities", []) or []
        if item.get("name")
    ]
    return {
        "date": None,
        "layer_strengths": layer_strengths,
        "holding_levels": holding_levels,
        "target_hits": target_hits,
        "opp_ch1": opp_ch1,
        "opp_ch2": opp_ch2,
        "name_by_symbol": name_by_symbol,
        "price_by_symbol": price_by_symbol,
        "ma50_by_symbol": ma50_by_symbol,
        "ma200_by_symbol": ma200_by_symbol,
        "target_by_symbol": target_by_symbol,
    }


def write_inspection_baseline(date: str, state: dict[str, Any]) -> None:
    out_dir = ROOT / "data" / "inspection"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "layer_strengths": state.get("layer_strengths", {}),
        "holding_levels": state.get("holding_levels", {}),
        "target_hits": state.get("target_hits", {}),
        "opp_ch1": state.get("opp_ch1", []),
        "opp_ch2": state.get("opp_ch2", []),
    }
    path = out_dir / f"baseline_{date}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError("inspection baseline write/read mismatch")
    if "\ufffd" in reread:
        raise RuntimeError("inspection baseline contains U+FFFD")


def latest_previous_baseline(date: str) -> dict[str, Any] | None:
    out_dir = ROOT / "data" / "inspection"
    if not out_dir.exists():
        return None
    candidates: list[tuple[str, Path]] = []
    for path in out_dir.glob("baseline_*.json"):
        baseline_date = path.stem.replace("baseline_", "")
        if baseline_date < date:
            candidates.append((baseline_date, path))
    if not candidates:
        return None
    _, latest_path = sorted(candidates)[-1]
    return read_json(latest_path)


def change_items(date: str, state: dict[str, Any]) -> list[str]:
    prev = latest_previous_baseline(date)
    if prev is None:
        return ["B类·变化提醒：明日起生效（今日首次存基线，需攒够前一日快照才能比对变化）"]
    changes: list[str] = []
    prev_layers = prev.get("layer_strengths", {})
    for node, strength in state.get("layer_strengths", {}).items():
        old = prev_layers.get(node)
        if old is not None and old != strength:
            changes.append(f"{node} 力度 {old}→{strength}，请确认")
    prev_levels = prev.get("holding_levels", {})
    for symbol, level in state.get("holding_levels", {}).items():
        old = prev_levels.get(symbol)
        if old is not None and old != level:
            changes.append(f"{state['name_by_symbol'].get(symbol, symbol)} 从「{old}」变「{level}」，请确认")
    prev_hits = prev.get("target_hits", {})
    for symbol, hit in state.get("target_hits", {}).items():
        if hit and not prev_hits.get(symbol):
            changes.append(f"{state['name_by_symbol'].get(symbol, symbol)} 新到目标价，请确认")
    old_opp2 = set(prev.get("opp_ch2", []))
    for name in state.get("opp_ch2", []):
        if name not in old_opp2:
            changes.append(f"机会池新进：{name}，请确认")
    return changes or ["较昨日无关键状态变化"]


def inspection_panel(date: str, daily: dict[str, Any], production: dict[str, Any], ma_by_symbol: dict[str, dict[str, Any]], target_by_base: dict[str, dict[str, Any]]) -> str:
    state = build_today_state(daily, production, ma_by_symbol, target_by_base)
    d_items: list[str] = []
    for symbol, level in state["holding_levels"].items():
        name = state["name_by_symbol"].get(symbol, symbol)
        price = state["price_by_symbol"].get(symbol)
        ma50 = state["ma50_by_symbol"].get(symbol)
        ma200 = state["ma200_by_symbol"].get(symbol)
        target = state["target_by_symbol"].get(symbol)
        if level == "止损":
            d_items.append(color_item(f"🔴 {name} 跌破年线（一年平均价）·危险·考虑减/止损（现价{fmt_level(price)}/年线{fmt_level(ma200)}）", "#f0616d"))
        elif level == "低吸":
            d_items.append(color_item(f"🟢 {name} 回踩到50日均价·便宜区·可考虑低吸（现价{fmt_level(price)}/50日线{fmt_level(ma50)}）", "#3ec38a"))
        if state["target_hits"].get(symbol):
            d_items.append(color_item(f"🟠 {name} 涨到了我们的目标价·考虑减仓（现价{fmt_level(price)}/目标{fmt_level(target)}）", "#ffa657"))
    if not d_items:
        d_items.append("<li>今天没有持仓碰到关键价（便宜价/危险价/目标价）</li>")
    weak_items = [
        color_item(f"⚠ {node} 这条判断的证据{plain_strength(strength)}（战略线要留意·请复核）", "#ffd479")
        for node, strength in state["layer_strengths"].items()
        if strength in ("弱", "证伪")
    ]
    if not weak_items:
        weak_items.append("<li>今天没有哪条判断证据转软或被推翻</li>")
    opp_ch1 = state.get("opp_ch1", [])
    opp_ch2 = state.get("opp_ch2", [])
    opp_line = f"机会池：{len(opp_ch1)}个换仓对比、{len(opp_ch2)}个新机会，等你看"
    if opp_ch1 or opp_ch2:
        opp_line += "；点下方⑥机会池查看"

    ma_pending = [symbol for symbol, item in ma_by_symbol.items() if item.get("status") != "OK"]
    true_target_count = sum(
        1
        for symbol in state["holding_levels"]
        if (target_by_base.get(symbol.split(".")[-1]) or target_by_base.get(symbol) or {}).get("take_profit") is not None
    )
    target_pending_count = len(state["holding_levels"]) - true_target_count
    moat_pending_count = sum(
        1 for item in production.get("holdings", [])
        if item.get("moat", {}).get("total_score") is None
    )
    # 宏观"接没接"读真实接入状态(单一来源=求证表)，已被某环用上的标"已接入"·禁写死"没接"(治#1/2/3/16)
    _re = daily.get("rule_engine", {}) or {}
    _macro_cal = (_re.get("macro_news", {}) or {}).get("fetched", {}).get("macro_calendar", {}) or {}
    _inputs = _re.get("inputs_used", {}) or {}
    _curve_ok = bool(_inputs.get("yield_curve") and "缺" not in str(_inputs.get("yield_curve")))
    _stable_ok = (ROOT / "data" / "onchain" / "stablecoin_supply_latest.csv").exists()
    _connected, _pending = [], []
    ("非农PAYEMS" in _macro_cal) and _connected.append("非农(FRED·总闸②在用)")
    ("CPI" in _macro_cal) and _connected.append("CPI(FRED·总闸②在用)")
    _curve_ok and _connected.append("收益率曲线(⑤资金在用)")
    _stable_ok and _connected.append("稳定币市值")
    ("非农PAYEMS" not in _macro_cal) and _pending.append("非农")
    ("CPI" not in _macro_cal) and _pending.append("CPI/PCE")
    _pending.append("FIMA(靠人读美联储公告·非数字接口)")
    _pending.append("真2年美债(现用3月^IRX替代)")
    _curve_ok or _pending.append("收益率曲线")
    _stable_ok or _pending.append("稳定币市值")
    macro_status_line = (
        f"宏观数据：已接入 {'、'.join(_connected) if _connected else '无'}；还没接 {'、'.join(_pending)}"
    )
    c_items = [
        f"均价线还没拉到：{('、'.join(ma_pending) if ma_pending else '无')}",
        f"目标价还没做（DCF=按公司未来能赚的钱倒推它值多少）：{target_pending_count}只",
        macro_status_line,
        f"护城河（靠什么长期赚钱）还没评：{moat_pending_count}只",
        "还知道有两处没做：板块自动更新（分类规则还没定）、迷你趋势图（还没存够历史数据）",
    ]

    b_items = change_items(date, state)
    write_inspection_baseline(date, state)

    return f"""
    <details class="card inspect" open>
      <summary><span>🔔 今日巡检提醒（每天先看这里）</span><b>自动汇总</b></summary>
      <h3 style="color:#ffcf6b;">D 需你拍板</h3>
      <ul>{''.join(d_items)}{''.join(weak_items)}<li>{esc(opp_line)}</li></ul>
      <h3>C 还缺的数据（等补上）</h3>
      <ul>{plain_items(c_items)}</ul>
      <h3>A 已自动刷好（这些不用你管）</h3>
      <ul><li>今天这些都自动算好了：宏观指标、每只持仓的均价线和便宜/危险价、现价、各层判断今天证据有多硬——这些不用你管。</li></ul>
      <h3>B 和昨天比有变化·要你确认</h3>
      <ul>{plain_items(b_items)}</ul>
    </details>
    """


def asset_by_symbol(snapshot: dict[str, Any], symbol: str) -> dict[str, Any] | None:
    for asset in snapshot.get("assets", []):
        if asset.get("symbol") == symbol:
            return asset
    return None


def fmt_number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "待接入"
    try:
        return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def fmt_pct(value: Any) -> str:
    if value is None:
        return "待接入"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.1f}%"


def chain_logic_section(daily: dict[str, Any]) -> str:
    logic = daily.get("chain_logic")
    if not isinstance(logic, dict) or not logic:
        return ""
    cards = [
        ("传导链", logic.get("传导链"), "#d9e7ef"),
        ("⚠ 核心张力", logic.get("核心张力"), "#ffcf6b"),
        ("跨层结论", logic.get("跨层结论"), "#d9e7ef"),
        ("对持仓的影响", logic.get("对持仓的影响"), "#d9e7ef"),
    ]
    body = []
    for title, value, color in cards:
        if value is None:
            value = "待填"
        body.append(
            f'<section style="background:#101b26;border:1px solid #2b4054;border-radius:8px;padding:10px 12px;">'
            f'<h3 style="margin:0 0 6px;color:{color};font-size:16px;">{esc(title)}</h3>'
            f'<p style="margin:0;color:{color};font-size:15px;line-height:1.7;">{esc(value)}</p>'
            f'</section>'
        )
    return f"""
    <section class="card" style="padding:14px 16px;margin:0 0 14px;border-color:#43627e;background:#13283a;">
      <h2 style="margin:0 0 10px;color:#9ed8ff;font-size:19px;">🔗 今日证据链贯穿 · 自上而下 + 张力</h2>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">{''.join(body)}</div>
    </section>
    """


def macro_badge(status: str, sentence: str) -> str:
    color = {"顺风": "#3ec38a", "逆风": "#f0616d", "中性": "#ffd479", "待接入": "#9aa8b5"}.get(status, "#ffd479")
    # 状态词已是人话（顺风=对我们有利/逆风=对我们不利/中性=没啥影响）；待接入换成大白话
    status_disp = {"待接入": "这项还没接进来"}.get(status, status)
    return f'<span style="color:{color};font-weight:700;">{esc(status_disp)}</span> {esc(sentence)}'


def macro_row(indicator: str, today: str, status: str, sentence: str) -> str:
    return f"<tr><td>{esc(indicator)}</td><td>{esc(today)}</td><td>{macro_badge(status, sentence)}</td></tr>"


def stablecoin_supply_row() -> tuple[str, str]:
    path = ROOT / "data" / "onchain" / "stablecoin_supply_latest.csv"
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        by_asset = {row.get("asset"): row for row in rows}
        usdt = float(by_asset["USDT"]["value"])
        usdc = float(by_asset["USDC"]["value"])
        date_text = str(by_asset["USDT"].get("time") or "")[:10]
        if not date_text:
            date_text = str(by_asset["USDC"].get("time") or "")[:10]
    except Exception:
        return "待接入·稳定币源读取失败", "待接入·稳定币源读取失败"
    today = f"USDT ${usdt / 1e9:.1f}B + USDC ${usdc / 1e9:.1f}B = 合计 ${(usdt + usdc) / 1e9:.1f}B"
    sentence = f"数据日期{date_text}·偏旧需定期刷（月度级）"
    return today, sentence


def macro_section(snapshot: dict[str, Any], yield_curve: dict[str, Any] | None = None,
                  daily: dict[str, Any] | None = None) -> str:
    rows: list[str] = []
    # 已接入的宏观真值(单一来源=求证表第二块 rule_engine.macro_news.fetched)
    macro_cal = (((daily or {}).get("rule_engine", {}) or {}).get("macro_news", {}) or {}).get("fetched", {}).get("macro_calendar", {}) or {}

    vix = asset_by_symbol(snapshot, "^VIX")
    if vix:
        price = float(vix.get("price", 0))
        change = float(vix.get("change_percent", 0))
        if price < 20:
            status, sentence = "顺风", "市场安心、敢冒险"
        elif price <= 28:
            status, sentence = "中性", "情绪一般"
        else:
            status, sentence = "逆风", "恐慌、先避险"
        if change > 20:
            sentence += "；今日突然飙升，警惕"
        rows.append(macro_row("VIX(市场怕不怕)", f"{fmt_number(price)} / {fmt_pct(change)}", status, sentence))
    else:
        rows.append(macro_row("VIX(市场怕不怕)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    us10y = asset_by_symbol(snapshot, "US10Y")
    if us10y:
        price = float(us10y.get("price", 0))
        change = float(us10y.get("change_percent", 0))
        high_note = "(利率水平已偏高)" if price > 4.5 else ""
        if change > 1:
            status, sentence = "逆风", f"利率上行{high_note}、压制成长股"
        elif change < -1:
            status, sentence = "顺风", f"利率回落{high_note}、利好"
        else:
            status, sentence = "中性", f"利率变化不大{high_note}"
        rows.append(macro_row("US10Y(10年美债利率)", f"{fmt_number(price, 3)} / {fmt_pct(change)}", status, sentence))
    else:
        rows.append(macro_row("US10Y(10年美债利率)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    dxy = asset_by_symbol(snapshot, "DXY")
    if dxy:
        price = float(dxy.get("price", 0))
        change = float(dxy.get("change_percent", 0))
        if change > 0.5:
            status, sentence = "逆风", "美元走强、全球流动性收紧"
        elif change < -0.5:
            status, sentence = "顺风", "美元回落、利好风险资产"
        else:
            status, sentence = "中性", "美元变化不大"
        rows.append(macro_row("DXY(美元强弱)", f"{fmt_number(price, 3)} / {fmt_pct(change)}", status, sentence))
    else:
        rows.append(macro_row("DXY(美元强弱)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    soxx = asset_by_symbol(snapshot, "SOXX")
    if soxx:
        price = float(soxx.get("price", 0))
        change = float(soxx.get("change_percent", 0))
        if change > 1:
            status, sentence = "顺风", "AI承接板块走强"
        elif change < -1:
            status, sentence = "逆风", "AI承接板块回调"
        else:
            status, sentence = "中性", "AI承接板块变化不大"
        rows.append(macro_row("SOXX(半导体温度=AI承接板块)", f"{fmt_number(price)} / {fmt_pct(change)}", status, sentence))
    else:
        rows.append(macro_row("SOXX(半导体温度=AI承接板块)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    spx = asset_by_symbol(snapshot, "SPX")
    if spx:
        price = spx.get("price")
        change = spx.get("change_percent")
        rows.append(macro_row("SPX(大盘)", f"{fmt_number(price)} / {fmt_pct(change)}", "中性", f"大盘今日{fmt_pct(change)}"))
    else:
        rows.append(macro_row("SPX(大盘)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    usdjpy = asset_by_symbol(snapshot, "USDJPY")
    if usdjpy:
        price = usdjpy.get("price")
        change = usdjpy.get("change_percent")
        rows.append(macro_row("USDJPY(美元日元·影响日股汇率)", f"{fmt_number(price, 3)} / {fmt_pct(change)}", "中性", f"美元/日元{fmt_number(price, 3)}，日股换算需留意"))
    else:
        rows.append(macro_row("USDJPY(美元日元·影响日股汇率)", "这项还没接进来", "待接入", "这项数据还没接进来·源没连"))

    # 非农/CPI：已被②总闸用上的 FRED 真值→标"已接入(来源+日期)"，禁写死"没接"(治#1/2)
    nonfarm = macro_cal.get("非农PAYEMS")
    if nonfarm:
        rows.append(macro_row("非农(每月新增就业人数·看经济冷热)",
                              f"{fmt_number(nonfarm.get('value'), 0)}千（{nonfarm.get('date')}）", "中性",
                              "已接入·FRED经济日历(总闸②在用)；月度级、非当日"))
    else:
        rows.append(macro_row("非农(每月新增就业人数·看经济冷热)", "这项还没接进来", "待接入", "FRED经济日历本次没取到·待接"))
    cpi = macro_cal.get("CPI")
    if cpi:
        rows.append(macro_row("CPI/PCE(物价涨得快不快·通胀)",
                              f"CPI指数{fmt_number(cpi.get('value'), 1)}（{cpi.get('date')}）", "中性",
                              "已接入·FRED经济日历(总闸②在用)；月度级、非当日"))
    else:
        rows.append(macro_row("CPI/PCE(物价涨得快不快·通胀)", "这项还没接进来", "待接入", "FRED经济日历本次没取到·待接"))
    rows.append(macro_row("FIMA对谁开关(美联储给谁开美元供应的龙头)", "这项还没接进来", "待接入", "这项要靠人读美联储公告来判·不是数字接口·真没接"))
    stable_today, stable_sentence = stablecoin_supply_row()
    stable_status = "待接入" if stable_today.startswith("待接入") else "中性"
    rows.append(macro_row("稳定币市值(链上有多少'数字美元'·加密市场的水位)", stable_today, stable_status, stable_sentence))
    yc = yield_curve or {}
    if yc.get("connection", {}).get("ok") and yc.get("spread_10y_3m") is not None:
        us10y = yc.get("us10y")
        us3m = yc.get("us3m")
        spread = yc.get("spread_10y_3m")
        inv = yc.get("inverted")
        status = "逆风" if inv else "中性"
        sentence = "曲线倒挂·历史衰退信号，警惕" if inv else "曲线正斜率·未倒挂"
        _yc_dd = yc.get("data_date") or yc.get("date")
        sentence += f"（已接入·⑤资金在用；最近快照{_yc_dd}；短端用3月^IRX，非2年，真2年待FRED源）"
        rows.append(macro_row("收益率曲线(10年-3月)(长短期利率谁高·倒挂常预警衰退)", f"10年{fmt_level(us10y)} − 3月{fmt_level(us3m)} = 利差{fmt_level(spread)}%", status, sentence))
    else:
        rows.append(macro_row("收益率曲线(10年-3月)(长短期利率谁高·倒挂常预警衰退)", "这项还没接进来·源没连", "待接入", "收益率曲线的数据源还没连上"))

    return f"""
    <details class="card" open>
      <summary><span>⑦ 宏观指标读数（钱往哪流·外部读数先机器粗读一遍·细看由人来判）</span><b>宏观</b></summary>
      <p class="plain">这些是"钱往哪流"这一层今天的外部读数，只做机器初步粗读；接不到的就标"还没接进来"，绝不拿旧数字冒充。状态词：顺风=眼下对我们有利、逆风=对我们不利、中性=没啥影响。</p>
      <table><thead><tr><th>看的是啥</th><th>今天数值</th><th>怎么读（对我们利不利）</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    </details>
    """


def opportunity_section(production: dict[str, Any]) -> str:
    pool = production.get("opportunity_pool", {})
    ch1 = pool.get("channel_1_swap_comparisons", [])
    ch2 = pool.get("channel_2_new_opportunities", [])

    # 通道① 换仓对比 → 每对一张卡：要不要把手里的换成候选？（默认保守·不自创买卖）
    ch1_cards: list[str] = []
    for item in ch1[:8]:
        current = item.get("current_holding", {}) or {}
        candidate = item.get("candidate", {}) or {}
        candidate_moat = item.get("candidate_moat", {}) or {}
        current_moat = item.get("current_moat", {}) or {}
        weak = candidate_moat.get("total_score") is None
        cur_name = esc(current.get("name"))
        cand_name = esc(candidate.get("name"))
        cur_phrase = plain_moat_phrase(current_moat)
        if weak:
            tone = "dc-soft"
            badge_text = "先别换"
            today_line = "今天先别换。"
            why = (
                f"手里的〔{cur_name}〕靠什么长期赚钱、护城河硬不硬我们已经研究清楚了（{cur_phrase}）；"
                f"但〔{cand_name}〕我们还没研究过它靠什么长期赚钱、护城河硬不硬。没弄明白之前，不瞎换。"
            )
        else:
            tone = "dc-hi"
            badge_text = "可考虑换（先别急）"
            today_line = "可以考虑换，但先别急——还要人工再核一遍。"
            cand_phrase = plain_moat_phrase(candidate_moat)
            why = (
                f"手里的〔{cur_name}〕靠什么长期赚钱、护城河硬不硬我们已经研究清楚了（{cur_phrase}）；"
                f"新候选〔{cand_name}〕靠什么长期赚钱我们也摸清了（{cand_phrase}），证据也够了，可以人工再深入比一比谁更值得拿。"
            )
        title = f"要不要把手里的〔{cur_name}〕换成〔{cand_name}（{esc(candidate.get('code'))}）〕？"
        ch1_cards.append(
            f"""
    <div class="dc-card {tone}">
      <div class="dc-top">
        <div class="dc-title">{title}</div>
        <div class="dc-badge {tone}">{esc(badge_text)}</div>
      </div>
      <div class="dc-row dc-now"><div class="dc-lab">今天答复</div><div class="dc-val">{today_line}</div></div>
      <div class="dc-row dc-judge"><div class="dc-lab">为什么</div><div class="dc-val">{why}</div></div>
    </div>"""
        )
    ch1_html = "".join(ch1_cards) if ch1_cards else '<p class="plain">今天没有可换的对比。</p>'

    # 通道② 新机会 → 每项一张卡：新冒出的候选（默认只观察·不下买入结论）
    ch2_cards: list[str] = []
    for item in ch2[:12]:
        moat = item.get("moat", {}) or {}
        weak = moat.get("total_score") is None
        name_e = esc(item.get("name"))
        node_class = str(item.get("node_class") or "").strip()
        node_h = f"它归在「{esc(node_class)}」这条线上" if node_class else "它的所属线还没归好"
        if weak:
            tone = "dc-soft"
            badge_text = "先只观察·不买"
            today_line = "今天先只观察、不买。"
            why = f"{node_h}；但我们还没研究透它靠什么长期赚钱、护城河硬不硬，先不下买入结论。"
        else:
            tone = "dc-hi"
            badge_text = "可深研·先别买"
            today_line = "证据够了，可以深入研究（但今天先别急着买）。"
            why = f"{node_h}；它靠什么长期赚钱、护城河硬不硬我们摸清了（{plain_moat_phrase(moat)}），证据也够了，可以进一步深研。"
        title = f"新冒出的候选：{name_e}（{esc(item.get('code'))}）"
        ch2_cards.append(
            f"""
    <div class="dc-card {tone}">
      <div class="dc-top">
        <div class="dc-title">{title}</div>
        <div class="dc-badge {tone}">{esc(badge_text)}</div>
      </div>
      <div class="dc-row dc-now"><div class="dc-lab">今天答复</div><div class="dc-val">{today_line}</div></div>
      <div class="dc-row dc-judge"><div class="dc-lab">为什么</div><div class="dc-val">{why}</div></div>
    </div>"""
        )
    ch2_html = "".join(ch2_cards) if ch2_cards else '<p class="plain">今天没有新冒出的候选。</p>'

    return f"""
    <details class="card" open>
      <summary><span>⑧ 机会池双通道</span><b>动态</b></summary>
      <p class="plain">这一栏在问两件事：一是手里的能不能换成更好的同类，二是有没有新冒出来的机会。凡是我们还没研究透它靠什么长期赚钱（护城河）的，今天一律先观察，不下买卖结论。</p>
      <h3>手里的能不能换成更好的？（换仓对比）</h3>
      {ch1_html}
      <h3>有没有新冒出来的机会？（新机会）</h3>
      {ch2_html}
    </details>
    """


def iteration_action(certainty: Any) -> tuple[str, str]:
    """按确定性 derive 一个迭代动作(动作文字HTML, 颜色)。只给建议/提醒，不自动执行。
    动作文字为本函数自撰的静态文案，内含<b>标签为有意HTML，不经esc；确定性取值由调用处另行esc。"""
    c = "" if certainty is None else str(certainty).strip()
    if c == "强":  # 把握标度归一：力度词"强"≡把握"高"(治#15·与把握列一致)
        c = "高"
    if c == "高":
        return (
            "🎓 毕业候选：这条判断连续判对了，可以升级成“系统自动判”（<b>但要你点头</b>，动的是系统的魂，不自动毕业）",
            "#3ec38a",
        )
    if c == "证伪":
        return ("🔥 回炉：这条判断被事实推翻了，得回去重审这把尺、改走备用思路", "#f0616d")
    if c == "弱":
        return ("⚠ 收着点：我们对这条判断把握小，先只守核心、别放大", "#ffd479")
    if c == "中":
        return ("⏳ 继续观察：把握一般，继续每天验证，攒够了再升级", "#9aa8b5")
    return ("— 还在攒把握", "#9aa8b5")


def pdca_section(pdca_daily: dict[str, Any], pdca_review: dict[str, Any]) -> str:
    quality = pdca_daily.get("decision_quality", {})
    ring_list = pdca_daily.get("rings", [])
    rings = []
    for ring in ring_list:
        act_text, act_color = iteration_action(ring.get("current_certainty"))
        rings.append(
            f"<tr><td>{esc(ring.get('ring_name'))}</td><td>{esc(plain_strength(ring.get('strength')))}</td>"
            f"<td>{esc(ring.get('daily_score'))}</td><td>{esc(plain_certainty(ring.get('current_certainty')))}</td>"
            f"<td>{esc(ring.get('score_reason'))}</td>"
            f"<td><span style=\"color:{act_color};font-weight:700;\">{act_text}</span></td></tr>"
        )
    tracks = []
    for item in pdca_review.get("certainty_trajectories", []):
        tracks.append(f"<li>{esc(item.get('ring_name'))}：累计得分 {esc(item.get('cumulative_score'))}，把握变化过程 {esc(item.get('certainty_path_text'))}</li>")
    weekly = pdca_review.get("multi_scale", {}).get("weekly", {})

    # ⑦复盘·5迭代动作：全部现算(从数据来)，只作建议/提醒，毕业/回炉不自动执行
    # 迭代动作1：每环一条(按每环确定性 derive)
    act_lines = []
    for ring in ring_list:
        act_text, act_color = iteration_action(ring.get("current_certainty"))
        act_lines.append(
            f"<li><b>{esc(ring.get('ring_name'))}</b>（我们的把握：{esc(plain_certainty(ring.get('current_certainty')))}）："
            f"<span style=\"color:{act_color};\">{act_text}</span></li>"
        )
    act_lines_html = "".join(act_lines) if act_lines else "<li>暂无环节数据</li>"

    # 迭代动作·毕业候选：确定性=高 的环
    grad_rings = [esc(r.get("ring_name")) for r in ring_list if str(r.get("current_certainty") or "").strip() == "高"]
    grad_text = "、".join(grad_rings) + "（<b>需董事长点头才升级为自动判，不自动毕业</b>）" if grad_rings else "暂无可毕业"
    # 迭代动作·回炉：确定性=证伪 的环
    reforge_rings = [esc(r.get("ring_name")) for r in ring_list if str(r.get("current_certainty") or "").strip() == "证伪"]
    reforge_text = "、".join(reforge_rings) + "：被证伪，重审这把尺、切备用逻辑" if reforge_rings else "无需回炉"
    # 迭代动作·调力度：读 decision_quality.level
    level = str(quality.get("level") or "").strip()
    tune_map = {
        "高": "可敢重仓/放机会池",
        "中": "收着点只守核心",
        "低": "停用相关逻辑切备用",
    }
    tune_text = tune_map.get(level, "先攒够底气再说")
    tune_full = f"今天下手的底气：{esc(plain_decision_quality(quality.get('level')))} → {tune_text}"
    # 迭代动作·沉淀新规则：读 pdca_review 若有 new_rules/sediment
    sediment = pdca_review.get("new_rules") or pdca_review.get("sediment")
    if sediment:
        if isinstance(sediment, list):
            sediment_text = "、".join(esc(x) for x in sediment)
        else:
            sediment_text = esc(sediment)
    else:
        sediment_text = "本期无新沉淀规则（理解岗发现随时补）"
    # 迭代动作·迭代清单：读 pdca_review.multi_scale.monthly 若有则列
    monthly = pdca_review.get("multi_scale", {}).get("monthly", {})
    monthly_items = None
    if isinstance(monthly, dict):
        monthly_items = monthly.get("items") or monthly.get("actions") or monthly.get("iterations")
    if monthly_items:
        if isinstance(monthly_items, list):
            iter_text = "、".join(esc(x) for x in monthly_items)
        else:
            iter_text = esc(monthly_items)
    else:
        iter_text = "待月度触发（定期出'该改什么'走董事长拍板）"

    return f"""
    <details class="card" open>
      <summary><span>⑩ 复盘记分卡（看我们最近判得准不准·该升级还是该回炉）</span><b>{esc(plain_decision_quality(quality.get('level')))}</b></summary>
      <p class="plain">今天下手的底气：{esc(plain_decision_quality(quality.get('level')))}（决策质量分=今天我们出手有多有把握），为什么：{esc(quality.get('reason'))}</p>
      <table><thead><tr><th>这一环</th><th>证据有多硬</th><th>今天打分</th><th>我们的把握</th><th>为什么</th><th>接下来该怎么办</th></tr></thead><tbody>{''.join(rings)}</tbody></table>
      <ul>{''.join(tracks)}</ul>
      <div class="meta">周复盘：{esc(weekly.get('status', '待累积'))}</div>
      <h3>⑦复盘·5迭代动作</h3>
      <p class="plain">复盘不是打完分就完——按每一环我们的把握，给出接下来该往哪走。下面都是<b>建议/提醒</b>，毕业（升级成系统自动判）、回炉（推翻重审）都不自动执行，动系统的魂要你点头。</p>
      <p class="plain">每一环接下来该怎么办（按我们的把握现算）：</p>
      <ul>{act_lines_html}</ul>
      <p class="plain">5迭代动作汇总（大白话）：</p>
      <ul>
        <li><b>① 毕业候选</b>（判得准的可升级为自动判）：{grad_text}</li>
        <li><b>② 回炉</b>（被证伪的重审换尺）：{reforge_text}</li>
        <li><b>③ 调力度</b>（按今天下手的底气·该收还是该放）：{tune_full}</li>
        <li><b>④ 沉淀新规则</b>（把这次学到的攒成规矩）：{sediment_text}</li>
        <li><b>⑤ 迭代清单</b>（该改什么·走董事长拍板）：{iter_text}</li>
      </ul>
    </details>
    """


def right_ruler_card(no: str, title: str, filename: str, summary: str, anchor_id: str) -> str:
    # 徽章按内部真实审核状态标(治#19)：①世界观已过审；②-⑥结构定稿·左栏已在用、仍待董事长审
    badge = "尺·已过审" if no == "①" else "尺·待审(左栏已在用)"
    ruler_path = ROOT / "00_请先看这里" / filename
    if not ruler_path.exists():
        return f"""
    <details class="card static" id="{esc(anchor_id)}">
      <summary><span>{esc(no)} {esc(title)}</span><b>{esc(badge)}</b></summary>
      <p class="plain">缺底子文件：{esc(filename)}</p>
    </details>
    """
    ruler_text = ruler_path.read_text(encoding="utf-8")
    ask_pattern = '<div class="ask">.*' + chr(63) + '</div>'
    ruler_text = re.sub(ask_pattern, '', ruler_text, flags=re.DOTALL)
    srcdoc = html.escape(ruler_text, quote=True)
    return f"""
    <details class="card static" id="{esc(anchor_id)}" ontoggle="var f=this.querySelector('iframe'); if(f){{setTimeout(function(){{try{{f.style.height=f.contentWindow.document.documentElement.scrollHeight+'px';}}catch(e){{}}}},30);}}">
      <summary><span>{esc(no)} {esc(title)}</span><b>{esc(badge)}</b></summary>
      <p class="plain">{esc(summary)}</p>
      <iframe srcdoc="{srcdoc}" style="width:100%;height:600px;border:0;background:#0e1621;" onload="try{{this.style.height=this.contentWindow.document.documentElement.scrollHeight+'px';}}catch(e){{}}"></iframe>
    </details>
    """


def build(date: str) -> str:
    daily_path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    production_path = ROOT / "data" / "reports" / f"production_{date}.json"
    pdca_daily_path = ROOT / "data" / "pdca" / f"pdca_daily_{date}.json"
    pdca_review_path = ROOT / "data" / "pdca" / f"pdca_review_{date}.json"
    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{date}.json"
    ma_path = ROOT / "data" / "holdings" / f"ma_levels_{date}.json"
    val_path = ROOT / "data" / "valuation" / f"valuation_samples_v7_{date}.json"
    cost_path = ROOT / "data" / "accounts" / "unified_holdings_latest.json"
    yc_path = ROOT / "data" / "market" / f"yield_curve_{date}.json"
    snapshot_path = ROOT / "data" / "market" / "latest_market_snapshot.json"
    sources = [daily_path, production_path, pdca_daily_path, pdca_review_path, holdings_path]
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError("缺零件：" + "；".join(missing))

    daily = read_json(daily_path)
    production = read_json(production_path)
    pdca_daily = read_json(pdca_daily_path)
    pdca_review = read_json(pdca_review_path)
    holdings = read_json(holdings_path)
    ma = read_json(ma_path) if ma_path.exists() else {"holdings": []}
    ma_by_symbol = {item.get("symbol"): item for item in ma.get("holdings", []) if item.get("symbol")}
    val = read_json(val_path) if val_path.exists() else {}
    # 估值唯一来源=valuation 实例(model_instances)：持仓卡价位与估值判断同源(治#5/6/8-12)
    target_by_base: dict[str, dict[str, Any]] = targets_from_model_instances(
        ROOT / "data" / "valuation" / "model_instances"
    )
    # 若当日另有更细的 valuation_samples(买/卖/止损)则叠加覆盖，仍属估值体系单一链
    for sample in val.get("samples", {}).values():
        target = _build_target_from_sample(sample)
        symbol_key = sample.get("symbol")
        if symbol_key:
            target_by_base[str(symbol_key)] = target
        for alias in sample.get("aliases", []) or []:
            target_by_base[str(alias)] = target
    cost_data = read_json(cost_path) if cost_path.exists() else {}
    cost_by_ticker = {
        str(item.get("ticker")): item
        for item in cost_data.get("aggregate_by_ticker", [])
        if item.get("ticker")
    }
    # 收益率曲线：当日文件缺失则回退到最近快照(与⑤资金同源·单一来源)，避免⑦读数表标"源没连"而⑤在用(治#2)
    if yc_path.exists():
        yc = read_json(yc_path)
    else:
        _yc_snaps = sorted((ROOT / "data" / "market").glob("yield_curve_*.json"))
        yc = read_json(_yc_snaps[-1]) if _yc_snaps else {}
    snapshot = read_json(snapshot_path) if snapshot_path.exists() else {"assets": []}
    quality = pdca_daily.get("decision_quality", {})

    evidence_cards = [
        evidence_card("①", "世界观", find_link(daily, ["总命题", "世界"]), "①", "right-ruler-1"),
        evidence_card("②", "总闸", find_link(daily, ["总闸", "美联储"]), "③", "right-ruler-3"),
        evidence_card("③", "战略", find_link(daily, ["战略指向"]), "②", "right-ruler-2"),
        evidence_card("④", "手段层·资金管道(稳定币/加密)", find_link(daily, ["手段层"]), "③", "right-ruler-3"),
        evidence_card("⑤", "资金轮动", find_link(daily, ["资金轮动"]), "③", "right-ruler-3"),
        evidence_card("⑥", "板块轮动", find_link(daily, ["板块轮动"]), "④", "right-ruler-4"),
    ]
    concentration = portfolio_concentration(production.get("holdings", []))
    holding_cards = "".join(holding_decision_card(item, ma_by_symbol, target_by_base, cost_by_ticker, concentration) for item in production.get("holdings", []))
    try:
        judgment_html = judgment_card(date)
    except Exception:  # 判断包缺失/异常不报错，正常跳过
        judgment_html = ""
    try:
        stock_research_html = stock_research_section(production.get("holdings", []))
    except Exception:  # 个股研究缺失/异常不报错，正常跳过
        stock_research_html = ""
    # 判断包卡紧跟①世界观 evidence_card 之后、macro_section 之前
    evidence_html = evidence_cards[0] + judgment_html + "".join(evidence_cards[1:])
    left = evidence_html + macro_section(snapshot, yc, daily) + opportunity_section(production) + f"""
    {concentration_summary_table(concentration)}
    <details class="card" open>
      <summary><span>⑨ 持仓</span><b>{fmt_summary(production.get('holding_summary'))}</b></summary>
      <p class="plain">每只持仓一张决策卡：一个明确动作＋买卖价不打架＋看图现价落在哪区。只给守/卖/观望，不下单。上限类(AI/单一/加密)超标的持仓卡自动追加"别加"。</p>
      {holding_cards}
    </details>
    """ + stock_research_html + pdca_section(pdca_daily, pdca_review)

    right = "".join([
        right_ruler_card("①", "世界观", "右栏_完整世界观描述.html", "旧的全球化大水漫灌、大家一起涨时代结束，进入美国优先·阵营化·集中砸钱给AI的新秩序——这是全系统一切判断的最上层源头。", "right-ruler-1"),
        right_ruler_card("②", "国家战略地图", "右栏_完整国家战略地图.html", "美国把国家资源集中砸向三条线——AI(主线·钱最多)、安全、能源；你的核心仓正压在AI承接链(算力/设备/代工/盟友节点)上。", "right-ruler-2"),
        right_ruler_card("③", "资金流动机制", "右栏_资金流动完整机制.html", "美国在往市场里收紧钱（这叫'收水'）、只把钱精准放给战略方向（不是大家普涨）；这层看钱是松还是紧、往哪流、是大机构还是散户在动。", "right-ruler-3"),
        right_ruler_card("④", "板块地图", "右栏_板块地图.html", "只到板块不锚死个股，进攻群+防御群，用过去1季/现在本周/未来1季状态词+箭头看趋势，快慢分离更新(不追单日噪声)。", "right-ruler-4"),
        right_ruler_card("⑤", "过滤标准", "右栏_过滤标准筛选规则.html", "从全市场筛到值得看的五关漏斗——硬性方向→软性位置→估值→护城河→个股研究；规则固定，扫出的名单每天变。", "right-ruler-5"),
        right_ruler_card("⑥", "持仓档案", "右栏_持仓完整档案.html", "每只持仓的静态计划(股数/成本/替换思路)。⚠护城河/估值/目标价以左栏⑨持仓卡为准(单一来源=moat_analysis+valuation实例)；本静态档案若与之不一致，一律以左栏实时单一来源为准、不各写一份。低吸/止损价待均线补、数据待生产时自动灌。", "right-ruler-6"),
    ])

    # 页头主句用短版一句话方向(治#21 超长run-on)；长版折进"展开看各层"
    today_short = production.get("today_direction_short") or "今天：守核心、不追高、控AI集中"
    # 强弱标签统一一套词(治#27)：页头「状态·力度」里的力度 → 与卡片同用 很硬/一般/偏软
    today_long = unify_strength_words(production.get("today_direction"))
    today_sentence = today_short  # 主句=短版
    confidence_line = f"今天下手的底气：{plain_decision_quality(quality.get('level'))}，因为{quality.get('reason')}"
    # 页脚闭环只留一行简短因果，不整段复述 today_direction(治#22)
    w_dir = find_link(daily, ['总命题', '世界']).get('direction')
    f_dir = find_link(daily, ['总闸']).get('direction')
    s_dir = find_link(daily, ['战略指向']).get('direction')
    close_loop = f"闭环：世界观{w_dir} → 总闸{f_dir} → 战略{s_dir}，一条线推出今天「{today_short}」的口径。"

    # ⑤ 徽章按真实符合/受检数动态显示，不写死"五关全通"(治#14)
    hs = production.get("holding_summary", {}) or {}
    n_pass = hs.get("符合", 0)
    n_check = hs.get("受检", 0)
    n_pend = hs.get("待补", 0)
    # 受检=正在一关一关检查、还没走完五关(给小白一句解释·治#28)
    badge_text = (f"五关已接通·多数还在逐关检查中（符合{n_pass}/受检{n_check}"
                  + (f"/待补{n_pend}" if n_pend else "")
                  + "）·相对估值精算迭代中　※受检=正在一关一关查、还没走完五关")

    # A · 护城河重评提示：沿用超阈值 → 页首醒目横幅(只提示不改评级·总则第十二条)
    moat_reeval_msg = production.get("fingerprint", {}).get("moat_reeval_msg")
    moat_banner = (
        f'<div class="moat-reeval">⚠ 护城河重评提示 · {esc(moat_reeval_msg)}</div>'
        if moat_reeval_msg else ""
    )

    fingerprint = {
        "date": date,
        "framework_fixed": True,
        "answers_from_parts": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [str(path) for path in sources],
    }

    # 行情实际日期(单一来源=求证表 inputs_used.snapshot_data_date)，与运行日区分标清(治#13)
    _snap_dd = str((daily.get("rule_engine", {}) or {}).get("inputs_used", {}).get("snapshot_data_date", ""))[:10]
    market_date_text = _snap_dd if _snap_dd else "待接"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>每日投资决策台</title>
  <style>
    body{{margin:0;background:#0b1118;color:#eef5f9;font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.65;}}
    .wrap{{max-width:1440px;margin:0 auto;padding:22px 18px 70px;}}
    header{{background:#151f2b;border:1px solid #2b4054;border-radius:12px;padding:18px 20px;margin-bottom:14px;}}
    h1{{margin:0 0 8px;font-size:25px;}}
    .badge{{display:inline-block;background:#5b2b22;color:#ffcfbd;border-radius:999px;padding:4px 12px;font-weight:700;margin-bottom:8px;}}
    .today{{font-size:18px;color:#ffcf6b;font-weight:700;}}
    .today-conf{{font-size:14px;color:#9ed8ff;margin-top:6px;}}
    .today-long{{margin-top:6px;}}
    .today-long>summary{{cursor:pointer;color:#8ea3b6;font-size:12.5px;list-style:revert;}}
    .today-long>div{{color:#c4d4e2;font-size:13px;line-height:1.7;margin-top:5px;}}
    .moat-reeval{{background:#3a2410;border:1px solid #b8791f;color:#ffd479;border-radius:10px;
      padding:10px 14px;margin:8px 0;font-weight:700;font-size:14.5px;}}
    .finger{{color:#8ea3b6;font-size:12px;margin-top:8px;}}
    .grid{{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(320px,.8fr);gap:14px;align-items:start;}}
    .col-title{{margin:0 0 10px;color:#9ed8ff;font-size:18px;}}
    .card{{background:#142231;border:1px solid #2b4054;border-radius:10px;margin-bottom:10px;padding:0;overflow:hidden;}}
    summary{{cursor:pointer;display:flex;justify-content:space-between;gap:12px;padding:13px 15px;background:#182b3b;color:#ffe2a8;font-size:16px;}}
    summary b{{color:#7ee0a0;white-space:nowrap;}}
    .static summary b{{color:#ffcf6b;}}
    .plain,.detail,.meta{{margin:10px 15px;}}
    .plain{{color:#d9e7ef;}}
    /* 大白话主文：最显眼 */
    .macro-plain{{margin:12px 15px;color:#eaf4fb;font-size:16px;line-height:1.7;font-weight:600;
      background:#122130;border-left:4px solid #3ec38a;border-radius:8px;padding:11px 14px;}}
    /* 术语版：收进二级·可不看 */
    .term-fold{{margin:8px 15px 12px;border:1px dashed #2b4054;border-radius:8px;}}
    .term-fold>summary{{cursor:pointer;color:#8ea3b6;font-size:12.5px;background:transparent;padding:8px 12px;}}
    .detail,.meta{{color:#93a9bc;font-size:13px;}}
    h3{{margin:14px 15px 6px;color:#cde7ff;}}
    table{{width:calc(100% - 30px);margin:10px 15px 15px;border-collapse:collapse;font-size:13px;}}
    th,td{{border:1px solid #2b4054;padding:7px 8px;text-align:left;vertical-align:top;}}
    th{{background:#101b26;color:#bcd0e2;}}
    td span{{color:#8ea3b6;font-size:12px;}}
    ul{{margin:10px 25px 16px;color:#d9e7ef;}}
    .event-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 15px 15px;}}
    .event-grid section{{background:#101b26;border:1px solid #2b4054;border-radius:8px;padding:8px 10px;}}
    .event-grid h3{{margin:0 0 4px;color:#9ed8ff;font-size:14px;}}
    .event-grid ul{{margin:5px 0 0 18px;padding:0;}}
    footer{{margin-top:14px;background:#111b26;border:1px solid #2b4054;border-radius:10px;padding:14px 16px;color:#ffcf6b;}}
    @media(max-width:980px){{.grid{{grid-template-columns:1fr;}}}}
    /* 决策卡（display-only·dc-前缀·不与现有 .card/.badge 冲突）
       配色沿用本页既有色板：good绿#3ec38a／bad红#f0616d／hi黄#ffd479／soft灰#9aa8b5／line#2b4054／card#142231 */
    .dc-card{{background:#142231;border:1px solid #2b4054;border-radius:12px;
      padding:16px 18px;margin-bottom:12px;border-left:5px solid #2b4054;overflow:hidden;}}
    .dc-card.dc-good{{border-left-color:#3ec38a;}}
    .dc-card.dc-bad{{border-left-color:#f0616d;}}
    .dc-card.dc-hi{{border-left-color:#ffd479;}}
    .dc-card.dc-soft{{border-left-color:#9aa8b5;}}
    .dc-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;}}
    .dc-title{{font-size:16.5px;font-weight:700;color:#eef5f9;}}
    .dc-badge{{flex:none;padding:5px 13px;border-radius:20px;font-size:13px;font-weight:700;white-space:nowrap;}}
    .dc-badge.dc-good{{background:rgba(62,195,138,.14);color:#3ec38a;border:1px solid #3ec38a;}}
    .dc-badge.dc-bad{{background:rgba(240,97,109,.14);color:#f0616d;border:1px solid #f0616d;}}
    .dc-badge.dc-hi{{background:rgba(255,212,121,.14);color:#ffd479;border:1px solid #ffd479;}}
    .dc-badge.dc-soft{{background:rgba(157,168,181,.14);color:#9aa8b5;border:1px solid #9aa8b5;}}
    .dc-row{{display:flex;gap:10px;margin-bottom:9px;font-size:14px;}}
    .dc-lab{{flex:none;color:#5cc8ff;font-weight:700;width:96px;}}
    .dc-val{{color:#eef5f9;flex:1;}}
    .dc-row.dc-judge .dc-val{{font-weight:700;}}
    .dc-card.dc-good .dc-row.dc-judge .dc-val{{color:#3ec38a;}}
    .dc-card.dc-bad .dc-row.dc-judge .dc-val{{color:#f0616d;}}
    .dc-card.dc-hi .dc-row.dc-judge .dc-val{{color:#ffd479;}}
    .dc-card.dc-soft .dc-row.dc-judge .dc-val{{color:#9aa8b5;}}
    .dc-mini{{margin-top:13px;padding-top:11px;border-top:1px dashed #2b4054;
      color:#9aa8b5;font-size:12.5px;font-style:italic;opacity:.75;}}
    /* "现在：…"翻译行·显眼（紧跟徽章，守家族语气） */
    .dc-row.dc-now{{background:rgba(92,200,255,.07);border:1px solid #2b4054;
      border-radius:8px;padding:9px 11px;margin-bottom:11px;}}
    .dc-row.dc-now .dc-lab{{color:#ffd479;}}
    .dc-row.dc-now .dc-val{{color:#eef5f9;font-weight:700;font-size:14px;line-height:1.6;}}
    .dc-row.dc-now .dc-val b{{color:#ffd479;}}
    .dc-caveat{{color:#9aa8b5;font-weight:400;font-size:12.5px;margin-left:4px;}}
    /* 仓位纪律"别加"（上限类超标·红/黄提示，与守家族并存不矛盾） */
    .dc-dontadd-row{{margin-top:10px;padding-top:9px;border-top:1px dashed #2b4054;}}
    .dc-dontadd-row .dc-lab{{color:#f0616d;}}
    .dc-dontadd{{background:rgba(240,97,109,.10);border:1px solid #f0616d;border-radius:7px;
      padding:6px 10px;margin-bottom:5px;color:#ff9aa2;font-weight:700;font-size:13.5px;}}
    /* 价位阶梯图（dc-ladder·治价位矛盾+图文，不与现有类冲突） */
    .dc-ladder-bar{{position:relative;height:12px;border-radius:6px;overflow:visible;
      display:flex;margin:2px 0 9px;background:#0e1621;border:1px solid #2b4054;}}
    .dc-ladder-seg{{height:100%;}}
    .dc-lad-red{{background:#f0616d;}}
    .dc-lad-yellow{{background:#ffd479;}}
    .dc-lad-green{{background:#3ec38a;}}
    .dc-ladder-mark{{position:absolute;top:-7px;transform:translateX(-50%);
      color:#eef5f9;font-size:13px;line-height:1;text-shadow:0 0 3px #000;}}
    .dc-ladder-line{{color:#d9e7ef;font-size:13px;line-height:1.7;}}
    .dc-zone{{display:inline-block;padding:1px 9px;border-radius:12px;
      font-size:12px;font-weight:700;margin-left:4px;white-space:nowrap;}}
    .dc-zone-red{{background:rgba(240,97,109,.14);color:#f0616d;border:1px solid #f0616d;}}
    .dc-zone-green{{background:rgba(62,195,138,.14);color:#3ec38a;border:1px solid #3ec38a;}}
    .dc-zone-blue{{background:rgba(158,216,255,.14);color:#9ed8ff;border:1px solid #9ed8ff;}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="badge">{esc(badge_text)}</div>
      <h1>每日投资决策台</h1>
      {moat_banner}
      <div class="today">{esc(today_sentence)}</div>
      <div class="today-conf">{esc(confidence_line)}</div>
      <details class="today-long"><summary>展开看各层（总闸/战略/资金/板块的完整判断）</summary>
        <div>{esc(today_long)}</div>
      </details>
      <div class="finger">运行日 {esc(date[:4] + "-" + date[4:6] + "-" + date[6:])} · 行情截至 {esc(market_date_text)}（休市/快照沿用最近交易日） · 生成 {esc(str(fingerprint.get('generated_at', ''))[:16].replace('T', ' '))} UTC · 本页所有数字由当日零件现读现算
        <details style="margin-top:4px;">
          <summary style="cursor:pointer;color:#8ea3b6;display:inline;background:transparent;padding:0;font-size:12px;">数据来源与指纹（点开可查）</summary>
          <div style="font-size:11px;color:#6f8496;word-break:break-all;margin-top:4px;">
            指纹：framework_fixed={esc(fingerprint.get('framework_fixed'))}，answers_from_parts={esc(fingerprint.get('answers_from_parts'))}<br>
            来源零件：<br>{'<br>'.join(esc(source) for source in fingerprint.get('sources', []))}
          </div>
        </details>
      </div>
    </header>
    {inspection_panel(date, daily, production, ma_by_symbol, target_by_base)}
    {chain_logic_section(daily)}
    <section class="grid">
      <div>
        <h2 class="col-title">左栏·动态·每天现算</h2>
        {left}
      </div>
      <aside>
        <h2 class="col-title">右栏·静态·判断依据的尺（①已过审／②-⑥待审）</h2>
        {right}
      </aside>
    </section>
    <footer>{esc(close_loop)}</footer>
  </main>
</body>
</html>
"""


def _selected_page_css() -> str:
    """自包含实物页样式：复用产品 dc- 卡观感（与 build() 同色板）。"""
    return """
    body{margin:0;background:#0b1118;color:#eef5f9;font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.65;}
    .wrap{max-width:960px;margin:0 auto;padding:22px 18px 70px;}
    header{background:#151f2b;border:1px solid #2b4054;border-radius:12px;padding:18px 20px;margin-bottom:14px;}
    h1{margin:0 0 8px;font-size:24px;}
    .badge{display:inline-block;background:#5b2b22;color:#ffcfbd;border-radius:999px;padding:4px 12px;font-weight:700;margin-bottom:8px;}
    .finger{color:#8ea3b6;font-size:12px;margin-top:8px;}
    .card{background:#142231;border:1px solid #2b4054;border-radius:10px;margin-bottom:10px;padding:0;overflow:hidden;}
    .plain{margin:10px 15px;color:#d9e7ef;}
    h2{color:#9ed8ff;}
    table{width:calc(100% - 30px);margin:10px 15px 15px;border-collapse:collapse;font-size:13px;}
    th,td{border:1px solid #2b4054;padding:7px 8px;text-align:left;vertical-align:top;}
    th{background:#101b26;color:#bcd0e2;}
    .dc-card{background:#142231;border:1px solid #2b4054;border-radius:12px;padding:16px 18px;margin-bottom:12px;border-left:5px solid #2b4054;overflow:hidden;}
    .dc-card.dc-good{border-left-color:#3ec38a;}
    .dc-card.dc-bad{border-left-color:#f0616d;}
    .dc-card.dc-hi{border-left-color:#ffd479;}
    .dc-card.dc-soft{border-left-color:#9aa8b5;}
    .dc-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;}
    .dc-title{font-size:16.5px;font-weight:700;color:#eef5f9;}
    .dc-badge{flex:none;padding:5px 13px;border-radius:20px;font-size:13px;font-weight:700;white-space:nowrap;}
    .dc-badge.dc-good{background:rgba(62,195,138,.14);color:#3ec38a;border:1px solid #3ec38a;}
    .dc-badge.dc-bad{background:rgba(240,97,109,.14);color:#f0616d;border:1px solid #f0616d;}
    .dc-badge.dc-hi{background:rgba(255,212,121,.14);color:#ffd479;border:1px solid #ffd479;}
    .dc-badge.dc-soft{background:rgba(157,168,181,.14);color:#9aa8b5;border:1px solid #9aa8b5;}
    .dc-row{display:flex;gap:10px;margin-bottom:9px;font-size:14px;}
    .dc-lab{flex:none;color:#5cc8ff;font-weight:700;width:96px;}
    .dc-val{color:#eef5f9;flex:1;}
    .dc-row.dc-judge .dc-val{font-weight:700;}
    .dc-card.dc-good .dc-row.dc-judge .dc-val{color:#3ec38a;}
    .dc-card.dc-bad .dc-row.dc-judge .dc-val{color:#f0616d;}
    .dc-card.dc-hi .dc-row.dc-judge .dc-val{color:#ffd479;}
    .dc-card.dc-soft .dc-row.dc-judge .dc-val{color:#9aa8b5;}
    .dc-row.dc-now{background:rgba(92,200,255,.07);border:1px solid #2b4054;border-radius:8px;padding:9px 11px;margin-bottom:11px;}
    .dc-row.dc-now .dc-lab{color:#ffd479;}
    .dc-row.dc-now .dc-val{color:#eef5f9;font-weight:700;font-size:14px;line-height:1.6;}
    .dc-row.dc-now .dc-val b{color:#ffd479;}
    .dc-caveat{color:#9aa8b5;font-weight:400;font-size:12.5px;margin-left:4px;}
    .dc-dontadd-row{margin-top:10px;padding-top:9px;border-top:1px dashed #2b4054;}
    .dc-dontadd-row .dc-lab{color:#f0616d;}
    .dc-dontadd{background:rgba(240,97,109,.10);border:1px solid #f0616d;border-radius:7px;padding:6px 10px;margin-bottom:5px;color:#ff9aa2;font-weight:700;font-size:13.5px;}
    .dc-ladder-bar{position:relative;height:12px;border-radius:6px;overflow:visible;display:flex;margin:2px 0 9px;background:#0e1621;border:1px solid #2b4054;}
    .dc-ladder-seg{height:100%;}
    .dc-lad-red{background:#f0616d;}
    .dc-lad-yellow{background:#ffd479;}
    .dc-lad-green{background:#3ec38a;}
    .dc-ladder-mark{position:absolute;top:-7px;transform:translateX(-50%);color:#eef5f9;font-size:13px;line-height:1;text-shadow:0 0 3px #000;}
    .dc-ladder-line{color:#d9e7ef;font-size:13px;line-height:1.7;}
    .dc-zone{display:inline-block;padding:1px 9px;border-radius:12px;font-size:12px;font-weight:700;margin-left:4px;white-space:nowrap;}
    .dc-zone-red{background:rgba(240,97,109,.14);color:#f0616d;border:1px solid #f0616d;}
    .dc-zone-green{background:rgba(62,195,138,.14);color:#3ec38a;border:1px solid #3ec38a;}
    .dc-zone-blue{background:rgba(158,216,255,.14);color:#9ed8ff;border:1px solid #9ed8ff;}
    """


def render_selected(date: str, symbols: list[str]) -> str:
    """自包含实物页：顶部仓位集中度摘要表 + 选定几只持仓决策卡（含"别加"句）。
    复用 build() 用的零件与 portfolio_concentration/holding_decision_card。只读不下单。"""
    production_path = ROOT / "data" / "reports" / f"production_{date}.json"
    ma_path = ROOT / "data" / "holdings" / f"ma_levels_{date}.json"
    val_path = ROOT / "data" / "valuation" / f"valuation_samples_v7_{date}.json"
    cost_path = ROOT / "data" / "accounts" / "unified_holdings_latest.json"

    production = read_json(production_path)
    ma = read_json(ma_path) if ma_path.exists() else {"holdings": []}
    ma_by_symbol = {item.get("symbol"): item for item in ma.get("holdings", []) if item.get("symbol")}
    val = read_json(val_path) if val_path.exists() else {}
    # 估值唯一来源=valuation 实例(model_instances)：持仓卡价位与估值判断同源(治#5/6/8-12)
    target_by_base: dict[str, dict[str, Any]] = targets_from_model_instances(
        ROOT / "data" / "valuation" / "model_instances"
    )
    # 若当日另有更细的 valuation_samples(买/卖/止损)则叠加覆盖，仍属估值体系单一链
    for sample in val.get("samples", {}).values():
        target = _build_target_from_sample(sample)
        symbol_key = sample.get("symbol")
        if symbol_key:
            target_by_base[str(symbol_key)] = target
        for alias in sample.get("aliases", []) or []:
            target_by_base[str(alias)] = target
    cost_data = read_json(cost_path) if cost_path.exists() else {}
    cost_by_ticker = {
        str(item.get("ticker")): item
        for item in cost_data.get("aggregate_by_ticker", [])
        if item.get("ticker")
    }

    holdings = production.get("holdings", [])
    # 集中度按【全持仓】现算（口径一致），"别加"只落到选定卡上
    concentration = portfolio_concentration(holdings)
    by_symbol = {str(h.get("symbol") or ""): h for h in holdings}
    picked = [by_symbol[s] for s in symbols if s in by_symbol]

    cards = "".join(
        holding_decision_card(item, ma_by_symbol, target_by_base, cost_by_ticker, concentration)
        for item in picked
    )
    summary = concentration_summary_table(concentration)
    date_disp = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    gen = datetime.now(timezone.utc).isoformat()[:16].replace("T", " ")
    picked_names = "、".join(f"{esc(h.get('name'))}({esc(h.get('symbol'))})" for h in picked)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>持仓决策卡·渲染实物</title>
  <style>{_selected_page_css()}</style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="badge">渲染实物 · 集中度别加自动判断</div>
      <h1>持仓决策卡 · 渲染实物（含仓位集中度别加）</h1>
      <div style="background:#3a2c12;color:#ffcf6b;border:1px solid #6b5220;border-radius:8px;padding:8px 12px;margin:8px 0;font-weight:700;font-size:14px;">07-03样本数据 · 真数上线待开取价网关 · 金额已按USDJPY统一折美元</div>
      <div class="finger">数据日期 {esc(date_disp)} · 生成 {esc(gen)} UTC · 集中度按全持仓 market_value 现算<br>
      选定核心几只：{picked_names}</div>
    </header>
    {summary}
    <h2 style="margin:16px 0 8px;">核心几只持仓决策卡（上限类超标自动追加"别加"）</h2>
    {cards}
    <p class="plain" style="color:#8ea3b6;font-size:12px;">说明：集中度为结构化现算（不靠散文）；上限类(AI/单一/加密)超标→卡上自动加"别加"；下限类(防御/现金)不足→非"别加"，见摘要表提示。只读不下单，不自创买卖。</p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render full semi-finished product from parts")
    parser.add_argument("--date", default="20260702")
    parser.add_argument("--selected", default="", help="逗号分隔symbol，出选定实物页；给了--out则写文件")
    parser.add_argument("--out", default="", help="选定实物页输出路径")
    args = parser.parse_args()
    if args.selected:
        symbols = [s.strip() for s in args.selected.split(",") if s.strip()]
        html_text = render_selected(args.date, symbols)
        if args.out:
            Path(args.out).write_text(html_text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(html_text)
        return 0
    html_text = build(args.date)
    output = ROOT / "00_请先看这里" / f"完整产品_{args.date}.html"
    output.write_text(html_text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
