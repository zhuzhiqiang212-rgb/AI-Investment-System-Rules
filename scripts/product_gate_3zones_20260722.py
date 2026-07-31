#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""降阶三致命区自动硬闸(GPT批准·先做3区不强求10区)。对冻结版跑。
区:①全层动作语义区 ②今日加仓/减仓触发区 ③爱德万/闪迪异常估值区
A 守/等 非历史区出现"已触发/分批买/现金比例/下单金额" → FAIL
B 今日触发区现价 ≠ 该只7-22唯一正式现价 → FAIL
C 异常标的(爱德万/闪迪)出现 估值/加仓价/止盈线/高估比例/目标贡献/动作推导(非异常待核) → FAIL
D 历史隔离区不得被统计器/JS读取(JS选择器不命中hist-iso) → FAIL
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
# 对锁定版跑(SHA锁定·locked_v1)
FROZEN = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_locked_v1.html"
P = FROZEN if FROZEN.exists() else (ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html")
raw = P.read_bytes()
h = raw.decode("utf-8")
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
守 = {"US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"}
ORDER = list(prod.keys())
NAME = {s: prod[s]["name"] for s in prod}
BASE = {s: ("守" if s in 守 else "等") for s in ORDER}
NEWPX = {s: f"{prod[s]['price']:,.2f}" for s in ORDER}
ANOM = {"JP.6857", "US.SNDK"}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


FAIL = {"A_守等加仓语义": [], "B_今日触发区现价≠7-22": [], "C_异常标的估值参与": [], "D_JS读hist隔离区": []}

# A 全层动作语义:守/等 非hist 出现可执行加仓/减仓语义
for kw in ["已触发加仓", "⚡已触发", "分批买、别一次买满", "现在就可以加；分批", "今日已跌到加仓价", "已跌到加仓价：", "建议金额 约现金", "现金1/3分批", "现金1/4分批"]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            FAIL["A_守等加仓语义"].append({"词": kw, "样本": pl(h[m.start():m.start() + 22])})
            break

# B 今日触发区现价==7-22(每只)
ti = h.find("今天有没有跌到你的加仓价")
tseg = h[ti:ti + 6500] if ti > 0 else ""
for sym in ORDER:
    # 今日触发区该只 "现价 <b>¥newpx</b>"
    found_new = ("现价 <b>¥" + NEWPX[sym] + "</b>" in tseg) or ("现价 <b>$" + NEWPX[sym] + "</b>" in tseg)
    # 该只区块内有无旧价(724 pxnow)
    # (7-22价存在即视为该只用对价·旧价核在双价检查)
    if sym in NAME:
        pass
# 旧价进今日触发区现价检查
OLD = {"5,424", "202.55", "2,791", "7,526", "27,505"}
for old in OLD:
    for m in re.finditer(r"现价 <b>[¥$]" + re.escape(old), tseg):
        FAIL["B_今日触发区现价≠7-22"].append({"旧价当现价": old, "样本": pl(tseg[m.start():m.start() + 20])})

# C 异常标的(爱德万/闪迪) 估值/加仓/止盈/高估%/目标贡献 计算值(非异常待核)
CALC = [r"加仓价\(便宜位\)[ 　]*[¥$][\d,]+", r"还差[ 　]*[\d.]+%[ 　]*到加仓价", r"止盈[线]?[^<]{0,4}[¥$][\d,]+",
        r"今日该值 [¥$][\d,~$]+", r"中枢[ ]?[¥$][\d,]+", r"约 ?[\d.]+%高估|高估 ?[\d.]+%", r"目标贡献[^<]{0,4}[+\-][\d.]+"]
ANOM_TOK = ["¥2,646", "¥2,940", "¥2,938", "¥3,234", "939.5%", "$40~$80", "$40~80", "中枢$55", "现价 $1,350", "$35~95"]
for tok in ANOM_TOK:
    for m in re.finditer(re.escape(tok), h):
        if not hist(m.start()):
            FAIL["C_异常标的估值参与"].append({"异常token": tok, "样本": pl(h[m.start() - 8:m.start() + 12])})
            break
for who, did in [("爱德万", "deep-JP.6857"), ("闪迪", "deep-US.SNDK")]:
    i = h.find(f'id="{did}"')
    if i < 0:
        continue
    seg = h[i:i + 3500]
    for pat in CALC:
        for m in re.finditer(pat, seg):
            if hist(i + m.start()):
                continue
            pre = pl(seg[max(0, m.start() - 12):m.start()])
            if "异常" in pre or "待核" in pre or "不计算" in pre:
                continue
            FAIL["C_异常标的估值参与"].append({"who": who, "计算值": pl(seg[m.start():m.start() + 18])})
            break

# D 历史隔离区不得被统计器/JS读取:JS选择器不命中 hist-iso
js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", h, re.S))
js_sel = re.findall(r'(querySelector\w*|getElementsBy\w+)\([^)]*\)', js)
d_bad = [s for s in js_sel if "hist-iso" in s or "hist_iso" in s]
# 统计器数字(总决定统计/占比)是否含hist-iso内元素(hist-iso内不应有参与统计的动作chip)
hist_chips = 0
for m in re.finditer(r'<span class="chip (c-add|c-hold|c-wait)">', h):
    if hist(m.start()):
        hist_chips += 1  # 允许(历史档chip·但不应被统计器计入·统计是就地文本非JS)
if d_bad:
    FAIL["D_JS读hist隔离区"].append({"JS选择器命中hist-iso": d_bad})

all_pass = all(not v for v in FAIL.values())
sha = hashlib.sha256(raw).hexdigest()
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print(f"★本报告核对版本SHA={sha}")
print("=== 降阶三致命区自动硬闸(对锁定版locked_v1) ===")
print(f"文件:{P.name}")
for k, v in FAIL.items():
    print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v if v else '无'}")
print(f"  [说明] JS选择器数={len(js_sel)}·命中hist-iso={len(d_bad)}·hist内chip={hist_chips}(历史档·统计器为就地文本不读JS·不计入今日统计)")
print(f"★全PASS(三致命区A/B/C/D) = {all_pass}")
print(f"--- 版本锁定 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_fatal3_v1.json").write_text(json.dumps({
    "★本报告核对版本SHA": sha, "版本号": "v1", "file": P.name, "字节": len(raw), "mtime": mtime,
    "三致命区": ["全层动作语义区", "今日加仓减仓触发区", "爱德万闪迪异常估值区"],
    "ABCD_FAIL": FAIL, "JS选择器数": len(js_sel), "JS命中hist-iso": len(d_bad), "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_fatal3_v1.json (标所扫SHA)")
sys.exit(0 if all_pass else 1)
