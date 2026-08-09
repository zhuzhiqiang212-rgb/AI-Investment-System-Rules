# -*- coding: utf-8 -*-
"""★★★轮219 补漏2:逾期未评预测扫描(纯机器·不涉判断)。
读 locked_predictions_registry.json·筛【PDCA核对日 <= 今天】且【状态 枚举含「待评」】·
输出 data/pdca/overdue_forecasts_{当日}.json(逐条:标的/尺度/核对日/已逾期天数)·并写入缺件提示文件。
★判定只读【结构化字段】(PDCA核对日 日期比较 + 状态 枚举)·不靠自由文本关键词(CLAUDE.md §5.4)。"""
import sys, json, time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_FLAG = ROOT / "00_请先看这里" / "★★今日缺件_卡在谁.txt"


def _parse(dstr):
    s = str(dstr or "").strip().replace("/", "-")[:10]
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def scan(today_s, upcoming_days=7):
    """★★★轮222 双源:返回 (逾期列表, 即将到期列表)·每条标『源』。判定只读结构化字段:到期日 日期比较 + 已评状态。
    逾期: 到期日<=today 且【未评】· 即将到期: today<到期日<=today+upcoming_days 且【未评】。
    源① pdca:到期日=PDCA核对日·未评=状态不含『已评』;源② forecast:到期日=verdict_date·未评=无记分文件。"""
    today = _parse(today_s)
    overdue, upcoming = [], []
    if not today:
        return overdue, upcoming
    import registry_sources as rs
    for e in rs.load_all():
        chk = _parse(e.get("到期日"))
        if not chk or e.get("已评"):              # 已评→不算逾期/临期
            continue
        row = {"源": e["源"], "标的": e["标的"], "尺度": e["尺度"], "到期日": e["到期日"],
               "状态": e["状态"], "sha": (str(e.get("sha") or "")[:10]), "forecast_id": e.get("forecast_id")}
        if chk <= today:
            row["已逾期天数"] = (today - chk).days
            overdue.append(row)
        elif (chk - today).days <= upcoming_days:
            row["还剩天数"] = (chk - today).days
            upcoming.append(row)
    overdue.sort(key=lambda x: -x["已逾期天数"])
    upcoming.sort(key=lambda x: x["还剩天数"])
    return overdue, upcoming


def update_flag(overdue, upcoming):
    """★marker式更新缺件文件的[逾期]/[临期]行·不动 preflight 写的[正文]行。"""
    lines = []
    if _FLAG.exists():
        lines = [l for l in _FLAG.read_text(encoding="utf-8").splitlines()
                 if not l.startswith("[逾期]") and not l.startswith("[临期]")]
    ts = time.strftime("%m-%d %H:%M JST")
    if overdue:
        names = "; ".join("%s%s[%s源](逾期%d天)" % (o["标的"], o["尺度"], o["源"], o["已逾期天数"]) for o in overdue[:6])
        lines.append("[逾期] %s ▲▲ 逾期未评预测 %d 条 · 卡在 Opus5: %s" % (ts, len(overdue), names))
    else:
        lines.append("[逾期] %s ✔ 无逾期未评预测" % ts)
    # ★★★轮220:[临期]档(7天内将到期)——让核对日当天就能评·不再补评。★轮222双源
    if upcoming:
        近 = upcoming[0]
        lines.append("[临期] %s ★★ %d 条预测 7 天内到期 · 最近一条：%s%s[%s源]（还剩 %d 天·%s）"
                     % (ts, len(upcoming), 近["标的"], 近["尺度"], 近["源"], 近["还剩天数"], 近["到期日"]))
    else:
        lines.append("[临期] %s ✔ 7 天内无临期预测" % ts)
    _FLAG.parent.mkdir(parents=True, exist_ok=True)
    _FLAG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(today_s, dd):
    overdue, upcoming = scan(today_s)
    out = {"_说明": "★轮219/220/222 逾期+临期预测扫描·★双源(pdca+forecast)每条标『源』·判定读结构化字段(到期日日期比较+已评状态·§5.4)·纯机器不涉判断",
           "date": today_s, "as_of": time.strftime("%Y-%m-%d %H:%M JST"),
           "逾期条数": len(overdue), "逾期清单": overdue,
           "即将到期条数": len(upcoming), "即将到期": upcoming}
    (ROOT / "data/pdca").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/pdca" / ("overdue_forecasts_%s.json" % dd)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    update_flag(overdue, upcoming)
    return overdue, upcoming


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    dd = time.strftime("%Y%m%d")
    today_s = time.strftime("%Y-%m-%d")
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            raw = sys.argv[i + 1].replace("-", "")
            dd = raw
            today_s = "%s-%s-%s" % (raw[:4], raw[4:6], raw[6:8])
    overdue, upcoming = run(today_s, dd)
    print("逾期未评预测: %d 条 · 7天内临期: %d 条" % (len(overdue), len(upcoming)))
    for o in overdue[:12]:
        print("  ▲ %s %s · 核对日%s · 逾期%d天 · %s" % (o["标的"], o["尺度"], o["PDCA核对日"], o["已逾期天数"], o["状态"]))
    for u in upcoming[:12]:
        print("  ○ %s %s · 核对日%s · 还剩%d天" % (u["标的"], u["尺度"], u["PDCA核对日"], u["还剩天数"]))
    return 0   # ★非关键环·恒0不阻断


if __name__ == "__main__":
    raise SystemExit(main())
