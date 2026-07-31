#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段17b·清残留『⚡已触发』加仓语义→价格触发·闸未过。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# 逐个替换 ⚡已触发(当日·非hist)
out, last, n = [], 0, 0
for m in re.finditer(r"⚡已触发", h):
    if hist(m.start()):
        continue
    out.append(h[last:m.start()])
    out.append("⚡价格条件触发·动作闸未通过·今日不得加仓·")
    last = m.end()
    n += 1
out.append(h[last:])
h = "".join(out)
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("⚡已触发改写:", n, "· 残留⚡已触发(当日):", sum(1 for m in re.finditer("⚡已触发", h) if not hist(m.start())))
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
