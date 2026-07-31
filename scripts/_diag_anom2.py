#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
lines = h.split("\n")
print("总行:", len(lines))
# line3737附近
for ln in range(3730, 3745):
    if ln < len(lines) and ("还差" in lines[ln] or "加仓价" in lines[ln] or "2,646" in lines[ln] or "2,940" in lines[ln] or "939" in lines[ln]):
        print(f"L{ln}:", re.sub("<[^>]+>", " ", lines[ln])[:130])


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


# 爱德万异常数字全位置(¥2,646/¥2,940/939.5/加仓价/还差)
print("\n=== 爱德万/闪迪 计算区异常数字(当日非hist) ===")
for kw in ["939.5", "2,646", "2,940", "3,234", "加仓价", "还差 9", "还差9"]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            ctx = pl(h[m.start() - 40:m.start() + 25])
            if any(x in ctx for x in ["爱德万", "6857", "闪迪", "SNDK", "加仓价", "还差", "止盈", "目标贡献", "2,646", "2,940", "939"]):
                print(f"  [{kw}] ...{ctx[-50:]}")
