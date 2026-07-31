#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
for m in re.finditer("5,424", h):
    pos = m.start()
    print("原始±40:", repr(h[pos - 30:pos + 10]))
    print("码:", [(c, hex(ord(c))) for c in h[pos - 10:pos]])
    print("---")
