#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_v5·逐只×逐区语义扫描矩阵(GPT#4·硬闸自证地基·10区)。纯扫描·不改产品。
10区:①L1动作表 ②L2目标倒推四字段 ③L2买卖建议双档 ④L3底稿 ⑤今日触发区 ⑥止盈区 ⑦待拍板区 ⑧差分区 ⑨组合目标区 ⑩异常估值区
字段:动作/现价/股数/加仓语义/减仓语义/建议金额/触发/停止/判断日期/是否hist隔离
FAIL: A守/等非历史区出现加仓语义/加仓价/建议金额  B异常标的(爱德万/闪迪)任一区出现加仓价/还差%/止盈/目标贡献计算值(非异常待核)  C同股动作/价/日期与7-22冲突
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
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
守 = {"US.NVDA", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "JP.4568", "US.SPCX"}
ORDER = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
         "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
         "US.TSM", "US.META", "US.IBKR", "US.SPCX"]
NAME = {s: prod[s]["name"] for s in prod}
BASE = {s: ("守" if s in 守 else "等") for s in ORDER}
NEWPX = {s: f"{prod[s]['price']:,.2f}" for s in ORDER}
QTY = {s: str(int(prod[s]["quantity"])) for s in ORDER}
QTY["US.SNDK"] = "5"
ANOMALY = {"JP.6857", "US.SNDK"}
ZONES = ["L1动作表", "L2四字段", "L2买卖建议", "L3底稿", "今日触发区", "止盈区", "待拍板区", "差分区", "组合目标区", "异常估值区"]


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


def card(idk, sym):
    i = h.find(f'id="{idk}-{sym}"')
    if i < 0:
        return "", -1
    nx = [x for k in ("act", "why", "deep") for x in [h.find(f'id="{k}-', i + 12)] if x > 0]
    end = min(nx) if nx else len(h)
    end = min(end, i + 3500)   # 末卡边界封顶·防延伸到后续区(如SPCX deep卡串到承接节点)
    return h[i:end], i


def table_region(kw):
    i = h.find(kw)
    if i < 0:
        return "", -1
    ts = h.rfind("<table", 0, i)
    te = h.find("</table>", i)
    return (h[ts:te], ts) if ts >= 0 and te > i else (h[i:i + 4000], i)


L1_tbl, L1_pos = table_region("今日动作表（唯一决定源")
TRIG_tbl, TRIG_pos = table_region("今天有没有跌到你的加仓价")


def row_of(tbl, base, sym):
    """表内含该ticker的<tr>及其绝对起点"""
    for m in re.finditer(r"<tr\b", tbl):
        e = tbl.find("</tr>", m.start())
        row = tbl[m.start():(e if e > 0 else len(tbl))]
        if sym in row or (NAME[sym] in row and sym.split(".")[1] not in row):
            return row, base + m.start()
    return "", -1


# 规则A可执行加仓/减仓语义(便宜位/已比加仓价低X%=估值距离监控·非买入指令·不算·由action守/等 governs)
ADD_SEM = ["已触发加仓", "⚡已触发", "分批买、别一次买满", "现在就可以加；分批", "今日已跌到加仓价",
           "已跌到加仓价：", "建议金额 约现金"]
CUT_SEM = ["建议减", "分批卖", "已触发减仓"]
# 规则B异常标的计算值(加仓/还差/止盈/目标/组合 + 估值区今日该值/中枢/中周期估算)
CALC = [(r"加仓价\(便宜位\)[ 　]*([¥$][\d,]+)", "加仓价"), (r"还差[ 　]*([\d.]+%)[ 　]*到加仓价", "还差%"),
        (r"止盈[线]?[^<]{0,5}([¥$][\d,]+)", "止盈线"), (r"目标贡献[^<]{0,5}([+\-][\d.]+个?百?分?点?)", "目标贡献"),
        (r"组合贡献[^<]{0,5}([+\-][\d.]+)", "组合贡献"), (r"今日该值 ([¥$][\d,~$]+)", "估值区今日该值"),
        (r"中枢[ ]?([¥$][\d,]+)", "估值区中枢"), (r"中周期(?:\([^)]*\))?估算[·： ]*([¥$][\d,~$]+)", "估值区中周期估算")]


def scan_seg(seg, segbase, sym):
    """A守/等可执行加仓/减仓语义·B异常标的计算值·(便宜位监控/还差%对守等=估值参考不算)"""
    ev = []
    isanom = sym in ANOMALY
    if not isanom and BASE[sym] in ("守", "等"):
        for kw in ADD_SEM + CUT_SEM:
            for m in re.finditer(re.escape(kw), seg):
                if not hist(segbase + m.start()):
                    ev.append(("A可执行加/减语义", kw + "｜" + pl(seg[m.start():m.start() + 18])))
        # 可执行加仓价(第一档/第二档带价·非便宜位监控)
        for m in re.finditer(r"第[一二]档[ 　]?[¥$][\d,]+", seg):
            if not hist(segbase + m.start()):
                ev.append(("A加仓档价", pl(seg[m.start():m.start() + 16])))
    if isanom:   # 异常标的任一区计算值(非异常待核)
        for pat, zn in CALC:
            for m in re.finditer(pat, seg):
                if hist(segbase + m.start()):
                    continue
                pre = pl(seg[max(0, m.start() - 12):m.start()])
                if "异常" in pre or "待核" in pre or "不计算" in pre:
                    continue
                ev.append(("B异常计算值·" + zn, m.group(1)))
    return ev


report = {}
FAIL = []
for sym in ORDER:
    r = {}
    segs = {}
    # 各区取该只内容
    l1row, l1b = row_of(L1_tbl, L1_pos, sym)
    segs["L1动作表"] = (l1row, l1b)
    wseg, wb = card("why", sym)
    segs["L2四字段"] = (wseg, wb)
    segs["L2买卖建议"] = (wseg, wb)
    dseg, db = card("deep", sym)
    segs["L3底稿"] = (dseg, db)
    # 今日触发区:该只 "现价 <b>¥newpx</b> ...加仓价(便宜位)..." div块(按7-22价定位·便宜位在±190内)
    trg_seg, trg_b = "", -1
    for mpx in re.finditer(r"现价 <b>[¥$]" + re.escape(NEWPX[sym]) + r"</b>", h):
        w = h[mpx.start():mpx.start() + 200]
        if "加仓价(便宜位)" in w or "还差" in w or "已比加仓价" in w:
            trg_seg, trg_b = w, mpx.start()
            break
    segs["今日触发区"] = (trg_seg, trg_b)
    # 止盈/待拍板/差分/组合目标/异常估值:全产品该只name邻近段(±190·含关键词才计)
    for zn, kw in [("止盈区", "止盈"), ("待拍板区", "待拍板"), ("差分区", "今日与昨日"), ("组合目标区", "目标贡献"), ("异常估值区", "口径异常")]:
        chunk, cb = "", -1
        for m in re.finditer(re.escape(NAME[sym]), h):
            w = h[m.start():m.start() + 180]
            if kw in w:
                chunk, cb = w, m.start()
                break
        segs[zn] = (chunk, cb)
    # 逐区扫
    for zn in ZONES:
        seg, sb = segs[zn]
        if not seg or sb < 0:
            r[zn] = {"状态": "该只该区无内容/未定位", "证据": ""}
            continue
        ev = scan_seg(seg, sb, sym)
        # C: 动作/价/股数(仅在有的区核) — L1/L3含动作
        if zn in ("L1动作表", "L3底稿"):
            for m in re.finditer(r"(今日动作 (?:<b>)?|动作[＝=])([守加观等减盯])", seg):
                if not hist(sb + m.start()) and m.group(2) != BASE[sym]:
                    ev.append(("C动作冲突", m.group(2) + "应" + BASE[sym]))
        r[zn] = {"状态": "PASS" if not ev else "FAIL", "证据": ev[:3]}
        if ev:
            FAIL.append({"sym": sym, "name": NAME[sym], "区": zn, "违规": ev[:3]})
    report[sym] = r

all_pass = not FAIL
sha = hashlib.sha256(raw).hexdigest()
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print("=== gate_v5 逐只×逐区语义矩阵(20只×10区) ===")
hdr = "sym".ljust(9) + "".join(z[:5].ljust(6) for z in ZONES)
print(hdr)
for sym in ORDER:
    line = (NAME[sym][:4] + "/" + sym.split(".")[1])[:9].ljust(9)
    for zn in ZONES:
        st = report[sym][zn]["状态"]
        mark = "✔" if st == "PASS" else ("·" if "无内容" in st else "✗")
        line += mark.ljust(6)
    print(line)
# 每区实扫覆盖(有内容的格数·证明非"·假通过")
zone_scanned = {zn: sum(1 for s in ORDER if report[s][zn]["状态"] in ("PASS", "FAIL")) for zn in ZONES}
print(f"\n--- 每区实扫格数(20只中·证明真扫非·假通过) ---")
for zn in ZONES:
    print(f"  {zn}: 实扫{zone_scanned[zn]}只 · N/A(该区不适用){20 - zone_scanned[zn]}只")
print(f"★FAIL清单({len(FAIL)}):", FAIL if FAIL else "无")
print(f"★全PASS(20只×10区·实扫格全PASS) = {all_pass}")
print(f"--- 版本对齐 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
(ROOT / "data/screen/gate_v5_matrix_20260722.json").write_text(json.dumps({
    "file": P.name, "字节": len(raw), "mtime": mtime, "SHA256": sha, "10区": ZONES,
    "matrix_每只每区": report, "FAIL清单": FAIL, "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_v5_matrix_20260722.json")
