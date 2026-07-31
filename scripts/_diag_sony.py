#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
i = h.find('id="deep-JP.6758"')
nxt = h.find('id="deep-', i + 12)
seg = h[i:(nxt if nxt > 0 else len(h))]
print("索尼deep卡 动作=X:")
for m in re.finditer(r"动作[＝=]([守加观等减盯])", seg):
    print("  ", repr(re.sub("<[^>]+>", "", seg[m.start() - 15:m.start() + 8])))
print("索尼deep卡 今日动作:")
for m in re.finditer(r"今日动作 (?:<b>)?([守加观等减盯])", seg):
    print("  ", m.group(1))
# 爱德万 止盈¥27505
i2 = h.find('id="deep-JP.6857"')
n2 = h.find('id="deep-', i2 + 12)
seg2 = h[i2:(n2 if n2 > 0 else len(h))]
print("爱德万 现价已在上沿之上（¥27,505:")
for m in re.finditer(r"现价已在上沿之上（¥27,505[^）<]*", seg2):
    print("  ", repr(re.sub("<[^>]+>", "", seg2[m.start() - 20:m.start() + 30])))
