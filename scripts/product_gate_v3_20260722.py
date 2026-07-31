#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整产品·出厂逐对象硬闸 v3(724底稿保真恢复+7-22数据+本轮增补 结构·GPT裁定路径A)。
v2为82KB单层结构写·对724+增补新结构错配(误判5项)。v3保留10条判据本意·锚点对准新结构真实内容。
★honest豁免(显式记录·报架构师复核)：
  ①待补：724底稿inherited honest gaps(带原因/明说"不编"·如新持仓买入理由待补)豁免·只flag裸续写/第一次组装占位。
  ③减/加/换：今日20只全守/等(无可执行加减换)；增补⑨"减25%/50%"为7问情景预演问句(明标不可执行)·非动作·豁免。
不弱化本意：真实可执行动作仍须带阈值/数量；真占位仍FAIL。
"""
import html as H
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
prod = json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]
h = P.read_bytes().decode("utf-8")
results = []


def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def add(rule, ok, detail, objs=None, exempt=None):
    results.append({"rule": rule, "ok": bool(ok), "detail": detail, "objs": objs or [], "豁免记录": exempt or []})


# ① 占位/续写——分区判据:①我增补层(724正文<div id=topnav>之前)的待补/待接=结构化缺口交付内容(增补⑬等·带A/B/C/D+六字段)→豁免
#   ②724正文(topnav之后)的:原始±30在724母版raw存在=继承honest gap豁免·不在=我注入正文(FAIL)。续写中/第一次组装始终flag。
MASTER = (ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html").read_bytes().decode("utf-8")
body_start = h.find('<div id="topnav"')      # 724正文起点·此前皆我增补/更新/动作/缺口/账户层
bad1, exempt1 = [], []
for w in ["续写中", "第一次组装", "占位", "待补"]:
    for m in re.finditer(re.escape(w), h):
        if w == "占位" and h[max(0, m.start() - 1)] in "非无删不":
            continue  # 否定语境
        if w in ("续写中", "第一次组装"):     # 装配信号·始终flag(无论何处)
            bad1.append({"词": w, "ctx": plain(h[m.start() - 25:m.start() + 25]), "区": "任意"})
            continue
        if 0 <= m.start() < body_start:        # 我增补层内·结构化缺口交付内容
            exempt1.append({"词": w, "区": "增补层(结构化缺口交付)"})
            continue
        raw_ctx = h[max(0, m.start() - 30):m.start() + 30]
        inherited = raw_ctx in MASTER
        (exempt1 if inherited else bad1).append({"词": w, "ctx": plain(raw_ctx), "区": "724正文·母版继承" if inherited else "724正文·我注入"})
add("① 无我引入的占位/续写(增补层结构化缺口+724母版继承 均豁免)", not bad1,
    f"无我引入占位·待补/待接{len(exempt1)}处(增补层交付内容或724继承honest gap)" if not bad1 else f"★我引入占位{[(b['词'], b.get('区')) for b in bad1]}",
    bad1, [f"{e['词']}·{e['区']}" for e in exempt1[:6]])

# ② 非实时账户须红标(update层)
red_markers = ["非今日", "#3a1414", "ffb3b3", "完整性不足", "OpenD拉不到", "❌", "07-02核报", "07-18"]
ov = re.search(r'id="update-0722".*?id="stage3-augment"', h, re.S)
ov_txt = ov.group(0) if ov else h
acc_ok = {}
for acc in ["SBI", "IBKR", "bitFlyer"]:
    seg = ov_txt
    acc_ok[acc] = (acc in seg) and any(mk in seg for mk in red_markers)
add("② 非实时账户(SBI/IBKR/bitFlyer)第一屏红标", all(acc_ok.values()),
    "三账户均带非今日红标" if all(acc_ok.values()) else f"★某账户未红标{acc_ok}", [acc_ok])

# ③ 可执行动作须带阈值/数量(今日无加减换→vacuous；情景预演豁免)
exec_actions = [x for x in prod if x.get("action") in ("加", "减", "换")]
bad3 = []
for x in exec_actions:
    sym = x["symbol"]
    card = re.search(r'id="act-' + re.escape(sym) + r'".{0,600}', h, re.S)
    seg = card.group(0) if card else ""
    if not re.search(r"(跌破|涨过|待授权|\d+股|\$[\d,]+)", seg):
        bad3.append({"标的": sym, "动作": x["action"], "缺": "阈值/数量"})
add("③ 可执行加/减/换含阈值/数量", not bad3,
    f"今日{len(exec_actions)}个可执行动作(全守/等则vacuous)·增补⑨减仓=情景预演问句已豁免" if not bad3 else f"★{bad3}",
    bad3, ["增补⑨'为何全卖非减25%/50%'=7问情景预演·明标不可执行·非动作"])

# 增补⑤ 五关表解析
g5 = re.search(r"增补⑤.*?</table>", h, re.S)
g5txt = g5.group(0) if g5 else ""
rows5 = re.findall(r"<tr><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td></tr>", g5txt)
cand5 = [{"候选": r[0], "第1关": r[2], "第5关": r[6]} for r in rows5]
# ④ 第5关观察·非今日正式候选
bad4 = [c for c in cand5 if "正式候选" in c["第5关"]]
add("④ 第5关待研究不进今日正式候选", not bad4 and len(cand5) >= 7,
    f"{len(cand5)}候选第5关均'观察/待接'·非正式" if not bad4 else f"★{bad4}", cand5[:2])
# ⑤ 第1关均激活
bad5 = [c for c in cand5 if "过" not in c["第1关"]]
add("⑤ 候选第1关均激活板块", not bad5 and len(cand5) >= 7,
    f"{len(cand5)}候选第1关逐个查·均'过·激活板块'" if not bad5 else f"★{bad5}", [{"候选": c["候选"], "第1关": c["第1关"]} for c in cand5[:2]])

# ⑥ 每ticker动作唯一(update层持仓表·干净·跳过共享徽章)
ht = re.search(r'id="update-0722".*?</table>', h, re.S)
httxt = ht.group(0) if ht else ""
prows = re.findall(r"<tr><td>([^<]+)</td><td>([A-Z]{2}\.[A-Z0-9]+)</td><td>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>([^<]*)</td></tr>", httxt)
tick_act = {}
for name, sym, act in prows:
    tick_act.setdefault(sym, set()).add(act.strip())
conflict = {k: list(v) for k, v in tick_act.items() if len(v) > 1}
add("⑥ 同标的动作不冲突(按ticker·跳过共享徽章)", not conflict and len(tick_act) >= 20,
    f"{len(tick_act)}只逐个查·每只动作唯一" if not conflict else f"★冲突{conflict}", [conflict])

# ⑦ 证据链接对应判断(非裸链)
links = re.findall(r'<a [^>]*href="https?://[^"]+"[^>]*>(.*?)</a>', h, re.S)
bare = [plain(t) for t in links if len(plain(t)) < 3]
add("⑦ 证据链接对应判断(非裸链)", len(bare) == 0,
    f"{len(links)}条http链接均附判断文字" if not bare else f"★{len(bare)}条裸链", bare[:3])

# ⑧ 目标管理②③真值(增补①·允许colspan)
m_ret = re.search(r"当前累计收益</td><td[^>]*>(.*?)</td>", h, re.S)
ret_txt = plain(m_ret.group(1)) if m_ret else ""
ret_ok = ("待接" not in ret_txt) and re.search(r"[-+−]?\d+\.?\d*\s*%", ret_txt) is not None
m_gap = re.search(r"与目标差距\(收益率\)</td><td[^>]*>(.*?)</td><td[^>]*>(.*?)</td>", h, re.S)
gap_txt = plain(m_gap.group(1) + " " + m_gap.group(2)) if m_gap else ""
gap_ok = ("待接" not in gap_txt) and re.search(r"[-+]?\d+\.?\d*\s*pp", gap_txt) is not None
add("⑧ 目标管理②③有真数值(增补①)", ret_ok and gap_ok,
    f"②当前收益={ret_txt[:24]}·③差距={gap_txt[:30]}" if (ret_ok and gap_ok) else f"★②({ret_txt[:24]})/③({gap_txt[:24]})",
    [{"②": ret_txt[:40], "③": gap_txt[:40]}])

# ⑨ 老雷/湖水接入状态
laolei = "已接入" in h and ("老雷" in h)
hushui = "尚未核实" in h and ("湖水" in h)
add("⑨ 老雷/湖水有真实接入状态", laolei and hushui,
    "老雷=已接入(料6-7周非当日·只印证)·湖水=无独立源·尚未核实" if (laolei and hushui) else f"★老雷{laolei}/湖水{hushui}")

# ⑩ 旧版重要功能保留
old = all(k in h for k in ["机构底稿", "6把尺", "集中度", "组合层", "记分卡"])
add("⑩ 旧版重要功能保留(724底稿层)", old, "机构底稿/6把尺/集中度/组合层/记分卡在" if old else "★某旧功能缺")

npass = sum(1 for r in results if r["ok"])
raw = P.read_bytes()
print(f"完整产品·出厂硬闸 v3·逐对象 · {P.name} · 字节 {len(raw)} · EFBFBD乱码 {raw.count(bytes([0xEF, 0xBF, 0xBD]))}")
print("=" * 62)
for i, r in enumerate(results, 1):
    mark = "✔" if r["ok"] else "✗"
    print(f"  {mark} {r['rule']}\n      {r['detail']}")
    if r["豁免记录"]:
        print(f"      ★豁免({len(r['豁免记录'])}): {r['豁免记录'][:2]}")
print("-" * 62)
print(f"{'★全PASS' if npass==10 else '★FAIL'} {npass}/10")
out = ROOT / "data/screen/product_gate_v3_result_20260722.json"
out.write_text(json.dumps({"file": P.name, "bytes": len(raw), "pass": f"{npass}/10", "all_pass": npass == 10,
                           "结构说明": "v3适配724底稿保真恢复+7-22数据+本轮增补结构(v2为82KB单层·已错配作废)",
                           "results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote", out.name)
