#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段19c·闪迪异常估值退出($35~95中周期公允/承接节点加仓价)+爱德万/闪迪承接节点行退出。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


log = {}
# 闪迪 中周期公允($35~95) → 异常
for a, b in [("中周期公允($35~95)", "中周期公允[异常待核·不计算·价格/复权口径异常]"),
             ("公允($35~95)", "公允[异常待核]")]:
    c = h.count(a)
    if c:
        h = h.replace(a, b)
        log[a] = c

# 承接节点/加仓触发区 表内 爱德万/闪迪 行(名称 未到 现价 加仓价 中间值 还差%) → 整行异常
# 行格式:名称</...>...加仓价(便宜位) X 中间值 Y → 还差 Z% 到加仓价
def row_anom(m):
    if hist(m.start()):
        return m.group(0)
    who = m.group(1)
    return m.group(0).split("加仓价(便宜位)")[0] + "<b style=\"color:#8A3E00\">价格/复权口径异常待核·不计算加仓价/中间值/还差%（" + who + "·见增补⑮）</b></td>"
h, n1 = re.subn(r"(爱德万|闪迪)([^\n]*?)加仓价\(便宜位\)[^\n]*?还差[ 　]*[\d.]+%[ 　]*到加仓价[^<]*</td>", row_anom, h)
log["承接节点行退出"] = n1

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段19c:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("残留 $35~95:", h.count("$35~95"), "· 爱德万/闪迪承接节点加仓价残:",
      sum(1 for m in re.finditer(r"(爱德万|闪迪)[^\n]*?加仓价\(便宜位\)[ 　]*[¥$][\d,]+", h) if not hist(m.start())))
