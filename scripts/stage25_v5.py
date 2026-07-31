#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段25·「今天哪些数据不能依赖」区 爱德万/闪迪 删公允价+倍数(架构师核v4·硬闸C漏此区)→locked_v5。字节级。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
log = {}
# 爱德万:现价27505.0是中周期公允3000的约9倍——待专项核准（...） → 模板(无公允/倍数/现价)
h, n1 = re.subn(r"现价 ?27505\.0 是中周期公允 ?3000 的约 ?9 ?倍——待专项核准（[^）]*）",
                "价格/复权口径异常·待专项核准；不计算估值/倍数/加仓价/止盈/目标；核准前不据此买卖。守＝因数据未核准暂停判断，非由估值推导。", h)
log["爱德万公允/倍数删"] = n1
# 闪迪:现价1350.034是中周期公允55的约25倍——待专项核准（...） → 模板(保留现价异常事实·删公允/倍数)
h, n2 = re.subn(r"现价 ?1350\.034 是中周期公允 ?55 的约 ?25 ?倍——待专项核准（[^）]*）",
                "现价 $1,519.49（7-22实时·原1350.03为7-17旧价）·价格/复权口径异常·待专项核准；不计算估值/倍数/加仓价/止盈/目标；核准前不据此买卖。", h)
log["闪迪公允/倍数删"] = n2

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段25:", log, "· 字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


# 验:爱德万/闪迪 ±40字内 公允/倍数残留
resid = []
for m in re.finditer(r"公允[ ]?\d|中周期公允|约 ?\d+ ?倍|\d+\.?\d* ?倍", h):
    if hist(m.start()):
        continue
    c = pl(h[max(0, m.start() - 40):m.start() + 14])
    if "爱德万" in c or "闪迪" in c:
        resid.append(pl(h[m.start():m.start() + 12]))
print("★爱德万/闪迪 公允/倍数 ±40字残留:", resid if resid else "无")
