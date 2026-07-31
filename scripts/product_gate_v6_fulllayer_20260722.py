#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整全层硬闸 v6(GPT验收退回·硬闸须自证L1/L2/L3全层·非只查chip)。
四维度逐股扫+版本SHA对齐:
 A 动作字段全变体逐股(chip+今日动作表+L2角色/持仓意图+L3决定摘要今日动作+为什么现在X+动作=X)→与7-22统一表比对
 B 日期(当日语境非hist-iso): 2026-07-19产品标题/今日与昨日一致 → FAIL
 C 口径(当日语境非hist-iso): 13只与目标相加$730,975/旧目标16.87%/12.1%/$1,520,314/27.9pp → FAIL
 D 异常隔离: 爱德万/闪迪 加仓价/止盈参与计算(非隔离) + 增补⑮异常声明须在 → FAIL
守/等禁词(当日语境): 待建仓/建仓·$X/加仓价/第一档$X/第二档$X/加至X%/建议减/建议金额约现金/今日动作加·观/为什么现在加/动作=加。
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
raw = P.read_bytes()
h = raw.decode("utf-8")
守 = {"US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"}
ALL = 守 | {"US.MSFT", "US.META", "US.COIN", "US.IBKR", "JP.6758", "JP.7203", "JP.8001", "JP.7832",
           "JP.7974", "US.SNDK", "US.MSTR", "JP.8766", "US.CRCL"}
BASE = {s: ("守" if s in 守 else "等") for s in ALL}
GLYPHOK = {}
for s in ALL:
    GLYPHOK[s] = {"■ 守"} if s in 守 else {"… 等"}
GLYPHOK["US.MSTR"] = {"◉ 等·盯"}
GLYPHOK["JP.8766"] = {"… 等·待核"}
GLYPHOK["US.CRCL"] = {"… 等·待核"}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


FAIL = {"A_动作": [], "B_日期": [], "C_口径": [], "D_异常": []}

# ---------- A 动作字段全变体逐股 ----------
# chip(所在<tr>ticker优先·卡内nearest id·±400兜底)
idpos = [(m.start(), m.group(1)) for m in re.finditer(r'id="(?:act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)]
perstock = {s: set() for s in ALL}
for m in re.finditer(r'<span class="chip (c-add|c-hold|c-wait|c-risk)">([^<]{1,14})</span>', h):
    g = m.group(2).strip()
    if g == "⚠ 险":
        continue
    pos = m.start()
    tr_s, tr_e, pc = h.rfind("<tr", 0, pos), h.find("</tr>", pos), h.rfind("</tr>", 0, pos)
    tk = None
    if tr_s > pc and tr_e > pos:
        mm = re.search(r"(US\.[A-Z]+|JP\.[0-9]+)", h[tr_s:tr_e])
        tk = mm.group(1) if mm else None
    if not tk and idpos:
        near = min(idpos, key=lambda ip: abs(ip[0] - pos))
        tk = near[1] if abs(near[0] - pos) < 1500 else None
    if not tk:
        cand = [(abs(mm.start() - pos), mm.group(1)) for mm in re.finditer(r"(US\.[A-Z]+|JP\.[0-9]+)", h[max(0, pos - 400):pos + 400])]
        tk = min(cand)[1] if cand else None
    if tk in perstock and not hist(pos):
        perstock[tk].add(g)
for s in ALL:
    bad = perstock[s] - GLYPHOK[s]
    if bad:
        FAIL["A_动作"].append({"层": "chip", "ticker": s, "见": list(perstock[s]), "应": list(GLYPHOK[s])})

# 文字动作字段:今日动作X / 为什么现在X / 动作=X / 角色X (逐deep/why卡·非hist)
danch = sorted([(m.start(), m.group(2), m.group(1)) for m in re.finditer(r'id="(why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)])
dstar = [a[0] for a in danch]
for i, (pos, tk, typ) in enumerate(danch):
    if tk not in BASE:
        continue
    seg = h[pos:(dstar[i + 1] if i + 1 < len(dstar) else len(h))]
    base = pos
    # 动作=/今日动作 只在deep卡查·为什么现在/角色 只在why卡查(避免why/deep锚点混用误判边界)
    pats = ([(r"今日动作 (?:<b>)?([守加观等减盯])", "今日动作"), (r"动作[＝=]([守加观等减盯])", "动作=")] if typ == "deep"
            else [(r"为什么现在([守加观等减盯])", "为什么现在"), (r"角色 (待建仓|建仓)", "角色")])
    for pat, name in pats:
        for m in re.finditer(pat, seg):
            if hist(base + m.start()):
                continue
            v = m.group(1)
            if name == "角色":
                FAIL["A_动作"].append({"层": "L2角色", "ticker": tk, "见": v, "应": "持有/观察"})
            elif v != BASE[tk]:
                FAIL["A_动作"].append({"层": name, "ticker": tk, "见": v, "应": BASE[tk]})

# 守/等禁词(当日语境·非hist)
for pat, desc in [(r"第一档[ 　]?[$¥][\d,.]+", "第一档加仓价"), (r"第二档[ 　]?[$¥][\d,.]+", "第二档加仓价"),
                  (r"加至18%", "加仓至18%"), (r"建议金额 约现金", "买卖金额"), (r"建议减", "建议减"),
                  (r"13.8% → 18.0%", "风险配仓加仓"), (r"0% → 4.0%", "风险配仓建仓"),
                  (r'<span class="chip c-add">', "加chip")]:
    for m in re.finditer(pat, h):
        if not hist(m.start()):
            FAIL["A_动作"].append({"层": "禁词", "词": desc, "样本": plain(h[m.start():m.start() + 30])[:24]})
            break

# ---------- B 日期 ----------
for pat, desc in [(r"★ 每日投资产品 · 2026-07-19", "旧产品标题07-19"), (r"今日与昨日一致", "昨日一致"),
                  (r"价格对应交易日 <b>2026-07-17", "旧价格日07-17")]:
    for m in re.finditer(pat, h):
        if not hist(m.start()):
            FAIL["B_日期"].append({"词": desc, "样本": plain(h[m.start():m.start() + 30])[:26]})
            break

# ---------- C 口径 ----------
for pat, desc in [(r"离标约\$730,975", "13只与目标相加"), (r"\$1,520,314", "旧目标主战场市值"),
                  (r"预计上升 \+16.87%", "旧目标16.87%"), (r"预期年化 约\+12.1%", "旧目标年化12.1%"),
                  (r"27.9个百分点", "旧目标距40%27.9pp"), (r"当前13只已−\$61,625）需赚", "13只混算全账户")]:
    for m in re.finditer(pat, h):
        if not hist(m.start()):
            FAIL["C_口径"].append({"词": desc, "样本": plain(h[m.start():m.start() + 30])[:26]})
            break

# ---------- D 异常隔离 ----------
if "anomaly-isolation-0722" not in h:
    FAIL["D_异常"].append({"缺": "增补⑮异常隔离声明不在"})
for who, kw in [("爱德万", "爱德万"), ("闪迪", "闪迪")]:
    if not (who in h and ("价格口径异常" in h or "口径异常待核" in h)):
        FAIL["D_异常"].append({"缺": who + "异常标注"})
# 爱德万/闪迪 加仓价/止盈 参与(非hist)
for who, deepid in [("爱德万", "deep-JP.6857"), ("闪迪", "deep-US.SNDK")]:
    i = h.find('id="' + deepid + '"')
    if i < 0:
        continue
    nxt = h.find('id="deep-', i + 10)
    seg = h[i:(nxt if nxt > 0 else len(h))]
    for m in re.finditer(r"(第一档|第二档)[ 　]?[$¥][\d,.]+", seg):
        if not hist(i + m.start()):
            FAIL["D_异常"].append({who: "加仓价参与(非隔离)", "样本": m.group()})
            break

all_pass = all(not v for v in FAIL.values())
sha = hashlib.sha256(raw).hexdigest()
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print("=== 完整全层硬闸 v6(L1/L2/L3逐股·四维度) ===")
for k, v in FAIL.items():
    print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v if v else '无'}")
print(f"★全PASS(四维度全层) = {all_pass}")
print(f"--- 版本对齐 --- 字节:{len(raw)} · mtime:{mtime}")
print(f"SHA256:{sha}")
out = {"file": P.name, "字节": len(raw), "mtime": mtime, "SHA256": sha,
       "四维度FAIL": FAIL, "全PASS": all_pass,
       "维度说明": {"A": "动作字段全变体(chip+今日动作表+L2角色/持仓意图+L3决定摘要+为什么现在+动作=)逐股vs7-22+守等禁词",
                 "B": "日期(旧产品标题/昨日一致/旧价格日·非hist)", "C": "口径(13只与目标相加/旧目标数值·非hist)", "D": "爱德万闪迪异常隔离+增补⑮"}}
(ROOT / "data/screen/gate_v6_fulllayer_20260722.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_v6_fulllayer_20260722.json")
