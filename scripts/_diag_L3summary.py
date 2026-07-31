#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")


def in_hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# 所有 "今日动作 X"(文字·含<b>)
print("=== 今日动作 X 文字字段(全产品) ===")
c = 0
for m in re.finditer(r"今日动作 (?:<b>)?([守加观等减盯])", h):
    c += 1
    # 该摘要的股数/价 → 判定标的
    pre = h[max(0, m.start() - 200):m.start()]
    stk = re.search(r"股数 ([0-9,]+)", pre)
    print(f"  今日动作 {m.group(1)} | 股数近={stk.group(1) if stk else '?'} | hist={in_hist(m.start())}")
print("今日动作X 总数:", c)
print()
print("建议金额 约现金 总数:", len(re.findall(r"建议金额 约现金", h)), "· 非hist:", sum(1 for m in re.finditer(r"建议金额 约现金", h) if not in_hist(m.start())))
print("决定摘要 块数:", h.count("决定摘要（与①②同一份数据"))
