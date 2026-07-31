#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段9b·净化增补①目标口径混算(GPT#3·字节级保CRLF)。"""
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
old = "需赚 $669,350（当前13只已−$61,625）</td><td>需赚 $1,673,375"
new = "需赚 $669,350（全账户40%档·A口径·不混13只亏损）</td><td>需赚 $1,673,375（全账户100%档）"
n = h.count(old)
h = h.replace(old, new)
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("净化混算:", n, "· 乱码", raw.count(b"\xef\xbf\xbd"), "· 裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("增补①残混算(669,350（当前13只):", "669,350（当前13只" in h)
