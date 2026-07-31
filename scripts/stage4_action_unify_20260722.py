#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段4·7-22动作统一(GPT 2026-07-23裁定:724内容冻结·7-19动作结论可更新为7-22)。
修⑥同股跨层一个答案+③数量格式。源=架构师deep_20260722+GPT裁定清单(SPCX/8766/CRCL 3处GPT override)。
在724底稿就地更新每股act卡/why卡的动作chip(class+字形一起改)→同股跨层一致;更新7-19文字结论;
加增补⑪7-22统一动作表(单一真值源:动作/账户/数量或状态/分档/理由/触发·停止/日期2026-07-22)+增补⑫变更表。
建议减(8766/CRCL)=情景预演·不可执行·无数量(profit_take=0无卖信号+账户快照未闭环)。
"""
import html as H
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段3增补.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段4动作统一.html"
deep = json.loads((ROOT / "data/analysis/deep_20260722.json").read_text(encoding="utf-8"))["holdings"]
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
SPLIT = {"JP.4568": "富通6500＋SBI3400", "US.NVDA": "富通830＋IBKR190", "US.MSFT": "富通550＋IBKR140",
         "US.MSTR": "富通700＋IBKR158", "US.COIN": "富通200＋IBKR45", "JP.9984": "富通4100＋SBI2800",
         "JP.8766": "SBI1000", "JP.6758": "SBI1000", "JP.6857": "SBI800", "JP.7203": "SBI800",
         "JP.8001": "SBI900", "JP.7832": "富通500", "JP.7974": "富通2000", "US.AVGO": "富通150",
         "US.CRCL": "富通400", "US.SNDK": "富通5", "US.TSM": "富通1", "US.META": "IBKR95",
         "US.IBKR": "IBKR14", "US.SPCX": "富途10"}
NAME = {s: prod[s]["name"] for s in prod}
# GPT裁定7-22统一动作(权威·SPCX/8766/CRCL为GPT override deep)
ACT = {
    "US.NVDA": ("守", ""), "US.AVGO": ("守", "重点"), "US.TSM": ("守", ""), "JP.6857": ("守", ""),
    "JP.9984": ("守", ""), "JP.4568": ("守", ""), "US.SPCX": ("守", "未上市·风险高"),
    "US.MSFT": ("等", "别再加"), "US.META": ("等", ""), "US.COIN": ("等", ""), "US.IBKR": ("等", ""),
    "JP.6758": ("等", ""), "JP.7203": ("等", ""), "JP.8001": ("等", ""), "JP.7832": ("等", ""),
    "JP.7974": ("等", ""), "US.SNDK": ("等", ""),
    "US.MSTR": ("等·盯", "mNAV<1"),
    "JP.8766": ("建议减", "情景预演·不可执行"), "US.CRCL": ("建议减", "情景预演·不可执行"),
}
ORDER = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
         "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
         "US.TSM", "US.META", "US.IBKR", "US.SPCX"]
# 动作→chip(class+字形)
CHIP = {"守": ("c-hold", "■ 守"), "等": ("c-wait", "… 等"), "等·盯": ("c-wait", "◉ 等·盯"),
        "建议减": ("c-risk", "▽ 减·演")}


def e(x):
    return H.escape("" if x is None else str(x))


h = SRC.read_bytes().decode("utf-8")

# ---------- 就地更新 act/why 卡动作chip ----------
anchors = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'id="(act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts = [a[0] for a in anchors]
chip_changes = []
# 逐卡替换:仅替换 c-add/c-wait/c-hold 的动作chip(跳过 c-risk⚠险 / c-tbd)
new_parts = []
last = 0
ACTION_CHIP_RE = re.compile(r'<span class="chip (c-add|c-wait|c-hold)">([^<]{1,14})</span>')
for i, (pos, typ, tk) in enumerate(anchors):
    if typ not in ("act", "why") or tk not in ACT:
        continue
    seg_start = pos
    seg_end = starts[i + 1] if i + 1 < len(starts) else len(h)
    m = ACTION_CHIP_RE.search(h, seg_start, seg_end)
    if not m:
        continue  # 如SPCX act卡只有⚠险·无动作chip
    action = ACT[tk][0]
    cls, glyph = CHIP[action]
    old = m.group(0)
    new = f'<span class="chip {cls}">{glyph}</span>'
    if old != new:
        chip_changes.append({"卡": f"{typ}-{tk}", "旧": m.group(2), "新": glyph})
    new_parts.append(h[last:m.start()])
    new_parts.append(new)
    last = m.end()
new_parts.append(h[last:])
h = "".join(new_parts)

# ---------- 7-19文字结论 → 7-22 ----------
old_concl = "加英伟达/博通、建仓台积电为方向确定下的补缺口建议·均待董事长拍板。"
if old_concl in h:
    h = h.replace(old_concl, "【7-22更新·架构师deep_20260722】英伟达/博通/台积电7-22统一动作＝<b>守</b>（守=不加不减）·原7-19『加/建仓补缺口』结论已更新·详见顶部『7-22统一动作表』。", 1)
    concl_updated = True
else:
    concl_updated = False

# ---------- 增补⑪ 7-22统一动作表(单一真值源) ----------
def qty_or_state(sym, act):
    if act == "建议减":
        return "情景预演·不可执行(无数量)"
    return f'{int(prod[sym]["quantity"])}股'
rows = ""
for sym in ORDER:
    act, tier = ACT[sym]
    d = deep.get(sym, {})
    reason = e((d.get("book") or d.get("biz") or "")[:56])
    trig = e((d.get("flip") or d.get("pricenote") or "")[:56])
    cls, glyph = CHIP[act]
    warn = ' style="background:#3a1414;color:#ffb3b3"' if act == "建议减" else ""
    rows += (f'<tr{warn}><td>{e(NAME[sym])}</td><td>{e(sym)}</td>'
             f'<td><b>{glyph}</b>{("·" + e(tier)) if tier else ""}</td><td>{e(SPLIT[sym])}</td>'
             f'<td>{qty_or_state(sym, act)}</td><td>{reason}</td><td>{trig}</td><td>2026-07-22</td></tr>')
sec11 = (f'<div id="unified-action-0722" style="border:3px solid #12324e;background:#f2f6fb;border-radius:10px;padding:14px 16px;margin:12px 0">'
         f'<div style="font-size:17px;font-weight:800;color:#12324e">■ 增补⑪ 7-22 统一动作表（同股跨层唯一真值源·GPT 2026-07-23裁定）</div>'
         f'<div style="font-size:12.5px;color:#555;margin:4px 0 8px">源=架构师deep_20260722+GPT裁定。724底稿各层动作chip已就地统一到本表（7-19旧结论已更新）。'
         f'<b>建议减(东京海上/Circle)=情景预演·不可执行</b>（profit_take=0无系统卖信号+SBI账户快照未闭环·仅演练不形成可执行数量）。判断日期均2026-07-22。</div>'
         f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11.5px">'
         f'<tr style="background:#12324e;color:#fff"><th>名称</th><th>代码</th><th>7-22动作</th><th>账户拆分</th><th>数量/状态</th><th>理由(deep)</th><th>触发·停止(证伪)</th><th>日期</th></tr>'
         f'{rows}</table></div></div>')

# ---------- 增补⑫ 7-19→7-22 动作变更表 ----------
OLD719 = {"JP.4568": "加", "US.NVDA": "等/加(层间不一致)", "US.MSFT": "守/等", "US.MSTR": "守", "US.COIN": "加/守",
          "JP.9984": "守/加", "JP.8766": "加/守", "JP.6758": "观/加", "JP.6857": "守/观", "JP.7203": "守",
          "JP.8001": "守", "JP.7832": "等/守", "JP.7974": "等", "US.AVGO": "守/等", "US.CRCL": "观/守",
          "US.SNDK": "守/观", "US.TSM": "等/守(含建仓文案)", "US.META": "守/等", "US.IBKR": "观/守", "US.SPCX": "险/观"}
crows = ""
for sym in ORDER:
    a722 = ACT[sym][0] + (("·" + ACT[sym][1]) if ACT[sym][1] else "")
    changed = "变" if OLD719[sym].split("/")[0] not in a722 else "—"
    crows += f'<tr><td>{e(NAME[sym])}</td><td>{e(sym)}</td><td>{e(OLD719[sym])}</td><td><b>{e(a722)}</b></td><td style="text-align:center">{changed}</td></tr>'
sec12 = (f'<div id="action-diff-0722" style="border:2px solid #7a5c00;background:#fffdf5;border-radius:9px;padding:12px 14px;margin:10px 0">'
         f'<div style="font-size:14.5px;font-weight:800;color:#7a5c00">增补⑫ 7-19→7-22 动作变更表（含724层间不一致→统一）</div>'
         f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11.5px;margin-top:6px">'
         f'<tr style="background:#12324e;color:#fff"><th>名称</th><th>代码</th><th>7-19(act/why·常不一致)</th><th>7-22统一</th><th>变更</th></tr>{crows}</table></div></div>')

# 插入到 stage3-augment 层之前(顶部·数据/动作层集中)
anchor_ins = '<div id="stage3-augment"'
h = h.replace(anchor_ins, sec11 + sec12 + anchor_ins, 1)
h = h.replace("<title>★每日投资产品 · 2026-07-22（724底稿保真恢复+7-22数据+本轮增补） · 三层</title>",
              "<title>★每日投资产品 · 2026-07-22（724冻结内容+7-22数据/动作+增补） · 三层</title>", 1)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
# 同股跨层一致性校验
anchors2 = sorted([(m.start(), m.group(1), m.group(2)) for m in re.finditer(r'id="(act|why)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
starts2 = [a[0] for a in anchors2]
consist = {}
for i, (pos, typ, tk) in enumerate(anchors2):
    if tk not in ACT:
        continue
    seg = h[pos:(starts2[i + 1] if i + 1 < len(starts2) else len(h))]
    m = ACTION_CHIP_RE.search(seg)
    if m:
        consist.setdefault(tk, set()).add(m.group(2).strip())
inconsist = {k: list(v) for k, v in consist.items() if len(v) > 1}
print("阶段4产物:", OUT.name, len(raw), "字节·EFBFBD乱码=", raw.count(b"\xef\xbf\xbd"), "·裸LF=", h.count("\n") - h.count("\r\n") if False else raw.count(b"\n") - raw.count(b"\r\n"))
print("chip更新:", len(chip_changes), "·7-19结论已更新:", concl_updated)
print("统一动作表/变更表已插:", "unified-action-0722" in h, "/", "action-diff-0722" in h)
print("★同股跨层一致性:", "全一致" if not inconsist else f"★不一致{inconsist}")
(ROOT / "data/screen/stage4_action_20260722.json").write_text(json.dumps({
    "authoritative_actions_722": {s: {"action": ACT[s][0], "tier": ACT[s][1], "account": SPLIT[s],
                                      "qty_or_state": qty_or_state(s, ACT[s][0]), "date": "2026-07-22"} for s in ORDER},
    "chip_changes": chip_changes, "7-19结论更新": concl_updated,
    "action_diff_719_722": {s: {"719": OLD719[s], "722": ACT[s][0] + (("·" + ACT[s][1]) if ACT[s][1] else "")} for s in ORDER},
    "同股跨层一致": not inconsist, "不一致项": inconsist,
    "GPT_override_vs_deep": {"US.SPCX": "deep等→GPT守", "JP.8766": "deep等·可优先减→GPT建议减(情景预演)", "US.CRCL": "deep等·警惕→GPT建议减(情景预演)"},
}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/stage4_action_20260722.json")
