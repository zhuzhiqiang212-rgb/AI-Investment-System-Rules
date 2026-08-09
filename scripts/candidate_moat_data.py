# -*- coding: utf-8 -*-
"""★轮155 B:第二批护城河客观数据(candidate_priority Top30·校准后评候选用)。
四项(毛利率/ROE/研发率/营收增速稳定性)+ROIC。★优先3只(三路径同时命中):JP.7735/US.CTSH/US.AMKR。
★日股走EDINET·美股走EDGAR·★不混口径(§5.5)。★HK无keyless财报源(EDGAR/EDINET不覆盖)→NK4。★取不到NK4不估算。机器只取数·质性留Opus5(G2)。"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
import edinet_moat_pull as ED
import edinet_financials as EF
import roic_compute as RC
import yahoo_financials as YF

PRIORITY = {"JP.7735", "US.CTSH", "US.AMKR"}


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def build(dc):
    prio = _rj(_latest("data/opportunity/candidate_priority_*.json"))
    top = (prio.get("★Top30_板块非受损(个股层面优先)", []) + prio.get("★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)", []))
    codes = [r["标的"] for r in top][:30]
    cikm = MD.cik_map()
    key = ED._key()
    secmap = None
    res = []
    got = {"毛利率": 0, "ROE": 0, "研发费用率": 0, "营收增速稳定性": 0, "ROIC": 0}
    for code in codes:
        mk = code.split(".")[0]; sym = code.split(".")[1]
        rec = {"代码": code, "★优先(三路径)": code in PRIORITY, "源": None, "数据": None, "ROIC": None}
        if mk == "US":
            cik = cikm.get(sym.upper())
            if cik:
                d, tags = MD.pull_one(cik)
                rec["源"] = "EDGAR"; rec["数据"] = {"毛利率": d.get("毛利率近3年"), "ROE": d.get("ROE近3年"),
                    "研发费用率": d.get("研发费用率近3年"), "营收增速稳定性": d.get("营收增速稳定性(增速标准差)")}
                rec["ROIC"] = RC.roic_us(cik).get("ROIC")
            else:
                rec["源"] = "NK4"; rec["数据"] = "NK4(EDGAR无CIK)"
        elif mk == "JP":
            if secmap is None:
                secmap = EF.build_secmap()
            edc = (secmap.get(sym[:4], {}) or {}).get("edinet")
            doc = None
            if edc:
                dd = EF.find_annual_doc(edc, key)
                doc = dd.get("docID") if isinstance(dd, dict) else None
            if doc:
                d = ED.pull_one(doc, key, code=code)
                rec["源"] = "EDINET"; rec["数据"] = {"会计准则": d.get("会计准则"), "毛利率": d.get("毛利率近年"),
                    "ROE": d.get("ROE近年(自算=归母净利/归母权益)"), "研发费用率": d.get("研发费用率近年"),
                    "营收增速稳定性": d.get("营收增速稳定性(增速标准差)")}
                rec["ROIC"] = RC.roic_jp(doc, key).get("ROIC")
            else:
                rec["源"] = "NK4"; rec["数据"] = "NK4(EDINET docID取不到)"
        else:  # HK → ★轮156 Yahoo(港交所无keyless XBRL·Yahoo quoteSummary crumb补)
            y = YF.get_financials(code)
            rec["源"] = "Yahoo(TTM)"
            rec["数据"] = {"毛利率": y.get("毛利率TTM"), "ROE": y.get("ROE_TTM"), "研发费用率": y.get("研发费用率"),
                          "营收增速稳定性": y.get("营收增速稳定性(增速标准差)"), "口径": y.get("口径"), "营收近年": y.get("营收近年")}
            rec["ROIC"] = "NK4(Yahoo无营业利润/投入资本分项)"
        # 统计(HK用标量·EDGAR/EDINET用dict·分别判)
        dd = rec["数据"]
        def _has(v):
            return (isinstance(v, dict) and len(v) > 0) or isinstance(v, (int, float))
        if isinstance(dd, dict):
            if _has(dd.get("毛利率")): got["毛利率"] += 1
            if _has(dd.get("ROE")): got["ROE"] += 1
            if _has(dd.get("研发费用率")): got["研发费用率"] += 1
            if isinstance(dd.get("营收增速稳定性"), (int, float)): got["营收增速稳定性"] += 1
        if isinstance(rec["ROIC"], (int, float)): got["ROIC"] += 1
        res.append(rec)
    out = {
        "_说明": "★轮155 B 第二批(Top30候选)护城河客观数据+ROIC。日股EDINET/美股EDGAR不混·HK无keyless源NK4·取不到不估算。机器只取数·打分留Opus5(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "Top30数": len(codes),
        "★取到项统计(/30)": got,
        "★三路径优先3只": [r for r in res if r["★优先(三路径)"]],
        "逐只": res,
    }
    (ROOT / f"data/opportunity/candidate_moat_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★取到项(/30):", json.dumps(o["★取到项统计(/30)"], ensure_ascii=False))
    print("=== 三路径优先3只 ===")
    for r in o["★三路径优先3只"]:
        dd = r["数据"]
        gm = (dd.get("毛利率") if isinstance(dd, dict) else None)
        gmv = (list(gm.values())[-1] if isinstance(gm, dict) and gm else "NK4")
        print("  %-9s %s ROIC=%s 毛利率%s" % (r["代码"], r["源"], r["ROIC"], gmv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
