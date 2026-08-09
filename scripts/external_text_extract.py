# -*- coding: utf-8 -*-
"""★轮84 BB2:外部研究资料正文提取(湖水/老雷)→纯文本+索引。贯穿性判据『外部研究资料消化』。
BB2-1 PDF正文→data/external/text/{原名}.txt。BB2-2 .gdoc提不出→标『需导出PDF』(★不许判资料缺失)。
BB2-3 出索引 _index_{date}.json(日期/标题/来源/字数/成功与否)。BB2-4 管线①a2每日提取最近7天。
BB2-5 告警:最近7天有新料但提取数=0→产品标『外部研究资料N份未消化』。"""
import sys, json, argparse, re, glob
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "external" / "text"
SRC_DIRS = {"湖水": Path("G:/我的云端硬盘/湖水资讯"), "老雷": Path("G:/我的云端硬盘/老雷")}


def _parse_date(name):
    """从文件名解析日期。格式 26-07-31-... / 26-07-2-... (单位数日)。返回 date 或 None。"""
    m = re.match(r"(\d{2})-(\d{1,2})-(\d{1,2})", name.strip())
    if not m:
        return None
    yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return _date(2000 + yy, mm, dd)
    except Exception:
        return None


def _extract_pdf(p):
    try:
        from pypdf import PdfReader
        r = PdfReader(str(p))
        txt = "\n".join((pg.extract_text() or "") for pg in r.pages)
        return txt.strip(), None
    except Exception as e:
        return "", str(e)[:120]


def build(date, days=7):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    cutoff = _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8])) - timedelta(days=days)
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    n_ok = n_gdoc = n_fail = 0
    for src, d in SRC_DIRS.items():
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            fd = _parse_date(p.name)
            if fd is None or fd < cutoff:
                continue
            ext = p.suffix.lower()
            title = re.sub(r"^\d{2}-\d{1,2}-\d{1,2}-?\d?\s*", "", p.stem).strip() or p.stem
            rec = {"日期": fd.isoformat(), "标题": title, "来源": src, "原文件": p.name, "字数": 0, "成功": False, "说明": ""}
            if ext == ".pdf":
                txt, err = _extract_pdf(p)
                if txt and len(txt) >= 30:
                    outp = OUT / (re.sub(r'[\\/:*?"<>|]', "_", p.stem) + ".txt")
                    outp.write_text("【来源】%s\n【原文件】%s\n【日期】%s\n\n%s\n" % (src, p.name, fd.isoformat(), txt),
                                    encoding="utf-8")
                    rec.update({"字数": len(txt), "成功": True, "txt": outp.name}); n_ok += 1
                else:
                    rec["说明"] = "PDF提取空/失败:" + (err or "无文本(可能扫描件)"); n_fail += 1
            elif ext == ".gdoc":
                # BB2-2:.gdoc提不出→标『需导出PDF』·★不许判『资料缺失』
                # 若同名.pdf已存在则跳过(用PDF那份)
                if (p.parent / (p.stem + ".pdf")).exists():
                    continue
                rec["说明"] = "★需导出PDF(gdoc是云端指针·本地无正文·不是资料缺失)"; n_gdoc += 1
            else:
                continue
            entries.append(rec)
    entries.sort(key=lambda r: r["日期"], reverse=True)
    n_new = len(entries)
    warn = ""
    if n_new > 0 and n_ok == 0:
        warn = "★最近%d天有新料%d份但提取成功0份→产品应标『外部研究资料%d份未消化』(BB2-5)" % (days, n_new, n_new)
    idx = {
        "_说明": "★轮84 BB2 外部研究资料正文提取索引。贯穿性『外部研究资料消化』判据。gdoc提不出=需导出PDF·非资料缺失。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "窗口天数": days, "起始日": cutoff.isoformat(),
        "统计": {"新料总数": n_new, "提取成功": n_ok, "需导出PDF(gdoc)": n_gdoc, "提取失败": n_fail},
        "★告警": warn, "条目": entries,
    }
    return idx


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    idx = build(a.date, a.days)
    p = OUT / f"_index_{a.date.replace('-', '')}.json"
    p.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    st = idx["统计"]
    print("[external_text_extract] %s · 新料%d · 提取成功%d · 需导出PDF%d · 失败%d · 乱码%d" % (
        a.date, st["新料总数"], st["提取成功"], st["需导出PDF(gdoc)"], st["提取失败"], b.count(b"\xef\xbf\xbd")))
    for e in idx["条目"][:12]:
        print("  %s [%s] %s %s" % ("✔" if e["成功"] else ("需PDF" if "需导出" in e["说明"] else "✗"),
                                   e["来源"], e["标题"][:34], ("%d字" % e["字数"]) if e["成功"] else e["说明"][:30]))
    if idx["★告警"]:
        print("  " + idx["★告警"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
