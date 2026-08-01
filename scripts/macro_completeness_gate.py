# -*- coding: utf-8 -*-
"""★轮73 AL2-6:宏观完备性闸。宏观层关键字段(US10Y真收益率/FOMC/日银/日债)为None或未接、或"沿用N天">1天 →
该层须标「未产出·原因」,且★证据不闭合时不许宣布板块激活(GPT第5条)。非关键(告警)·但把"该不该宣激活"从靠人记变机器提醒。"""
import sys, json, argparse, glob, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def check(date):
    warns = []
    snap = ROOT / "data/market" / "latest_market_snapshot.json"
    if not snap.exists():
        return ["宏观快照 latest_market_snapshot.json 不存在→宏观层全未产出·须先跑 market_macro_snapshot.py"], False
    d = json.loads(snap.read_text(encoding="utf-8"))
    mc = d.get("macro_completeness", {})
    not_closed = [k for k in ("US10Y真收益率_present", "FOMC事件_present", "日银_present", "日债_present") if not mc.get(k)]
    macro_closed = not not_closed
    if not_closed:
        warns.append("宏观层未闭合·未产出项:%s(如实标未接·不沿用旧事件冒充当日·AL2-5)" % "、".join(k.replace("_present", "") for k in not_closed))
    # 沿用>1天检查(若快照/证据里有"沿用第N天")
    for f in glob.glob(str(ROOT / "data/evidence_chain" / f"daily_{date}.json")):
        try:
            s = Path(f).read_text(encoding="utf-8")
            for m in re.finditer(r"沿用第?\s*(\d+)\s*天", s):
                if int(m.group(1)) > 1:
                    warns.append("证据链出现『沿用第%s天』>1天→该层须标未产出·不许当当日事件(AL2-5)" % m.group(1))
                    break
        except Exception:
            pass
    # ★AL2-6核心:宏观不闭合时,若 sector_activation 宣布了激活→报"证据不闭合不许宣激活"
    sa = sorted(glob.glob(str(ROOT / "data/market" / "sector_activation_*.json")))
    if sa and not macro_closed:
        sad = Path(sa[-1]).name
        warns.append("★证据不闭合却存在激活清单 %s→宏观层(US10Y/FOMC/日银/日债)未接·板块激活证据链不闭合·不许据此宣布板块激活(AL2-6/GPT第5条)" % sad)
    return warns, macro_closed


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    warns, closed = check(a.date)
    if warns:
        print("[macro_completeness 告警·不阻断] 宏观层闭合=%s" % closed)
        for w in warns:
            print("  ⚠", w)
    else:
        print("[macro_completeness PASS] 宏观层闭合·关键字段齐")
    return 0   # 非关键(告警)·不阻断出品·但产品该层须据此标未产出


if __name__ == "__main__":
    raise SystemExit(main())
