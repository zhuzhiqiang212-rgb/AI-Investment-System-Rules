#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基线登记进PDCA记分卡（派工单收尾1·2026-07-22）。读 locked_predictions_registry → 按PDCA核对日排期·核对日自动提醒待评。
进分母(短25+长29=54)正式登记待评;不锁/不适用(4条)记录不进胜率分母。累计架构师短/长期胜率。
用法：python scripts/build_pdca_scorecard.py --date 20260722 [--check-due]"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[1]
PDCA = ROOT / "data" / "pdca"
JST = timezone(timedelta(hours=9))


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def due_date(cd):
    s = str(cd or "")[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=JST)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260722"); ap.add_argument("--check-due", action="store_true"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    today = datetime.now(JST)
    reg = json.loads((PDCA / "locked_predictions_registry.json").read_text(encoding="utf-8"))
    tot = reg["已登记预测"]
    active = [e for e in tot if e.get("进胜率分母", True) and e.get("状态", "").startswith("已锁定")]
    not_scored = [e for e in tot if not (e.get("进胜率分母", True) and e.get("状态", "").startswith("已锁定"))]

    if a.check_due:
        due = [e for e in active if due_date(e.get("PDCA核对日")) and due_date(e["PDCA核对日"]) <= today]
        print("到期待评:", len(due))
        for e in due:
            print("  ", e["标的"], e["尺度"], e["PDCA核对日"])
        return 0

    # 按核对日排期
    sched = defaultdict(list)
    for e in active:
        sched[str(e.get("PDCA核对日"))].append({"标的": e["标的"], "尺度": e["尺度"], "方向": e.get("方向"),
                                              "概率": e.get("概率"), "版本": e.get("版本"), "sha": e.get("锁定sha256", "")[:12],
                                              "PDCA判据": e.get("PDCA判据"), "状态": "待评(锁定·未到核对日)"})
    sched_sorted = dict(sorted(sched.items(), key=lambda kv: kv[0]))
    # 最近待评核对日
    upcoming = sorted([dd for cd in sched for dd in [due_date(cd)] if dd and dd >= today])
    next_due = (upcoming[0].strftime("%Y-%m-%d") if upcoming else None)
    due_now = [e["标的"] + "·" + e["尺度"] for e in active if due_date(e.get("PDCA核对日")) and due_date(e["PDCA核对日"]) <= today]

    sd = [e for e in active if e["尺度"] == "短期"]; ld = [e for e in active if e["尺度"] == "长期"]
    hit = reg.get("架构师胜率累计", {"短期": {"命中": 0, "已评": 0}, "长期": {"命中": 0, "已评": 0}})

    def rate(k):
        n = hit[k]["已评"]
        return (round(hit[k]["命中"] / n * 100, 1) if n else None)

    doc = {
        "_说明": "PDCA预测记分卡(基线登记)。进分母条目按PDCA核对日排期·核对日跑 --check-due 自动提醒待评·评判后累计架构师短/长期胜率。不锁/不适用不进分母(单列记录)。",
        "date": d, "generated_at": now(), "计时开始": now(),
        "登记来源": "data/pdca/locked_predictions_registry.json(forecast_lock已锁·SHA+外部时间+哈希链)",
        "登记条数": {"进胜率分母合计": len(active), "短期": len(sd), "长期": len(ld),
                  "记录不进分母(不锁/不适用)": len(not_scored),
                  "★口径注": "短25+长29=54进分母(派工单写53为算术笔误·如实以54为准)+4不进分母=58总登记"},
        "架构师短期预测胜率%": rate("短期"), "架构师长期预测胜率%": rate("长期"),
        "胜率说明": "分子=核对日已评命中·分母=进分母的已锁定条目。当前0已评→待核对日。",
        "按PDCA核对日排期": sched_sorted,
        "自动提醒": {"今日": today.strftime("%Y-%m-%d"), "今日到期待评": due_now or "无",
                 "最近待评核对日": next_due,
                 "提醒机制": "每日跑 python scripts/build_pdca_scorecard.py --check-due 列到期项;核对日评判命中/未命中→累加胜率"},
        "记录不进分母(单列)": [{"标的": e["标的"], "尺度": e["尺度"], "状态": e.get("状态"), "核对日": e.get("PDCA核对日")} for e in not_scored],
    }
    p = PDCA / f"pdca_scorecard_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("登记进分母:", len(active), "(短", len(sd), "长", len(ld), ")·不进分母", len(not_scored))
    print("核对日排期:", list(sched_sorted.keys()))
    print("最近待评核对日:", next_due, "· 今日到期:", due_now or "无")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
