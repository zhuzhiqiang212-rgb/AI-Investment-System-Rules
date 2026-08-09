# -*- coding: utf-8 -*-
"""★轮158 A:异动标的公告日历(原因线索最后一块——公告是异动最常见原因)。
US→SEC EDGAR submissions(8-K/10-Q/10-K/6-K·近5日窗口·轮121证SEC可达需UA含邮箱)。JP→EDINET documents(近日窗口)。HK→无keyless源→原因未知。
★A-3 有公告→标『可能原因:X月X日 公告(类型)』+链接·★仍不判因果(只给线索·Opus5判)。★A-4 无公告→维持原因未知。"""
import sys, json, time, urllib.request, ssl
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
import edinet_financials as EF
from datetime import date as _date, timedelta as _td
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
_SECMAP = None
FORMS = {"8-K": "重大事项/业绩", "10-Q": "季报(财报)", "10-K": "年报(财报)", "6-K": "外国发行人临时报告", "8-K/A": "重大事项修订"}
WINDOW_DAYS = 7


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _us_ann(cik, win):
    s = MD._get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    if not s:
        return None
    rf = (s.get("filings", {}) or {}).get("recent", {}) or {}
    forms = rf.get("form", []); dates = rf.get("filingDate", [])
    acc = rf.get("accessionNumber", []); prim = rf.get("primaryDocument", [])
    hits = []
    for i in range(len(forms)):
        if dates[i] >= win and forms[i] in FORMS:
            a = acc[i].replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{prim[i]}" if i < len(prim) else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
            hits.append({"日期": dates[i], "类型": forms[i], "类型说明": FORMS[forms[i]], "链接": url})
    return hits


def _jp_ann(sym4, win_days, today_str):
    """EDINET 窗口内公告(day-scan·bounded)。返回 hits列表·None=证券码映射取不到。"""
    global _SECMAP
    if _SECMAP is None:
        try:
            _SECMAP = EF.build_secmap()
        except Exception:
            _SECMAP = {}
    edc = (_SECMAP.get(sym4[:4], {}) or {}).get("edinet")
    if not edc:
        return None
    try:
        key = EF._load_key()
    except Exception:
        return None
    y, m, d = int(today_str[:4]), int(today_str[5:7]), int(today_str[8:10])
    today = _date(y, m, d)
    hits = []
    for i in range(win_days + 1):
        day = (today - _td(days=i)).isoformat()
        try:
            url = f"{EF.API_BASE}/documents.json?date={day}&type=2"
            req = urllib.request.Request(url); req.add_header("Ocp-Apim-Subscription-Key", key)
            j = json.loads(urllib.request.urlopen(req, timeout=20, context=CTX).read())
            for doc in j.get("results", []):
                if doc.get("edinetCode") == edc:
                    hits.append({"日期": day, "类型": "EDINET提出書類", "类型说明": (doc.get("docDescription") or "")[:30],
                                 "链接": f"https://disclosure2.edinet-fsa.go.jp/WEEK0010.aspx"})
        except Exception:
            pass
        time.sleep(0.15)
    return hits


def build(dc, today_str="2026-08-04"):
    tg = _rj(_latest("data/universe/type_gate3_*.json"))
    anom = [a["code"] for a in tg.get("★C异动明细", [])]
    y, m, d = int(today_str[:4]), int(today_str[5:7]), int(today_str[8:10])
    today = date(y, m, d); win = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    cikm = MD.cik_map()
    res = {}
    for code in anom:
        mk, sym = code.split(".", 1)
        if mk == "US":
            cik = cikm.get(sym.upper())
            hits = _us_ann(cik, win) if cik else None
            if hits:
                res[code] = {"★公告状态": "★窗口内有公告(可能原因·不判因果)", "公告": hits, "源": "SEC EDGAR submissions"}
            else:
                res[code] = {"★公告状态": "窗口内无公告→维持原因未知", "公告": [], "源": "SEC EDGAR submissions"}
        elif mk == "JP":
            hits = _jp_ann(sym, WINDOW_DAYS, today_str)
            if hits is None:
                res[code] = {"★公告状态": "★EDINET证券码映射取不到→原因未知", "公告": [], "源": "EDINET"}
            elif hits:
                res[code] = {"★公告状态": "★窗口内有公告(可能原因·不判因果)", "公告": hits, "源": "EDINET"}
            else:
                res[code] = {"★公告状态": "窗口内无公告→维持原因未知", "公告": [], "源": "EDINET"}
        else:  # HK
            res[code] = {"★公告状态": "★原因未知(HKEXnews端点keyless可达但per-stock需内部stockId映射·本轮未接)", "公告": [], "源": "HKEXnews(端点通·stockId映射待接)"}
        time.sleep(0.1)
    n_ann = sum(1 for v in res.values() if v["公告"])
    out = {
        "_说明": "★轮158 异动公告日历。US=SEC submissions(8-K/10-Q/10-K/6-K近%d日)·JP=EDINET待接·HK无源。★有公告=可能原因(不判因果·Opus5判)·无公告=维持原因未知。" % WINDOW_DAYS,
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "窗口": f"{win} ~ {today.isoformat()}",
        "异动数": len(anom), "★窗口内有公告只数": n_ann,
        "逐只公告": res,
    }
    (ROOT / f"data/universe/announcements_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("异动 %d · 窗口内有公告 %d 只 · 窗口 %s" % (o["异动数"], o["★窗口内有公告只数"], o["窗口"]))
    for code, v in o["逐只公告"].items():
        if v["公告"]:
            print("  %-9s %s" % (code, "; ".join("%s %s(%s)" % (h["日期"], h["类型"], h["类型说明"]) for h in v["公告"][:3])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
