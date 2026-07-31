#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2·退化硬闸(15项对照724) + 数据更新清单ABC + SHA/字节。
判定：结构类计数任一 < 724 → 退出FAIL(须逐项报GPT裁定)；正文字符/字节允许增(加更新层)。"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
MASTER = ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html"
STAGE2 = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段2数据更新.html"
OUT = ROOT / "data/screen/stage2_dataupdate_20260722.json"
MODMARK = {"机构底稿层": ["机构底稿", "底稿"], "规则附件6把尺": ["6把尺", "六把尺", "规则附件", "世界观", "战略地图"],
           "持仓完整档案": ["档案"], "组合层": ["组合层", "⑦组合"], "复盘记分卡": ["记分卡"], "安全线/能源线": ["安全线", "能源线"]}


def load(p):
    raw = p.read_bytes()
    return raw, raw.decode("utf-8", "replace")


def metrics(h, raw):
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S))
    js = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S)
    return {
        "字节": len(raw),
        "可见正文字符": len(plain),
        "大章节h1h2": len(re.findall(r"<h[12]\b", h)),
        "div模块": h.count("<div"),
        "图块data-chart": len(re.findall(r"data-chart", h)),
        "details折叠": len(re.findall(r"<details\b", h)),
        "锚点id": len(re.findall(r'\sid="[^"]+"', h)),
        "跳转href#": len(re.findall(r'href="#', h)),
        "链接a": len(re.findall(r"<a\b", h)),
        "标题h1h2h3": len(re.findall(r"<h[123]\b", h)),
        "表格table": h.count("<table"),
        "表行tr": h.count("<tr"),
        "持仓候选(股数头)": len(re.findall(r"</span> · [0-9,]+股（", h)),
        "证据链接http": len(re.findall(r"https?://", h)),
        "JS+CSS字节": sum(len(x) for x in js) + len(css),
    }


mraw, mh = load(MASTER)
sraw, sh = load(STAGE2)
mm, sm = metrics(mh, mraw), metrics(sh, sraw)

# 结构类(必须 >=724·退出即FAIL)；字节/正文允许增
STRUCT = ["大章节h1h2", "div模块", "图块data-chart", "details折叠", "锚点id", "跳转href#", "链接a", "标题h1h2h3", "表格table", "表行tr", "持仓候选(股数头)"]
GROW_OK = ["字节", "可见正文字符", "证据链接http", "JS+CSS字节"]
rows = []
fails = []
for k in mm:
    a, b = mm[k], sm[k]
    if k in STRUCT:
        ok = b >= a
        rule = "结构·须≥724"
    else:
        ok = True  # 允许增/技术字段
        rule = "允许增(加更新层)"
    if not ok:
        fails.append(k)
    rows.append({"项": k, "724": a, "阶段2": b, "差": b - a, "规则": rule, "零退出": ok})

# 模块存在
mod = []
for name, alts in MODMARK.items():
    inm = any(x in mh for x in alts)
    ins = any(x in sh for x in alts)
    ok = ins or not inm
    if not ok:
        fails.append("模块:" + name)
    mod.append({"模块": name, "724": ("在" if inm else "无"), "阶段2": ("在" if ins else "缺"), "零退出": ok})

# 724有而阶段2消失 / 阶段2新增(章节标题级)
def titles(h):
    return set(re.sub("<[^>]+>", "", t).strip() for t in re.findall(r"<h[12][^>]*>(.*?)</h[12]>", h, re.S))
t_m, t_s = titles(mh), titles(sh)
raw_vanished = sorted(t_m - t_s)
raw_added = sorted(t_s - t_m)


def norm(t):  # 抹去股数/数字,判断是否"同一章节·仅数据字段更新"
    return re.sub(r"[0-9,]+股（[^）]*）", "股（）", re.sub(r"[0-9,.]+", "#", t))


added_norm = {norm(a): a for a in raw_added}
vanished = []          # 真消失(无对应新增)
title_data_updates = []  # 标题内数据更新(消失↔新增配对)
for v in raw_vanished:
    if norm(v) in added_norm:
        title_data_updates.append({"旧标题": v, "新标题": added_norm[norm(v)]})
    else:
        vanished.append(v)
paired = {u["新标题"] for u in title_data_updates}
added = [a for a in raw_added if a not in paired]

# ABC 清单
ch = json.loads((ROOT / "data/screen/stage2_changes_20260722.json").read_text(encoding="utf-8"))

all_pass = len(fails) == 0 and len(vanished) == 0
# 体积量级闸：阶段2不得显著低于724(<80%即FAIL)
mag_ok = sm["字节"] >= mm["字节"] * 0.8

doc = {
    "_说明": "阶段2退化硬闸(15项对照724)+数据更新ABC+SHA/字节。路径A·GPT裁定20260723。",
    "生成于": datetime.now(JST).isoformat(timespec="seconds"),
    "文件": {
        "724母版": {"字节": len(mraw), "SHA256": hashlib.sha256(mraw).hexdigest(), "mtime": datetime.fromtimestamp(os.path.getmtime(MASTER), JST).isoformat(timespec="seconds")},
        "阶段2产物": {"路径": str(STAGE2), "字节": len(sraw), "SHA256": hashlib.sha256(sraw).hexdigest(), "mtime": datetime.fromtimestamp(os.path.getmtime(STAGE2), JST).isoformat(timespec="seconds")},
        "字节差(阶段2-724)": len(sraw) - len(mraw),
    },
    "退化硬闸15项": rows,
    "关键模块存在": mod,
    "724有而阶段2真消失(章节)": vanished,
    "标题内数据更新(消失↔新增配对·非退化)": title_data_updates,
    "阶段2真新增(章节)": added,
    "体积量级闸(≥724×80%)": {"724字节": mm["字节"], "阶段2字节": sm["字节"], "通过": mag_ok},
    "数据更新清单ABC": {
        "A_724有且7-22未变": ch["ABC"]["A"],
        "B_724有但7-22变化(已更新)": ch["ABC"]["B"],
        "C_724确实没有(标注不编)": ch["ABC"]["C"],
    },
    "变更逐条": ch["changes"],
    "FAIL项": fails,
    "全通过(零退出+无消失+量级)": all_pass and mag_ok,
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

print("=== 阶段2 退化硬闸 15项(对照724) ===")
for r in rows:
    print(f"  [{'零退出' if r['零退出'] else 'FAIL'}] {r['项'].ljust(16)} 724={str(r['724']).rjust(8)} 阶段2={str(r['阶段2']).rjust(8)} 差={r['差']:+} ({r['规则']})")
print("--- 模块 ---")
for r in mod:
    print(f"  [{'零退出' if r['零退出'] else 'FAIL'}] {r['模块'].ljust(14)} 724={r['724']} 阶段2={r['阶段2']}")
print(f"724有而真消失章节: {vanished if vanished else '无'}")
print(f"标题内数据更新(非退化): {[u['旧标题'].split('·')[0].strip()+':'+re.sub(chr(60)+'[^'+chr(62)+']*'+chr(62),'',u['旧标题'])[-14:]+'→'+u['新标题'][-14:] for u in title_data_updates] if title_data_updates else '无'}")
print(f"阶段2真新增章节: {added if added else '无(更新层用div非h1h2)'}")
print(f"体积量级闸: 724={mm['字节']} 阶段2={sm['字节']} 通过={mag_ok}")
print(f"ABC: A={len(ch['ABC']['A'])}项 B={len(ch['ABC']['B'])}项 C={len(ch['ABC']['C'])}项")
print(f"FAIL项: {fails if fails else '无'}")
print(f"★全通过 = {all_pass and mag_ok}")
print("报告:", OUT)
