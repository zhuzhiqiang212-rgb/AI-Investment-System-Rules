#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scan_date_consistency_gate.py —— U2(轮57):文件名日期 vs 内容时点一致闸。
daily_scan_{YYYYMMDD}.json 里每条 update_time 的日期必须与文件名日期相符:
  · 日股(JP.*)：update_time 日期 必须 = 文件名日期(同日盘中/收盘)。
  · 美股(US.*)：允许 = 文件名日期 或 文件名−1（★美股收盘时区滞后:JST早晨时最新完整美股交易日=前一日·合法）。
不符 → FAIL 并报出差几天、哪些条目不符。
★理由:这次文件名写07-31、内容全是07-30·它是所有下游(target_gap/预测/产品)的价格源头·源头标签与实质不符则下游全错不显眼。
★口径注:美股「前一日=收盘合法」这一放宽尚需董事长确认;日股严格同日。
用法: python scripts/scan_date_consistency_gate.py --date 20260731
返回码 0=PASS · 7=FAIL
"""
import argparse, json, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _iter_rows(d):
    """兼容两种结构:新(轮57)『逐只』/旧 items['1_当日20只价']['逐只'] 或 items[]。"""
    if isinstance(d.get("逐只"), list):
        for x in d["逐只"]:
            yield x.get("code"), x.get("update_time"), x.get("时点")
        return
    items = d.get("items")
    if isinstance(items, dict):
        for v in items.values():
            if isinstance(v, dict) and isinstance(v.get("逐只"), list):
                for x in v["逐只"]:
                    yield x.get("code"), x.get("update_time"), None
    elif isinstance(items, list):
        for x in items:
            yield x.get("code") or x.get("symbol"), x.get("update_time"), None


def check(date_compact):
    p = ROOT / "data/market" / f"daily_scan_{date_compact}.json"
    if not p.exists():
        return ["daily_scan_%s.json 不存在" % date_compact], {}
    d = json.loads(p.read_text(encoding="utf-8"))
    fn_date = datetime.date(int(date_compact[:4]), int(date_compact[4:6]), int(date_compact[6:8]))
    fails = []; n = 0
    for code, ut, shidian in _iter_rows(d):
        if not code or not ut:
            continue
        n += 1
        try:
            ud = datetime.date(int(str(ut)[:4]), int(str(ut)[5:7]), int(str(ut)[8:10]))
        except Exception:
            fails.append(f"{code} update_time 无法解析日期：{ut}")
            continue
        diff = (fn_date - ud).days
        is_us = str(code).startswith("US.")
        if is_us:
            if diff not in (0, 1):  # 美股允许当日或前一日(收盘时区滞后)
                fails.append(f"{code}(美股) update_time {ud} 与文件名 {fn_date} 差 {diff} 天（美股仅允许 0/1 天·>1=陈旧）")
        else:
            if diff != 0:  # 日股必须同日
                fails.append(f"{code}(日股) update_time {ud} 与文件名 {fn_date} 差 {diff} 天（日股必须同日）")
    return fails, {"条目数": n, "文件名日期": str(fn_date)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, stats = check(a.date)
    if fails:
        print(f"[scan_date_consistency FAIL] {len(fails)} 条不符 · {stats}")
        for x in fails:
            print("  ✗", x)
        return 7
    print(f"[scan_date_consistency PASS] 文件名日期与内容时点一致 · {stats}（日股同日·美股允许前一日=收盘时区滞后）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
