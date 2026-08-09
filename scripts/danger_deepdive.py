# -*- coding: utf-8 -*-
"""★轮167 B:危险组合(capex升+库存升)深查——★库存增速 vs 营收增速(区分备货/积压·★机器只给数不判)。
判据(董事长·结构化·Code只算不判):营收增速>库存增速=备货(健康)·库存增速>营收增速=积压(危险)。
逐季序列:库存/营收/capex(US=EDGAR季度·JP=EDINET年度)。★取不到NK4不估算。"""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
import inventory_capex as IC
import edinet_moat_pull as ED
import edinet_financials as EF

DANGER = ["US.NVDA", "US.GOOGL", "US.DELL", "US.QCOM", "US.CACI", "JP.8001", "JP.7832"]
REV = [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"), ("us-gaap", "Revenues"), ("us-gaap", "SalesRevenueNet")]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _yoy_latest(seq_dict):
    """{end:val}→(最新, 去年同期, YoY%)。按end月份匹配~365天前。"""
    from datetime import date
    if not seq_dict:
        return None, None, None
    ends = sorted(seq_dict)
    le = ends[-1]; ld = date.fromisoformat(le)
    prior = None
    for e in ends[:-1]:
        d = date.fromisoformat(e)
        if 350 <= (ld - d).days <= 380:
            prior = e
    if prior and seq_dict[prior]:
        return seq_dict[le], seq_dict[prior], round((seq_dict[le] - seq_dict[prior]) / abs(seq_dict[prior]) * 100, 1)
    return seq_dict[le], None, None


def _consec_up(seq):
    vals = [seq[k] for k in sorted(seq)]
    n = 0
    for i in range(len(vals) - 1, 0, -1):
        if vals[i] > vals[i - 1]:
            n += 1
        else:
            break
    return n


def us_deep(cik):
    inv = {r["end"]: r["val"] for r in IC._us_q(cik, IC.US_INV, instant=True)}
    rev = {r["end"]: r["val"] for r in IC._us_q(cik, REV, instant=False)}
    capex = {r["end"]: r["val"] for r in IC._us_q(cik, IC.US_CAPEX, instant=False)}
    inv_l, inv_p, inv_yoy = _yoy_latest(inv)
    rev_l, rev_p, rev_yoy = _yoy_latest(rev)
    _, _, cap_yoy = _yoy_latest(capex)
    verdict = "NK4"
    if isinstance(inv_yoy, (int, float)) and isinstance(rev_yoy, (int, float)):
        verdict = "营收增速>库存增速=备货侧(健康)" if rev_yoy > inv_yoy else ("库存增速>营收增速=积压侧(危险)" if inv_yoy > rev_yoy else "两增速相当")
    return {"口径": "US EDGAR季度", "库存YoY%": inv_yoy, "营收YoY%": rev_yoy, "capexYoY%": cap_yoy,
            "库存连升季": _consec_up(inv), "★库存vs营收增速(董事长判据·Code只标)": verdict,
            "库存序列(近6季·亿)": [round(inv[k] / 1e8, 1) for k in sorted(inv)[-6:]],
            "营收序列(近6季·亿)": [round(rev[k] / 1e8, 1) for k in sorted(rev)[-6:]]}


def jp_deep(code, key):
    doc = IC.JP_DOCID.get(code)
    if not doc:
        return {"口径": "NK4(无缓存docID)"}
    try:
        xml = ED._download_xbrl(doc, key)
    except Exception:
        return {"口径": "NK4(XBRL取不到)"}
    ctxs, facts = ED._parse(xml); std = ED._detect_std(facts); t = IC.JP_TAGS[std]
    def by(names):
        out = {}
        for f in facts:
            if f["tag"] in set(names) and "_" not in f["ctx"] and "Member" not in f["ctx"]:
                y = ctxs.get(f["ctx"])
                if y:
                    out[y] = f["val"]
        return out
    inv = by(t["存货"]); rev = by(["RevenueIFRSSummaryOfBusinessResults", "NetSalesSummaryOfBusinessResults", "RevenueIFRS", "NetSales"])
    def yoy2(d):
        ys = sorted(d)
        if len(ys) >= 2 and d[ys[-2]]:
            return round((d[ys[-1]] - d[ys[-2]]) / abs(d[ys[-2]]) * 100, 1)
        return None
    iy, ry = yoy2(inv), yoy2(rev)
    verdict = "NK4"
    if isinstance(iy, (int, float)) and isinstance(ry, (int, float)):
        verdict = "营收增速>库存增速=备货侧(健康)" if ry > iy else ("库存增速>营收增速=积压侧(危险)" if iy > ry else "两增速相当")
    return {"口径": "JP EDINET年度(2点)", "库存YoY%": iy, "营收YoY%": ry, "★库存vs营收增速(董事长判据·Code只标)": verdict}


def build(dc):
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    cikm = MD.cik_map(); key = ED._key()
    res = []
    for code in DANGER:
        rec = {"代码": code, "全名": idm.get(code, {}).get("全名", "?")}
        if code.startswith("US."):
            cik = cikm.get(code.split(".")[1].upper())
            rec["深查"] = us_deep(cik) if cik else {"口径": "NK4(无CIK)"}
        else:
            rec["深查"] = jp_deep(code, key)
        res.append(rec)
        time.sleep(0.1)
    out = {
        "_说明": "★轮167 危险组合深查。★库存增速vs营收增速区分备货(健康)/积压(危险)·★Code只算两增速+标哪个大·不判(董事长判·G2)。取不到NK4。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "对象(capex升+库存升7只)": DANGER, "逐只": res,
    }
    (ROOT / f"data/universe/danger_deepdive_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    for r in o["逐只"]:
        d = r["深查"]
        print("%-9s %-16s 库存YoY %s%% 营收YoY %s%% → %s" % (
            r["代码"], str(r["全名"])[:16], d.get("库存YoY%"), d.get("营收YoY%"), d.get("★库存vs营收增速(董事长判据·Code只标)", d.get("口径"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
