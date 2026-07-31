#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_fatal3_v2·三致命区A/B/C/D + 4扩查(补硬闸盲区·GPT复验locked_v2)。对locked_v2跑。
扩查:①触发%=(加仓价-现价)/加仓价 重算一致 ②股数×现价=市值 一致 ③爱德万/闪迪异常具体字段残留 ④JS选择器命中hist-iso。
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_locked_v2.html"
raw = P.read_bytes()
h = raw.decode("utf-8")
sha = hashlib.sha256(raw).hexdigest()
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


F = {"A_守等加仓语义": [], "B_今日触发区现价≠7-22": [], "C_异常估值参与": [], "D_JS读hist": [],
     "扩①触发%重算不一致": [], "扩②股数×价≠市值": [], "扩③爱德万闪迪异常字段残留": [], "扩④JS命中hist-iso": []}

# A
for kw in ["已触发加仓", "⚡已触发", "分批买、别一次买满", "现在就可以加；分批", "今日已跌到加仓价", "建议金额 约现金"]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            F["A_守等加仓语义"].append(kw)
            break
# B 今日触发区旧价当现价
ti = h.find("今天有没有跌到你的加仓价")
tseg = h[ti:ti + 6500] if ti > 0 else ""
for old in ["5,424", "202.55", "2,791", "7,526", "27,505"]:
    if re.search(r"现价 <b>[¥$]" + re.escape(old), tseg):
        F["B_今日触发区现价≠7-22"].append(old)
# C 异常token
for tok in ["¥2,646", "¥2,940", "¥3,234", "939.5%", "$40~$80", "中枢$55", "现价 $1,350", "$35~95"]:
    for m in re.finditer(re.escape(tok), h):
        if not hist(m.start()):
            F["C_异常估值参与"].append(tok)
            break
# D JS
js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", h, re.S))
sels = re.findall(r"querySelectorAll?\('([^']*)'\)", js)
d_bad = [s for s in sels if "details" in s and "hist-iso" not in s]
if d_bad:
    F["D_JS读hist"].append(d_bad)
    F["扩④JS命中hist-iso"].append({"选择器命中全部details(含hist)": d_bad})

# 扩① 触发%重算:今日触发区 现价¥X 加仓价¥Y → 已比加仓价低 W%  须 W=round((Y-X)/Y*100,1)
for m in re.finditer(r"现价 <b>[¥$]([\d,]+(?:\.\d+)?)</b>[ 　]*加仓价\(便宜位\) <b>[¥$]([\d,]+(?:\.\d+)?)</b>[^→]*→[ 　]*已比加仓价低 <b>([\d.]+)%</b>", h):
    if hist(m.start()):
        continue
    cur = float(m.group(1).replace(",", "")); buy = float(m.group(2).replace(",", "")); shown = float(m.group(3))
    calc = round((buy - cur) / buy * 100, 1)
    if abs(calc - shown) > 0.15:
        F["扩①触发%重算不一致"].append({"现价": m.group(1), "加仓价": m.group(2), "显示%": shown, "重算%": calc})
# 扩② 股数×现价=市值:持仓表 <td>qty</td><td>$price</td><td>mktval</td> (闪迪等)
for m in re.finditer(r'text-align:right">(\d+)[ 　]*</td>\s*<td[^>]*>[¥$]([\d,]+\.\d+)</td>\s*<td[^>]*>([\d,]+)</td>', h):
    qty = float(m.group(1)); price = float(m.group(2).replace(",", "")); mv = float(m.group(3).replace(",", ""))
    if abs(qty * price - mv) > max(2, mv * 0.01):
        F["扩②股数×价≠市值"].append({"股数": m.group(1), "价": m.group(2), "市值": m.group(3), "应≈": round(qty * price)})
# 扩③ 爱德万/闪迪 异常字段残留(目标价¥33,544/估值合理/倍数/30,390/闪迪1.8%)
for tok, desc in [("目标价¥33,544", "爱德万目标价"), ("¥33,544(+6.5%)", "爱德万目标价+上行%"), ("超上沿约1.9倍", "爱德万倍数"),
                  (">30,390<", "闪迪错市值20股"), ("闪迪1.8%", "闪迪错占比")]:
    for m in re.finditer(re.escape(tok), h):
        if not hist(m.start()):
            F["扩③爱德万闪迪异常字段残留"].append({"token": tok, "说明": desc})
            break

all_pass = all(not v for v in F.values())
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print(f"★本报告核对版本SHA={sha}")
print("=== gate_fatal3_v2(三致命区A/B/C/D + 4扩查·对locked_v2) ===")
for k, v in F.items():
    print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v if v else '无'}")
print(f"★全PASS = {all_pass}")
print(f"--- 版本 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_fatal3_v2.json").write_text(json.dumps({
    "★本报告核对版本SHA": sha, "版本号": "v2", "file": P.name, "字节": len(raw), "mtime": mtime,
    "ABCD+4扩查_FAIL": F, "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_fatal3_v2.json")
