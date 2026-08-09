# -*- coding: utf-8 -*-
"""★轮83 AW2:产品模块完整性闸——从此判断产品完整性的唯一依据(★不看体积)。
读 data/content/product_module_manifest.json,渲染后逐模块核实物(核验标记在不在),
缺任一『必需』模块→FAIL(AW2-2)。选填缺→进缺失清单(标原因·不拦)。
用法:①渲染器内 check_html(html,date) 出品前调,缺必需返 ok=False 不出品;
     ②CLI --file 核已渲HTML。"""
import sys, json, argparse, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "content" / "product_module_manifest.json"


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("modules", [])


def check_html(html: str, date: str = "") -> tuple:
    """核一份已渲HTML。返回 (ok, fails, warns, rows)。ok=无缺必需。"""
    mods = _load()
    fails, warns, rows = [], [], []
    for m in mods:
        marks = m.get("核验标记", [])
        hit_mark = next((mk for mk in marks if mk and mk in html), None)
        present = hit_mark is not None
        cnt = None
        need_n = m.get("最少出现次数")
        if present and need_n:
            cnt = html.count(marks[0])
            if cnt < need_n:
                present = False
        # 子尺(六把尺)逐条核
        sub_missing = []
        for s in m.get("子尺", []):
            if s not in html:
                sub_missing.append(s)
        status = "✔在" if present else "✗缺"
        if present and sub_missing:
            status = "△部分(缺子尺:%s)" % "、".join(sub_missing)
        row = {"id": m["id"], "模块名": m["模块名"], "必需": m["必需"], "状态": status,
               "命中标记": hit_mark, "计数": cnt}
        rows.append(row)
        if not present:
            if m["必需"]:
                extra = ("(出现%d次<需%d)" % (cnt, need_n)) if need_n and cnt is not None else ""
                fails.append("%s %s 缺失%s → %s" % (m["id"], m["模块名"], extra, m.get("缺失处理", "FAIL")))
            else:
                warns.append("%s %s 缺(选填)→ %s" % (m["id"], m["模块名"], m.get("缺失处理", "标缺失清单")))
        elif sub_missing and m["必需"]:
            fails.append("%s %s 子尺不全(缺:%s)→ 六把尺正文须齐" % (m["id"], m["模块名"], "、".join(sub_missing)))
    return (len(fails) == 0, fails, warns, rows)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="已渲HTML(00_请先看这里/下的文件名或全路径)")
    ap.add_argument("--date", default="")
    a = ap.parse_args()
    p = Path(a.file)
    if not p.is_absolute() and not p.exists():
        p = ROOT / "00_请先看这里" / a.file
    if not p.exists():
        print("[module_gate FAIL] 文件不存在:", p); return 5
    html = p.read_text(encoding="utf-8", errors="replace")
    ok, fails, warns, rows = check_html(html, a.date)
    n_req = sum(1 for r in rows if r["必需"])
    n_req_ok = sum(1 for r in rows if r["必需"] and r["状态"].startswith("✔"))
    print("[module_completeness] %s · 必需 %d/%d 在 · 选填缺 %d" % (p.name, n_req_ok, n_req, len(warns)))
    for r in rows:
        flag = "必需" if r["必需"] else "选填"
        print("  %s [%s] %s %s%s" % (r["状态"][:6], flag, r["id"], r["模块名"][:30],
                                     ("×%d" % r["计数"]) if r["计数"] is not None else ""))
    if warns:
        print("--- 选填缺失清单 ---")
        for w in warns:
            print("  △", w)
    if fails:
        print("[module_completeness FAIL] 缺 %d 个必需模块→不出品(AW2-2)" % len(fails))
        for f in fails:
            print("  ✗", f)
        return 5
    print("[module_completeness PASS] 0 缺必需模块")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
