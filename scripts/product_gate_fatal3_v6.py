#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_fatal3_v6·三致命区A/B/C/D·硬闸C从「名称±40字临近」升级为「按个股卡片边界」(架构师核v5抓C结构缺陷·漏卡内远段)。对locked_v6跑。
C:定位爱德万(JP.6857)/闪迪(US.SNDK)卡片容器(act/why/deep)→卡内任意文字出现『\\d+\\s?倍』『公允』『极贵』『景气高点』『峰值定价』『合理值』『中周期』『穿牛熊』→FAIL。
另:全文核 line906「倍数压向高20/低30倍」、line955「¥2,939落中周期公允」是否属异常只(即是否落在异常卡内)。"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_locked_v6.html"
raw = P.read_bytes()
h = raw.decode("utf-8")
sha = hashlib.sha256(raw).hexdigest()


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


def card_bounds(sym):
    """按卡片边界:act/why/deep 三容器各自 [起, 下一个卡片anchor)"""
    res = []
    for idk in ("act", "why", "deep"):
        i = h.find(f'id="{idk}-{sym}"')
        if i < 0:
            continue
        nx = [x for k in ("act", "why", "deep") for x in [h.find(f'id="{k}-', i + 12)] if x > 0]
        res.append((idk, i, min(nx) if nx else len(h)))
    return res


F = {"A_守等加仓语义": [], "B_今日触发区现价≠7-22": [], "C_异常卡内估值禁词(卡片边界)": [], "D_JS读hist": [],
     "扩·line906倍数压向高低": [], "扩·line955中周期公允归属": []}

# A 守/等 无 已触发/分批买/现金比例/下单金额
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

# ★C 按卡片边界:异常两卡(act/why/deep)内任意禁词→FAIL
PATS = [r"\d+\s?倍", "公允", "极贵", "景气高点", "峰值定价", "合理值", "中周期", "穿牛熊"]
for who, sym in [("爱德万", "JP.6857"), ("闪迪", "US.SNDK")]:
    for idk, s, e in card_bounds(sym):
        seg = h[s:e]
        for pat in PATS:
            for m in re.finditer(pat, seg):
                if hist(s + m.start()):
                    continue
                F["C_异常卡内估值禁词(卡片边界)"].append(
                    {"股": who, "卡": idk, "禁词": pat, "命中": pl(seg[m.start():m.start() + 10]), "上下文": pl(seg[max(0, m.start() - 20):m.start() + 12])})

# D JS选择器不命中hist-iso
js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", h, re.S))
d_bad = [s for s in re.findall(r"querySelectorAll?\('([^']*)'\)", js) if "details" in s and "hist-iso" not in s]
if d_bad:
    F["D_JS读hist"].append(d_bad)

# 扩·line906「倍数压向高N/低N倍」是否落异常卡内(架构师点名核)
an_ranges = []
for sym in ("JP.6857", "US.SNDK"):
    for idk, s, e in card_bounds(sym):
        an_ranges.append((sym, s, e))


def in_anom(pos):
    for sym, s, e in an_ranges:
        if s <= pos < e:
            return sym
    return None


for m in re.finditer(r"倍数压向高 ?\d+/低 ?\d+ ?倍", h):
    who = in_anom(m.start())
    F["扩·line906倍数压向高低"].append({"行": h[:m.start()].count("\n"), "命中": pl(h[m.start():m.start() + 16]),
                                  "属异常卡?": who or "否(非异常只·或已清)", "hist?": hist(m.start())})
for m in re.finditer(r"[¥$]2,939[^。]{0,6}落中周期公允|2,939 ?落中周期", h):
    who = in_anom(m.start())
    F["扩·line955中周期公允归属"].append({"行": h[:m.start()].count("\n"), "命中": pl(h[m.start() - 4:m.start() + 16]),
                                    "属异常卡?": who or "否(丰田¥2,939·非异常只→C不管辖)", "hist?": hist(m.start())})

# 致命判定:A/B/C/D 有内容即FAIL(扩项为归属核查·仅当落异常卡才算C违规·已并入C)
fatal = {k: v for k, v in F.items() if k.startswith(("A_", "B_", "C_", "D_"))}
all_pass = all(not v for v in fatal.values())
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print(f"★本报告核对版本SHA={sha}")
print("=== gate_fatal3_v6(三致命A/B/C/D·硬闸C按卡片边界·对locked_v6) ===")
for k, v in F.items():
    tag = "PASS" if not v else ("FAIL" if k.startswith(("A_", "B_", "C_", "D_")) else "核查")
    print(f"  [{tag}] {k}: {v if v else '无'}")
print(f"★三致命全PASS = {all_pass}")
print(f"--- 版本 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_fatal3_v6.json").write_text(json.dumps({
    "★本报告核对版本SHA": sha, "版本号": "v6", "file": P.name, "字节": len(raw), "mtime": mtime,
    "硬闸C口径": "按个股卡片边界(act/why/deep)·非名称±40字临近", "ABCD_FAIL": fatal,
    "扩查归属": {k: v for k, v in F.items() if k.startswith("扩")}, "三致命全PASS": all_pass},
    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_fatal3_v6.json")
