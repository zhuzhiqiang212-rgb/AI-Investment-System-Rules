#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


# 闪迪 加仓触发区行
for m in re.finditer(r"闪迪[^<]{0,140}", h):
    t = pl(m.group())
    if "加仓价" in t or "还差" in t or "现价" in t:
        print("闪迪触发行:", t[:130])
# 承接节点表内 闪迪/SNDK
i = h.find("承接节点")
if i > 0:
    seg = h[i:i + 3000]
    for m in re.finditer(r"闪迪[^\n]{0,120}", seg):
        print("承接节点闪迪:", pl(m.group())[:120])
