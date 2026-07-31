#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段22·GPT复验locked_v1退回5项计算正确性修正(→locked_v2)。字节级。
①触发%用7-22价重算(旧值用旧价算错) ②动作闸失败逐只具体项 ③爱德万异常完全退出(目标价/倍数)
④闪迪股数×价=市值统一(5×$1,519.49=$7,597·非30390) ⑤JS排除hist-iso(details:not(.hist-iso))。
"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
log = {}

# ① 触发%重算 + ② 动作闸具体项(4只·已比加仓价低)
TRIG = {  # 旧%: (新%, 具体闸)
    "14.2%": ("9.8%", "现金口径过旧(SBI/IBKR/bitFlyer=07-02核报·全账户现金非当日实时→加仓下单额无法精算)+日股集中度(软银日股占比大)"),
    "6.4%": ("5.0%", "仓位过高(英伟达占总资产约12.6%·接近单只高位)+集中度限制"),
    "6.3%": ("7.0%", "现金口径过旧(账户现金非当日)+催化剂可信度不足(索尼AI相机/影像需下次决算验证)"),
    "5.7%": ("6.7%", "现金口径过旧+日股集中度(第一三共占约10.1%)+临床事件风险(Enhertu单药占1/3·ILD监测)"),
}
for old, (new, gate) in TRIG.items():
    a = f"已比加仓价低 <b>{old}</b>"
    b = f"已比加仓价低 <b>{new}</b>（价格触发·但<b>动作闸未通过</b>：{gate}·今日不得加仓）"
    if a in h:
        h = h.replace(a, b)
        log["触发%" + old] = new

# ③ 爱德万异常完全退出(目标价¥33,544/+6.5%/1.9倍/估值合理)
for a, b in [
    ("仅爱德万有分析师目标价¥33,544(+6.5%)·", "仅爱德万有分析师目标价[<b>价格/复权口径异常待核·不计算目标/上行%·不据此</b>]·"),
    ("超上沿约1.9倍", "[异常待核·不计算倍数]"),
]:
    c = h.count(a)
    if c:
        h = h.replace(a, b)
        log[a[:12]] = c

# ④ 闪迪市值统一(5×$1,519.49=$7,597·非30,390)+占比退出
h2, n = re.subn(r'(text-align:right">5[ 　]*</td>\s*<td[^>]*>\$1,519\.49</td>\s*<td[^>]*>)30,390(</td>)',
                r"\g<1>7,597\g<2>", h)
if n == 0:  # 兜底:直接换30,390(闪迪市值·唯一)
    h2, n = re.subn(r">30,390<", ">7,597（5股×$1,519.49·原30,390为20股旧算·已改）<", h)
h = h2
log["闪迪市值30390→7597"] = n
# 闪迪占比退出(核准前不计入)
for a, b in [("爱德万9.0%+闪迪1.8%= 10.8%·超限一倍", "爱德万9.0%（★闪迪股数×价核准前不计入占比·原1.8%/合计10.8%基于错误20股市值·已退出）"),
             ("爱德万9.0%+闪迪1.8%=10.8%", "爱德万9.0%（闪迪占比待核·不计入）")]:
    if a in h:
        h = h.replace(a, b)
        log["闪迪占比退出"] = 1

# ⑤ JS排除hist-iso
h2, nj = re.subn(r"querySelectorAll\('details'\)", "querySelectorAll('details:not(.hist-iso)')", h)
h = h2
log["JS排除hist-iso"] = nj

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段22:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("残留旧触发%(14.2/6.4/6.3/5.7):", sum(h.count(f"<b>{x}</b>") for x in ["14.2%", "6.4%", "6.3%", "5.7%"]))
print("残留爱德万33,544未隔离:", "目标价¥33,544(+6.5%)" in h, "· 闪迪30,390残:", ">30,390<" in h)
print("JS现:", re.search(r"querySelectorAll\([^)]*\)", "".join(re.findall(r"<script[^>]*>(.*?)</script>", h, re.S))).group())
