#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径A·以724为冻结母版保真恢复★每日产品(GPT裁定2026-07-23)。

阶段1(本文件当前职责)：渲染路径读724母版 → 生成保真测试件 → 与724逐项零退出核对。
  render(master_text, phase="1", data=None) → 阶段1为恒等复刻(不装7-22数据·不加模块)。
  仅允许变化：生成时间等技术字段/无害空白缩进/经证明的无效重复代码。阶段1一律不动，保证零退出。
阶段2(保真过后才启用)：render(..., phase="2", data=<7-22>) 在既有槽位注入7-22数据，只增不删724原文。

★保真复刻未通过 → 不得装7-22数据、不得加新模块、不得申请验收。
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
MASTER = ROOT / "00_请先看这里" / "★每日产品_2026-07-19.html"          # 724冻结母版·唯一内容基底
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_保真测试件.html"    # 阶段1产物(与82KB送验件分离·不覆盖证据)
REPORT = ROOT / "data/screen/restore_faithful_report_20260722.json"


# ---------- 渲染路径 ----------
def render(master_text, phase="1", data=None):
    """阶段1=恒等复刻(零内容变换)。阶段2将在此扩展数据注入函数(只增不删)。"""
    if phase == "1":
        # 保真复刻：不做任何内容变换，母版原文即产物。
        # (生成时间技术字段/CSS去重虽被允许，但阶段1一律不启用，以取得干净的零退出证明。)
        return master_text
    raise NotImplementedError("阶段2数据注入待保真复刻通过后启用")


# ---------- 保真度量(15项·覆盖12核对+退化硬闸) ----------
def measure(text_or_bytes, raw_bytes):
    h = text_or_bytes
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
    b64 = re.findall(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", h)
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", h, re.S))
    js = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S)
    return {
        "HTML字节": len(raw_bytes),
        "可见正文字符": len(plain),
        "大章节h1h2": len(re.findall(r"<h[12]\b", h)),
        "div模块": h.count("<div"),
        "section": h.count("<section") + len(re.findall(r'class="sec"', h)),
        "图块(chart/canvas/svg痕迹)": len(re.findall(r"<canvas|chart|Chart\(|echarts|<svg", h)),
        "details折叠": h.count("<details"),
        "锚点跳转href#": len(re.findall(r'href="#', h)),
        "链接a": h.count("<a "),
        "标题h1h2h3": len(re.findall(r"<h[123]\b", h)),
        "表格table": h.count("<table"),
        "表行tr": h.count("<tr"),
        "锚点id": len(re.findall(r'id="[^"]+"', h)),
        "JS字节": sum(len(x) for x in js),
        "CSS字节": len(css),
        "base64图块数": len(b64),
    }


# 12项零退出核对(order 阶段1 ①-⑫)
CHECK12 = [
    ("①66大章节不减", "大章节h1h2"),
    ("②div模块不无故减", "div模块"),
    ("③section数不减", "section"),
    ("④338图块不减", "图块(chart/canvas/svg痕迹)"),
    ("⑤79 details折叠不减", "details折叠"),
    ("⑥309锚点跳转不减", "锚点跳转href#"),
    ("⑦链接数不减", "链接a"),
    ("⑧标题数不减", "标题h1h2h3"),
    ("⑨可见正文无大规模退出", "可见正文字符"),
    ("⑩机构底稿层/6把尺/持仓档案/组合层/记分卡/安全能源线全在", "__module__"),
    ("⑪一键展开/三层主色/层间跳转可用", "__interactive__"),
    ("⑫手机/电脑/断网打开能力不退化", "__portable__"),
]

# ⑩关键模块存在性(必须逐项在正文出现·724原有)
MODULE_MARKERS = {
    "机构底稿层": ["机构底稿", "底稿"],
    "规则附件6把尺": ["6把尺", "六把尺", "规则附件", "世界观", "战略地图", "资金流动"],
    "完整持仓档案": ["持仓", "档案"],
    "组合层": ["组合层", "⑦组合"],
    "复盘记分卡": ["记分卡", "复盘"],
    "安全线/能源线": ["安全线", "能源线"],
    "机会池": ["机会池"],
    "全市场五关漏斗": ["五关漏斗", "漏斗"],
}


def module_presence(h):
    res = {}
    for name, alts in MODULE_MARKERS.items():
        res[name] = any(a in h for a in alts)
    return res


def interactive_presence(h):
    return {
        "details一键展开": h.count("<details") > 0,
        "三层主色(CSS类)": bool(re.search(r"class=\"[^\"]*(l1|l2|l3|layer|层)", h)) or "background" in h,
        "层间跳转(href#锚点)": len(re.findall(r'href="#', h)) > 0,
    }


def portable_presence(h, raw):
    # 断网可打开=无外部资源依赖(无 http(s) 引入的 script/link/img src)
    ext_script = re.findall(r'<script[^>]+src="https?://', h)
    ext_link = re.findall(r'<link[^>]+href="https?://', h)
    ext_img = re.findall(r'<img[^>]+src="https?://', h)
    return {
        "无外部script依赖": len(ext_script) == 0, "外部script数": len(ext_script),
        "无外部css依赖": len(ext_link) == 0, "外部link数": len(ext_link),
        "无外部图依赖": len(ext_img) == 0, "外部img数": len(ext_img),
        "UTF8可解码(乱码EFBFBD)": raw.count(b"\xef\xbf\xbd"),
    }


def main():
    master_raw = MASTER.read_bytes()
    master_txt = master_raw.decode("utf-8", "replace")

    # 渲染路径产出保真测试件。阶段1字节级写入(不经文本模式换行转换)→ 与母版 SHA 等同=像素级保真。
    out_txt = render(master_txt, phase="1")
    OUT.write_bytes(out_txt.encode("utf-8"))
    out_raw = OUT.read_bytes()

    m_master = measure(master_txt, master_raw)
    m_out = measure(out_txt, out_raw)

    # 12项核对
    checks = []
    passed = 0
    for label, key in CHECK12:
        if key == "__module__":
            mp_m = module_presence(master_txt)
            mp_o = module_presence(out_txt)
            missing = [k for k in mp_m if mp_m[k] and not mp_o[k]]
            ok = len(missing) == 0
            checks.append({"项": label, "母版模块": mp_m, "测试件模块": mp_o, "母版有而测试件缺": missing, "结果": "PASS" if ok else "FAIL"})
        elif key == "__interactive__":
            ip_m, ip_o = interactive_presence(master_txt), interactive_presence(out_txt)
            ok = all(ip_o.values()) if any(ip_m.values()) else True
            checks.append({"项": label, "母版": ip_m, "测试件": ip_o, "结果": "PASS" if ok else "FAIL"})
        elif key == "__portable__":
            pp_m, pp_o = portable_presence(master_txt, master_raw), portable_presence(out_txt, out_raw)
            ok = (pp_o["外部script数"] <= pp_m["外部script数"] and pp_o["外部link数"] <= pp_m["外部link数"]
                  and pp_o["外部img数"] <= pp_m["外部img数"] and pp_o["UTF8可解码(乱码EFBFBD)"] <= pp_m["UTF8可解码(乱码EFBFBD)"])
            checks.append({"项": label, "母版": pp_m, "测试件": pp_o, "结果": "PASS" if ok else "FAIL"})
        else:
            a, b = m_master[key], m_out[key]
            # 正文项允许仅生成时间等技术字段带来的极小变化(阈值0=严格零退出)
            ok = b >= a
            checks.append({"项": label, "度量键": key, "母版": a, "测试件": b, "差(测-母)": b - a, "结果": "PASS" if ok else "FAIL"})
        if checks[-1]["结果"] == "PASS":
            passed += 1

    all_pass = passed == len(CHECK12)
    same_sha = hashlib.sha256(master_raw).hexdigest() == hashlib.sha256(out_raw).hexdigest()

    doc = {
        "_说明": "阶段1保真复刻核对(路径A·724冻结母版·GPT裁定20260723)。渲染路径=恒等复刻。",
        "生成于": datetime.now(JST).isoformat(timespec="seconds"),
        "母版": {"路径": str(MASTER), "字节": len(master_raw), "SHA256": hashlib.sha256(master_raw).hexdigest(), "mtime": datetime.fromtimestamp(os.path.getmtime(MASTER), JST).isoformat(timespec="seconds")},
        "保真测试件": {"路径": str(OUT), "字节": len(out_raw), "SHA256": hashlib.sha256(out_raw).hexdigest(), "mtime": datetime.fromtimestamp(os.path.getmtime(OUT), JST).isoformat(timespec="seconds")},
        "字节等同": len(master_raw) == len(out_raw), "SHA256等同": same_sha,
        "15项度量_母版": m_master, "15项度量_测试件": m_out,
        "12项零退出核对": checks,
        "通过": f"{passed}/{len(CHECK12)}", "全过": all_pass,
        "允许变化说明": "阶段1恒等复刻·未启用生成时间戳/CSS去重(留干净零退出证明)。SHA256与母版一致=像素级保真。",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("=== 阶段1保真复刻核对 ===")
    print(f"母版  : {len(master_raw)}字节 SHA {doc['母版']['SHA256'][:16]}")
    print(f"测试件: {len(out_raw)}字节 SHA {doc['保真测试件']['SHA256'][:16]}  字节等同={doc['字节等同']} SHA等同={same_sha}")
    for c in checks:
        extra = ""
        if "差(测-母)" in c:
            extra = f"母={c['母版']} 测={c['测试件']} 差={c['差(测-母)']}"
        elif "母版有而测试件缺" in c:
            extra = f"缺={c['母版有而测试件缺']}"
        print(f"  [{c['结果']}] {c['项']}  {extra}")
    print(f"通过 {passed}/{len(CHECK12)} · 全过={all_pass}")
    print("报告:", REPORT)


main()
