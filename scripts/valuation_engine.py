#!/usr/bin/env python3
"""分类型估值引擎（派工单 2026-07-14）· 只读不下单

一个引擎按公司类型分派 4 种估值法，出统一结果供 full_product_render 的持仓卡「贵不贵」/买卖价用：
  ① 成长股  growth_dcf : 两段式 EPS-DCF(复用 dcf_valuation.two_stage_dcf)。需 eps0,g_stage1,years,terminal_g,wacc
  ② 控股公司 nav        : 净资产法。Σ资产估值 − 净负债 → 每股NAV；控股常有折价→合理中枢=NAV×(1−折价)
  ③ 半导体周期股 mid_cycle: 中周期盈利法(不用峰值)。normal_eps×中周期PE，或 EV/EBITDA(中周期EBITDA×倍数−净负债)/股本
  ④ 保险   pbv          : P/B 或内含价值法。每股净资产×目标PB，或 内含价值/股×倍数

输入：data/valuation/val_inputs.json —— 理解岗(Cowork)按 symbol 填【方法+真输入】。
  缺真输入的 → status='待接真源'，不硬编假值(红线)。方法算法锚在本引擎(定义)、symbol→方法+数在输入文件(不锚死名单)。
输出：data/valuation/valuation_results_{date}.json —— 每只 {symbol,name,currency,method,method_disp,
  intrinsic,reasonable_low/high,target,confidence:'A·<法>',assumptions,status}。与旧 dcf_results 同形，render 直接吃。
每日现算不写死；未接真源今天就照实标待接、不编。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

sys.path.insert(0, str(ROOT / "scripts"))
from dcf_valuation import two_stage_dcf  # 复用成长股两段式 DCF 原语

METHOD_DISP = {
    "growth_dcf": "成长股·两段式DCF",
    "nav": "控股公司·净资产法(NAV)",
    "mid_cycle": "周期股·中周期盈利法",
    "pbv": "保险·P/B或内含价值法",
}


def _f(v):
    """转 float；None/空/非数 → None(不硬编)。"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pack(sym, name, cur, method, intrinsic, target, assumptions, extra_note=""):
    """内在价值→合理区(±10%)统一封装。"""
    return {
        "symbol": sym, "name": name, "currency": cur, "status": "OK",
        "method": method, "method_disp": METHOD_DISP.get(method, method),
        "intrinsic": round(intrinsic, 2),
        "reasonable_low": round(target * 0.90, 2),
        "reasonable_high": round(target * 1.10, 2),
        "target": round(target, 2),
        "confidence": "A·" + method,
        "assumptions": assumptions,
        "note": extra_note,
    }


def _pending(sym, name, method, missing):
    disp = METHOD_DISP.get(method, method or "未定方法")
    reason = (f"缺真输入：{('、'.join(missing))}（用 {disp}）" if method
              else "理解岗未定方法+真输入")
    return {"symbol": sym, "name": name, "status": "待接真源",
            "method": method or "", "method_disp": disp,
            "reason": reason + "·不硬编"}


def val_growth_dcf(sym, name, cur, it):
    need = {"eps0": _f(it.get("eps0")), "g_stage1": _f(it.get("g_stage1")),
            "years": it.get("years"), "terminal_g": _f(it.get("terminal_g")), "wacc": _f(it.get("wacc"))}
    missing = [k for k, v in need.items() if v is None]
    if missing:
        return _pending(sym, name, "growth_dcf", missing)
    try:
        iv = two_stage_dcf(need["eps0"], need["g_stage1"], int(need["years"]), need["terminal_g"], need["wacc"])
    except ValueError as exc:
        return _pending(sym, name, "growth_dcf", [f"假设不合法({exc})"])
    return _pack(sym, name, cur, "growth_dcf", iv, iv,
                 {**need, "note": it.get("note", "")})


def val_nav(sym, name, cur, it):
    assets = it.get("assets") or []
    vals = [_f(a.get("value")) for a in assets] if isinstance(assets, list) else []
    net_debt = _f(it.get("net_debt"))
    shares = _f(it.get("shares"))
    missing = []
    if not vals or any(v is None for v in vals):
        missing.append("assets[各资产估值]")
    if net_debt is None:
        missing.append("net_debt(净负债)")
    if shares is None or shares == 0:
        missing.append("shares(总股本)")
    if missing:
        return _pending(sym, name, "nav", missing)
    gross = sum(vals)
    nav_ps = (gross - net_debt) / shares
    if nav_ps <= 0:
        return _pending(sym, name, "nav", ["资产减净负债后为负·核对输入"])
    disc = _f(it.get("holding_discount"))          # 控股折价(0~1)·可选；有则合理中枢打折
    target = nav_ps * (1 - disc) if disc is not None else nav_ps
    return _pack(sym, name, cur, "nav", nav_ps, target,
                 {"资产合计": round(gross, 2), "净负债": net_debt, "总股本": shares,
                  "每股NAV": round(nav_ps, 2), "控股折价": disc,
                  "资产明细": [{a.get("name"): _f(a.get("value"))} for a in assets], "note": it.get("note", "")},
                 extra_note=("合理中枢已按控股折价" + (f"{disc:.0%}" if disc is not None else "0%") + "折"))


def val_mid_cycle(sym, name, cur, it):
    # 优先 normal_eps×PE；否则 EV/EBITDA。都不足→待接。峰值EPS不用(红线:用正常年景)
    normal_eps = _f(it.get("normal_eps")); pe_mid = _f(it.get("pe_mid"))
    if normal_eps is not None and pe_mid is not None:
        iv = normal_eps * pe_mid
        return _pack(sym, name, cur, "mid_cycle", iv, iv,
                     {"法": "正常年景EPS×中周期PE", "normal_eps": normal_eps, "pe_mid": pe_mid, "note": it.get("note", "")})
    ebitda = _f(it.get("ebitda_normal")); mult = _f(it.get("ev_ebitda"))
    net_debt = _f(it.get("net_debt")); shares = _f(it.get("shares"))
    if None not in (ebitda, mult, net_debt, shares) and shares != 0:
        ev = ebitda * mult
        per_share = (ev - net_debt) / shares
        if per_share <= 0:
            return _pending(sym, name, "mid_cycle", ["EV减净负债后为负·核对输入"])
        return _pack(sym, name, cur, "mid_cycle", per_share, per_share,
                     {"法": "中周期EV/EBITDA", "ebitda_normal": ebitda, "ev_ebitda": mult,
                      "净负债": net_debt, "总股本": shares, "EV": round(ev, 2), "note": it.get("note", "")})
    return _pending(sym, name, "mid_cycle",
                    ["normal_eps+pe_mid 或 ebitda_normal+ev_ebitda+net_debt+shares(任一整套)"])


def val_pbv(sym, name, cur, it):
    bvps = _f(it.get("bvps")); target_pb = _f(it.get("target_pb"))
    if bvps is not None and target_pb is not None:
        iv = bvps * target_pb
        return _pack(sym, name, cur, "pbv", iv, iv,
                     {"法": "每股净资产×目标PB", "bvps": bvps, "target_pb": target_pb, "note": it.get("note", "")})
    evps = _f(it.get("ev_per_share")); evm = _f(it.get("ev_multiple"))
    if evps is not None and evm is not None:
        iv = evps * evm
        return _pack(sym, name, cur, "pbv", iv, iv,
                     {"法": "内含价值/股×倍数", "ev_per_share": evps, "ev_multiple": evm, "note": it.get("note", "")})
    return _pending(sym, name, "pbv", ["bvps+target_pb 或 ev_per_share+ev_multiple(任一套)"])


DISPATCH = {"growth_dcf": val_growth_dcf, "nav": val_nav, "mid_cycle": val_mid_cycle, "pbv": val_pbv}


def compute(inputs: dict) -> dict:
    rows = []
    holdings = inputs.get("holdings", {})
    items = holdings.items() if isinstance(holdings, dict) else [(h.get("symbol"), h) for h in holdings]
    for sym, it in items:
        name = it.get("name")
        cur = it.get("currency", "$")
        method = (it.get("method") or "").strip()
        if not method:
            rows.append(_pending(sym, name, "", []))
            continue
        fn = DISPATCH.get(method)
        if fn is None:
            rows.append({"symbol": sym, "name": name, "status": "待接真源",
                         "method": method, "reason": f"未知方法 {method}（支持 {'/'.join(DISPATCH)}）·不硬编"})
            continue
        rows.append(fn(sym, name, cur, it))
    return {"generated_at": datetime.now(JST).isoformat(),
            "engine": "分类型估值引擎 v1", "methods": METHOD_DISP, "results": rows}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="分类型估值引擎·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    inp = ROOT / "data" / "valuation" / "val_inputs.json"
    if not inp.exists():
        print(f"[待接真源] 缺输入位 {inp}，不编造。")
        return 2
    out = compute(json.loads(inp.read_text(encoding="utf-8")))
    out_path = ROOT / "data" / "valuation" / f"valuation_results_{date}.json"
    text = json.dumps(out, ensure_ascii=False, indent=2)
    out_path.write_text(text, encoding="utf-8")
    if out_path.read_bytes().count(b"\xef\xbf\xbd") > 0:
        print("[WARN] 输出疑似乱码 EF BF BD>0")
    ok = sum(1 for r in out["results"] if r.get("status") == "OK")
    pend = len(out["results"]) - ok
    print(f"wrote {out_path} · 精算 {ok} 只(可信度A)、待接 {pend} 只")
    for r in out["results"]:
        if r.get("status") == "OK":
            print(f"  [A] {r['symbol']:11} {r['method_disp']:16} 中枢={r['currency']}{r['target']} 合理区 {r['currency']}{r['reasonable_low']}~{r['currency']}{r['reasonable_high']}")
        else:
            print(f"  [待接] {str(r['symbol']):11} {r.get('method_disp','')}: {r.get('reason','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
