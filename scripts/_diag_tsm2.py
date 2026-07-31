#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def in_hist(pos):
    ds = h.rfind('class="hist-iso"', 0, pos)
    de = h.rfind("</details>", 0, pos)
    return ds > de


print("约现金 分布(是否在hist-iso内):")
for m in re.finditer(r"约现金[0-9/]*", h):
    ctx = re.sub("<[^>]+>", "", h[m.start() - 20:m.start() + 6])[-24:]
    print(f"  [{'hist-iso内' if in_hist(m.start()) else '★当日正文'}] ...{ctx}")
print("---")
print("建仓 全部(非hist):")
cnt_body = 0
for m in re.finditer(r"建仓", h):
    if not in_hist(m.start()):
        cnt_body += 1
        ctx = re.sub("<[^>]+>", "", h[m.start() - 18:m.start() + 12])[-28:]
        print(f"  ★正文建仓: ...{ctx}")
print("建仓在当日正文数:", cnt_body)
# 台积电why卡内 约现金/建仓
i = h.find('id="why-US.TSM"')
seg = h[i:i + 4000]
print("--- 台积电why卡 约现金/建仓 ---")
for kw in ["约现金1/4", "约现金1/2", "约现金1/3", "建仓", "hist-iso"]:
    print(f"  台积电why卡 '{kw}': {seg.count(kw)}")
