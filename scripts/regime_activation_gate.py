# -*- coding: utf-8 -*-
"""激活清单作废告警闸（轮23 N1④·裁定2026-07-27）。

★为什么:第1关是一票否决关·用作废的激活清单去筛整个漏斗=白跑·且结果看着完全正常没任何地方报错。
  这套系统凡『靠人记住』的最后都漏(vintage/求证表倒序/防御下限)。把『该不该重出激活清单』从
  靠人记得FOMC开过了·变成机器提醒——FOMC后架构师若忘了重出·系统自己喊。

判据:最新 sector_activation_*.json 的 date  <  最近【已发生】的 regime 事件日(FOMC/重大政策·regime_events.json)
      → 告警『激活清单(日期X)早于最近regime事件(Y)·可能已作废·尚未重出·第1关在拿作废清单筛』。
非关键·只告警不阻断。产物 data/logs/regime_activation_alert_{date}.json。
"""
import json, glob, argparse, sys
from pathlib import Path
from datetime import date as _date

ROOT = Path(__file__).resolve().parents[1]


def _pd(s):
    try:
        p = str(s).replace("-", "")
        return _date(int(p[:4]), int(p[4:6]), int(p[6:8]))
    except Exception:
        return None


def run(date: str) -> dict:
    today = _pd(date) or _date.today()
    # 最新激活清单
    cands = sorted(glob.glob(str(ROOT / "data" / "market" / "sector_activation_*.json")))
    act_date, act_name = None, None
    if cands:
        act_name = Path(cands[-1]).name
        try:
            d = json.loads(Path(cands[-1]).read_text(encoding="utf-8"))
            act_date = _pd(d.get("data_date") or act_name.split("_")[-1].replace(".json", ""))
        except Exception:
            act_date = _pd(act_name.split("_")[-1].replace(".json", ""))
    # 最近已发生的regime事件
    ev, latest_ev = [], None
    try:
        ev = json.loads((ROOT / "data" / "market" / "regime_events.json").read_text(encoding="utf-8")).get("events", [])
    except Exception:
        pass
    past = [(_pd(e.get("date")), e) for e in ev if _pd(e.get("date")) and _pd(e.get("date")) <= today]
    if past:
        past.sort(key=lambda x: x[0]); latest_ev = past[-1]
    alert = None
    if act_date is None:
        alert = "⚠缺 sector_activation·须架构师出激活清单再跑第1关"
    elif latest_ev and act_date < latest_ev[0]:
        alert = (f"★激活清单可能已作废·尚未重出：最新 {act_name}(日期{act_date.isoformat()}) "
                 f"早于最近regime事件 {latest_ev[1].get('type')} {latest_ev[0].isoformat()}"
                 f"（{latest_ev[1].get('note','')[:40]}）→第1关在拿作废清单筛·请架构师重出激活清单。")
    return {"as_of": date, "gate": "激活清单作废告警闸",
            "sector_activation": act_name, "sector_activation_date": act_date.isoformat() if act_date else None,
            "latest_regime_event": (latest_ev[1] if latest_ev else None),
            "alert": alert,
            "note": "非关键只告警。FOMC后架构师写新sector_activation(date≥事件日)→告警自消。regime_events.json架构师维护。"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True)
    a = ap.parse_args()
    out = run(a.date)
    (ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "logs" / f"regime_activation_alert_{a.date}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if out["alert"]:
        print("激活清单闸:", out["alert"])
    else:
        print(f"激活清单闸 {a.date}: OK·{out['sector_activation']} 未早于最近regime事件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
