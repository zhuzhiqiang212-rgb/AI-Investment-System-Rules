#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段19·爱德万/闪迪异常从全部计算区真退出(架构师GPT#3未彻底:加仓触发区/止盈/目标贡献/估值多格式)。字节级。
爱德万异常数(¥2,646/¥2,940/¥3,234/939.5%)全格式退出;闪迪加仓触发区行退出。历史数字留但标异常待核。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
ANOM = "价格/复权口径异常待核·不计算加仓价/止盈线/目标贡献/差距%（见增补⑮）"
log = {}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# 爱德万 加仓触发区行(便宜位¥2,646/中间值¥2,940/还差939.5%) — 多空格变体
def r_trig(m):
    return m.group(0) if hist(m.start()) else ("加仓价(便宜位) <b>" + ANOM + "</b>")
h, n1 = re.subn(r"加仓价\(便宜位\)[ 　]*¥2,646[ 　]*中间值[ 　]*¥2,940[ 　]*→[ 　]*还差[ 　]*939\.5%[ 　]*到加仓价", r_trig, h)
log["爱德万加仓触发区行"] = n1

# 爱德万 估值区多格式(¥2,646~¥3,234 / 今日该值 / 区间 / 跌回便宜位) — 逐短语
for a, b in [
    ("今日价值区（今天该值）：¥2,646 ~ ¥3,234", "今日价值区（今天该值）：[价格/复权口径异常待核·不计算估值区]"),
    ("今日该值 ¥2,646~¥3,234", "今日该值 [异常待核·不计算估值]"),
    ("（区间¥2,646~3,234）", "（[异常待核·不计算]）"),
    ("跌回 ¥2,646 便宜位才谈加", "[价格/复权口径异常待核·不生成加仓价]"),
    ("×中周期PE20=¥2,938", "×中周期PE20=[异常待核]"),
    ("加仓价(便宜位) ¥2,646 中间值 ¥2,940", "加仓价(便宜位) [异常待核·不计算]"),
]:
    c = h.count(a)
    if c:
        h = h.replace(a, b)
        log[a[:14]] = c

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
# 验:爱德万异常数残留(当日非hist)
resid = {}
for num in ["2,646", "2,940", "3,234", "939.5"]:
    live = [m.start() for m in re.finditer(re.escape(num), h) if not hist(m.start())]
    if live:
        resid[num] = [re.sub("<[^>]+>", "", h[pos - 18:pos + 8])[-24:] for pos in live]
print("阶段19执行:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("★爱德万异常数当日残留:", resid if resid else "无(全退出)")
