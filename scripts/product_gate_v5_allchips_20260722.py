#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐股全节点硬闸 v5(GPT#6·修真):扫全产品每个动作chip(顶部表+今日动作表+风险表+why/deep卡+机会池)。
按所在<tr>内ticker优先/卡内nearest id兜底归属→每只收集所有位置的chip字形集合。
同股出现≥2个不同当日动作chip → FAIL(不被顶部表覆盖判过)。并核每只=7-22。
交付②:每只每位置的动作chip清单。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
NAME = {s: prod[s]["name"] for s in prod}
GLYPH = {}
for s in ["US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"]:
    GLYPH[s] = "■ 守"
for s in ["US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.SNDK"]:
    GLYPH[s] = "… 等"
GLYPH["US.MSTR"] = "◉ 等·盯"
GLYPH["JP.8766"] = "… 等·待核"
GLYPH["US.CRCL"] = "… 等·待核"
h = P.read_bytes().decode("utf-8")
idpos = [(m.start(), m.group(1)) for m in re.finditer(r'id="(?:act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)]


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


perstock = {s: {} for s in GLYPH}   # ticker -> {glyph: [位置摘要,...]}
unattributed = []
for m in re.finditer(r'<span class="chip (c-add|c-hold|c-wait|c-risk)">([^<]{1,14})</span>', h):
    g = m.group(2).strip()
    if g == "⚠ 险":
        continue
    pos = m.start()
    tr_s, tr_e, prev_close = h.rfind("<tr", 0, pos), h.find("</tr>", pos), h.rfind("</tr>", 0, pos)
    ticker = None
    if tr_s > prev_close and tr_e > pos:
        tkm = re.search(r"(US\.[A-Z]+|JP\.[0-9]+)", h[tr_s:tr_e])
        if tkm:
            ticker = tkm.group(1)
    if not ticker and idpos:
        near = min(idpos, key=lambda ip: abs(ip[0] - pos))
        if abs(near[0] - pos) < 1500:
            ticker = near[1]
    if not ticker:      # 兜底:最近ticker(±400·任一方向)
        cand = [(abs(mm.start() - pos), mm.group(1)) for mm in re.finditer(r"(US\.[A-Z]+|JP\.[0-9]+)", h[max(0, pos - 400):pos + 400])]
        if cand:
            ticker = min(cand)[1]
    if ticker in GLYPH:
        loc = plain(h[max(0, pos - 60):pos])[-24:]
        perstock[ticker].setdefault(g, []).append(loc)
    else:
        unattributed.append((g, plain(h[max(0, pos - 40):pos])[-30:]))

fails = []
report = {}
for sym in GLYPH:
    glyphs = perstock[sym]
    want = GLYPH[sym]
    distinct = set(glyphs)
    ok_single = len(distinct) <= 1
    ok_match = (not distinct) or (distinct == {want})
    n = sum(len(v) for v in glyphs.values())
    report[sym] = {"name": NAME[sym], "应7-22": want, "chip位置数": n, "字形集合": {k: len(v) for k, v in glyphs.items()}, "唯一": ok_single, "符7-22": ok_match}
    if not (ok_single and ok_match):
        fails.append({"sym": sym, "name": NAME[sym], "应": want, "见": {k: len(v) for k, v in glyphs.items()}})

# ---------- GPT#3扩查:风险配仓表/target-gap 未隔离的旧动作/旧目标数值 ----------
def in_hist_iso_at(pos, hh):
    """位置pos是否在某未闭合hist-iso折叠内"""
    return hh.rfind('class="hist-iso"', 0, pos) > hh.rfind("</details>", 0, pos)


def in_hist_iso(sub):
    """该串是否只出现在hist-iso折叠内(已隔离)"""
    for m in re.finditer(re.escape(sub), h):
        if not in_hist_iso_at(m.start(), h):
            return False
    return True


residual = []
for bad, desc in [("13.8% → 18.0%", "风险配仓英伟达加仓数值"), ("0% → 4.0%", "风险配仓台积电建仓数值"),
                  ("加至18%", "英伟达加仓建议"), ("$1,520,314", "旧目标主战场市值"),
                  ("+16.87%", "旧目标预计上升"), ("27.9个百分点", "旧目标距40%差"),
                  ("待建仓", "L2角色旧动作"), ("买卖建议·双档并列", "L2买卖建议旧结构")]:
    cnt = h.count(bad)
    if cnt and not in_hist_iso(bad):
        residual.append({"旧值": bad, "说明": desc, "次数": cnt, "未隔离": True})
# L2/L3 第一档/第二档 加仓价(守/等不该有) — 泛式正则
for pat, desc in [(r"第一档[ 　]?[$¥][\d,.]+", "L2/L3第一档加仓价"), (r"第二档[ 　]?[$¥][\d,.]+", "L2/L3第二档加仓价")]:
    ms = re.findall(pat, h)
    ms = [x for x in ms if not in_hist_iso(x)]
    if ms:
        residual.append({"旧值": desc, "样本": ms[:3], "次数": len(ms), "未隔离": True})
# L2买卖建议双档历史内容 + L2/L3买卖动作 须已隔离(hist-iso内) — 未隔离即FAIL
for bad, desc in [("【中性档", "L2买卖建议中性档"), ("【激进档", "L2买卖建议激进档"),
                  ("建仓·约现金", "L2/L3建仓买卖动作"), ("角色 待建仓", "L2目标倒推角色")]:
    cnt = h.count(bad)
    if cnt and not in_hist_iso(bad):
        residual.append({"旧值": bad, "说明": desc + "(未移hist-iso)", "次数": cnt, "未隔离": True})

# ---------- L3决定摘要『今日动作 X』文字字段 逐deep卡核7-22(三轮遗漏根因·补查) ----------
BASE = {s: ("守" if GLYPH[s] == "■ 守" else "等") for s in GLYPH}
danchors = sorted([(m.start(), m.group(1)) for m in re.finditer(r'id="deep-([A-Z]{2}\.[A-Z0-9]+)"', h)])
dstarts = [a[0] for a in danchors]
l3_fail = []
for i, (pos, tk) in enumerate(danchors):
    if tk not in BASE:
        continue
    seg = h[pos:(dstarts[i + 1] if i + 1 < len(dstarts) else len(h))]
    for m in re.finditer(r"今日动作 (?:<b>)?([守加观等减盯])", seg):
        if not in_hist_iso_at(pos + m.start(), h) and m.group(1) != BASE[tk]:
            l3_fail.append({"ticker": tk, "L3今日动作": m.group(1), "应": BASE[tk]})
# 建议金额 约现金(买卖金额) 当日正文残留
amt = [m.start() for m in re.finditer(r"建议金额 约现金", h) if not in_hist_iso_at(m.start(), h)]
if amt:
    residual.append({"旧值": "建议金额 约现金", "说明": "L3决定摘要买卖金额未隔离", "次数": len(amt), "未隔离": True})

all_pass = not fails and not unattributed and not residual and not l3_fail
print("=== 逐股全节点硬闸 v5(全产品所有chip) ===")
print(f"{'sym':<9}{'name':<8}{'应7-22':<10}{'位置数':<6}{'字形集合'}")
for sym in GLYPH:
    r = report[sym]
    mk = "✔" if (r["唯一"] and r["符7-22"]) else "✗"
    print(f"  {mk} {sym:<9}{r['name']:<8}{r['应7-22']:<10}{r['chip位置数']:<6}{r['字形集合']}")
print(f"未归属chip: {len(unattributed)}", unattributed[:3] if unattributed else "")
print(f"★同股多答案/不符FAIL: {fails if fails else '无'}")
print(f"★L3决定摘要『今日动作X』不符7-22: {l3_fail if l3_fail else '无'}")
print(f"★扩查·风险配仓/target-gap/L3买卖金额 未隔离旧数值: {residual if residual else '无(全隔离/删除)'}")
print(f"★全PASS(chip+L3今日动作+旧数值 全一致/隔离) = {all_pass}")
(ROOT / "data/screen/gate_v5_allchips_20260722.json").write_text(json.dumps({
    "per_stock_chip清单": report, "未归属": unattributed, "chipFAIL": fails, "L3今日动作FAIL": l3_fail, "风险配仓target_L3金额旧数值残留": residual, "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_v5_allchips_20260722.json")
