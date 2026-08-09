#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★★轮183 C-2:轻量前置正文检查(供 07:00 JST 定时·生产前30分钟)。
★若无当日Opus5正文→主控写醒目「等Opus5正文」待办→Opus5 开工读主控立刻看到「今天正文还没交」。
★不跑数据/不渲染·只查文件+回写主控(秒级)·非阻断。

技术可行性:Windows任务计划可注册【第二个】任务(07:00)独立于07:30生产任务·故【技术上可行】。
注册命令(★董事长决定是否装·不擅改系统设置):
  schtasks /Create /TN "AI投资系统_07点正文前置检查" /TR "\"<pythonw路径>\" \"<本脚本路径>\"" /SC DAILY /ST 07:00 /F
用法:
  python scripts/preflight_content_check.py            # 查今天(JST)
  python scripts/preflight_content_check.py --date 20260805
"""
import sys, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="07:00 轻量正文前置检查(C-2)")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    date = a.date or datetime.now(JST).strftime("%Y%m%d")
    dc = date.replace("-", "")
    sys.path.insert(0, str(ROOT / "scripts"))
    import daily_auto_produce as d   # 复用同一前置检查逻辑(单一真相·不重复实现)
    ok = d._preflight_zhengwen(dc)
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    dsp = f"{dc[4:6]}-{dc[6:8]}"
    # ★C-1(轮215):除写主控外·再写一个显眼缺件文件(董事长不一定看主控)。★轮219 改 marker 式:[正文]行+[逾期]行并存。
    flag = ROOT / "00_请先看这里" / "★★今日缺件_卡在谁.txt"
    # 只保留 [逾期] 行(由 forecast_due_scan 刷新)·丢弃旧[正文]行及无marker遗留行
    keep = [l for l in (flag.read_text(encoding="utf-8").splitlines() if flag.exists() else []) if l.startswith("[逾期]")]
    if ok:
        print(f"[07点前置检查 {now}] ✔ 当日Opus5正文已交(opus5_content_{dc}.json)·07:30生产可出产品。")
        zline = f"[正文] {dsp} {now} ✔ 无缺件 · 当日Opus5正文已交(opus5_content_{dc}.json)·07:30生产可出产品。"
    else:
        print(f"[07点前置检查 {now}] ▲▲ 缺当日Opus5正文(opus5_content_{dc}.json)→主控已写『等Opus5正文』待办。"
              "★Opus5开工读主控即见『今天正文还没交』·07:30前交上则生产可出产品。")
        zline = f"[正文] {dsp} {now} ▲▲ 缺件 · 缺 opus5_content_{dc}.json · 卡在 Opus5（07:30前交上则可出）"
    flag.write_text("\n".join([zline] + keep) + "\n", encoding="utf-8")
    # ★★★轮219 补漏2:07:00前置也扫【逾期未评预测】→写缺件文件[逾期]行+overdue json(让Opus5写正文前就看见欠账)
    try:
        import forecast_due_scan as fds
        today_s = f"{dc[:4]}-{dc[4:6]}-{dc[6:8]}"
        overdue, upcoming = fds.run(today_s, dc)
        print(f"[07点前置检查 {now}] 逾期未评 {len(overdue)} 条 · 7天内临期 {len(upcoming)} 条")
    except Exception as e:
        print(f"[07点前置检查] 逾期扫描失败(非阻断): {str(e)[:80]}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
