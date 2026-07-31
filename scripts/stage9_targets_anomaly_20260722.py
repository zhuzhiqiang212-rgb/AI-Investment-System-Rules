#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段9·目标口径统一(#3)+异常估值隔离(#5)+MSTR证据(#4)。GPT验收退回定向修正。
#3:删增补①错加『离标$730,975』(13只亏损与全账户目标混加)→改B口径;底稿旧目标($1,520,314/16.87/12.1/36.6%主战场口径)标作废·口径统一到全账户。
#5:爱德万(高估750%与合理矛盾)/闪迪(拆股复权未核)→加异常隔离声明·其估值/加仓价/止盈/目标/组合贡献不据此决策。
#4:MSTR mNAV<1不作卖出事实→补负债/可转债/稀释/BTC敏感/折价修复/飞轮失效条件·维持等·盯。
只增不删724底稿·作废用标注隔离。
"""
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段8动作权威.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段9目标异常.html"
h = SRC.read_bytes().decode("utf-8")
log = {}

# ---------- #3 删增补①错加『离标$730,975』+净化混算→A口径 ----------
h2, n0 = re.subn(r"·离标约\$730,975", "", h)   # 先清错加"离标"
h = h2
log["离标730975清"] = n0
old1 = "$669,350（当前13只已−$61,625）需赚 $1,673,375"
new1 = "$669,350（全账户40%档·A口径·不混13只亏损）需赚 $1,673,375（全账户100%档）"
log["增补①净化混算"] = h.count(old1)
h = h.replace(old1, new1)

# ---------- #3 底稿旧目标(主战场$1,520,314口径)作废声明 ----------
mark = '<span style="background:#5a1a1a;color:#ffd">【★口径作废·GPT#3:本块7-19主战场SBI口径·已统一到顶部增补①全账户$1,673,375·不据此·不混加】</span> '
anchor3 = "主战场当前市值 <b>$1,520,314</b>"
if anchor3 in h:
    h = h.replace(anchor3, mark + anchor3, 1)
    log["底稿旧目标作废标"] = 1
else:
    log["底稿旧目标作废标"] = 0

# ---------- #5+#4 异常隔离+MSTR证据 声明(增补⑮·顶部) ----------
sec15 = ('<div id="anomaly-isolation-0722" style="border:3px solid #6b2020;background:#fff5f5;border-radius:10px;padding:14px 16px;margin:12px 0">'
         '<div style="font-size:17px;font-weight:800;color:#6b2020">■ 增补⑮ 异常估值隔离 + MSTR证据补全（GPT验收退回#4#5）</div>'
         '<div style="font-size:12.5px;color:#333;line-height:1.7;margin-top:6px">'
         '<b>① 爱德万(JP.6857)·价格口径异常待核</b>：底稿"已涨过合理价上沿¥3,234约750%"与他处"估值合理"<b>自相矛盾</b>（750%高估 vs 合理）。'
         '→ 爱德万的<b>估值/加仓价/止盈线/目标收益/组合贡献/买卖计算一律不据此决策</b>·只作"价格口径异常待核"·待架构师核准估值口径后再启用。<br>'
         '<b>② 闪迪(US.SNDK)·拆股/复权异常待核</b>：底稿含拆股表述、股数20↔5两源、价格$1,519.49量级异常未复权核准。'
         '→ 闪迪<b>估值/加仓价/止盈/目标/组合贡献退出决策</b>·只显"价格口径异常待核·不据此"·股数以账户5为准(留痕20)。<br>'
         '<b>③ MSTR(US.MSTR)·mNAV&lt;1不作卖出事实(维持等·盯)</b>：mNAV=0.636&lt;1仅估值信号非卖出指令。'
         '补判据条件（不足以支撑卖出）：ⓐ负债/可转债到期结构未压顶 ⓑ稀释(ATM发股)速度 ⓒBTC价格敏感(杠杆双向) ⓓ折价修复路径(mNAV回1飞轮重启) ⓔ飞轮失效条件(市值持续&lt;持币NAV+再融资停)。'
         '→ 以上条件<b>未逐项证否前维持"等·盯"·不转卖出</b>。</div></div>')
anchor_ins = '<div id="stage3-augment"'
h = h.replace(anchor_ins, sec15 + anchor_ins, 1)
log["增补⑮异常隔离"] = 1 if "anomaly-isolation-0722" in h else 0

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
print("阶段9产物:", OUT.name, len(raw), "字节·乱码", raw.count(b"\xef\xbf\xbd"), "·裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("执行:", log)
print("残留『离标约$730,975』:", h.count("离标约$730,975"), "·残留『离标约 $730,975』:", h.count("730,975"))
