#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段3退化硬闸(15项·对照724 且 对照阶段2)+新增清单+SHA/字节。只增不删→结构类须≥两基线。"""
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
STAGE3 = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
OUT = ROOT / "data/screen/stage3_augment_20260722.json"
MODMARK = {"机构底稿层": ["机构底稿", "底稿"], "规则附件6把尺": ["6把尺", "六把尺", "规则附件", "世界观", "战略地图"],
           "持仓完整档案": ["档案"], "组合层": ["组合层", "⑦组合"], "复盘记分卡": ["记分卡"], "安全线/能源线": ["安全线", "能源线"]}
STRUCT = ["大章节h1h2", "div模块", "图块data-chart", "details折叠", "锚点id", "跳转href#", "链接a", "标题h1h2h3", "表格table", "表行tr", "持仓候选(股数头)"]


def load(p):
    raw = p.read_bytes()
    return raw, raw.decode("utf-8", "replace")


def metrics(h, raw):
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S))
    js = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S)
    return {"字节": len(raw), "可见正文字符": len(plain), "大章节h1h2": len(re.findall(r"<h[12]\b", h)),
            "div模块": h.count("<div"), "图块data-chart": len(re.findall(r"data-chart", h)),
            "details折叠": len(re.findall(r"<details\b", h)), "锚点id": len(re.findall(r'\sid="[^"]+"', h)),
            "跳转href#": len(re.findall(r'href="#', h)), "链接a": len(re.findall(r"<a\b", h)),
            "标题h1h2h3": len(re.findall(r"<h[123]\b", h)), "表格table": h.count("<table"), "表行tr": h.count("<tr"),
            "持仓候选(股数头)": len(re.findall(r"</span> · [0-9,]+股（", h)), "证据链接http": len(re.findall(r"https?://", h)),
            "JS+CSS字节": sum(len(x) for x in js) + len(css)}


mraw, mh = load(MASTER)
s2raw, s2h = load(STAGE2)
s3raw, s3h = load(STAGE3)
mm, s2, s3 = metrics(mh, mraw), metrics(s2h, s2raw), metrics(s3h, s3raw)

rows, fails = [], []
for k in mm:
    ok_724 = (s3[k] >= mm[k]) if k in STRUCT else True
    ok_s2 = (s3[k] >= s2[k]) if k in STRUCT else True
    ok = ok_724 and ok_s2
    if not ok:
        fails.append(k)
    rows.append({"项": k, "724": mm[k], "阶段2": s2[k], "阶段3": s3[k], "vs724": s3[k] - mm[k], "vs阶段2": s3[k] - s2[k],
                 "规则": ("结构·须≥两基线" if k in STRUCT else "允许增"), "零退出": ok})

mod = []
for name, alts in MODMARK.items():
    inm = any(x in mh for x in alts); ins = any(x in s3h for x in alts)
    ok = ins or not inm
    if not ok:
        fails.append("模块:" + name)
    mod.append({"模块": name, "724": ("在" if inm else "无"), "阶段3": ("在" if ins else "缺"), "零退出": ok})


def titles(h):
    return set(re.sub("<[^>]+>", "", t).strip() for t in re.findall(r"<h[12][^>]*>(.*?)</h[12]>", h, re.S))


def norm(t):
    return re.sub(r"[0-9,]+股（[^）]*）", "股（）", re.sub(r"[0-9,.]+", "#", t))


# 阶段3 vs 724 消失(排除标题内数据更新)
tm, t3 = titles(mh), titles(s3h)
addn = {norm(a): a for a in (t3 - tm)}
vanished, data_upd = [], []
for v in sorted(tm - t3):
    (data_upd if norm(v) in addn else vanished).append(v)
mag_ok = s3["字节"] >= mm["字节"] * 0.8
mods = json.loads((ROOT / "data/screen/stage3_modules_20260722.json").read_text(encoding="utf-8"))["新增模块"]
all_pass = len(fails) == 0 and len(vanished) == 0 and mag_ok

doc = {
    "_说明": "阶段3退化硬闸(15项对照724且阶段2)+新增清单+SHA/字节。路径A·GPT裁定20260723。",
    "生成于": datetime.now(JST).isoformat(timespec="seconds"),
    "文件": {t: {"字节": len(r), "SHA256": hashlib.sha256(r).hexdigest(),
                "mtime": datetime.fromtimestamp(os.path.getmtime(p), JST).isoformat(timespec="seconds")}
             for t, r, p in [("724母版", mraw, MASTER), ("阶段2", s2raw, STAGE2), ("阶段3", s3raw, STAGE3)]},
    "字节链": {"724→阶段2": len(s2raw) - len(mraw), "阶段2→阶段3": len(s3raw) - len(s2raw), "724→阶段3": len(s3raw) - len(mraw)},
    "退化硬闸15项": rows,
    "关键模块存在": mod,
    "724有而阶段3真消失(章节)": vanished,
    "标题内数据更新(非退化)": data_upd,
    "体积量级闸(≥724×80%)": {"724": mm["字节"], "阶段3": s3["字节"], "通过": mag_ok},
    "新增模块清单(10项)": mods,
    "FAIL项": fails,
    "全通过(零退出+无消失+量级)": all_pass,
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

print("=== 阶段3 退化硬闸 15项(对照724且阶段2) ===")
for r in rows:
    print(f"  [{'零退出' if r['零退出'] else 'FAIL'}] {r['项'].ljust(15)} 724={str(r['724']).rjust(8)} 阶2={str(r['阶段2']).rjust(8)} 阶3={str(r['阶段3']).rjust(8)} vs724={r['vs724']:+} vs阶2={r['vs阶段2']:+}")
print("--- 模块 ---")
for r in mod:
    print(f"  [{'零退出' if r['零退出'] else 'FAIL'}] {r['模块'].ljust(14)} 724={r['724']} 阶段3={r['阶段3']}")
print(f"724有而真消失章节: {vanished if vanished else '无'}")
print(f"标题内数据更新(非退化): {len(data_upd)}项")
print(f"字节链: 724={len(mraw)} →阶2={len(s2raw)}(+{len(s2raw)-len(mraw)}) →阶3={len(s3raw)}(+{len(s3raw)-len(s2raw)})")
print(f"新增模块: {len(mods)}/10项")
print(f"FAIL项: {fails if fails else '无'}")
print(f"★全通过 = {all_pass}")
print("报告:", OUT)
