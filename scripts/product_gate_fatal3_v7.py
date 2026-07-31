#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_fatal3_v7·三致命A/B/C/D·硬闸C=卡片边界(v6) + 【新增·全区共现规则】(架构师核v6抓line422卡外共现:风险区把异常只当"峰值定价"举例·卡片边界扫不到)。对locked_v7跑。
C1(卡片边界):爱德万/闪迪 act/why/deep 卡内任意『\\d+倍/公允/极贵/景气高点/峰值定价/合理值/中周期/穿牛熊』→FAIL。
C2(全区共现·补盲):全HTML『爱德万』或『闪迪』与『景气高点/峰值定价/极贵/高位/合理值/N倍/中周期/穿牛熊』±60字同现(非hist)→FAIL。"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_locked_v7.html"
raw = P.read_bytes()
h = raw.decode("utf-8")
sha = hashlib.sha256(raw).hexdigest()


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


def card_bounds(sym):
    res = []
    for idk in ("act", "why", "deep"):
        i = h.find(f'id="{idk}-{sym}"')
        if i < 0:
            continue
        nx = [x for k in ("act", "why", "deep") for x in [h.find(f'id="{k}-', i + 12)] if x > 0]
        res.append((idk, i, min(nx) if nx else len(h)))
    return res


F = {"A_守等加仓语义": [], "B_今日触发区现价≠7-22": [], "C1_异常卡内估值禁词(卡片边界)": [],
     "C2_异常只×定价类全区共现(±60字)": [], "D_JS读hist": []}

# A
for kw in ["已触发加仓", "⚡已触发", "分批买、别一次买满", "现在就可以加；分批", "今日已跌到加仓价", "建议金额 约现金"]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            F["A_守等加仓语义"].append(kw)
            break
# B
ti = h.find("今天有没有跌到你的加仓价")
tseg = h[ti:ti + 6500] if ti > 0 else ""
for old in ["5,424", "202.55", "2,791", "7,526", "27,505"]:
    if re.search(r"现价 <b>[¥$]" + re.escape(old), tseg):
        F["B_今日触发区现价≠7-22"].append(old)

# ★C1 按卡片边界
PATS = [r"\d+\s?倍", "公允", "极贵", "景气高点", "峰值定价", "合理值", "中周期", "穿牛熊"]
for who, sym in [("爱德万", "JP.6857"), ("闪迪", "US.SNDK")]:
    for idk, s, e in card_bounds(sym):
        seg = h[s:e]
        for pat in PATS:
            for m in re.finditer(pat, seg):
                if hist(s + m.start()):
                    continue
                F["C1_异常卡内估值禁词(卡片边界)"].append({"股": who, "卡": idk, "禁词": pat, "上下文": pl(seg[max(0, m.start() - 18):m.start() + 12])})

# ★C2 全区共现(补卡片边界盲区):爱德万/闪迪 与 定价类 ±60字同现
CO = ["景气高点", "峰值定价", "极贵", "高位", "合理值", "中周期", "穿牛熊"]
for nm in ["爱德万", "闪迪"]:
    for m in re.finditer(nm, h):
        if hist(m.start()):
            continue
        ctx = h[max(0, m.start() - 60):m.start() + 60]
        hit = [dz for dz in CO if dz in ctx]
        if re.search(r"\d+\s?倍", ctx):
            hit.append("N倍")
        if hit:
            F["C2_异常只×定价类全区共现(±60字)"].append({"股": nm, "行": h[:m.start()].count("\n"), "共现": hit, "上下文": pl(ctx)})

# D
js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", h, re.S))
d_bad = [s for s in re.findall(r"querySelectorAll?\('([^']*)'\)", js) if "details" in s and "hist-iso" not in s]
if d_bad:
    F["D_JS读hist"].append(d_bad)

all_pass = all(not v for v in F.values())
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print(f"★本报告核对版本SHA={sha}")
print("=== gate_fatal3_v7(三致命·硬闸C=卡片边界+全区共现·对locked_v7) ===")
for k, v in F.items():
    print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v if v else '无'}")
print(f"★三致命全PASS = {all_pass}")
print(f"--- 版本 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_fatal3_v7.json").write_text(json.dumps({
    "★本报告核对版本SHA": sha, "版本号": "v7", "file": P.name, "字节": len(raw), "mtime": mtime,
    "硬闸C口径": "C1按卡片边界(act/why/deep) + C2全区共现(爱德万/闪迪×定价类±60字)", "ABCD_FAIL": F, "三致命全PASS": all_pass},
    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_fatal3_v7.json")
