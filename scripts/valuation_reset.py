# -*- coding: utf-8 -*-
"""★轮161 B:估值/预期重置线索(★取数不判断)。
B-1 AMKR/RBLX 财报前后PE/PS变化(倍数压缩=价跌但基本面周内未变→估值重置)。
B-2 封测/半导体设备同行(ASX/SCREEN/TSM等)同期5日涨跌+PE→板块级 vs 个股级。
B-3 8-K EX-99.1【风险/挑战】段原文(只提取·不解读)。★取不到NK4。机器只给数·因果Opus5判(G2)。"""
import sys, json, ssl, urllib.request, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import yahoo_financials as YF
import moat_data_pull as MD
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}
TARGETS = {"US.AMKR": ["US.ASX", "JP.7735", "US.TSM", "JP.6857"], "US.RBLX": ["US.APP", "US.U", "US.TTWO"]}
RISK_KW = ["risk", "challenge", "headwind", "uncertain", "macro", "weakness", "soft demand", "decline", "tariff", "inventory"]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def chg5(code):
    sym = YF.to_yahoo(code)
    try:
        j = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d", headers=UA), timeout=15, context=CTX).read())
        adj = j["chart"]["result"][0]["indicators"].get("adjclose", [{}])[0].get("adjclose")
        cl = [c for c in (adj or []) if c is not None]
        return round((cl[-1] - cl[-6]) / cl[-6] * 100, 2) if len(cl) >= 6 else None
    except Exception:
        return None


def valuation(code):
    d = YF._qs(YF.to_yahoo(code), "summaryDetail,defaultKeyStatistics")
    sd = (d or {}).get("summaryDetail", {}) or {}
    pe = YF._raw(sd, "trailingPE"); pef = YF._raw(sd, "forwardPE"); ps = YF._raw(sd, "priceToSalesTrailing12Months")
    c5 = chg5(code)
    # 财报前(5日前)隐含PE = 现PE / (1+涨跌)  (EPS周内未变→倍数变化≈价格变化)
    pe_before = round(pe / (1 + c5 / 100), 2) if (isinstance(pe, (int, float)) and isinstance(c5, (int, float)) and (1 + c5 / 100) != 0) else None
    return {"PE_trailing": pe, "PE_forward": pef, "PS_trailing": (round(ps, 2) if isinstance(ps, (int, float)) else "NK4"),
            "5日涨跌%": c5, "隐含PE_5日前": pe_before,
            "★倍数压缩": (f"PE {pe_before}→{round(pe,2)}(-{round((1-pe/pe_before)*100,1)}%·基本面周内未变→估值重置)" if pe_before and pe else "NK4")}


def risk_segment(code):
    """从8-K EX-99.1提取风险/挑战段(原文·不解读)。复用guidance文件的EX99定位。"""
    g = _rj(_latest("data/universe/guidance_*.json"))
    hit = next((r for r in g.get("逐只", []) if r["代码"] == code), None)
    if not hit or "EX99文件" not in hit:
        return "NK4(无EX-99.1定位)"
    cik = MD.cik_map().get(code.split(".")[1].upper())
    s = MD._get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json") if cik else None
    if not s:
        return "NK4"
    rf = s["filings"]["recent"]; acc = None
    for i in range(len(rf["form"])):
        if rf["form"][i] == "8-K" and rf["filingDate"][i] >= "2026-07-25":
            acc = rf["accessionNumber"][i].replace("-", ""); break
    if not acc:
        return "NK4"
    try:
        html = urllib.request.urlopen(urllib.request.Request(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{hit['EX99文件']}", headers=UA), timeout=20, context=CTX).read().decode("utf-8", "replace")
    except Exception:
        return "NK4(EX99取不到)"
    txt = re.sub("<[^>]+>", " ", html); txt = re.sub(r"&#\d+;", " ", txt); txt = re.sub(r"\s+", " ", txt)
    low = txt.lower()
    segs = []
    for kw in RISK_KW:
        i = low.find(kw)
        if i > 0:
            seg = txt[max(0, i - 40):i + 180].strip()
            if seg not in segs:
                segs.append(seg)
        if len(segs) >= 3:
            break
    return segs or "未识别到风险/挑战关键段(可能无·或在10-Q风险因素)"


def build(dc):
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    res = {}
    for code, peers in TARGETS.items():
        res[code] = {
            "全名": idm.get(code, {}).get("全名", "?"),
            "B1_自身估值重置": valuation(code),
            "B2_同行同期(可比公司)": {p: {"全名": idm.get(p, {}).get("全名", "?"), **valuation(p)} for p in peers},
            "B3_EX99风险挑战段(原文·不解读)": risk_segment(code),
        }
    out = {
        "_说明": "★轮161 B 估值/预期重置线索。★Code只取数(PE/PS/同行/风险段原文)·不判断是不是估值重置·因果Opus5判(G2)。取不到NK4。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "逐只": res,
    }
    (ROOT / f"data/universe/valuation_reset_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    for code, r in o["逐只"].items():
        v = r["B1_自身估值重置"]
        print("%s %s: %s" % (code, r["全名"][:18], v["★倍数压缩"]))
        for p, pv in r["B2_同行同期(可比公司)"].items():
            print("   同行 %-8s %s PE%s 5日%s%%" % (p, pv["全名"][:16], pv["PE_trailing"], pv["5日涨跌%"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
