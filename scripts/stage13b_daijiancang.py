#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段13b·清残留待建仓(角色/对目标贡献)→持有观察。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
for m in re.finditer("待建仓", h):
    print(repr(re.sub("<[^>]+>", "", h[m.start() - 14:m.start() + 8])))
n = h.count("待建仓")
h = h.replace("待建仓", "持有/观察(7-22守·非建仓)")
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("待建仓清:", n, "→", h.count("待建仓"), "· 乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
