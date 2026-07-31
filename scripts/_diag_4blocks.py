#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def in_hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# 4处 建议金额 约现金 当日正文块
for m in re.finditer(r"建议金额 约现金[0-9/]*", h):
    if not in_hist(m.start()):
        # 往前找该"买卖建议"块起点/标的
        pre = h[max(0, m.start() - 500):m.start()]
        tkm = re.findall(r"(US\.[A-Z]+|JP\.[0-9]+)", pre)
        # 往前找"买卖建议"或档头
        print("=== 当日正文块 标的近:", tkm[-1] if tkm else "?", "===")
        print(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", h[m.start() - 180:m.start() + 60])))
        print("原始前120:", repr(h[m.start() - 120:m.start() + 30]))
        print()
