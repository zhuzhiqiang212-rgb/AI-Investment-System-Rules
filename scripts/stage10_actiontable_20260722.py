#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段10·就地替换724今日动作表/全产品所有动作chip(架构师抓出:id在行末→stage8改错·今日动作表20行chip全是7-19旧值)。
通用chip归属:优先所在<tr>内ticker·卡内用nearest id兜底。全20只现均守/等·无加仓→今日动作表加仓字段(第一档/第二档/下单)中和;
总决定统计重算7-22(加0)。同股所有chip收敛7-22。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段10动作表.html"
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
NAME = {s: prod[s]["name"] for s in prod}
GLYPH = {}
for s in ["US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"]:
    GLYPH[s] = ("c-hold", "■ 守")
for s in ["US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.SNDK"]:
    GLYPH[s] = ("c-wait", "… 等")
GLYPH["US.MSTR"] = ("c-wait", "◉ 等·盯")
GLYPH["JP.8766"] = ("c-wait", "… 等·待核")
GLYPH["US.CRCL"] = ("c-wait", "… 等·待核")

h = SRC.read_bytes().decode("utf-8")
top = h.find('<div id="topnav"')
idre = re.compile(r'id="(?:act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"')
idpos = [(m.start(), m.group(1)) for m in idre.finditer(h)]

# ---------- 通用chip归属+修复 ----------
fixes = []
for m in re.finditer(r'<span class="chip (c-add|c-hold|c-wait|c-risk)">([^<]{1,14})</span>', h):
    if m.start() < top:
        continue           # 顶部层已对
    g = m.group(2).strip()
    if g == "⚠ 险":
        continue
    pos = m.start()
    # 所在<tr>内ticker优先
    tr_s = h.rfind("<tr", 0, pos)
    tr_e = h.find("</tr>", pos)
    prev_close = h.rfind("</tr>", 0, pos)
    ticker = None
    if tr_s > prev_close and tr_e > pos:      # chip在某<tr>内
        tkm = re.search(r"(US\.[A-Z]+|JP\.[0-9]+)", h[tr_s:tr_e])
        if tkm:
            ticker = tkm.group(1)
    if not ticker:                             # 卡内:nearest id
        near = min(idpos, key=lambda ip: abs(ip[0] - pos)) if idpos else None
        if near and abs(near[0] - pos) < 1500:
            ticker = near[1]
    if ticker in GLYPH:
        cls, glyph = GLYPH[ticker]
        newchip = f'<span class="chip {cls}">{glyph}</span>'
        if m.group(0) != newchip:
            fixes.append((m.start(), m.end(), newchip, ticker, g, glyph))
# 逆序应用
for start, end, newchip, tk, old, new in sorted(fixes, reverse=True):
    h = h[:start] + newchip + h[end:]
chip_fixed = len(fixes)

# ---------- 今日动作表 加仓字段中和(全20只守/等·无加仓) ----------
i = h.find("今日动作表（唯一决定源")
tstart = h.rfind("<table", 0, i)
tend = h.find("</table>", i)
tbl = h[tstart:tend]
n_field = 0
for lbl, repl in [("第一档", "—<span style=\"color:#888\">（7-22守/等·今日不加仓·无第一档）</span>"),
                  ("第二档", "—<span style=\"color:#888\">（无第二批加仓）</span>"),
                  ("下单", "—<span style=\"color:#888\">（守=不加不减·今日无下单）</span>")]:
    tbl, c = re.subn(r'(<td data-l="' + lbl + r'">).*?(</td>)', r"\g<1>" + repl + r"\g<2>", tbl)
    n_field += c
h = h[:tstart] + tbl + h[tend:]

# ---------- 总决定统计重算7-22 ----------
old_stat = "加 4·守 9·等 4·减 0·观察 3"
new_stat = "加 0·守 7·等 10·等·盯 1(MSTR)·等·待核 2(东京海上/Circle)·减 0·观察 0（7-22就地重算·全表守/等·无加仓）"
n_stat = h.count(old_stat)
h = h.replace(old_stat, new_stat)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
print("阶段10产物:", OUT.name, len(raw), "字节·乱码", raw.count(b"\xef\xbf\xbd"), "·裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("chip就地修复:", chip_fixed, "· 加仓字段中和:", n_field, "· 总决定重算:", n_stat)
from collections import Counter
print("修复明细(旧→新 by ticker):", Counter((f[3], f[4], f[5]) for f in fixes))
print("残留c-add:", h.count('class="chip c-add"'))
