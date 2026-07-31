#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段21·第一三共顶部表动作等→守统一(架构师:顶部等vs统一表守·我stage6漏了第一三共)。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
top = h.find('<div id="topnav"')
log = {}
# 增补⑥前瞻表 + update层 第一三共行 动作cell 等→守(仅顶部·仅第一三共)
pat = re.compile(r'(第一三共</td><td>JP\.4568</td>(?:<td[^>]*>[^<]*</td>){0,5}?<td style="text-align:center">)等(</td>)')
out, last, n = [], 0, 0
for m in pat.finditer(h):
    if m.start() >= top:
        continue
    out.append(h[last:m.start()]); out.append(m.group(1) + "守" + m.group(2)); last = m.end(); n += 1
out.append(h[last:])
h = "".join(out)
log["第一三共顶部等→守"] = n
# 兜底:update层持仓表第一三共(name code split qty price mktval action)
pat2 = re.compile(r'(第一三共</td><td>JP\.4568</td><td>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td style="text-align:center">)等(</td>)')
h, n2 = pat2.subn(r"\g<1>守\g<2>", h)
log["update层第一三共等→守"] = n2

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段21:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 验:第一三共顶部残留"等"动作
resid = 0
for m in re.finditer(r'第一三共</td><td>JP\.4568</td>(?:<td[^>]*>[^<]*</td>){0,6}?<td style="text-align:center">等</td>', h):
    if m.start() < top:
        resid += 1
print("★第一三共顶部动作=等残留:", resid, "· 顶部第一三共守数:", len(re.findall(r'第一三共</td><td>JP\.4568</td>(?:<td[^>]*>[^<]*</td>){0,6}?<td style="text-align:center">守</td>', h[:top])))
