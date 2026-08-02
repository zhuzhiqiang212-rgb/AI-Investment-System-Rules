# -*- coding: utf-8 -*-
"""★轮77 AQ3-2:资金流层(第③层)完备性闸。5核心指标(10Y/VIX/DXY/FOMC/CPI-PCE)≥2个「取不到」→
产品第③层标「资金流层数据不足·本层判断不成立」,且★禁下游(④板块/⑤机会池)以"激活"为结论(证据链不闭合·GPT终验第5条)。
非关键(告警·不阻断出品)·但把结论从靠人记变机器判。"""
import sys, json, argparse, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def check(date):
    dc = date.replace("-", "")
    p = ROOT / "data/market" / f"macro_flow_{dc}.json"
    if not p.exists():
        return ["资金流层 macro_flow_%s.json 不存在→第③层全未产出·须先跑 macro_flow_layer.py" % dc], False, False
    d = json.loads(p.read_text(encoding="utf-8"))
    comp = d.get("★资金流层完备性(供 macro_flow_gate)", {})
    n_missing = comp.get("核心5指标(10Y/VIX/DXY/FOMC/CPI-PCE)取不到数")
    if n_missing is None:
        core = d.get("核心指标", [])
        n_missing = sum(1 for x in core if x.get("指标") in ("10年期美债收益率", "VIX恐慌指数", "DXY美元指数(贸易加权广义)", "FOMC决议", "CPI") and not x.get("接通"))
    layer_ok = n_missing < 2
    warns = []
    if not layer_ok:
        warns.append("★资金流层数据不足:核心5指标有 %d 个取不到(≥2)→第③层判断不成立·产品该层须标『资金流层数据不足·本层判断不成立』" % n_missing)
        # 禁下游宣激活
        sa = sorted(glob.glob(str(ROOT / "data/market" / "sector_activation_*.json")))
        if sa:
            warns.append("★证据链不闭合(资金流层不足)却存在激活清单 %s→禁下游④板块/⑤机会池以『激活』为结论(GPT终验第5条)" % Path(sa[-1]).name)
    # 接通N/10 供八步表
    conn = d.get("★接通统计", {}).get("接通N/10", "?/10")
    return warns, layer_ok, conn


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    warns, ok, conn = check(a.date)
    if warns:
        print("[macro_flow_gate 告警·不阻断] 资金流层闭合=%s · 接通%s" % (ok, conn))
        for w in warns:
            print("  ⚠", w)
    else:
        print("[macro_flow_gate PASS] 资金流层核心指标足 · 接通%s" % conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
