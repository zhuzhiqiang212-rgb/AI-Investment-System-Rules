#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段19b·爱德万独有异常数字token直接退出(全格式·当日非hist·robust)。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# 爱德万拆股基准错价(唯一)·所有含¥的token → [异常待核]
TOKENS = ["¥2,646", "¥2,940", "¥2,938", "¥3,234", "939.5%", "2,646~3,234", "2,646 ~ ¥3,234"]
total = 0
for tok in TOKENS:
    out, last, n = [], 0, 0
    for m in re.finditer(re.escape(tok), h):
        if hist(m.start()):
            continue
        out.append(h[last:m.start()])
        out.append("[异常待核·不计算]")
        last = m.end()
        n += 1
    out.append(h[last:])
    h = "".join(out)
    if n:
        total += n
        print(f"  {tok}: 退出{n}")
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("爱德万异常token退出:", total)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
resid = {num: sum(1 for m in re.finditer(re.escape(num), h) if not hist(m.start())) for num in ["2,646", "2,940", "3,234", "939.5"]}
print("★爱德万异常数当日残留:", {k: v for k, v in resid.items() if v} or "无(全退出)")
