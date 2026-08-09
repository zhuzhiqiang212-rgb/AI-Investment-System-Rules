#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮342乙3:见分晓日 与 horizon 是否匹配(结构化§5.4·只读 horizon枚举 + 两个日期·不读自由文本)。
根因(Opus5记COIN时发现):horizon=0~30天·见分晓日却设在锁定后第2天→测的是两天波动·不是那个判断。

判据(董事长2026-08-09定):
  · 短期(0~30d)  → 锁定→见分晓 间隔应 ≥20 天
  · 长期(1y/长期) → 间隔应 ≥80 天
用法:
  python scripts/horizon_verdict_match_gate.py --date 20260810   # 全表复查·列不匹配·【不自动改】
另供 check_lock(horizon, locked_at, verdict_date) 作【锁定闸】:新锁定间隔不匹配→拒绝锁定(源头挡)。
★★不自动改历史条目:改见分晓日会改胜率·须董事长逐条重设(否则=输了就改考试日期)。
"""
import sys, json, argparse
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

MIN_DAYS = {"short": 20, "long": 80}


def _asdate(s):
    try:
        y, m, dd = map(int, str(s)[:10].replace("/", "-").split("-")); return date(y, m, dd)
    except Exception:
        return None


def horizon_class(h):
    """结构化枚举分类·返回 'short'/'long'/None(无法判)。"""
    if not h:
        return None
    s = str(h).strip().lower()
    if s in ("0-30d", "30d", "1m", "短期", "短") or "30d" in s or s.startswith("短"):
        return "short"
    if s in ("1y", "12m", "长期", "长") or s.endswith("y") or "1y" in s or s.startswith("长") or "年" in s:
        return "long"
    return None


def check_interval(horizon, d_lock, d_verdict):
    """核心判据·返回 (匹配bool, 间隔天数, 要求最小天数, 类别)。无法判→(None,...)。"""
    cls = horizon_class(horizon)
    dl, dv = _asdate(d_lock), _asdate(d_verdict)
    if cls is None or dl is None or dv is None:
        return (None, None, None, cls)
    interval = (dv - dl).days
    need = MIN_DAYS[cls]
    return (interval >= need, interval, need, cls)


def check_lock(horizon, locked_at, verdict_date):
    """★锁定闸:新锁定用。返回 (可锁bool, 原因)。间隔不匹配→拒绝(False)。无法判→放行但标注(不硬拦未知)。"""
    ok, interval, need, cls = check_interval(horizon, locked_at, verdict_date)
    if ok is None:
        return True, "horizon/日期无法结构化判定(cls=%s)·锁定闸放行但请人工核" % cls
    if not ok:
        return False, "★拒绝锁定:horizon=%s(%s)要求见分晓距锁定≥%d天·实际仅%d天(测的是短波动·不是该判断)" % (
            horizon, cls, need, interval)
    return True, "间隔%d天≥%d天·匹配" % (interval, need)


def scan_registry(dh):
    """全表复查·列不匹配·【不自动改】。写 data/pdca/horizon_verdict_mismatch_{date}.json。"""
    reg_p = ROOT / "data/forecast/locked_predictions_registry.json"
    d = json.loads(reg_p.read_text(encoding="utf-8"))
    mismatches, unjudgeable, ok_rows = [], [], 0
    for r in d.get("已登记预测", []) or []:
        horizon = r.get("horizon"); dl = r.get("locked_at"); dv = r.get("verdict_date")
        ok, interval, need, cls = check_interval(horizon, dl, dv)
        row = {"forecast_id": r.get("forecast_id"), "标的": r.get("ticker"), "horizon": horizon,
               "类别": cls, "锁定日": str(dl)[:10], "见分晓日": str(dv)[:10],
               "实际间隔天数": interval, "要求最小天数": need}
        if ok is None:
            unjudgeable.append(row)
        elif not ok:
            row["★问题"] = "间隔%d天 < 要求%d天(%s)·见分晓日设太早·须董事长重设" % (interval, need, cls)
            mismatches.append(row)
        else:
            ok_rows += 1
    out = {
        "_说明": "★轮342乙3 见分晓日↔horizon 匹配复查(结构化§5.4)·【只列不自动改】。改见分晓日会改胜率·须董事长逐条重设(写明改前改后+为什么)·否则=输了就改考试日期。",
        "date": dh, "判据": "短期(0~30d)≥20天·长期(1y)≥80天", "总条数": len(d.get("已登记预测", [])),
        "匹配": ok_rows, "不匹配数": len(mismatches), "无法判定数": len(unjudgeable),
        "★不匹配清单(待董事长逐条重设)": mismatches,
        "无法结构化判定(horizon/日期缺)": unjudgeable,
        "★重设动作归属": "董事长(逐条·写明改前改后+理由)。Code不代改·此表只列。",
    }
    p = ROOT / "data/pdca" / ("horizon_verdict_mismatch_%s.json" % dh.replace("-", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    json.loads(txt); p.write_text(txt, encoding="utf-8")
    return out


def _selftest():
    # COIN那个错:0-30d·07-30锁·08-01判=2天→应拒绝
    ok, why = check_lock("0-30d", "2026-07-30", "2026-08-01")
    assert ok is False, ("COIN应被锁定闸拒绝", ok, why)
    # 合规:0-30d·锁到25天后→放行
    ok2, _ = check_lock("0-30d", "2026-07-30", "2026-08-24")
    assert ok2 is True
    # 长期:1y·锁到90天→放行;锁到50天→拒绝
    assert check_lock("1y", "2026-07-30", "2027-07-30")[0] is True
    assert check_lock("1y", "2026-07-30", "2026-09-18")[0] is False
    print("[selftest] PASS · COIN(2天/0-30d)被拒 · 长期50天被拒 · 合规放行")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest(); return 0
    dh = a.date or date.today().strftime("%Y%m%d")
    dh = dh if "-" in dh else "%s-%s-%s" % (dh[:4], dh[4:6], dh[6:])
    out = scan_registry(dh)
    print("[horizon↔见分晓匹配] %s · 总%d · 匹配%d · ★不匹配%d · 无法判%d" % (
        dh, out["总条数"], out["匹配"], out["不匹配数"], out["无法判定数"]))
    for m in out["★不匹配清单(待董事长逐条重设)"]:
        print("  ✗", m["标的"], m["horizon"], "锁", m["锁定日"], "→见分晓", m["见分晓日"],
              "仅%d天(<%d)" % (m["实际间隔天数"], m["要求最小天数"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
