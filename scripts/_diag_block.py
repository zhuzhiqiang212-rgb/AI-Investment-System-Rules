#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
i = h.find("以下为7-19历史档·作废·不据此：")
seg = h[i:i + 900]
print("从'以下为7-19历史档'起900字符原始:")
print(seg)
