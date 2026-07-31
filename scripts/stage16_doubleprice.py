#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段16·消除双价(GPT复验#2·补stage7漏的格式:现价约¥X/margin块现价 ¥X)。逐股只留一套7-22现价。
不动历史stat(近20日最低价/52周)。字节级保CRLF。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
M = (ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html").read_bytes().decode("utf-8")
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
pat = re.compile(r'([A-Z]{2}\.[A-Z0-9]+)</span></td>\s*<td data-l="现价"><b class="pxnow">([¥$])([^<]+)</b>')
OLD = {m.group(1): (m.group(2), m.group(3)) for m in pat.finditer(M)}

h = P.read_bytes().decode("utf-8")


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


log = {}
for sym, (cur, oldnum) in OLD.items():
    base = re.sub(r"\.00$", "", oldnum)
    newnum = f"{prod[sym]['price']:,.2f}"
    # 补漏格式:现价[空格/约/全角空格]*(<b>)?[¥$]旧价 (含<b>标签在现价与¥之间的决定摘要块)·排除最低价/52周历史
    rx = re.compile(r"(现价|现在)([ 　约]{0,3})(<b>)?([¥$])" + re.escape(base) + r"(?:\.\d+)?")
    cnt = [0]

    def rep(mm):
        if hist(mm.start()):
            return mm.group(0)
        cnt[0] += 1
        return mm.group(1) + mm.group(2).replace("约", "") + (mm.group(3) or "") + mm.group(4) + newnum
    h = rx.sub(rep, h)
    if cnt[0]:
        log[sym] = {"旧": cur + base, "新": cur + newnum, "补改": cnt[0]}

P.write_bytes(h.encode("utf-8"))
raw = P.read_bytes()
print("阶段16双价补消除:", sum(v["补改"] for v in log.values()), "处 ·涉", len(log), "只")
for s, v in log.items():
    print(f"  {s}: {v['旧']}→{v['新']} ×{v['补改']}")
print("字节", len(raw), "乱码", raw.count(b"\xef\xbf\xbd"), "裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
# 验:5只旧价在当日区残留
resid = {}
for name, old in [("软银", "5,424"), ("英伟达", "202.55"), ("第一三共", "2,791"), ("东京海上", "7,526"), ("爱德万", "27,505")]:
    body = [m.start() for m in re.finditer(re.escape(old), h) if not hist(m.start())]
    # 排除历史stat(最低价/52周/上沿)
    live = [pos for pos in body if not re.search(r"(最低|最高|52周|上沿|20个交易日)", h[max(0, pos - 30):pos])]
    if live:
        resid[name] = [re.sub("<[^>]+>", "", h[p - 20:p + 8])[-24:] for p in live]
print("★当日双价残留(非历史stat):", resid if resid else "无(双价消除)")
