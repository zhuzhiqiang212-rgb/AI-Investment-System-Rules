#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


print("=== 加仓语义(当日·非hist) ===")
for kw in ["已触发", "已跌到加仓", "分批买", "触发加仓"]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            print(f"  [{kw}] ...{pl(h[m.start()-40:m.start()+40])}")
print()
print("=== 爱德万 deep卡 异常字段(估值/加仓/止盈/目标) ===")
i = h.find('id="deep-JP.6857"')
nxt = h.find('id="deep-', i + 12)
seg = h[i:nxt if nxt > 0 else i + 4000]
for kw in ["2,646", "3,234", "939", "750%", "止盈", "估值", "加仓", "目标收益", "组合贡献"]:
    c = seg.count(kw)
    if c:
        m = seg.find(kw)
        print(f"  爱德万'{kw}'×{c}: ...{pl(seg[m-20:m+22])}")
