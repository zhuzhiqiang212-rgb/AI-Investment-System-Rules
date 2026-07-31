#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_v5·一次性语义覆盖全部10区(GPT#4·别再一区一区补)。逐股逐区扫。
10区:L1动作表/L2目标倒推四字段/L2买卖建议双档/L3底稿/今日触发区(加仓触发)/止盈区/待拍板区/差分区/组合目标区/异常估值区。
规则①守/等 非历史区出现"已触发加仓/分批买/现金比例加仓/现在就可以加" → FAIL。
规则②异常标的(爱德万/闪迪) 任一区仍出现 加仓价/还差X%/止盈线/目标贡献/组合贡献 计算值(非'异常待核') → FAIL。
输出SHA。
"""
import hashlib
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
NAME = {"JP.6857": "爱德万", "US.SNDK": "闪迪"}


def hist(pos):
    return h.rfind('class="hist-iso"', 0, pos) > h.rfind("</details>", 0, pos)


def pl(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s)).strip()


FAIL = {"规则①守等加仓语义": [], "规则②异常标的计算值": []}

# ---------- 规则① 守/等 加仓语义(全产品·非hist·可执行加仓词) ----------
for kw in ["已触发加仓", "⚡已触发", "分批买、别一次买满", "现在就可以加；分批", "今日已跌到加仓价", "已跌到加仓价："]:
    for m in re.finditer(re.escape(kw), h):
        if not hist(m.start()):
            FAIL["规则①守等加仓语义"].append({"词": kw, "样本": pl(h[m.start():m.start() + 26])})
            break

# ---------- 规则② 异常标的(爱德万/闪迪) 任一区计算值残留 ----------
# 2a 已知异常token
for tok in ["¥2,646", "¥2,940", "¥2,938", "¥3,234", "939.5%", "$35~95", "35~95"]:
    for m in re.finditer(re.escape(tok), h):
        if not hist(m.start()):
            FAIL["规则②异常标的计算值"].append({"类": "异常token", "token": tok, "样本": pl(h[m.start() - 10:m.start() + 12])})
            break
# 2b 爱德万/闪迪 邻近 加仓价/还差%/止盈/目标贡献/组合贡献 带LIVE数值(非[异常/待核])
ZONE = [(r"加仓价\(便宜位\)[ 　]*([¥$][\d,]+)", "今日触发区加仓价"),
        (r"还差[ 　]*([\d.]+%)[ 　]*到加仓价", "今日触发区还差%"),
        (r"止盈[线]?[^<]{0,6}([¥$][\d,]+)", "止盈区"),
        (r"目标贡献[^<]{0,6}([+\-][\d.]+)", "目标贡献区"),
        (r"组合贡献[^<]{0,6}([+\-][\d.]+)", "组合目标区")]
for tk, who in NAME.items():
    for m in re.finditer(re.escape(who), h):
        if hist(m.start()):
            continue
        win = h[m.start():m.start() + 160]
        wbase = m.start()
        for pat, zone in ZONE:
            mm = re.search(pat, win)
            if mm and not hist(wbase + mm.start()):
                val = mm.group(1)
                # 异常待核标注视为已退出
                ctx = win[max(0, mm.start() - 12):mm.start()]
                if "异常" in ctx or "待核" in ctx or "不计算" in ctx:
                    continue
                FAIL["规则②异常标的计算值"].append({"who": who, "区": zone, "值": val, "样本": pl(win[:44])})

all_pass = all(not v for v in FAIL.values())
sha = hashlib.sha256(raw).hexdigest()
mtime = datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds")
print("=== gate_v5 · 全10区语义扫描 ===")
for k, v in FAIL.items():
    print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v if v else '无'}")
print(f"★全PASS(10区语义) = {all_pass}")
print(f"--- 版本对齐 --- 字节:{len(raw)} · mtime:{mtime} · SHA256:{sha}")
import json
(ROOT / "data/screen/gate_v5_10zones_20260722.json").write_text(json.dumps({
    "file": P.name, "字节": len(raw), "mtime": mtime, "SHA256": sha,
    "10区": ["L1动作表", "L2目标倒推四字段", "L2买卖建议双档", "L3底稿", "今日触发区", "止盈区", "待拍板区", "差分区", "组合目标区", "异常估值区"],
    "两规则FAIL": FAIL, "全PASS": all_pass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/gate_v5_10zones_20260722.json")
