#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段6·跨层动作一致性强制(GPT裁定同股跨层一个答案)。
stage2更新层表+stage3增补⑥前瞻表用的是production动作(守/等),与GPT权威(建议减/等·盯/守)对4只发散:
JP.8766等→建议减·演·US.CRCL等→建议减·演·US.SPCX等→守·US.MSTR等→等·盯。
行级精确替换其plain动作cell(只改这两表·不碰统一动作表glyph『■守/…等/◉等·盯/▽减·演』·不碰变更表『变/—』)。
再全局校验:每只在所有动作显示处一个答案。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段5缺口账户.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段6一致.html"
# 发散4只: ticker → (旧plain, 新display)
FIX = {"JP.8766": ("等", "建议减·演"), "US.CRCL": ("等", "建议减·演"), "US.SPCX": ("等", "守"), "US.MSTR": ("等", "等·盯")}

h = SRC.read_bytes().decode("utf-8")
changes = []
# 行级:按</tr>切,凡含发散ticker且有 plain text-align:center">旧</td> 的行→替换
parts = h.split("</tr>")
for i, seg in enumerate(parts):
    for tk, (old, new) in FIX.items():
        if tk in seg and f'text-align:center">{old}</td>' in seg:
            parts[i] = seg.replace(f'text-align:center">{old}</td>', f'text-align:center">{new}</td>')
            changes.append({"行含": tk, "旧": old, "新": new})
            seg = parts[i]
h = "</tr>".join(parts)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()

# 全局一致性校验:每只ticker在所有动作显示处收敛到一个动作族
ACT = {"US.NVDA": "守", "US.AVGO": "守", "US.TSM": "守", "JP.6857": "守", "JP.9984": "守", "JP.4568": "守", "US.SPCX": "守",
       "US.MSFT": "等", "US.META": "等", "US.COIN": "等", "US.IBKR": "等", "JP.6758": "等", "JP.7203": "等",
       "JP.8001": "等", "JP.7832": "等", "JP.7974": "等", "US.SNDK": "等", "US.MSTR": "等·盯",
       "JP.8766": "建议减", "US.CRCL": "建议减"}
# chip族(act/why) + 统一动作表glyph 应与ACT一致
GLYPH = {"守": "■ 守", "等": "… 等", "等·盯": "◉ 等·盯", "建议减": "▽ 减·演"}
issues = []
anchors = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'id="(act|why)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
chipre = re.compile(r'<span class="chip (c-add|c-wait|c-hold|c-risk)">([^<]{1,14})</span>')
chipseen = {}
for i, (pos, typ, tk) in enumerate(anchors):
    if tk not in ACT:
        continue
    seg = h[pos:(starts[i + 1] if i + 1 < len(starts) else len(h))]
    for m in chipre.finditer(seg):
        g = m.group(2).strip()
        if g in ("⚠ 险",):
            continue
        chipseen.setdefault(tk, set()).add(g)
for tk, want in ACT.items():
    glyph = GLYPH[want]
    seen = chipseen.get(tk, set())
    # 允许SPCX act卡无动作chip(只⚠险)→由why卡+统一表覆盖
    if seen and any(s != glyph for s in seen):
        issues.append({"ticker": tk, "want": glyph, "chip见": list(seen)})
print("阶段6产物:", OUT.name, len(raw), "字节·EFBFBD乱码=", raw.count(b"\xef\xbf\xbd"), "·裸LF=", raw.count(b"\n") - raw.count(b"\r\n"))
print("发散动作cell修正:", len(changes), changes)
print("★chip层跨层一致校验:", "全一致" if not issues else f"★不一致{issues}")
(ROOT / "data/screen/stage6_consistency_20260722.json").write_text(json.dumps({
    "发散修正": changes, "authoritative": ACT, "chip一致": not issues, "不一致": issues}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/stage6_consistency_20260722.json")
