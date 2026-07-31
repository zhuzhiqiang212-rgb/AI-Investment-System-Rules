#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段23·前瞻预测表爱德万"估值=合理"退出(架构师抓·硬闸扩③漏前瞻区)→locked_v3。字节级。
爱德万/闪迪 前瞻表/一句话/决定摘要 任何"估值=合理/极贵/估值合理"→异常待核·不计算。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


AN = "估值=异常待核·不计算（价格/复权口径异常·见增补⑮）"
log = {}
# 爱德万前瞻表 估值=合理(唯一·增补⑥)
for a in ["软性=位置中性+估值=合理+护城河", "估值=合理+护城河=宽护城河→守"]:
    c = h.count(a)
    if c:
        h = h.replace(a, a.replace("估值=合理", AN))
        log[a[:16]] = c

# 兜底:全产品爱德万/闪迪邻近"估值=合理/估值合理/估值=极贵"(当日非hist)
for m in list(re.finditer(r"估值[=＝]合理|估值合理|估值[=＝]极贵", h)):
    if hist(m.start()):
        continue
    ctx = pl(h[max(0, m.start() - 45):m.start() + 10])
    if "爱德万" in ctx or "闪迪" in ctx:
        h = h[:m.start()] + AN + h[m.end():]
        log.setdefault("兜底异常股估值合理", 0)
        log["兜底异常股估值合理"] += 1

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段23:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 验:爱德万/闪迪 估值=合理 当日残留
resid = 0
for m in re.finditer(r"估值[=＝]合理|估值合理", h):
    if not hist(m.start()):
        ctx = pl(h[m.start() - 45:m.start() + 8])
        if "爱德万" in ctx or "闪迪" in ctx:
            resid += 1
print("★爱德万/闪迪 估值=合理 当日残留:", resid)
