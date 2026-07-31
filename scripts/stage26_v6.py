#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段26·爱德万/闪迪整张卡片退出估值(架构师核v5·硬闸C临近法漏卡内远段)→locked_v6。字节级。
按卡片边界(act/why/deep)清:①关键可见句清爽替换(守理由只留数据未核准) ②卡内token级中和禁词
(『\\d+倍』『公允』『极贵』『景气高点』『峰值定价』『合理值』『中周期』『穿牛熊』『中枢』『合理上沿』)。
标记文本严格不含任何禁词。+line173残句(双句号/重复守)。仅动异常两卡·不碰其余18只。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")

ANV = "数据未核准·暂停判断·不据此买卖（非由估值推导）"       # 守理由(禁词零)
NA = "[异常待核·不计算]"                                        # 通用(禁词零)
NAB = "[倍数待核·不计算]"                                       # 替 \d+倍(无数字·硬闸\d+倍不命中)
NAM = "中期[待核]"                                             # 替 中周期(非"中周期")
NAF = "[参考值待核]"                                           # 替 公允/合理值(非"公允""合理值")
NAP = "峰值[口径待核]"                                         # 替 峰值定价(保留"峰值"·硬闸只禁"峰值定价")
NAZ = "[中值待核]"                                             # 替 中枢


def card_bounds(sym):
    res = []
    for idk in ("act", "why", "deep"):
        i = h.find(f'id="{idk}-{sym}"')
        if i < 0:
            continue
        nx = [x for k in ("act", "why", "deep") for x in [h.find(f'id="{k}-', i + 12)] if x > 0]
        res.append((i, min(nx) if nx else len(h)))
    return res


log = {}
segs = []
for sym in ("JP.6857", "US.SNDK"):
    segs += card_bounds(sym)
segs.sort(reverse=True)  # 逆序·防偏移

# 有序替换:先关键可见句(清爽)·再token级中和(兜底禁词)
SENT = [  # 关键可见句·守理由只留数据未核准(括号内估值短语→非由估值推导·不受</b>标签间隔影响)
    (r"（现价约为中周期合理值 ?\d+ ?倍）", "（非由估值推导）"),
    (r"后正常消化、倍数压向高 ?\d+/低 ?\d+ ?倍", "后[异常待核·估值情景不计算]"),
    (r"中周期/穿牛熊算 ?极贵（景气高点·峰值定价）（现价约合理上沿 ?\[异常待核·不计算\] 的 ?\d+\.?\d* ?倍）", NA),
    (r"峰值可能持续·中周期/穿牛熊只作参考", "峰值可能持续·相关读数异常待核"),
    (r"现价\$1,519\.49 ?→ ?极贵（峰值定价） ?→ ?守", "现价$1,519.49 → " + NA + " → 守"),
    (r"现价虽已过上沿、显极贵，", "现价虽已过上沿、" + NA + "，"),
    (r"周期性的极贵读数", "周期性的" + NA + "读数"),
    (r"\(穿牛熊/数据不足\)", "(数据不足·异常待核)"),
    (r"中周期盈利法\(不用峰值\)", "[异常待核·估值尺不适用]"),
    (r"（中周期盈利法·峰值利润压回中枢）", "（[异常待核·估值尺不适用]）"),
    (r"中周期EPS ?\$?[\d~]+→公允远低于现价", "[异常待核·EPS/公允不计算]"),
    (r"估值按中周期EPS×[\d~]+ ?倍锚", "[异常待核·估值尺不适用]"),
    (r"估值·重P/B约 ?\d+ ?倍·价约中周期公允 ?\d+ ?倍\+?·倍数?", "[异常待核·倍数/公允不计算]"),
]
TOK = [  # token级兜底(禁词→无禁词标记)
    (r"\d+\.?\d*\s?倍", NAB), ("峰值定价", NAP), ("景气高点", NA), ("穿牛熊", NA),
    ("极贵", NA), ("合理上沿", NA), ("合理值", NAF), ("公允", NAF), ("中周期", NAM), ("中枢", NAZ),
]
for s, e in segs:
    seg = h[s:e]
    for pat, rep in SENT:
        seg, n = re.subn(pat, rep, seg)
        if n:
            log["句·" + pat[:10]] = log.get("句·" + pat[:10], 0) + n
    for pat, rep in TOK:
        seg, n = re.subn(pat, rep, seg)
        if n:
            log["tok·" + pat[:8]] = log.get("tok·" + pat[:8], 0) + n
    h = h[:s] + seg + h[e:]

# line173残句:去重复守(…)+双句号
h = h.replace("非由估值推导。。守（因数据未核准而暂停判断·不是由估值推导的守）·[异常价·不计算止盈/加仓/目标]", "非由估值推导。")
h = h.replace("。。", "。")

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段26 replace:", {k: v for k, v in sorted(log.items())})
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))


# 验:爱德万/闪迪 卡内 硬闸C禁词(架构师口径) 残留=0
def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


PATS = [r"\d+\s?倍", "公允", "极贵", "景气高点", "峰值定价", "合理值", "中周期", "穿牛熊"]
resid = []
for sym in ("JP.6857", "US.SNDK"):
    for s, e in card_bounds(sym):
        seg = h[s:e]
        for pat in PATS:
            for m in re.finditer(pat, seg):
                if hist(s + m.start()):
                    continue
                resid.append((sym, pat, re.sub("<[^>]+>", "", seg[m.start() - 6:m.start() + 8])))
print("★爱德万/闪迪 卡内 硬闸C禁词残留:", resid if resid else "0(无)")
