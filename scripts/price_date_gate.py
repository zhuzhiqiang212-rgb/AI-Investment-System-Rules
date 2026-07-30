# -*- coding: utf-8 -*-
"""A2①(38号)价格数据日拒绝闸:产品内任一价格的数据日 ≠ 当日 → FAIL(拒绝生成)。
机器可核:扫产品里带价格语境的日期标签(盘中/收盘/价),任一≠当日即FAIL。Code只校验不改判断。"""
import sys, re, argparse, pathlib
def check(html_path, date):
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"          # 2026-07-30
    mmdd = f"{date[4:6]}-{date[6:]}"                     # 07-30
    t = pathlib.Path(html_path).read_text(encoding="utf-8")
    txt = re.sub(r"<[^>]+>", " ", t)
    # 价格语境里的 MM-DD 日期(盘中/收/收盘/价 前后20字内)
    bad = {}
    for m in re.finditer(r"(0[1-9]|1[0-2])-([0-3][0-9])", txt):
        d = m.group(0)
        ctx = txt[max(0, m.start() - 12):m.end() + 12]
        if re.search(r"盘中|收盘|收\b|价|close|收$", ctx) and d != mmdd:
            bad[d] = bad.get(d, 0) + 1
    ok = not bad
    return ok, bad, mmdd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    ok, bad, mmdd = check(a.html, a.date)
    print("价格日拒绝闸 · 当日=%s · 文件=%s" % (mmdd, pathlib.Path(a.html).name))
    if ok:
        print("  ✓ PASS:未发现价格数据日 ≠ 当日")
        return 0
    print("  ★ FAIL·拒绝生成:发现价格数据日≠当日 →", {("非当日 " + k): v for k, v in bad.items()})
    return 5

if __name__ == "__main__":
    raise SystemExit(main())
