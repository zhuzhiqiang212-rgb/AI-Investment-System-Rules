#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段8·动作权威强制到全产品所有节点(GPT验收退回#1/#4)。
以7-22最终动作为唯一源,同步替换:①act/why卡chip ②叙述『为什么现在X』③决定摘要『动作=X』④顶部表。
GPT#4改判:东京海上/Circle 不写"建议减"→"等·待核实·无卖出决定·不可执行";MSTR维持"等·盯"。
+COIN/IBKR漏网四舍五入现价 +724标题7-19→7-22改日。同股所有层收敛到一个7-22答案。
"""
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段7价格日期.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段8动作权威.html"
HOLD守 = ["US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"]
BASE = {}   # 叙述单字动作
for s in ["US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"]:
    BASE[s] = "守"
for s in ["US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832",
          "JP.7974", "US.SNDK", "US.MSTR", "JP.8766", "US.CRCL"]:
    BASE[s] = "等"
# chip glyph(顶部+卡)
GLYPH = {s: ("c-hold", "■ 守") for s in HOLD守}
for s in ["US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.SNDK"]:
    GLYPH[s] = ("c-wait", "… 等")
GLYPH["US.MSTR"] = ("c-wait", "◉ 等·盯")
GLYPH["JP.8766"] = ("c-wait", "… 等·待核")
GLYPH["US.CRCL"] = ("c-wait", "… 等·待核")
PROD_PX = {"US.COIN": ("157", "172"), "US.IBKR": ("91", "94")}   # 漏网四舍五入现价

h = SRC.read_bytes().decode("utf-8")
log = {"chip": 0, "为什么现在": 0, "动作=": 0, "价漏网": 0, "建议减改": 0, "标题": 0}

# ---------- ① act/why 卡chip → GLYPH ----------
anchors = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'id="(act|why)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
chipre = re.compile(r'<span class="chip (c-add|c-wait|c-hold|c-risk)">([^<]{1,14})</span>')
parts = []
last = 0
for i, (pos, typ, tk) in enumerate(anchors):
    if tk not in GLYPH:
        continue
    seg_end = starts[i + 1] if i + 1 < len(starts) else len(h)
    m = chipre.search(h, pos, seg_end)
    if not m or m.group(2).strip() == "⚠ 险":
        continue
    cls, glyph = GLYPH[tk]
    parts.append(h[last:m.start()]); parts.append(f'<span class="chip {cls}">{glyph}</span>'); last = m.end()
    log["chip"] += 1
parts.append(h[last:])
h = "".join(parts)

# ---------- ②③ 叙述『为什么现在X』+『动作=X』per卡 ----------
anchors = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'id="(act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
parts = []; last = 0
for i, (pos, typ, tk) in enumerate(anchors):
    if tk not in BASE:
        continue
    seg_end = starts[i + 1] if i + 1 < len(starts) else len(h)
    seg = h[pos:seg_end]
    new = seg
    new, n1 = re.subn(r"(为什么现在)[守加观等减盯]", r"\g<1>" + BASE[tk], new)
    new, n2 = re.subn(r"(动作[＝=])[守加观等减盯]", r"\g<1>" + BASE[tk], new)
    log["为什么现在"] += n1; log["动作="] += n2
    parts.append(h[last:pos]); parts.append(new); last = seg_end
parts.append(h[last:])
h = "".join(parts)

# ---------- ④ COIN/IBKR 漏网现价 ----------
for sym, (old, new) in PROD_PX.items():
    h, n = re.subn(r"(现[价在][ 　]?[¥$])" + old + r"(?![0-9,])", r"\g<1>" + new, h)
    log["价漏网"] += n

# ---------- GPT#4:建议减→等·待核实·无卖出决定 ----------
rep4 = [
    ('<span class="chip c-risk">▽ 减·演</span>', '<span class="chip c-wait">… 等·待核</span>'),
    ("建议减·演", "等·待核实(无卖出决定·不可执行)"),
    ("▽ 减·演", "… 等·待核"),
    ("<b>建议减(东京海上/Circle)=情景预演·不可执行</b>", "<b>东京海上/Circle=等·待核实(profit_take=0无卖信号+账户快照未闭环→无卖出决定·不可执行·非建议减)</b>"),
    ("建议减", "等·待核实"),
]
for a, b in rep4:
    c = h.count(a)
    if c:
        h = h.replace(a, b); log["建议减改"] += c

# ---------- 标题 7-19→7-22改日 ----------
h, nt = re.subn(r"★ 每日投资产品 · 2026-07-19　\[生产日·价为最近交易日 2026-07-17\]",
                "★ 每日投资产品 · 2026-07-22　[7-22实时·价=OpenD 2026-07-22·7-19底稿动作/价已更新为7-22]", h)
log["标题"] = nt

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
print("阶段8产物:", OUT.name, len(raw), "字节·乱码", raw.count(b"\xef\xbf\xbd"), "·裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("执行:", log)
print("残留『建议减』:", h.count("建议减"), "·残留▽减演:", h.count("▽ 减"))
