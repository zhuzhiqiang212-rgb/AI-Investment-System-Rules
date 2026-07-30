# -*- coding: utf-8 -*-
"""E2(49号)·估值重估触发巡检闸。每日巡检 val_inputs.json 每一只·三类触发:
 ①财报日型:earnings_calendar 该只 report_date ≤ 今日 且 last_reviewed < report_date
 ②指引变动型:尺A(valuation_ruler_guidance_revision)当日对该只已触发
 ③陈旧型:today − priced_at > 30 日
产出 data/valuation/review_due_{date}.json(命中清单+触发类型+理由+距今天数)。
★Code 只发现并摆清单·不改任何 fair 值(重估是 Opus 5 的活)。"""
import json, argparse, glob, pathlib
from datetime import date as _date, datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); ROOT = pathlib.Path(__file__).resolve().parent.parent
def _d(s):
    try: return _date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except Exception: return None
def build(dstr):
    today = _date(int(dstr[:4]), int(dstr[4:6]), int(dstr[6:8]))
    vi = json.loads((ROOT / "data" / "valuation" / "val_inputs.json").read_text(encoding="utf-8")).get("holdings", {})
    # 财报日历
    ecal = {}
    ep = ROOT / "data" / "valuation" / "earnings_calendar.json"
    if ep.exists():
        for e in json.loads(ep.read_text(encoding="utf-8")).get("events", []):
            if e.get("symbol") and e.get("report_date"):
                ecal[e["symbol"]] = e["report_date"]
    # 尺A当日已触发的只(指引变动型)
    rulerA = set()
    for f in glob.glob(str(ROOT / "data" / "valuation" / f"ruler_a_*_{dstr}.json")):
        try: rulerA.add(json.loads(pathlib.Path(f).read_text(encoding="utf-8")).get("标的"))
        except Exception: pass
    due = []
    for code, h in vi.items():
        triggers = []
        pa = _d(h.get("priced_at", "")); lr = _d(h.get("last_reviewed", h.get("priced_at", "")))
        # ①财报日型
        rd = _d(ecal.get(code, ""))
        if rd and rd <= today and (lr is None or lr < rd):
            triggers.append({"类型": "财报日型", "理由": "财报日 %s ≤ 今日·last_reviewed %s < 财报日→财报后未重估" % (rd, lr)})
        # ②指引变动型
        if code in rulerA:
            triggers.append({"类型": "指引变动型", "理由": "尺A当日已触发(全年净利指引变动≥15%)·公允须按尺A重估"})
        # ③陈旧型
        if pa and (today - pa).days > 30:
            triggers.append({"类型": "陈旧型", "理由": "priced_at %s 距今 %d 天 >30" % (pa, (today - pa).days)})
        if triggers:
            due.append({"code": code, "name": h.get("name", ""), "priced_at": h.get("priced_at"),
                        "last_reviewed": h.get("last_reviewed"), "距priced_at天数": ((today - pa).days if pa else None),
                        "触发": triggers, "review_trigger原文": h.get("review_trigger", "")})
    return {"_说明": "估值重估触发巡检·Code只发现摆清单不改fair(重估=Opus5)", "date": dstr,
            "巡检时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), "巡检只数": len(vi),
            "命中重估": [d["code"] for d in due], "命中数": len(due), "详情": due}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d")); a = ap.parse_args()
    r = build(a.date)
    out = ROOT / "data" / "valuation" / f"review_due_{a.date}.json"
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print("重估巡检 %s → %s · 巡检%d只 · 命中重估 %d:" % (a.date, out.name, r["巡检只数"], r["命中数"]))
    for d in r["详情"]:
        print("  ★%s %s:" % (d["code"], d["name"]), "; ".join(t["类型"] for t in d["触发"]))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
