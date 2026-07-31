#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段11b·英伟达风险配仓加仓语句→守(7-22)+底稿盲区36.6%作废。字节级保CRLF。"""
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22_阶段11目标风险.html")
h = p.read_bytes().decode("utf-8")
reps = [
    ("风险配仓建议加至18%", "7-22守·不加仓(加仓建议已废止)"),
    ("45%上限已废止→可加", "45%上限已废止·但7-22统一动作=守·今日不加仓"),
    ("→现可加；", "·但7-22守·今日不加仓；"),
    ("⚠ 盲区占 36.6%（软银", "⚠ 盲区占 [作废·口径见增补①三情景B级盲区]（软银"),
]
log = {}
for a, b in reps:
    c = h.count(a)
    log[a[:14]] = c
    if c:
        h = h.replace(a, b)
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("执行:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("残留加至18%:", h.count("加至18%"), "·残留可加（:", h.count("可加（"), "·残留盲区占 36.6%（软银:", h.count("盲区占 36.6%（软银"))
