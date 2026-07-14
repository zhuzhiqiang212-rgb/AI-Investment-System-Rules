#!/usr/bin/env python3
"""财报密集期处理（派工单2026-07-14）· 只读不下单

在"按类型自动估值"架构上加财报窗口：
  ① 财报日历：读 earnings_calendar.json，算谁近几天出财报(持仓+候选)，供第一屏+机会池标注。
  ② 出财报自动刷新：某只【已出】后理解岗更新 val_inputs 真输入→估值引擎按【同一类型模型】自动重算；
     本模块对比【今日 vs 最近一份历史】valuation_results，检出估值区间/买卖价变化，并判现价是否触发买卖。
  ③ 把"财报事件+估值变化+触发的机会"顶到第一屏(机会窗口期最该看)。
缺真源(日历没登记/财报数没更新)→标"待接真源"、不编财报日、不编财报数。每日现算不写死。

供 full_product_render 调用；不改估值方法本身(方法仍由 security_classifier 按类型自动定)。
"""
from __future__ import annotations

import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _esc(v: Any) -> str:
    import html
    return html.escape("" if v is None else str(v))


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_calendar() -> dict:
    return _read(ROOT / "data" / "valuation" / "earnings_calendar.json")


def _to_date(s: str):
    s = str(s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10] if "-" in s else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def days_until(today_str: str, report_str: str):
    d0 = _to_date(today_str); d1 = _to_date(report_str)
    if d0 is None or d1 is None:
        return None
    return (d1 - d0).days


def prior_valuation(today_str: str) -> dict[str, dict]:
    """最近一份【早于今天】的 valuation_results，用于检出估值变化。无→{}。"""
    out: list[tuple[str, Path]] = []
    for p in glob.glob(str(ROOT / "data" / "valuation" / "valuation_results_*.json")):
        d = Path(p).stem.replace("valuation_results_", "")
        if d < str(today_str):
            out.append((d, Path(p)))
    if not out:
        return {}
    _, latest = sorted(out)[-1]
    res = _read(latest).get("results") or []
    return {str(r.get("symbol")): r for r in res if r.get("symbol")}


def _fmt(v: Any) -> str:
    try:
        f = float(v)
        return f"{f:,.2f}".rstrip("0").rstrip(".") if f % 1 else f"{f:,.0f}"
    except (TypeError, ValueError):
        return _esc(v)


def valuation_change(sym: str, cur: dict[str, dict], prior: dict[str, dict]) -> dict | None:
    """今日 vs 历史估值对比。返回 None=无可比/无变化；否则含 old/new 区间与首次精算标记。"""
    c = cur.get(sym)
    if not c or c.get("status") != "OK":
        return None
    p = prior.get(sym)
    cur_t = c.get("target")
    if not p or p.get("status") != "OK":
        return {"symbol": sym, "first_time": True, "new_low": c.get("reasonable_low"),
                "new_high": c.get("reasonable_high"), "new_target": cur_t,
                "currency": c.get("currency", ""), "model_disp": c.get("model_disp", "")}
    old_t = p.get("target")
    try:
        if old_t is not None and cur_t is not None and abs(float(cur_t) - float(old_t)) < 1e-9:
            return None                       # 无变化
    except (TypeError, ValueError):
        pass
    return {"symbol": sym, "first_time": False,
            "old_low": p.get("reasonable_low"), "old_high": p.get("reasonable_high"), "old_target": old_t,
            "new_low": c.get("reasonable_low"), "new_high": c.get("reasonable_high"), "new_target": cur_t,
            "currency": c.get("currency", ""), "model_disp": c.get("model_disp", "")}


def _trigger(price: Any, low: Any, high: Any) -> str:
    """现价 vs 新买卖价 → 触发提示。缺现价→待接。"""
    try:
        pf = float(price)
    except (TypeError, ValueError):
        return "现价待接·暂判不了是否触发"
    try:
        if low is not None and pf <= float(low):
            return "🟢 现价已跌破新便宜价·可考虑低吸/换入(按纪律·不追高)"
        if high is not None and pf >= float(high):
            return "🟠 现价已到新减仓价·可考虑减/被换出"
    except (TypeError, ValueError):
        return "新区间不完整·暂判不了"
    return "现价落在新合理区·暂不触发买卖"


def _universe(holdings: list[dict], candidates: list[dict]) -> dict[str, str]:
    """symbol/base/name → 身份(持仓/候选)。"""
    m: dict[str, str] = {}
    for h in holdings or []:
        s = str(h.get("symbol") or "")
        for k in (s, s.split(".")[-1], h.get("name")):
            if k:
                m[str(k)] = "持仓"
    for c in candidates or []:
        for k in (c.get("symbol"), c.get("name")):
            if k:
                m.setdefault(str(k), "候选")
    return m


def _role(ev: dict, uni: dict[str, str]) -> str:
    for k in (ev.get("symbol"), str(ev.get("symbol") or "").split(".")[-1], ev.get("name")):
        if k and str(k) in uni:
            return uni[str(k)]
    return "关注"


def analyze(date: str, holdings: list[dict], candidates: list[dict],
            cur_val: dict[str, dict], price_by_symbol: dict[str, Any]) -> dict:
    """汇总财报窗口：即将出/已出+估值变化+触发。供第一屏与巡检共用。"""
    cal = load_calendar()
    events = cal.get("events") or []
    window = int(cal.get("upcoming_window_days", 10) or 10)
    uni = _universe(holdings, candidates)
    prior = prior_valuation(date)
    upcoming: list[dict] = []
    reported: list[dict] = []
    for ev in events:
        sym = str(ev.get("symbol") or "")
        dd = days_until(date, ev.get("report_date"))
        role = _role(ev, uni)
        base = {"symbol": sym, "name": ev.get("name"), "date": ev.get("report_date"),
                "session": ev.get("session"), "fiscal": ev.get("fiscal"), "role": role, "days": dd}
        if str(ev.get("status")) == "已出":
            chg = valuation_change(sym, cur_val, prior)
            price = price_by_symbol.get(sym)
            base["change"] = chg
            base["trigger"] = _trigger(price, (chg or {}).get("new_low"), (chg or {}).get("new_high")) if chg else "估值未更新·待理解岗接财报数"
            reported.append(base)
        elif dd is not None and 0 <= dd <= window:
            upcoming.append(base)
        elif dd is not None and dd < 0:
            base["overdue"] = True                # 财报日已过但未标已出→待确认
            upcoming.append(base)
    upcoming.sort(key=lambda e: (e["days"] if e["days"] is not None else 999))
    return {"calendar_ok": bool(events), "upcoming": upcoming, "reported": reported,
            "has_focus": bool(upcoming or reported)}


def badge_for(symbol: Any, name: Any, date: str) -> str:
    """机会池/持仓小标记：📅 近N天出财报。无→''。"""
    info = analyze(date, [], [{"symbol": symbol, "name": name}], {}, {})
    for e in info["upcoming"]:
        if str(e.get("symbol")) == str(symbol) or str(e.get("name")) == str(name):
            dd = e.get("days")
            when = ("今天" if dd == 0 else f"{dd}天后" if isinstance(dd, int) and dd > 0 else "近期")
            return f'<span style="color:#ffd479;font-size:12px;">📅 {_esc(e.get("date"))} 出财报({when})</span>'
    return ""


def first_screen_html(date: str, holdings: list[dict], candidates: list[dict],
                      cur_val: dict[str, dict], price_by_symbol: dict[str, Any]) -> str:
    """第一屏·财报窗口块(顶到最前)：即将出财报 + 已出+估值变化+触发。无事件→诚实说明。"""
    info = analyze(date, holdings, candidates, cur_val, price_by_symbol)
    rows = ""
    # 已出+估值变化+触发(最该看·排前)
    for e in info["reported"]:
        chg = e.get("change")
        if chg and chg.get("first_time"):
            vtxt = (f'首次精算(财报后接上真输入)：新合理区 {_esc(chg["currency"])}{_fmt(chg["new_low"])}~{_esc(chg["currency"])}{_fmt(chg["new_high"])}'
                    f'、中枢 {_esc(chg["currency"])}{_fmt(chg["new_target"])}（{_esc(chg["model_disp"])}）')
        elif chg:
            vtxt = (f'估值已更新：中枢 {_esc(chg["currency"])}{_fmt(chg.get("old_target"))} → <b>{_esc(chg["currency"])}{_fmt(chg["new_target"])}</b>'
                    f'、新合理区 {_esc(chg["currency"])}{_fmt(chg["new_low"])}~{_esc(chg["currency"])}{_fmt(chg["new_high"])}（{_esc(chg["model_disp"])}·同法重算）')
        else:
            vtxt = '<span style="color:#c9a86a;">估值未更新·待理解岗接财报数(不编)</span>'
        rows += (f'<div style="margin:7px 0;padding:8px 10px;background:rgba(255,212,121,.08);border:1px solid #4a3f22;border-radius:8px;">'
                 f'<b style="color:#ffd479;">📊 {_esc(e.get("name"))}（{_esc(e.get("role"))}）出了财报</b>'
                 f'（{_esc(e.get("fiscal"))}·{_esc(e.get("date"))}）<br>{vtxt}<br>'
                 f'<span style="color:#eef5f9;">是否触发买卖/换仓：{e.get("trigger")}</span></div>')
    # 即将出财报
    if info["upcoming"]:
        items = "".join(
            f'<li>{_esc(u.get("name"))}（{_esc(u.get("role"))}）· {_esc(u.get("date"))} {_esc(u.get("session") or "")}'
            + (f'·<b style="color:#ffd479;">{"今天" if u.get("days")==0 else str(u.get("days"))+"天后" if isinstance(u.get("days"),int) and u.get("days")>0 else "日期已过·待确认"}</b>' )
            + (f'·{_esc(u.get("fiscal"))}' if u.get("fiscal") else "") + '</li>'
            for u in info["upcoming"])
        rows += f'<div style="margin:7px 0;"><b style="color:#ffcf8f;">📅 即将出财报（盯紧·出报后估值会自动重算）</b><ul style="margin:4px 0;">{items}</ul></div>'
    if not rows:
        note = ("财报日历已接、但近期无持仓/候选财报窗口" if info["calendar_ok"]
                else "财报日历待接真源（理解岗补登财报日后自动显示·不编日期）")
        rows = f'<div style="color:#9aa8b5;">近期无需盯的财报事件：{note}。</div>'
    return (f'<section style="background:#151f2b;border:1px solid #4a3f22;border-radius:12px;padding:14px 16px;margin-bottom:14px;">'
            f'<div style="font-size:16px;font-weight:700;color:#ffd479;margin-bottom:6px;">🗓 财报窗口 · 机会窗口期最该看</div>'
            f'<div style="font-size:12.5px;color:#9aa8b5;margin-bottom:6px;">谁快出财报、谁出了财报估值怎么变、变化有没有触发买卖/换仓——出报后由同一类型模型自动重算(不换方法)。财报数暂由理解岗出报后更新·缺标待接不编。</div>'
            f'{rows}</section>')


def inspection_items(date: str, holdings: list[dict], candidates: list[dict],
                     cur_val: dict[str, dict], price_by_symbol: dict[str, Any]) -> list[str]:
    """今日巡检·财报提示行(已出+估值更新+是否触发)。无→空列表。"""
    info = analyze(date, holdings, candidates, cur_val, price_by_symbol)
    out: list[str] = []
    for e in info["reported"]:
        chg = e.get("change")
        if chg:
            seg = ("估值首次精算" if chg.get("first_time")
                   else f"估值已更新(中枢{_fmt(chg.get('old_target'))}→{_fmt(chg.get('new_target'))})")
            out.append(f"📊 {e.get('name')} 出了财报（{e.get('fiscal')}）·{seg}·{e.get('trigger')}——是否触发买卖/换仓请确认")
        else:
            out.append(f"📊 {e.get('name')} 出了财报（{e.get('fiscal')}）·估值数待理解岗接财报后更新(不编)")
    for u in info["upcoming"]:
        if u.get("days") == 0:
            out.append(f"📅 {u.get('name')} 今天出财报（{u.get('session') or ''}）·出报后估值会自动重算·留意")
    return out
