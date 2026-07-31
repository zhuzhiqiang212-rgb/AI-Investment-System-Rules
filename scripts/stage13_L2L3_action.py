#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段13·L2目标倒推四字段+买卖建议双档+L3底稿 动作/买卖价 全统一7-22(GPT第三轮)。
全20只守/等·无一加仓→通用中和:①买卖建议双档标"无买卖建议" ②第一档/第二档加仓价删 ③角色待建仓→持有观察 ④四字段／式加仓价删 ⑤加至价删。字节级保CRLF。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
log = {}

# ① 买卖建议·双档 intro → 7-22无买卖建议(整块标作废)
a1 = "买卖建议·双档并列（董事长自己选一档·系统不替他选）"
b1 = "买卖建议：<b>7-22守/等·今日无买卖建议</b>（原加仓双档已废止·见顶部统一动作表）｜<span style=\"color:#888\">以下为7-19历史档·作废·不据此：</span>"
log["买卖建议双档标无"] = h.count(a1)
h = h.replace(a1, b1)

# ② 四字段／式加仓价(TSM 第一档$360／第二档$325)
h, n2 = re.subn(r"第一档[ 　]?[\$¥][\d,\.]+[／/][ 　]?第二档[ 　]?[\$¥][\d,\.]+",
                "[7-22守·今日无加仓价·加仓档已废止]", h)
log["四字段式加仓价删"] = n2

# ③ 第一档/第二档 带价(泛·L2/L3买卖建议) → 删价
h, n3a = re.subn(r"第一档[ 　]?[\$¥][\d,\.]+", "第一档[7-22无加仓价]", h)
h, n3b = re.subn(r"第二档[ 　]?[\$¥][\d,\.]+", "第二档[7-22无加仓价]", h)
log["第一档价删"] = n3a
log["第二档价删"] = n3b

# ④ 角色 待建仓 → 持有观察
h, n4 = re.subn(r"角色 待建仓", "角色 持有/观察·非待建仓", h)
log["角色待建仓改"] = n4

# ⑤ 加至约X% / 加至价
h, n5 = re.subn(r"再加至约[\d]+%", "·7-22守·今日不加仓", h)
h, n5b = re.subn(r"加至约[\d,\.]+", "[7-22无加仓]", h)
log["加至价删"] = n5 + n5b

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段13执行:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
res1 = len(re.findall(r"第一档[ 　]?[\$¥][\d,\.]+", h)) + len(re.findall(r"第二档[ 　]?[\$¥][\d,\.]+", h))
print("残留第一档/第二档带价:", res1, "· 残留待建仓:", h.count("待建仓"), "· 残留买卖建议·双档并列:", h.count("买卖建议·双档并列"))
