# -*- coding: utf-8 -*-
"""★★★轮186 A:见分晓日历——从 locked_predictions_registry 读全部锁定预测的 verdict_date·机器算到期。

★★★A-3 铁规矩(§5.4·董事长轮186立)：
   ★「见分晓/到期/记分」的判定【必须由机器从 registry 读 verdict_date 得出】·
   ★★★【不得由 Opus5 口头指定】——轮176 就是 Opus5 口头把【财报日08-05】当成【预测到期日】·
      实际 SNDK 是 1y·verdict_date=2027-07-30·口头指定错了。★到期只认 registry 的 verdict_date 数值比较·不认任何口头说法。

产物 data/forecast/verdict_calendar.json:按 verdict_date 排序·每条 forecast_id/ticker/horizon/locked_at/verdict_date/sha256/状态。
状态:已过期未记分 / 已过期已记分 / 今日到期 / 未来。接 daily:今日到期→产品显要·未来7/30天→提前准备·★已过期未记分→告警(记分卡空转)。"""
import sys, json, glob, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
REGISTRY = ROOT / "data" / "forecast" / "locked_predictions_registry.json"
OUT = ROOT / "data" / "forecast" / "verdict_calendar.json"


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _scored_ids():
    """★真记分过的 forecast_id 集合(已判定=true·非改期/撤回)。verdict_*.json 里 已判定==true 才算记分。"""
    ids = set()
    for f in glob.glob(str(ROOT / "data" / "pdca" / "verdict_*.json")) + glob.glob(str(ROOT / "data" / "forecast" / "verdict_*.json")):
        o = _rj(f)
        for v in (o.get("verdicts", []) or []):
            if isinstance(v, dict) and v.get("已判定") is True and v.get("forecast_id"):
                ids.add(v["forecast_id"])
    return ids


def build(today=None):
    today = today or datetime.now(JST).strftime("%Y-%m-%d")
    reg = _rj(REGISTRY)
    preds = reg.get("已登记预测", []) or []
    scored = _scored_ids()
    rows = []
    for p in preds:
        vd = str(p.get("verdict_date") or "")
        fid = p.get("forecast_id")
        is_scored = fid in scored
        if not vd or vd == "None":
            state = "★verdict_date缺失(异常)"
        elif vd < today:
            state = "已过期已记分" if is_scored else "★★已过期·未记分(记分卡空转)"
        elif vd == today:
            state = "★今日到期·须Opus5记分"
        else:
            state = "未来"
        try:
            days = (datetime.strptime(vd, "%Y-%m-%d").date() - datetime.strptime(today, "%Y-%m-%d").date()).days if vd and vd != "None" else None
        except Exception:
            days = None
        rows.append({
            "forecast_id": fid, "ticker": p.get("ticker"), "horizon": p.get("horizon"),
            "locked_at": p.get("locked_at"), "verdict_date": vd, "sha256": p.get("sha256"),
            "距今天数": days, "★记分状态": state, "已记分": is_scored,
        })
    rows.sort(key=lambda r: (str(r["verdict_date"]) or "9999"))
    today_due = [r for r in rows if r["★记分状态"].startswith("★今日到期")]
    expired_unscored = [r for r in rows if "已过期·未记分" in r["★记分状态"]]
    next7 = [r for r in rows if r["距今天数"] is not None and 0 < r["距今天数"] <= 7]
    next30 = [r for r in rows if r["距今天数"] is not None and 0 < r["距今天数"] <= 30]
    out = {
        "_说明": "★轮186 A 见分晓日历。★★到期判定=机器从registry读verdict_date数值比较(§5.4)·【不得Opus5口头指定】(轮176 Opus5把财报日当到期日就错了)。",
        "date": today, "总预测数": len(rows),
        "★今日到期数": len(today_due), "★★已过期未记分数(记分卡空转)": len(expired_unscored),
        "未来7天到期数": len(next7), "未来30天到期数": len(next30),
        "★今日到期": today_due, "★★已过期未记分": expired_unscored,
        "未来7天": next7, "未来30天": next30, "全部(按verdict_date排序)": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def alert_line(today=None):
    """供 daily/render:今日到期 + 已过期未记分 告警行。"""
    o = _rj(OUT) or build(today)
    td, eu = o.get("★今日到期数", 0), o.get("★★已过期未记分数(记分卡空转)", 0)
    parts = []
    if td:
        parts.append("★今日有 %d 条预测到期·须Opus5记分" % td)
    if eu:
        parts.append("★★已过期未记分 %d 条(记分卡空转·须Opus5补记)" % eu)
    if not parts:
        parts.append("今日无预测到期·未来30天 %d 条" % o.get("未来30天到期数", 0))
    return " | ".join(parts), td, eu, o


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=None); a = ap.parse_args()
    today = None
    if a.date:
        d = a.date.replace("-", ""); today = "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
    o = build(today)
    print("[见分晓日历] %d条 · 今日到期%d · ★★已过期未记分%d · 未来7天%d · 未来30天%d" % (
        o["总预测数"], o["★今日到期数"], o["★★已过期未记分数(记分卡空转)"], o["未来7天到期数"], o["未来30天到期数"]))
    for r in o["★★已过期未记分"]:
        print("  ★已过期未记分:", r["forecast_id"], r["ticker"], r["horizon"], "verdict_date", r["verdict_date"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
