# -*- coding: utf-8 -*-
"""基准 vintage 过期告警闸（轮13 D1·架构师裁定 2026-07-25）。

补 (A) 类机制陈旧问题的『根』：没有这个闸，"基准过期"只能靠人偶然撞上。

逐只持仓判：
  ① priced_at / last_reviewed = "unknown"          → 告警『vintage未记录·无法验证是否过期』
  ② priced_at / last_reviewed 以 "n/a" 开头(待接)   → 不告警（从未产出基准=诚实待接·非陈旧）
  ③ 距 last_reviewed > 90 天未复核                   → 告警『超90天未复核(N天)』
  ④ 最近一次【已发布】财报日 > last_reviewed         → 告警『基准未纳入最新财报(财报日X)』

数据源：data/valuation/val_inputs.json（priced_at/last_reviewed/review_trigger）
        data/valuation/earnings_calendar.json（report_date/status/reported_on）
产物：  data/valuation/vintage_alerts_{date}.json
只体检报警·不改基准（重估口径是判据·架构师定）。
"""
import json, argparse, sys
from pathlib import Path
from datetime import date as _date

ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 90


def _rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse(s: str):
    """'YYYY-MM-DD' 或 'YYYY-MM'(→当月1日·偏保守取更旧) → date；不可解析→None。"""
    if not s or not isinstance(s, str):
        return None
    p = s.strip().split("-")
    try:
        if len(p) == 3:
            return _date(int(p[0]), int(p[1]), int(p[2]))
        if len(p) == 2:
            return _date(int(p[0]), int(p[1]), 1)
    except Exception:
        return None
    return None


def _latest_reported(sym: str, cal: dict, today: _date):
    """该股最近一次【已发布】财报日 = max(report_date ≤ today)。
    优先 reported_on(理解岗回填真发布日)；否则 status=已出 或 report_date≤today 视为已发布。"""
    best = None
    for e in cal.get("events", []):
        if str(e.get("symbol")) != sym:
            continue
        rd = _parse(e.get("reported_on")) or _parse(e.get("report_date"))
        if rd is None:
            continue
        reported = bool(e.get("reported_on")) or str(e.get("status")) == "已出" or rd <= today
        if reported and rd <= today and (best is None or rd > best):
            best = rd
    return best


def run(date: str) -> dict:
    today = _parse(date) or _date.today()
    vi = _rj(ROOT / "data" / "valuation" / "val_inputs.json")
    cal = _rj(ROOT / "data" / "valuation" / "earnings_calendar.json")
    alerts, ok, waiting = [], [], []
    for sym, v in (vi.get("holdings") or {}).items():
        name = v.get("name", sym)
        pa = str(v.get("priced_at", "unknown"))
        lr = str(v.get("last_reviewed", "unknown"))
        reasons = []
        # ② 诚实待接：从未产出基准·不算陈旧
        if pa.startswith("n/a") or lr.startswith("n/a"):
            waiting.append({"symbol": sym, "name": name,
                            "state": "待接真源（从未产出基准·非陈旧）",
                            "review_trigger": v.get("review_trigger", "")})
            continue
        # ① vintage 未记录
        lr_d = _parse(lr)
        if lr == "unknown" or lr_d is None:
            reasons.append("vintage未记录·无法验证是否过期（priced_at/last_reviewed=unknown→需补真实定价日）")
        else:
            # ③ 超 90 天未复核
            age = (today - lr_d).days
            if age > STALE_DAYS:
                reasons.append(f"超{STALE_DAYS}天未复核（距last_reviewed {lr} 已 {age} 天）")
            # ④ 最近已发布财报晚于复核
            er = _latest_reported(sym, cal, today)
            if er is not None and er > lr_d:
                reasons.append(f"基准未纳入最新财报（最近已发布财报 {er.isoformat()} 晚于 last_reviewed {lr}）")
        if reasons:
            alerts.append({"symbol": sym, "name": name, "priced_at": pa, "last_reviewed": lr,
                           "alerts": reasons, "review_trigger": v.get("review_trigger", ""),
                           "severity": "高" if any("未纳入最新财报" in r for r in reasons) else "中"})
        else:
            ok.append({"symbol": sym, "name": name, "last_reviewed": lr})
    return {
        "as_of": date, "gate": "基准vintage过期告警闸", "stale_days_threshold": STALE_DAYS,
        "summary": {"告警": len(alerts), "通过": len(ok), "待接不计": len(waiting), "总持仓": len(vi.get('holdings') or {})},
        "alerts": alerts, "ok": ok, "waiting": waiting,
        "note": ("只报警不改基准（重估口径=判据·架构师定）。unknown→告警是有意的：现有基准普遍无定价日记录，"
                 "这正是要补的根。理解岗回填真实 priced_at/last_reviewed 后告警自动消。财报判据读 earnings_calendar.json。"),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="基准vintage过期告警闸")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    out = run(args.date)
    p = ROOT / "data" / "valuation" / f"vintage_alerts_{args.date}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    s = out["summary"]
    print(f"vintage闸 {args.date}: 告警{s['告警']} 通过{s['通过']} 待接{s['待接不计']} / 共{s['总持仓']}")
    for a in out["alerts"]:
        print(f"  ⚠ {a['name']}({a['symbol']}) [{a['severity']}]: {'；'.join(a['alerts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
