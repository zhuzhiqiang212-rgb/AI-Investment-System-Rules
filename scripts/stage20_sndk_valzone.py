#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段20·闪迪估值区异常退出(架构师行2043/2065:$40~$80/中枢$55/现价$1,350漏了)。同爱德万标准。字节级。
只清闪迪-unique的$40~$80/中枢$55/现价$1,350·避开BTC$55~75K(MSTR无关)。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


AN = "[价格/复权口径异常待核·不计算估值/加仓价/止盈/目标贡献·见增补⑮]"
log = {}
# 整段闪迪估值区(行2043/2065式) → 异常
for a in [r"架构师中周期\(峰值定价对照\)估算·\$40~\$80·中枢\$55（[^）]*） → 现价 \$1,350 → 极贵（峰值定价）",
          r"架构师中周期估算 \$40~\$80·中枢\$55"]:
    h2, n = re.subn(a, AN, h)
    if n:
        h = h2
        log[a[:20]] = n
# 逐token兜底(闪迪-unique·非hist)
for tok in ["今日该值 $40~$80", "$40~$80", "中枢$55", "现价 $1,350", "$1,350"]:
    out, last, n = [], 0, 0
    for m in re.finditer(re.escape(tok), h):
        if hist(m.start()):
            continue
        out.append(h[last:m.start()])
        out.append("今日该值 " + AN if tok == "今日该值 $40~$80" else ("现价 " + AN if tok in ("现价 $1,350",) else AN))
        last = m.end()
        n += 1
    out.append(h[last:])
    h = "".join(out)
    if n:
        log[tok] = n

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段20闪迪估值区退出:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
resid = {t: sum(1 for m in re.finditer(re.escape(t), h) if not hist(m.start())) for t in ["$40~$80", "中枢$55", "现价 $1,350"]}
print("★闪迪估值区当日残留:", {k: v for k, v in resid.items() if v} or "无(全退出)")
print("★BTC$55~75K保留(不误伤):", "$55~75K" in h)
