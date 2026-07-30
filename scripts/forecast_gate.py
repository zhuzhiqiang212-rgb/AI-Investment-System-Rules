#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
forecast_gate.py —— 预测优先口径·出厂硬闸(正式尺 §七·2026-07-30 立·董事长看板 G0)
七条硬闸(任一命中即当轮 FAIL):
  ① 任一持仓无预测(★含盲区只、待重估只·无豁免)
  ② 三情景概率合计 ≠ 100%
  ③ 使用非粗档概率(只许 10/20/30/40/50/60/70/80/90)
  ④ 缺证伪信号(invalidation_signal)或见分晓日期(verdict_date)
  ⑤ 预测未写入 locked_predictions_registry
  ⑥ 结论句只有现值核算(有 fair_value_anchor 却无前瞻情景/expected_upside)而无前瞻判断
  ⑦ ★当轮新增预测数 = 0(locked_at 日 = data_date 的预测数为0)→ FAIL(防精度工作挤占预测)
用法: python scripts/forecast_gate.py --date 2026-07-30
返回码: 0=PASS · 6=FAIL
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COARSE = {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9}


def _holdings_codes(date_compact: str) -> list:
    """持仓全集(富途+SBI逐只·gate① 用)。以 (account, code) 为单位。"""
    p = ROOT / "data/target" / f"target_gap_{date_compact}.json"
    out = []
    if p.exists():
        tg = json.loads(p.read_text(encoding="utf-8"))
        for acct in ("富途", "SBI"):
            for r in (tg.get(acct, {}).get("逐只(按贡献pp降序)", []) or []):
                out.append((acct, r.get("code")))
    return out


def check(date_hyphen: str):
    """返回 (fails:list, stats:dict)。date_hyphen 形如 2026-07-30。"""
    fails = []
    date_compact = date_hyphen.replace("-", "")
    fp = ROOT / "data/forecast" / f"forecast_{date_hyphen}.json"
    if not fp.exists():
        return [f"forecast 文件缺失: {fp.name}(尚未生产预测)"], {}
    fc = json.loads(fp.read_text(encoding="utf-8"))
    forecasts = fc.get("forecasts", []) or []

    # locked registry(尺 §五路径 data/forecast/)
    reg_p = ROOT / "data/forecast/locked_predictions_registry.json"
    reg_ids = set()
    if reg_p.exists():
        reg = json.loads(reg_p.read_text(encoding="utf-8"))
        for e in (reg.get("已登记预测", []) or []):
            if e.get("forecast_id"):
                reg_ids.add(e["forecast_id"])

    have = {(f.get("account"), f.get("ticker")) for f in forecasts}

    # ① 每持仓有预测(含盲区/待重估·无豁免)
    holds = _holdings_codes(date_compact)
    miss = [hc for hc in holds if hc not in have]
    if miss:
        fails.append(f"闸① 持仓无预测 ×{len(miss)}(含盲区/待重估无豁免)：{['%s/%s'%(a,c) for a,c in miss][:6]}{' …' if len(miss)>6 else ''}")

    new_cnt = 0
    for f in forecasts:
        tag = f"{f.get('account')}/{f.get('ticker')}"
        scen = f.get("scenarios", []) or []
        # ② 概率合计=100%
        s = round(sum(x.get("prob", 0) for x in scen), 6)
        if abs(s - 1.0) > 1e-6:
            fails.append(f"闸② {tag} 三情景概率合计 {s*100:.1f}% ≠ 100%")
        # ③ 粗档
        for x in scen:
            if x.get("prob") not in COARSE:
                fails.append(f"闸③ {tag} 非粗档概率 {x.get('prob')}(只许 0.1~0.9 整十档)")
                break
        # ④ 证伪信号 + 见分晓日期
        if not (f.get("invalidation_signal") or "").strip():
            fails.append(f"闸④ {tag} 缺证伪信号 invalidation_signal")
        if not (f.get("verdict_date") or "").strip():
            fails.append(f"闸④ {tag} 缺见分晓日期 verdict_date")
        # ⑤ 写入 locked registry
        fid = f.get("forecast_id")
        if not fid or fid not in reg_ids:
            fails.append(f"闸⑤ {tag} 预测未写入 locked_predictions_registry(forecast_id={fid})")
        # ⑥ 只有现值核算而无前瞻:有 anchor 却无情景/expected_upside
        has_anchor = bool((f.get("fair_value_anchor") or {}).get("value"))
        has_forward = bool(scen) and (f.get("expected_upside_pct") is not None)
        if has_anchor and not has_forward:
            fails.append(f"闸⑥ {tag} 结论只有现值核算(fair_value_anchor)而无前瞻情景/expected_upside")
        if not scen:
            fails.append(f"闸⑥ {tag} 无三情景(前瞻判断缺失)")
        # 当轮新增
        if (f.get("locked_at") or "")[:10] == date_hyphen:
            new_cnt += 1

    # ⑦ 当轮新增预测数=0
    if new_cnt == 0:
        fails.append("闸⑦ 当轮新增预测数=0 → 方向错(精度工作挤占预测)·按 FAIL 判")

    stats = {"forecast数": len(forecasts), "持仓数": len(holds), "缺预测数": len(miss),
             "当轮新增": new_cnt, "registry已登记": len(reg_ids)}
    return fails, stats


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="预测优先口径·出厂七闸(尺§七)")
    ap.add_argument("--date", required=True, help="形如 2026-07-30")
    a = ap.parse_args()
    fails, stats = check(a.date)
    if fails:
        print(f"[forecast_gate FAIL] {len(fails)} 条 · {stats}")
        for x in fails:
            print("  ✗", x)
        return 6
    print(f"[forecast_gate PASS] 七闸全过 · {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
