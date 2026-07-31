#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐股全节点硬闸 v4(GPT验收退回:硬闸不得只读顶部统一表·须逐股扫全部节点)。
逐股扫全产品:①所有『现价/现在』价 →须唯一7-22 ②所有动作显示(chip+决定摘要动作+为什么现在X)→须唯一7-22
③旧日期(2026-07-19标题/07-17/07-18当日语境) ④异常估值隔离(爱德万/闪迪)。
同股两不同当日价 或 两不同当日动作 → FAIL。不只读顶部表。
"""
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
ACT722 = {"US.NVDA": "守", "US.AVGO": "守", "US.TSM": "守", "JP.6857": "守", "JP.9984": "守", "JP.4568": "守", "US.SPCX": "守",
          "US.MSFT": "等", "US.META": "等", "US.COIN": "等", "US.IBKR": "等", "JP.6758": "等", "JP.7203": "等",
          "JP.8001": "等", "JP.7832": "等", "JP.7974": "等", "US.SNDK": "等", "US.MSTR": "等·盯",
          "JP.8766": "等·待核", "US.CRCL": "等·待核"}   # GPT#4:改建议减→等·待核实(无卖出决定)
NAME = {s: prod[s]["name"] for s in prod}
h = P.read_bytes().decode("utf-8")


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def hist(pos):
    """位置pos是否在某未闭合hist-iso历史隔离折叠内(作废档豁免)"""
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def card(idkey, sym):
    """取该只 act/why/deep 卡片HTML段+起点(到下一个卡锚)"""
    i = h.find(f'id="{idkey}-{sym}"')
    if i < 0:
        return "", -1
    nxts = [x for k in ("act", "why", "deep") for x in [h.find(f'id="{k}-', i + 12)] if x > 0]
    end = min(nxts) if nxts else len(h)
    return h[i:end], i


# 每股所有『现价/现在』价
def prices_of(name):
    vals = set()
    for m in re.finditer(r"现[价在][ 　]?[¥$]([0-9,]+(?:\.\d+)?)", h):
        # 判断这个现价属于哪只:往前360字找name/ticker
        pre = plain(h[max(0, m.start() - 400):m.start()])
        if name in pre[-40:] or name in pre[-80:]:
            vals.add(m.group(1))
    return vals


report = {}
price_fail, act_fail = [], []
for sym, want_act in ACT722.items():
    name = NAME[sym]
    new_price = f"{prod[sym]['price']:,.2f}"
    # 现价:全产品该股name邻近的现价值集合
    pv = set()
    for m in re.finditer(r"现[价在][ 　]?[¥$]([0-9,]+(?:\.\d+)?)", h):
        pre = plain(h[max(0, m.start() - 300):m.start()])
        if name in pre[-30:]:
            pv.add(re.sub(r"\.00$", "", m.group(1)))
    pv_norm = {re.sub(r"\.00$", "", v) for v in pv}
    want_norm = re.sub(r"\.00$", "", new_price)

    def _same(v):   # 接受精确值或整数四舍五入(叙述里≈现价·同为7-22价)
        try:
            return v == want_norm or round(float(v.replace(",", ""))) == round(prod[sym]["price"])
        except ValueError:
            return v == want_norm
    price_ok = (not pv_norm) or all(_same(v) for v in pv_norm)
    if not price_ok:
        price_fail.append({"sym": sym, "现价集合": list(pv_norm), "应=": want_norm})
    report[sym] = {"现价集合": sorted(pv_norm), "应7-22": want_norm, "价一致": price_ok, "应动作": want_act}

# 动作chip一致性(按所在<tr>内ticker优先归属·卡内nearest id/±400兜底·非hist·修v4老逻辑act-id在行末串行bug)
GLYPH = {"守": "■ 守", "等": "… 等", "等·盯": "◉ 等·盯", "等·待核": "… 等·待核"}
idpos = [(m.start(), m.group(1)) for m in re.finditer(r'id="(?:act|why|deep)-([A-Z]{2}\.[A-Z0-9]+)"', h)]
chipseen = {}
for m in re.finditer(r'<span class="chip (c-add|c-wait|c-hold|c-risk)">([^<]{1,14})</span>', h):
    g = m.group(2).strip()
    if g == "⚠ 险":
        continue
    pos = m.start()
    if hist(pos):
        continue
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
    if tk in ACT722:
        chipseen.setdefault(tk, set()).add(g)
for sym, want in ACT722.items():
    seen = chipseen.get(sym, set())
    want_glyph = GLYPH[want]
    ok = (not seen) or (seen == {want_glyph})
    report[sym]["chip集合"] = list(seen)
    report[sym]["动作一致"] = ok
    if not ok:
        act_fail.append({"sym": sym, "chip集合": list(seen), "应=": want_glyph})

# ========== L2/L3 逐股扫(GPT验收退回核心:硬闸须证L2/L3·非只chip) ==========
l2l3_fail = []
PRICE_RX = re.compile(r"第[一二]档[ 　]?[$¥][\d,.]+")
for sym, want_act in ACT722.items():
    base = "守" if want_act == "守" else "等"   # 文字动作基字(等·盯/等·待核均属等)
    # ① L2「目标倒推·四字段」角色/持仓意图(why卡·非hist折叠)
    wseg, wpos = card("why", sym)
    l2f = []
    for m in re.finditer(r"角色 (待建仓|建仓)", wseg):
        if not hist(wpos + m.start()):
            l2f.append("角色·" + m.group(1))
    for m in re.finditer(r"为什么现在([守加观等减盯])", wseg):
        if not hist(wpos + m.start()) and m.group(1) != base:
            l2f.append("为什么现在" + m.group(1) + "(应" + base + ")")
    for m in PRICE_RX.finditer(wseg):
        if not hist(wpos + m.start()):
            l2f.append("加仓价·" + m.group())
    # ② L2「买卖建议·双档」当日正文(hist折叠内作废档豁免)
    l2b = []
    for m in re.finditer(r"建议金额 约现金|【中性档|【激进档|建仓·约现金", wseg):
        if not hist(wpos + m.start()):
            l2b.append(plain(wseg[m.start():m.start() + 14]))
    # ③ L3「完整研究底稿」今日动作/动作=/加仓价(deep卡·非hist)
    dseg, dpos = card("deep", sym)
    l3 = []
    for m in re.finditer(r"今日动作 (?:<b>)?([守加观等减盯])", dseg):
        if not hist(dpos + m.start()) and m.group(1) != base:
            l3.append("今日动作" + m.group(1) + "(应" + base + ")")
    for m in re.finditer(r"动作[＝=]([守加观等减盯])", dseg):
        if not hist(dpos + m.start()) and m.group(1) != base:
            l3.append("动作=" + m.group(1) + "(应" + base + ")")
    for m in PRICE_RX.finditer(dseg):
        if not hist(dpos + m.start()):
            l3.append("加仓价·" + m.group())
    for m in re.finditer(r"建议金额 约现金", dseg):
        if not hist(dpos + m.start()):
            l3.append("建议金额约现金")
    report[sym]["L2四字段一致"] = not l2f
    report[sym]["L2四字段证据"] = l2f
    report[sym]["L2买卖建议一致"] = not l2b
    report[sym]["L2买卖建议证据"] = l2b
    report[sym]["L3底稿一致"] = not l3
    report[sym]["L3底稿证据"] = l3
    if l2f or l2b or l3:
        l2l3_fail.append({"sym": sym, "L2四字段": l2f, "L2买卖建议": l2b, "L3底稿": l3})

# ========== 语义扫描(GPT复验#4:chip一致≠交易语义一致·须扫加仓语义/双价/异常) ==========
sem_fail = []
# ① 加仓语义(守/等·当日非hist出现"已触发加仓/已跌到加仓价/分批买满/现在就可以加/⚡已触发"→FAIL)
for kw in ["⚡已触发", "今日已跌到加仓价", "分批买、别一次买满", "现在就可以加；分批", "已跌到加仓价："]:
    body = [m.start() for m in re.finditer(re.escape(kw), h) if not hist(m.start())]
    if body:
        sem_fail.append({"类": "加仓语义(守/等禁)", "词": kw, "当日出现": len(body), "样本": plain(h[body[0]:body[0] + 24])})
# ② 双价(每只724旧价 在"现价/现在"当日语境·非历史stat·非hist → FAIL)
try:
    MST = (ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html").read_bytes().decode("utf-8")
    oldpx = {m.group(1): m.group(3) for m in re.finditer(r'([A-Z]{2}\.[A-Z0-9]+)</span></td>\s*<td data-l="现价"><b class="pxnow">([¥$])([^<]+)</b>', MST)}
    for sym, oldnum in oldpx.items():
        if sym not in ACT722:
            continue
        base = re.sub(r"\.00$", "", oldnum)
        for m in re.finditer(r"(现价|现在)[ 　约]{0,3}(?:<b>)?[¥$]" + re.escape(base) + r"(?:\.\d+)?", h):
            if not hist(m.start()):
                sem_fail.append({"类": "双价(旧现价当日)", "sym": sym, "旧价": base, "样本": plain(h[m.start():m.start() + 20])})
                break
except Exception as ex:
    sem_fail.append({"类": "双价扫描异常", "err": str(ex)})
# ③ 异常标的(爱德万/闪迪)估值/加仓价/止盈/目标贡献 仍参与计算(全产品·当日非hist)→FAIL
#    覆盖: 加仓触发区/止盈区/目标贡献区/差分区/估值区(GPT复验:不能只查deep卡·漏加仓触发区line3737)
for tok, desc in [("¥2,646", "爱德万拆股基准价"), ("¥2,940", "爱德万中间值"), ("¥3,234", "爱德万合理上沿"),
                  ("939.5%", "爱德万还差%"), ("$35~95", "闪迪中周期公允"), ("¥2,938", "爱德万PE推算")]:
    for m in re.finditer(re.escape(tok), h):
        if not hist(m.start()):
            sem_fail.append({"类": "异常标的计算值残留(非异常待核)", "token": tok, "说明": desc, "样本": plain(h[m.start() - 12:m.start() + 10])})
            break
for who in ["爱德万", "闪迪"]:
    for m in re.finditer(who + r"[^\n]{0,130}?加仓价\(便宜位\)[ 　]*[¥$][\d,]+", h):
        if not hist(m.start()):
            sem_fail.append({"类": "异常标的加仓触发区仍有加仓价数值", "who": who, "样本": plain(h[m.start():m.start() + 40])})
            break

# 旧日期(724当日语境·非历史research)
date_old = {kw: len([m.start() for m in re.finditer(re.escape(kw), h) if not hist(m.start())]) for kw in ["产品 · 2026-07-19", "价格对应交易日 <b>2026-07-17", "今日与昨日一致"]}
for kw, n in date_old.items():
    if n:
        sem_fail.append({"类": "旧日期当日语境", "词": kw, "当日": n})
# 异常隔离(爱德万/闪迪 是否已标价格口径异常待核)
anomaly = {"爱德万(6857)": "价格口径异常" in h or "口径异常待核" in h, "闪迪(SNDK)": "拆股" in h}

all_pass = not price_fail and not act_fail and not l2l3_fail and not sem_fail
import hashlib
import os
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
raw = P.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print("=== 逐股全节点硬闸 v4(含L2四字段/L2买卖建议/L3底稿) ===")
print(f"{'sym':<9}{'价一致':<7}{'chip一致':<8}{'L2四字段':<8}{'L2买卖':<7}{'L3底稿':<7}")
for sym in ACT722:
    r = report[sym]
    print(f"  {sym:<9}{str(r['价一致']):<7}{str(r.get('动作一致')):<8}{str(r.get('L2四字段一致')):<8}{str(r.get('L2买卖建议一致')):<7}{str(r.get('L3底稿一致')):<7}")
print("--- 旧日期(当日语境) ---", date_old, "· 异常隔离 ---", anomaly)
print(f"★价FAIL: {price_fail if price_fail else '无'}")
print(f"★动作chipFAIL: {act_fail if act_fail else '无'}")
print(f"★L2/L3FAIL(四字段/买卖建议/底稿): {l2l3_fail if l2l3_fail else '无'}")
print(f"★语义FAIL(加仓语义/双价/异常估值/旧日期): {sem_fail if sem_fail else '无'}")
print(f"★全PASS(价+chip+L2/L3+语义 逐股一致) = {all_pass}")
print(f"--- 版本对齐 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_v4_perstock_20260722.json").write_text(json.dumps({
    "file": P.name, "字节": len(raw), "mtime": mtime, "SHA256": sha,
    "per_stock": report, "价FAIL": price_fail, "动作chipFAIL": act_fail,
    "L2L3FAIL": l2l3_fail, "语义FAIL(加仓语义/双价/异常估值/旧日期)": sem_fail,
    "旧日期当日语境": date_old, "异常隔离": anomaly, "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_v4_perstock_20260722.json")
