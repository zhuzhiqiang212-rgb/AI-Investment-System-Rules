# -*- coding: utf-8 -*-
"""★轮160 B:指引提取(8-K EX-99.1业绩新闻稿·guidance在自由文本非XBRL)。
对有公告US异动·取8-K的EX-99.1全文→提取【下季/全年指引段落数值】(Net sales/EPS/margin区间)。
★Code只提取数值段·★不解读(是好是坏由Opus5判·G2)。★取不到→NK4。"""
import sys, json, ssl, urllib.request, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
GUIDE_KW = ["guidance", "outlook", "we expect", "we anticipate", "third quarter", "fourth quarter",
            "first quarter", "second quarter", "full year", "for the quarter ending", "next quarter"]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _fetch(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=MD.UA), timeout=20, context=CTX).read().decode("utf-8", "replace")
    except Exception:
        return None


def _find_ex99(cik, acc):
    html = _fetch(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/")
    if not html:
        return None
    files = re.findall(r'href="[^"]*?/([^/"]+\.(?:htm|txt))"', html)
    ex = [f for f in files if ("ex99" in f.lower() or "ex-99" in f.lower()) and "index" not in f.lower()]
    return ex[0] if ex else None


def guidance_for(cik):
    """取该公司最近8-K的EX-99.1·提取指引段。返回 dict 或 NK4。"""
    s = MD._get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    if not s:
        return {"★指引": "NK4(submissions取不到)"}
    rf = (s.get("filings", {}) or {}).get("recent", {}) or {}
    forms = rf.get("form", []); dates = rf.get("filingDate", []); acc = rf.get("accessionNumber", [])
    for i in range(len(forms)):
        if forms[i] == "8-K" and dates[i] >= "2026-07-25":
            a = acc[i].replace("-", "")
            ex = _find_ex99(cik, a)
            if not ex:
                continue
            html = _fetch(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{ex}")
            if not html:
                continue
            txt = re.sub("<[^>]+>", " ", html)
            txt = re.sub(r"&#\d+;", lambda m: {"38": "&", "58": ":", "8226": "·", "160": " ", "8217": "'", "8211": "-", "8212": "-"}.get(m.group(0)[2:-1], " "), txt)
            txt = re.sub(r"\s+", " ", txt)
            low = txt.lower()
            # ★遍历所有关键词命中·选【$金额区间最密】的段(跳过safe-harbor免责/标题·优先真指引数值)
            best = None; best_score = 0
            for kw in GUIDE_KW:
                start = 0
                while True:
                    idx = low.find(kw, start)
                    if idx < 0:
                        break
                    start = idx + 1
                    seg = txt[idx:idx + 360]
                    # 打分:含【$数字 ... to ... 】区间强信号·%区间·排除免责段
                    score = len(re.findall(r"\$\s?[\d,.]+", seg)) * 3 + len(re.findall(r"\bto\s?\$", seg)) * 4 + seg.count("%")
                    if "may differ materially" in seg.lower() or "safe harbor" in seg.lower():
                        score -= 5
                    if score > best_score:
                        best_score = score; best = seg
            if best and best_score >= 3:
                return {"★指引段(EX-99.1原文·Code不解读)": best.strip(), "指引信号强度": best_score, "8-K日期": dates[i], "EX99文件": ex, "源": "SEC EDGAR 8-K EX-99.1"}
            return {"★指引": "8-K EX-99.1取到但未识别到量化指引数值段(可能仅定性展望)", "8-K日期": dates[i]}
    return {"★指引": "NK4(窗口内无带EX-99.1的8-K)"}


def build(dc):
    ann = _rj(_latest("data/universe/announcements_*.json")).get("逐只公告", {}) or {}
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    targets = [c for c, v in ann.items() if v.get("公告") and c.startswith("US.")]
    cikm = MD.cik_map()
    res = []
    got = 0
    for code in targets:
        cik = cikm.get(code.split(".")[1].upper())
        g = guidance_for(cik) if cik else {"★指引": "NK4(无CIK)"}
        if "★指引段(EX-99.1原文·Code不解读)" in g:
            got += 1
        res.append({"代码": code, "全名": idm.get(code, {}).get("全名", "?"), **g})
    out = {
        "_说明": "★轮160 指引提取(8-K EX-99.1)。★Code只提取指引数值段·不解读(好坏由Opus5判G2)。取不到NK4。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "对象数": len(res), "★指引段取到": got,
        "逐只": res,
    }
    (ROOT / f"data/universe/guidance_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("指引对象 %d · 指引段取到 %d" % (o["对象数"], o["★指引段取到"]))
    for r in o["逐只"]:
        seg = r.get("★指引段(EX-99.1原文·Code不解读)")
        print("  %-9s %s" % (r["代码"], (seg[:120] if seg else r.get("★指引"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
