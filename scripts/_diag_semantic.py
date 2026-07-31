#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def plain(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


print("=== A. GPT列5只旧价 全位置(非hist=当日双价) ===")
for name, old in [("软银", "5,424"), ("英伟达", "202.55"), ("第一三共", "2,791"), ("东京海上", "7,526"), ("爱德万", "27,505")]:
    for m in re.finditer(re.escape(old), h):
        z = "HIST" if hist(m.start()) else "★当日"
        print(f"  {name} 旧价{old} [{z}]: ...{plain(h[m.start()-22:m.start()+8])[-26:]}")
print()
print("=== B. 加仓语义词(守/等标的·当日) ===")
for kw in ["已触发", "分批买", "已跌到加仓", "下单", "现金1/3", "现金1/4", "今日价值区", "触发加仓"]:
    body = [m.start() for m in re.finditer(re.escape(kw), h) if not hist(m.start())]
    print(f"  '{kw}' 当日={len(body)} · hist={h.count(kw)-len(body)}")
print()
print("=== C. 爱德万异常估值/止盈 ===")
for kw in ["2,646", "3,234", "939", "750%", "还差", "估值区", "止盈"]:
    n = h.count(kw)
    if n:
        m = h.find(kw)
        print(f"  '{kw}'×{n}: [{'HIST' if hist(m) else '★当日'}] ...{plain(h[m-18:m+14])[-22:]}")
