# -*- coding: utf-8 -*-
"""★★轮190 E:SBI持仓数据新鲜度告警——SBI只能靠董事长手动截图·不发就静默用旧数字算(不报错)。
★若最新 sbi_positions_*.json 的 data_date > N天(默认3)未更新 → 主控/产品显要处告警「SBI持仓可能过期·所有权重待核」。"""
import sys, json, glob, re, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
N_DAYS = 3

def latest_sbi_date():
    fs = sorted(glob.glob(str(ROOT / "data/accounts/sbi_positions_*.json")))
    if not fs:
        return None, None
    m = re.search(r"sbi_positions_(\d{8})", Path(fs[-1]).name)
    return (m.group(1) if m else None), fs[-1]

def check(today=None):
    today = today or datetime.now(JST).strftime("%Y%m%d")
    sd, f = latest_sbi_date()
    if not sd:
        return {"stale": True, "days": None, "告警": "★SBI持仓快照缺失·所有含SBI的权重不可信·须董事长截图", "sbi_date": None}
    try:
        days = (datetime.strptime(today, "%Y%m%d").date() - datetime.strptime(sd, "%Y%m%d").date()).days
    except Exception:
        days = None
    stale = (days is not None and days > N_DAYS)
    return {"stale": stale, "days": days, "sbi_date": "%s-%s-%s" % (sd[:4], sd[4:6], sd[6:8]),
            "N_DAYS": N_DAYS, "文件": Path(f).name if f else None,
            "告警": ("★★SBI持仓可能过期(%d天未更新>%d)·★所有含SBI权重/集中度/防御仓待核·须董事长发新截图" % (days, N_DAYS)) if stale else "SBI快照新鲜(%d天内)" % (days or 0)}

def alert_line(today=None):
    r = check(today)
    return (r["告警"], r["stale"], r)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=None); a = ap.parse_args()
    d = a.date.replace("-", "") if a.date else None
    r = check(d)
    print("[SBI新鲜度] sbi_date=%s · %d天前 · stale=%s · %s" % (r["sbi_date"], r["days"] if r["days"] is not None else -1, r["stale"], r["告警"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
