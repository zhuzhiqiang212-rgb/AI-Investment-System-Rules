#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段14·买卖建议历史档(6块)移入<details hist-iso>折叠(GPT收尾#1·与target-gap一致·不留当日正文)。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
SUMMARY = ('<details class="hist-iso" style="border:1px dashed #b58;background:#fbf3f7;border-radius:6px;margin:4px 0">'
           '<summary style="color:#6b2020;cursor:pointer;font-size:12px">展开7-19历史买卖档（作废·不据此·今日无买卖建议）</summary>')
# 匹配:以下为7-19历史档·作废·不据此：[闭合标签] (历史内容) </div>  →内容包进<details>
pat = re.compile(r"(以下为7-19历史档·作废·不据此：(?:</span>)?(?:</b>)?(?:<br>)?)(.*?)(</div>)", re.S)
n = 0


def wrap(m):
    global n
    n += 1
    return m.group(1) + SUMMARY + m.group(2) + "</details>" + m.group(3)


h = pat.sub(wrap, h)
p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("买卖建议历史档移hist-iso折叠:", n, "块")
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 校验:hist-iso折叠数·details平衡
print("hist-iso折叠总数:", h.count('class="hist-iso"'), "· <details>:", h.count("<details"), "· </details>:", h.count("</details>"))
print("『建仓·约现金』在正文(非hist-iso前提):", h.count("建仓·约现金"), "· 『中性档』:", h.count("【中性档"))
