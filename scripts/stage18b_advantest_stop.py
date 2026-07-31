#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段18b·爱德万止盈¥27,505退出(GPT#3异常标的止盈退出)。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
n = 0
h, n1 = re.subn(r"现价已在上沿之上（¥27,505[^）]*）?",
                "价格/复权口径异常待核·不生成止盈线（爱德万·见增补⑮）", h)
n += n1
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("爱德万止盈退出:", n, "· 残留¥27,505止盈:", h.count("现价已在上沿之上（¥27,505"))
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
