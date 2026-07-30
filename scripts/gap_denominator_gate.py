# -*- coding: utf-8 -*-
"""D1(46号)·分母核平闸。target_gap 的富途A 与当日 futu_positions 快照 total_assets 差 >0.5% → FAIL 不出品。
缺口是一切判断的出发点·分母不许有不明差额。Code只校验不改判断。"""
import json, argparse, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
def check(date):
    tg = ROOT / "data" / "target" / f"target_gap_{date}.json"
    fp = ROOT / "data" / "accounts" / f"futu_positions_{date}.json"
    if not tg.exists() or not fp.exists():
        return False, "缺 target_gap 或 futu_positions_%s.json" % date
    A = json.loads(tg.read_text(encoding="utf-8")).get("富途", {}).get("当日总资产A_USD")
    snap = json.loads(fp.read_text(encoding="utf-8")).get("futu_cash", {}).get("total_assets")
    if A is None or snap is None:
        return False, "A 或 total_assets 缺"
    diff = abs(A - snap) / snap * 100
    return diff <= 0.5, "富途A=%.2f vs 快照total=%.2f · 差%.4f%%(阈值0.5%%)" % (A, snap, diff)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    ok, msg = check(a.date)
    print("分母核平闸:", msg, "→", "PASS" if ok else "★FAIL·不出品")
    return 0 if ok else 5
if __name__ == "__main__":
    raise SystemExit(main())
