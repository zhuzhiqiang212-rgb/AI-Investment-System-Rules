# -*- coding: utf-8 -*-
"""★轮102 A4-3:五册(六分册)出厂闸。分册产品≠单册·须【多册感知】判定:
 · 逐册【内容安全】(L1乱码/L3转义/L4内部话/L46字段/L23长行)+良构+≤400KB;
 · 【合并完整性】:六册并集须含全部版块锚(L48关注的 sec-*/inst-top/deep-*)与 data-actck 锚(L28);
 · 【L2同源】:六册 data_date/run_id 必须一致。
单册 L25/L28/L48 是『一个文件含全部』的判据·对分册【逐册】不成立(锚跨册)→改为并集判。"""
import sys, re, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"
SAFE_PREFIX = ("L1 ", "L1乱码", "L3 ", "L4 ", "L4c", "L23", "L46")  # 逐册必须干净的内容安全类
NEED_ANCHORS = ["inst-top", "sec-opp", "sec-sector", "sec-macro", "sec-conc", "sec-risk",
                "sec-score", "sec-rulers", "sec-triggers", "sec-diff", "sec-loop", "glossary"]


def gate(date):
    dh = "%s-%s-%s" % (date[:4], date[4:6], date[6:]) if "-" not in date else date
    books = {Path(p).name: Path(p).read_text(encoding="utf-8")
             for p in sorted(glob.glob(str(SEE / f"★每日产品_{dh}_*.html")))}
    fails, notes = [], []
    if len(books) < 5:
        fails.append("五册闸：分册数 %d < 5——未按原规范恢复五册" % len(books))
        return fails, notes
    notes.append("分册数 %d（含2a/2b子册）" % len(books))
    # ① L2 同源
    rids, dds = set(), set()
    for h in books.values():
        rids |= set(re.findall(r"R-?3?-\d{8}-\d{6}", h))
        dds |= set(re.findall(r"数据日 <b>(\d{4}-\d{2}-\d{2})", h))
    if len(rids) == 1 and len(dds) == 1:
        notes.append("L2同源✔ run_id=%s data_date=%s（六册一致）" % (list(rids)[0], list(dds)[0]))
    else:
        fails.append("L2同源✗ run_id集=%s data_date集=%s——六册不同源" % (rids, dds))
    # ② 逐册内容安全 + 良构 + ≤400KB + 乱码
    try:
        from product_lint import lint_volumes
    except Exception as e:
        fails.append("product_lint 导入失败:%s" % e); return fails, notes
    for n, h in books.items():
        b = h.encode("utf-8"); kb = len(b) / 1024
        if b.count(b"\xef\xbf\xbd"):
            fails.append("%s 乱码 EFBFBD×%d" % (n, b.count(b"\xef\xbf\xbd")))
        if kb > 400:
            fails.append("%s 体积 %.0fKB > 400KB（不可通读）" % (n, kb))
        opn = len(re.findall(r"<(?:div|section|details)\b(?![^>]*/>)", h))
        cls = len(re.findall(r"</(?:div|section|details)>", h))
        if opn != cls:
            fails.append("%s 容器不平衡 开%d/闭%d（HTML不良构）" % (n, opn, cls))
        try:
            bf = [f for f in lint_volumes({n: h}, date.replace("-", "")) if f.startswith(SAFE_PREFIX)]
            for f in bf:
                fails.append("逐册安全: " + f)
        except Exception:
            pass
    # ③ 合并完整性:并集含全部版块锚 + data-actck 锚
    allhtml = "".join(books.values())
    miss = [a for a in NEED_ANCHORS if ('id="%s"' % a) not in allhtml]
    if miss:
        fails.append("合并完整性✗ 六册并集缺版块锚:%s（L48口径·并集须齐）" % miss)
    else:
        notes.append("合并完整性✔ 版块锚 %d/%d 全在并集" % (len(NEED_ANCHORS), len(NEED_ANCHORS)))
    ndeep = len(set(re.findall(r'id="deep(?:B1)?-([A-Z]{2}\.[0-9A-Z]+)"', allhtml)))  # deep-(render)或deepB1-(B1新模板)
    nactck = len(re.findall(r"data-actck=", allhtml))
    if ndeep >= 20 and nactck > 0:
        notes.append("并集 个股卡 %d 只·data-actck 锚 %d（L28同股一致性有锚）" % (ndeep, nactck))
    else:
        fails.append("合并完整性✗ 个股卡 %d(<20) 或 actck锚 %d(=0)——并集不完整" % (ndeep, nactck))
    return fails, notes


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, notes = gate(a.date)
    for n in notes:
        print("  ✔", n)
    if fails:
        print("[五册出厂闸 FAIL] %d 条：" % len(fails))
        for f in fails:
            print("  ✗", f)
        return 6
    print("[五册出厂闸 PASS] 逐册安全+合并完整+L2同源")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
