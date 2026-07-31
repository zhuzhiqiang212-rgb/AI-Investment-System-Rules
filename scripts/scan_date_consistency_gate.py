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


def _latest_complete_us_trading_day(fn_date):
    """V1-2(裁定A):文件名日期(JST早晨)对应的【最新完整美股交易日】=从前一日起回退·跳周末。
    ★美国假日未接(仅周末顺延)→遇假日可能误判·已在报告注明待接假日历。"""
    d = fn_date - datetime.timedelta(days=1)
    while d.weekday() >= 5:  # 周六/周日非交易
        d -= datetime.timedelta(days=1)
    return d


def check(date_compact):
    p = ROOT / "data/market" / f"daily_scan_{date_compact}.json"
    if not p.exists():
        return ["daily_scan_%s.json 不存在" % date_compact], {}
    d = json.loads(p.read_text(encoding="utf-8"))
    fn_date = datetime.date(int(date_compact[:4]), int(date_compact[4:6]), int(date_compact[6:8]))
    latest_us = _latest_complete_us_trading_day(fn_date)
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
        is_us = str(code).startswith("US.")
        if is_us:
            # V1-2:美股 update_time 必须 = 最新完整美股交易日(周末顺延)·不超过1个完整交易日
            if ud != latest_us:
                td = (latest_us - ud).days
                # ★轮70 AI2:只改措辞不动判定——ud>latest_us 不是"数据太新是异常",而是"该美股交易日尚未收盘·抓到的是盘中价"。
                if ud < latest_us:
                    fails.append(f"{code}(美股) update_time {ud} ≠ 最新完整美股交易日 {latest_us}·陈旧 {td} 天(超1个完整交易日→FAIL)")
                else:
                    fails.append(f"{code}(美股) 取到 {ud} 盘中价，但该美股交易日尚未收盘"
                                 f"（收盘时刻 05:00 JST）→ 不可当完整交易日数据用。请于收盘后重跑，或改用 {latest_us} 收盘价。")
            # V1-1:时点标注须写明「最新完整美股交易日」不许只写日期
            elif shidian and "完整" not in str(shidian) and "收盘" not in str(shidian):
                fails.append(f"{code}(美股) 时点标注「{shidian}」未写明=最新完整美股交易日(V1-1)")
        else:
            if ud != fn_date:  # V1-3:日股严格同日
                fails.append(f"{code}(日股) update_time {ud} ≠ 文件名 {fn_date}（日股必须同日·差{(fn_date-ud).days}天）")
    return fails, {"条目数": n, "文件名日期": str(fn_date), "最新完整美股交易日": str(latest_us),
                   "★假日历": "未接·仅周末顺延·遇美国假日可能误判(待接)"}


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
