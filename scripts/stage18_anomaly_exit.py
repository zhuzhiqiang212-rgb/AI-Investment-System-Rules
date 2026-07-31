#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段18·爱德万/闪迪异常真正退出(GPT复验#3:非顶部声明·从估值/加仓/止盈/目标/组合贡献退出)。
两只deep卡内:今日价值区/估值区/止盈线/目标收益/组合贡献/加仓价 → 价格/复权口径异常待核·不计算。字节级。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
ANOM = "<b style=\"color:#8A3E00\">[价格/复权口径异常待核·不计算估值/加仓价/止盈/目标/买卖·见增补⑮]</b>"
log = {}


def in_card(deepid):
    i = h.find(f'id="{deepid}"')
    if i < 0:
        return -1, -1
    nxt = h.find('id="deep-', i + 12)
    return i, (nxt if nxt > 0 else len(h))


for who, deepid in [("爱德万", "deep-JP.6857"), ("闪迪", "deep-US.SNDK")]:
    i, e = in_card(deepid)
    if i < 0:
        continue
    seg = h[i:e]
    c = 0
    # 今日价值区 X~Y → 异常
    seg, n1 = re.subn(r"今日价值区 [¥$][\d,]+~[¥$][\d,]+", "今日价值区 " + ANOM, seg)
    c += n1
    # 未来目标 数值 → 异常(仅这两只)
    seg, n2 = re.subn(r"未来目标 [¥$][\d,]+（2026底）~[¥$][\d,]+（2027底）", "未来目标 " + ANOM, seg)
    c += n2
    log[who] = {"今日价值区异常": n1, "未来目标异常": n2}
    h = h[:i] + seg + h[e:]

# 爱德万 特有异常数字(750%高估/939/合理价上沿) → 异常标注
for a, b in [("已涨过合理价上沿¥3,234约750%", "价格/复权口径异常待核·不计算(原标750%高估与合理矛盾)"),
             ("涨过合理价上沿 ¥3,234 约 750%", "价格/复权口径异常待核·不计算"),
             ("还差 939.5%", "[异常待核·不计算]"), ("还差939.5%", "[异常待核·不计算]")]:
    if a in h:
        h = h.replace(a, b)
        log.setdefault("爱德万特有", []).append(a[:16])

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段18异常退出:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 验:爱德万/闪迪 deep卡内 今日价值区数值残留
for who, deepid in [("爱德万", "deep-JP.6857"), ("闪迪", "deep-US.SNDK")]:
    i, e = in_card(deepid)
    seg = h[i:e]
    print(f"  {who} deep卡 残留『今日价值区 [¥$]数值』:", len(re.findall(r"今日价值区 [¥$][\d,]+~", seg)), "· 750%:", seg.count("750%"))
