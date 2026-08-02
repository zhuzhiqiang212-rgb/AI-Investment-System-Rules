# -*- coding: utf-8 -*-
"""★轮80 AT2-2:未读源码不得对机器行为下判断(★这条拦的是 Opus5·不是 Code)。
Opus5 在任务包/正文里对某脚本/闸的行为下【判定】(如『闸判对了』『逻辑不动』『脚本判错』)时·须先声明读过该脚本——
做法:文件里出现「闸/脚本名 + 判定词」时·检查同文件内是否有对应源码路径引用(scripts/xxx.py 或『读过/已核 xxx.py』)·无→告警。
非阻断(告警)·把『凭印象判机器行为』从靠自觉变机器提醒。"""
import sys, argparse, glob, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
JUDGE = re.compile(r"(闸|脚本|渲染器|生成器|管线|gate|render_3layer|target_gap|daily_scan|forecast_gate)[^。\n]{0,20}(判对|判错|判定|逻辑不动|逻辑没?错|行为对|行为错|应该会|一定会|肯定|误判|判得对|不会错)")
SRC_HINT = re.compile(r"scripts/[\w_]+\.py|读过[^。\n]{0,20}\.py|已(读|核|看)过?[^。\n]{0,20}(源码|脚本|\.py)|逐行核|贴了源码")


def check_file(p):
    try:
        s = Path(p).read_text(encoding="utf-8")
    except Exception:
        return []
    has_src = bool(SRC_HINT.search(s))
    hits = []
    for m in JUDGE.finditer(s):
        seg = m.group(0)[:40]
        # 若该判定句附近或全文有源码引用→放行;否则告警
        if not has_src:
            hits.append(seg)
    return hits


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--files", nargs="*", help="要查的任务包/正文文件·缺省=当日任务中心md")
    a = ap.parse_args()
    dc = a.date.replace("-", "")
    files = a.files or (glob.glob(str(ROOT / "00_任务中心" / f"*{dc}*.md")) + glob.glob(str(ROOT / "00_任务中心" / "*Opus5*.md")))
    warns = []
    for f in files:
        hits = check_file(f)
        if hits:
            warns.append((Path(f).name, hits[:3]))
    if warns:
        print("[unread_source_gate 告警·拦Opus5·不阻断] 疑『未声明读源码就对机器行为下判定』:")
        for nm, hits in warns:
            print("  ⚠ %s:%s→该文件无源码路径引用(scripts/xx.py)·请先声明读过该脚本再下判定(AT2-2)" % (nm, hits))
    else:
        print("[unread_source_gate PASS] 未见『未读源码对机器行为下判定』(或已声明读过源码)·查%d文件" % len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
