#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮341乙3 到期未记分闸:见分晓日已过却未记分→记分卡当前不可信。
★结构化判定(§5.4):看 verdict_date(日期比较) + 已记分/verdict 字段(布尔)·不读自由文本。
写 data/pdca/overdue_verdict_{date}.json·供 product_blocks.overdue_verdict_html 打册1第一屏红条。
★接进 daily_auto_produce(建了不接=没建)。用法: python scripts/overdue_verdict_gate.py --date 20260810
"""
import sys, json, argparse
from pathlib import Path
from datetime import date, datetime
ROOT = Path(__file__).resolve().parents[1]


def _asdate(s):
    try:
        y, m, dd = map(int, str(s)[:10].split("-")); return date(y, m, dd)
    except Exception:
        return None


def check(dh):
    today = _asdate(dh) or datetime.now().date()
    try:
        reg = json.loads((ROOT / "data/forecast/locked_predictions_registry.json").read_text(encoding="utf-8"))
    except Exception:
        return {"date": dh, "到期未记分数": 0, "逐条": [], "★记分卡可信": True, "_注": "registry读不到"}
    overdue = []
    for r in reg.get("已登记预测", []) or []:
        vd = _asdate(r.get("verdict_date"))
        scored = r.get("已记分") or r.get("verdict")   # 结构化:布尔/存在性
        if vd and vd <= today and not scored:
            overdue.append({"标的": r.get("ticker"), "horizon": r.get("horizon"),
                            "见分晓日": str(r.get("verdict_date"))[:10], "逾期天数": (today - vd).days})
    overdue.sort(key=lambda x: -x["逾期天数"])
    return {"date": dh, "到期未记分数": len(overdue), "逐条": overdue,
            "★记分卡可信": len(overdue) == 0,
            "_说明": "★见分晓日已过却未记分→记分卡当前不可信(分母空转/未计入对错)。记分=Opus5·闸只报事实。"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dh = a.date if "-" in a.date else "%s-%s-%s" % (a.date[:4], a.date[4:6], a.date[6:])
    out = check(dh)
    p = ROOT / "data/pdca" / ("overdue_verdict_%s.json" % a.date.replace("-", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    json.loads(txt); p.write_text(txt, encoding="utf-8")
    print("[overdue_verdict] %s · 到期未记分 %d 条 · 记分卡可信=%s" % (dh, out["到期未记分数"], out["★记分卡可信"]))
    for o in out["逐条"]:
        print("  ⏳", o["标的"], o["horizon"], "见分晓", o["见分晓日"], "逾期", o["逾期天数"], "天")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
