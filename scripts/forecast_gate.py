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


def selftest_denominator():
    """K2-2 常设回归:用【已知答案】样例测 E[上行] 公式——中性=当日价、乐观悲观对称 → E[上行] 必 ≈0。
    超出 ±1% 即说明分母被换成了锚/别的值(轮47 软银 bug 的复现防线)。返回 (ok, msg)。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    from target_gap import compute_expected_upside
    cur = 4622.0  # 任取一个"当日价"(此处用软银轮47实测价)
    scen = [
        {"name": "乐观", "range": [round(cur * 1.05), round(cur * 1.15)], "prob": 0.2},
        {"name": "中性", "range": [round(cur * 0.98), round(cur * 1.02)], "prob": 0.6},
        {"name": "悲观", "range": [round(cur * 0.85), round(cur * 0.95)], "prob": 0.2},
    ]
    _, e_up = compute_expected_upside(scen, cur)          # 分母=当日价
    ok = abs(e_up) <= 1.0
    # 反向:若误用锚(≠当日价)当分母,E[上行]应显著偏离0(证公式对分母敏感)
    _, e_up_wrong = compute_expected_upside(scen, cur * 3.2)   # 模拟锚=3.2×当日价(软银bug)
    return ok, "中性=当日价·对称样例 E[上行]=%.2f%%(须∈±1%%)·误用锚分母则 E[上行]=%.1f%%(应显著≠0)" % (e_up, e_up_wrong)


def check(date_hyphen: str):
    """返回 (fails:list, stats:dict)。date_hyphen 形如 2026-07-30。"""
    fails = []
    # K2-2 常设回归:每次跑闸先自测 E[上行] 公式(已知答案样例)·分母被换成锚立刻 FAIL
    st_ok, st_msg = selftest_denominator()
    if not st_ok:
        fails.append("K2-2 公式回归失败(E[上行] 分母疑被换成锚)：" + st_msg)
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

    # account 归一:尺§六用 FUTU|SBI·持仓用 富途|SBI(中文)→ 统一到中文比对
    _acc = {"FUTU": "富途", "SBI": "SBI", "富途": "富途"}
    have = {(_acc.get(f.get("account"), f.get("account")), f.get("ticker")) for f in forecasts}

    # M3(74号):当日价映射(用于重算 E[上行]·验 expected_upside_pct 是机器算不是手给)
    _px = {}
    _tp = ROOT / "data/target" / f"target_gap_{date_compact}.json"
    if _tp.exists():
        _tg = json.loads(_tp.read_text(encoding="utf-8"))
        for _a in ("富途", "SBI"):
            for _r in (_tg.get(_a, {}).get("逐只(按贡献pp降序)", []) or []):
                _px[(_a, _r.get("code"))] = _r.get("price_local_0730", _r.get("price_local"))
    _FORBID = ("opus5_given_upside_pct", "weight", "权重", "贡献pp", "contribution_pp", "手给贡献pp", "手给权重")

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
        # M3 手给pp/权重路径已关闭:填报出现手给字段 → FAIL(不静默采用/丢弃)
        _hit = [k for k in _FORBID if k in f]
        if _hit:
            fails.append(f"M3 {tag} 含手给字段 {_hit}——E[上行]/权重/贡献pp 一律机器算·填报只给区间/概率/依据/证伪/日期/置信度")
        # M3 expected_upside_pct 必须=机器复算(分母=当日价)·防手给蒙混
        _acccn = _acc.get(f.get("account"), f.get("account"))
        _pt = _px.get((_acccn, f.get("ticker")))
        _stored = f.get("expected_upside_pct")
        if scen and _pt and _stored is not None:
            sys.path.insert(0, str(ROOT / "scripts"))
            from target_gap import compute_expected_upside
            _, _re = compute_expected_upside(scen, _pt)
            if abs(_re - _stored) > 0.02:
                fails.append(f"M3 {tag} expected_upside_pct={_stored} ≠ 机器复算 {_re}(分母=当日价 {_pt})——疑手给/未用当日价")
        # W4-1(轮59尺修正):三情景区间必须无缝相接(悲观上沿=中性下沿·中性上沿=乐观下沿)·有间隙或重叠→FAIL
        if len(scen) == 3 and all(len(s.get("range", [])) == 2 for s in scen):
            lo_o, hi_o = sorted(scen[0]["range"]); lo_m, hi_m = sorted(scen[1]["range"]); lo_p, hi_p = sorted(scen[2]["range"])
            if abs(hi_p - lo_m) > 1e-6:
                seg = f"[{min(hi_p,lo_m):.0f}~{max(hi_p,lo_m):.0f}]"
                fails.append(f"W4 {tag} 悲观上沿({hi_p:.0f})≠中性下沿({lo_m:.0f})·{'间隙' if hi_p<lo_m else '重叠'}{seg}(区间须无缝相接)")
            if abs(hi_m - lo_o) > 1e-6:
                seg = f"[{min(hi_m,lo_o):.0f}~{max(hi_m,lo_o):.0f}]"
                fails.append(f"W4 {tag} 中性上沿({hi_m:.0f})≠乐观下沿({lo_o:.0f})·{'间隙' if hi_m<lo_o else '重叠'}{seg}(区间须无缝相接)")
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
