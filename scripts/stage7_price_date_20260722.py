#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段7·价格/日期一致(GPT验收退回#2:724底稿旧价没换日→双值)。
以7-22为唯一源,就地替换724底稿所有『现价/现在 ¥旧价』→7-22(前缀锚定现价/现在·不碰"最低价/最高/未来目标/历史"等非当日stat)。
每只只留一个7-22现价。消除软银¥5703/¥5424·英伟达$205.23/$202.55·东京海上¥7971/¥7526双值。
不删724底稿·只换当日价字段。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段7价格日期.html"
M = (ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html").read_bytes().decode("utf-8")
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
# 724旧pxnow(7-17)
pat = re.compile(r'([A-Z]{2}\.[A-Z0-9]+)</span></td>\s*<td data-l="现价"><b class="pxnow">([¥$])([^<]+)</b>')
OLD = {m.group(1): (m.group(2), m.group(3)) for m in pat.finditer(M)}   # sym->(sym符号, 数字如5,424.00)

h = SRC.read_bytes().decode("utf-8")
changes = []
for sym, (cur, oldnum) in OLD.items():
    p = prod[sym]
    newnum = f"{p['price']:,.2f}"
    base = re.sub(r"\.00$", "", oldnum)   # JP去.00·US保留小数
    # 前缀锚定:现价/现在 [空格] [¥$] 旧数字(可带小数) → 换7-22(不碰最低价/未来目标/历史)
    rx = re.compile(r"(现[价在][ 　]?)([¥$])" + re.escape(base) + r"(?:\.\d+)?")
    h, n = rx.subn(lambda mm: mm.group(1) + mm.group(2) + newnum, h)
    if n:
        changes.append({"sym": sym, "旧": cur + oldnum, "新": cur + newnum, "换": n})

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
# 验:724底稿残留旧价(现价/现在前缀)
body = h[h.find('<div id="topnav"'):]
resid = {}
for sym, (cur, oldnum) in OLD.items():
    base = re.sub(r"\.00$", "", oldnum)
    r = len(re.findall(r"现[价在][ 　]?[¥$]" + re.escape(base) + r"(?:\.\d+)?", body))
    if r:
        resid[sym] = r
print("阶段7产物:", OUT.name, len(raw), "字节·乱码", raw.count(b"\xef\xbf\xbd"), "·裸LF", raw.count(b"\n") - raw.count(b"\r\n"))
print("价格换日:", sum(c["换"] for c in changes), "处 ·涉", len(changes), "只")
for c in changes:
    print(f"  {c['sym']:<9} {c['旧']} → {c['新']} ×{c['换']}")
print("★残留『现价/现在=旧价』:", resid if resid else "无(双值消除)")
(ROOT / "data/screen/stage7_price_20260722.json").write_text(json.dumps({"changes": changes, "残留旧现价": resid}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
