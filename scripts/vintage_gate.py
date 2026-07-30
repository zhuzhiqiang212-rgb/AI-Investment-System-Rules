# -*- coding: utf-8 -*-
"""E3(49号)·vintage同源闸。账户级 vintage_gap_days >30天 → 缺口标『不可信』并告警(★不阻断出品)。Code只校验不改判断。"""
import json, argparse, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
def check(date):
    p = ROOT / "data" / "target" / f"target_gap_{date}.json"
    if not p.exists(): return True, "无 target_gap_%s.json" % date
    tg = json.loads(p.read_text(encoding="utf-8"))
    msgs = []; warn = False
    for k in ("富途", "SBI"):
        acc = tg.get(k, {})
        v = acc.get("vintage_gap_days")
        if v is not None and v > 30:
            warn = True; msgs.append("%s vintage_gap_days=%d>30→缺口不可信告警" % (k, v))
        else:
            msgs.append("%s vintage_gap_days=%s(≤30合格)" % (k, v))
    return (not warn), " · ".join(msgs)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    ok, msg = check(a.date)
    print("vintage同源闸(不阻断出品):", msg, "→", "合格" if ok else "★告警(>30天·不阻断)")
    return 0  # 不阻断出品:始终0
if __name__ == "__main__":
    raise SystemExit(main())
