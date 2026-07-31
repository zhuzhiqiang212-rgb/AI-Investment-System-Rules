#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段15·L3决定摘要『今日动作X』文字字段就地改7-22(三轮遗漏:stage8只改『动作=X』带等号·漏了『今日动作 X』空格式)。
按deep卡ticker归属·每只今日动作→7-22基字(守/等)。+『建议金额 约现金X分批』中和+闪迪决定摘要股数20→5。字节级。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
守 = {"US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"}
BASE = {}
for s in 守:
    BASE[s] = "守"
for s in ["US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.SNDK", "US.MSTR", "JP.8766", "US.CRCL"]:
    BASE[s] = "等"

# 按 deep 卡 就地改 今日动作 X
anchors = sorted([(m.start(), m.group(1)) for m in re.finditer(r'id="deep-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
parts, last, n_act = [], 0, 0
for i, (pos, tk) in enumerate(anchors):
    if tk not in BASE:
        continue
    seg_end = starts[i + 1] if i + 1 < len(starts) else len(h)
    seg = h[pos:seg_end]
    new, c = re.subn(r"(今日动作 (?:<b>)?)[守加观等减盯]", r"\g<1>" + BASE[tk], seg)
    n_act += c
    parts.append(h[last:pos]); parts.append(new); last = seg_end
parts.append(h[last:])
h = "".join(parts)

# 建议金额 约现金X分批 → 中和(守/等无买卖金额)
h, n_amt = re.subn(r"建议金额 约现金[0-9/]+分批", "建议金额 <b>7-22守/等·今日无买卖金额</b>", h)

# 闪迪 deep决定摘要 股数 20 → 5(留痕)。仅SNDK卡内
i = h.find('id="deep-US.SNDK"')
if i >= 0:
    nxt = h.find('id="deep-', i + 10)
    seg = h[i:nxt if nxt > 0 else len(h)]
    seg2, c = re.subn(r"股数 20\b", "股数 5(账户为准·原富途今日显20留痕)", seg, count=1)
    if c:
        h = h[:i] + seg2 + (h[nxt:] if nxt > 0 else "")
    n_sndk = c
else:
    n_sndk = 0

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段15:今日动作X改", n_act, "· 建议金额中和", n_amt, "· 闪迪股数20→5", n_sndk)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 校验:今日动作 与7-22不符
bad = []
anchors = sorted([(m.start(), m.group(1)) for m in re.finditer(r'id="deep-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
for i, (pos, tk) in enumerate(anchors):
    if tk not in BASE:
        continue
    seg = h[pos:(starts[i + 1] if i + 1 < len(starts) else len(h))]
    for m in re.finditer(r"今日动作 (?:<b>)?([守加观等减盯])", seg):
        if m.group(1) != BASE[tk]:
            bad.append((tk, m.group(1), "应" + BASE[tk]))
print("残留今日动作不符7-22:", bad if bad else "无")
print("残留 建议金额 约现金:", len(re.findall(r"建议金额 约现金", h)))
