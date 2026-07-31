#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段12·风险配仓调整建议表就地改守(GPT#1)+target-gap旧目标块整块移历史隔离(GPT#3·非仅标注)。字节级保CRLF。"""
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
log = {}

# ---------- 风险配仓调整建议表 英伟达加/台积电建仓 → 守(表格数值就地改) ----------
r1a = "<tr><td><b>加</b></td><td>英伟达</td><td>13.8% → 18.0%</td><td>未来+60%·仍在单只20%上限内</td></tr>"
r1b = "<tr><td><b>守</b></td><td>英伟达</td><td>13.8%·维持</td><td>7-22统一动作=守·今日不加仓·原→18.0%加仓建议已废止</td></tr>"
log["英伟达行改守"] = h.count(r1a)
h = h.replace(r1a, r1b)
r2a = "<tr><td><b>建仓</b></td><td>台积电</td><td>0% → 4.0%</td><td>PEG0.6便宜·董事长本就在等回调上车·分档买入</td></tr>"
r2b = "<tr><td><b>守</b></td><td>台积电</td><td>0%·维持</td><td>7-22统一动作=守·今日不建仓·原→4.0%建仓建议已废止</td></tr>"
log["台积电行改守"] = h.count(r2a)
h = h.replace(r2a, r2b)

# ---------- target-gap 旧目标块 整块移历史隔离(折叠) ----------
start = h.find('<div id="target-gap"')
if start >= 0:
    depth, i, cnt = 0, start, 0
    while i < len(h) and cnt < 99999:
        cnt += 1
        nd, cd = h.find("<div", i), h.find("</div>", i)
        if cd == -1:
            break
        if nd != -1 and nd < cd:
            depth += 1
            i = nd + 4
        else:
            depth -= 1
            i = cd + 6
            if depth == 0:
                break
    block = h[start:i]
    wrapped = ('<details class="hist-iso" style="border:2px solid #5a1a1a;background:#fdf0f0;border-radius:8px;margin:8px 0">'
               '<summary style="color:#6b2020;font-weight:800;padding:6px;cursor:pointer">【★历史底稿·7-19主战场SBI口径·作废·移历史隔离·不参加今日决策 — 今日目标只用顶部增补①全账户$1,673,375双档】</summary>'
               + block + '</details>')
    h = h[:start] + wrapped + h[i:]
    log["target-gap移历史隔离"] = 1
    log["块长"] = i - start
else:
    log["target-gap移历史隔离"] = 0

# 底稿盲区36.6%(若在块外仍裸) → 作废
r3 = "⚠ 盲区占 36.6%（软银"
if r3 in h:
    h = h.replace(r3, "⚠ 盲区占 [作废·口径见增补①三情景B级盲区]（软银")
    log["底稿盲区36.6作废"] = 1

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段12执行:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("残留『13.8% → 18.0%』:", h.count("13.8% → 18.0%"), "·『0% → 4.0%』:", h.count("0% → 4.0%"), "·hist-iso折叠:", h.count('class="hist-iso"'))
