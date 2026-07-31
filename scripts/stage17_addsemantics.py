#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段17·加仓语义改写(GPT复验#1:chip守/等但正文加仓语义矛盾)。
守/等标的的『已触发/已跌到加仓价/现在就可以加·分批买』→『仅价格条件触发·但动作闸未通过·今日不得加仓』。字节级。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


log = {}

# ① ⚡已触发 今天 → 价格条件触发·闸未过
def r1(m):
    return m.group(0) if hist(m.start()) else '<span style="color:#8A3E00;font-weight:800">⚡价格条件触发·动作闸未通过·今日不得加仓</span><span style="display:none"> 今天'
h, n1 = re.subn(r'<span style="color:#1E7A45;font-weight:800">⚡已触发 今天', r1, h)
log["已触发改写"] = n1

# ② 今日已跌到加仓价：N 只 → 价格条件触发·闸未过
h, n2 = re.subn(r"⚡ 今日已跌到加仓价：(\d+) 只",
                r"⚡ 今日价格条件触发：\1 只（<b>动作闸未通过·今日不得加仓</b>·守/等）", h)
log["已跌到加仓价头改写"] = n2

# ③ 现在就可以加(...)；分批买、别一次买满；涨回 X 以上就别再追了。→ 闸未过不得加仓
def r3(m):
    if hist(m.start()):
        return m.group(0)
    ref = m.group(1)
    return (f"<b>7-22统一动作=守/等·仅价格条件触发·动作闸未通过·今日不得加仓</b>（原7-19『加·分批买』建议已废止·不据此；参考位 {ref}）。")
h, n3 = re.subn(r"（?现在就可以加[^；]*；分批买、别一次买满；涨回 ([¥$][\d,]+) 以上就别再追了。", r3, h)
# 兼容无前括号变体
h, n3b = re.subn(r"现在就可以加；分批买、别一次买满；涨回 ([¥$][\d,]+) 以上就别再追了。",
                 r"<b>7-22统一动作=守/等·仅价格条件触发·动作闸未通过·今日不得加仓</b>（原7-19加仓建议已废止；参考位 \1）。", h)
log["加仓建议改写"] = n3 + n3b

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段17:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
res = sum(1 for kw in ["已触发", "已跌到加仓", "分批买、别一次买满"] for m in re.finditer(kw, h) if not hist(m.start()))
print("残留加仓语义(当日):", res, "· 已触发:", sum(1 for m in re.finditer("⚡已触发", h) if not hist(m.start())), "· 分批买满:", sum(1 for m in re.finditer("分批买、别一次买满", h) if not hist(m.start())))
