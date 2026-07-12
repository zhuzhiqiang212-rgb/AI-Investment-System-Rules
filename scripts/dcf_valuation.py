#!/usr/bin/env python3
"""DCF 精算模块（派工单 2026-07-13 §2.3）· 只读不下单

两段式 DCF（基于 forward EPS 作现金流代理·假设全部明标、可审可回溯）：
  intrinsic = Σ_{t=1..N} EPS0·(1+g)^t / (1+wacc)^t   +   TV/(1+wacc)^N
  其中 TV = EPS_N·(1+tg) / (wacc - tg)

输入：data/valuation/dcf_inputs.json —— 每只 {symbol,name,eps0,g_stage1,years,terminal_g,wacc,note}
  · eps0/increments 为真实 forward EPS（来源 valuation 实例/研究包，非编）；
  · 增长/折现为明标的假设（DCF 本就需假设，非编造），列进结果供审。
输出：data/valuation/dcf_results_{date}.json —— 每只 {intrinsic, reasonable_low/high, target, confidence:'A·DCF', assumptions}

覆盖策略：先大仓/单一超限几只；未覆盖的持仓仍用相对估值(valuation 实例)、标"待DCF"。
缺真输入的：标"待接真源"，不硬编假值。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def two_stage_dcf(eps0: float, g: float, years: int, tg: float, wacc: float) -> float:
    """两段式 DCF 内在价值/股。wacc 必须 > tg。"""
    if wacc <= tg:
        raise ValueError("wacc 必须大于永续增长 tg")
    pv = 0.0
    eps = eps0
    for t in range(1, years + 1):
        eps = eps0 * ((1 + g) ** t)
        pv += eps / ((1 + wacc) ** t)
    tv = eps * (1 + tg) / (wacc - tg)          # eps 此时=EPS_N
    pv += tv / ((1 + wacc) ** years)
    return pv


def compute(inputs: dict) -> dict:
    rows = []
    for it in inputs.get("holdings", []):
        sym = it.get("symbol")
        try:
            eps0 = float(it["eps0"]); g = float(it["g_stage1"]); years = int(it["years"])
            tg = float(it["terminal_g"]); wacc = float(it["wacc"])
        except (KeyError, TypeError, ValueError):
            rows.append({"symbol": sym, "name": it.get("name"), "status": "待接真源",
                         "reason": "缺真实 EPS/假设输入，不硬编"})
            continue
        iv = two_stage_dcf(eps0, g, years, tg, wacc)
        cur = it.get("currency", "$")
        rows.append({
            "symbol": sym, "name": it.get("name"), "status": "OK",
            "currency": cur,
            "intrinsic": round(iv, 2),
            "reasonable_low": round(iv * 0.90, 2),
            "reasonable_high": round(iv * 1.10, 2),
            "target": round(iv, 2),
            "confidence": "A·DCF",
            "assumptions": {"eps0": eps0, "g_stage1": g, "years": years,
                            "terminal_g": tg, "wacc": wacc, "note": it.get("note", "")},
        })
    return {"generated_at": datetime.now(JST).isoformat(), "model": "两段式DCF·EPS代理",
            "results": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description="DCF 精算模块·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    inp_path = ROOT / "data" / "valuation" / "dcf_inputs.json"
    if not inp_path.exists():
        print(f"[待接真源] 缺输入文件 {inp_path}，不编造。")
        return 2
    inputs = json.loads(inp_path.read_text(encoding="utf-8"))
    out = compute(inputs)
    out_path = ROOT / "data" / "valuation" / f"dcf_results_{date}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in out["results"] if r.get("status") == "OK")
    print(f"wrote {out_path} · 覆盖 {ok}/{len(out['results'])} 只(DCF·A)")
    for r in out["results"]:
        if r.get("status") == "OK":
            print(f"  {r['symbol']:9} 内在={r['currency']}{r['intrinsic']} 合理区 {r['currency']}{r['reasonable_low']}~{r['currency']}{r['reasonable_high']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
