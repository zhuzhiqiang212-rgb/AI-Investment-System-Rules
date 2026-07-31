#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段27·风险区/持仓比 异常只当"高位/峰值定价"举例退出(架构师核v6·卡片边界外共现)→locked_v7。字节级。
①line422风险举例 闪迪/爱德万→台积电/英伟达 ②line2318闪迪年内+737%已在高位→异常待核不作高位判断。
全文核:闪迪/爱德万不得与 景气高点/峰值定价/极贵/高位/合理值/N倍/中周期/穿牛熊 共现(卡外·±60字)。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
log = {}

# ① 风险区"半导体周期高位"举例:异常只→价口径正常的半导体重仓(架构师指定)
a1 = "闪迪/爱德万等处景气高点·峰值定价"
b1 = "台积电/英伟达等处景气高点·峰值定价"
log["①风险举例换正常只"] = h.count(a1)
h = h.replace(a1, b1)

# ② 持仓比④:闪迪 年内+737%已在高位 → 异常待核·不作高位判断(价口径异常·+737%由异常价系列推导)
a2 = "闪迪(SNDK,闪存芯片,年内+737%已在高位)"
b2 = "闪迪(SNDK,闪存芯片·价格/复权口径异常待核·暂不评价价位)"
log["②持仓比高位退出"] = h.count(a2)
h = h.replace(a2, b2)

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段27:", log, "· 字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


# 验:全文 闪迪/爱德万 与定价类词 ±60字共现(卡外+卡内·全区)=0
DZ = ["景气高点", "峰值定价", "极贵", "高位", "合理值", "中周期", "穿牛熊"]
resid = []
for nm in ["闪迪", "爱德万"]:
    for m in re.finditer(nm, h):
        if hist(m.start()):
            continue
        ctx = h[max(0, m.start() - 60):m.start() + 60]
        for dz in DZ:
            if dz in ctx:
                resid.append((nm, dz, pl(ctx)))
                break
        else:
            if re.search(r"\d+\s?倍", ctx):
                resid.append((nm, "N倍", pl(ctx)))
print("★闪迪/爱德万 全区定价类共现残留:", resid if resid else "0(无)")
