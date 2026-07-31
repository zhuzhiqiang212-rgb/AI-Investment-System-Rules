#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

h = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
print("=== 建仓·约现金 分布 ===")
for m in re.finditer(r"建仓·约现金[^<·]{0,6}", h):
    pre = re.sub("<[^>]+>", "", h[m.start() - 30:m.start()])[-22:]
    print("  ...", pre, "|", m.group())
print("总数 建仓·约现金:", len(re.findall(r"建仓·约现金", h)))
print("总数 以下为7-19历史档:", h.count("以下为7-19历史档·作废·不据此："))
# 台积电买卖建议块结构:找'以下为7-19历史档'后到该<td>/<div>结束
i = h.find('id="why-US.TSM"')
seg = h[i:i + 4000]
j = seg.find("以下为7-19历史档")
if j > 0:
    print("=== 台积电 历史档后280(含标签) ===")
    print(repr(seg[j + 20:j + 300]))
# 该买卖建议内容所在的容器:'买卖建议：'所在td/div
k = h.find("买卖建议：")
if k > 0:
    # 往后找该cell/块结束(</td>或</div>)
    tdend = h.find("</td>", k)
    divend = h.find("</div>", k)
    print("买卖建议cell:</td>@", tdend - k, "</div>@", divend - k)
