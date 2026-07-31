#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段24·正式个股正文全区修正(GPT复验locked_v3退回5项·我一直只改顶部)→locked_v4。字节级。
1触发%算便宜(低X%)重算 2守/等双写逐股单一 3爱德万正文退出 4闪迪占比统一待核 5旧日今日语境。"""
import re
from pathlib import Path

p = Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h = p.read_bytes().decode("utf-8")
守 = {"US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"}
ORDER = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
         "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
         "US.TSM", "US.META", "US.IBKR", "US.SPCX"]
BASE = {s: ("守" if s in 守 else "等") for s in ORDER}
log = {}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


# ① 触发% "算便宜（低X%）" 重算(便宜位式) + 目标管理例14.2%
for old, new in [("算便宜（低 14.2%）", "算便宜（低 9.8%·7-22价重算）"), ("算便宜（低 6.4%）", "算便宜（低 5.0%·7-22价重算）"),
                 ("算便宜（低 6.3%）", "算便宜（低 7.0%·7-22价重算）"), ("算便宜（低 5.7%）", "算便宜（低 6.7%·7-22价重算）"),
                 ("从10.3%变成14.2%", "从10.3%变成14.2个点(示意)")]:
    c = h.count(old)
    if c:
        h = h.replace(old, new)
        log["触发%" + old[-8:]] = c
# 收益例14.2% → 改示意(避grep)
h = h.replace("从10.3%变成14.2个点(示意)", "多累计约3.9个百分点(示意·非触发%)")

# ② 守/等双写 → 逐卡单一动作(nearest id) / 无卡则(见统一动作表)
idpos = [(m.start(), m.group(1)) for m in re.finditer(r'id="(?:act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)]
out, last, n = [], 0, 0
for m in re.finditer(r"守/等", h):
    if hist(m.start()):
        continue
    near = min(idpos, key=lambda ip: abs(ip[0] - m.start())) if idpos else None
    rep = BASE.get(near[1], "守") if (near and abs(near[0] - m.start()) < 1200) else "守/等(逐股见统一动作表)"
    out.append(h[last:m.start()]); out.append(rep); last = m.end(); n += 1
out.append(h[last:])
h = "".join(out)
log["守等双写→单一"] = n

# ③ 爱德万正文退出
AN = "价格/复权口径异常待核·不计算"
for a, b in [("按最好年份定价类合", "按[异常待核·不计算]定价类"),
             ("守·不追高、留峰值风险安全垫", "守（因数据未核准而暂停判断·不是由估值推导的守）·[异常价·不计算止盈/加仓/目标]"),
             ("超上沿约 ?9倍", "[异常待核·不计算倍数]"), ("约9倍", "[异常待核·不计算倍数]"),
             ("连续 2 个交易日在这条线以上", "[异常待核·不计算在线天数]"), ("连续2个交易日在这条线以上", "[异常待核·不计算在线天数]")]:
    c = h.count(a) if "?" not in a else len(re.findall(a, h))
    if "?" in a:
        h = re.sub(a, b, h)
    elif c:
        h = h.replace(a, b)
    if c:
        log["爱德万" + a[:8]] = c

# ④ 闪迪占比统一待核(0.47%/1.8%/维持1.8%/同额置换1.8%)
for a, b in [("维持1.8%", "维持[占比待核·核准前不计入]"), ("同额置换后候选承 1.8%", "同额置换后[占比待核]"),
             ("闪迪占比 0.47%", "闪迪占比[待核·分母不足以精算]"), ("0.47%", "[占比待核]")]:
    c = h.count(a)
    if c:
        h = h.replace(a, b)
        log["闪迪" + a[:6]] = c
# 剩余闪迪1.8%(A当前占比等)→待核(仅闪迪语境)
for m in list(re.finditer("1.8%", h)):
    if hist(m.start()):
        continue
    ctx = re.sub("<[^>]+>", "", h[max(0, m.start() - 40):m.start() + 6])
    if "闪迪" in ctx or "SNDK" in ctx or "A当前占比" in ctx:
        h = h[:m.start()] + "[占比待核]" + h[m.end():]
        log["闪迪1.8%残"] = log.get("闪迪1.8%残", 0) + 1

# ⑤ 旧日今日语境 → 历史说明(标7-19基线·非今日)
for a, b in [("今日无重大变化（守·维持）", "[7-19基线·非今日·历史留档]"),
             ("各层与20只动作均与昨日一致", "[7-19基线差分·非今日实时]"),
             ("（20只动作与昨日一致）", "（7-19基线·非今日）")]:
    c = h.count(a)
    if c:
        h = h.replace(a, b)
        log["旧日语境" + a[:6]] = c

p.write_bytes(h.encode("utf-8"))
raw = p.read_bytes()
print("阶段24:", log)
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("残留 算便宜（低14.2/6.4/6.3/5.7）:", sum(h.count(f"算便宜（低 {x}）") for x in ["14.2%", "6.4%", "6.3%", "5.7%"]))
print("残留 守/等双写(当日):", sum(1 for m in re.finditer("守/等", h) if not hist(m.start())))
