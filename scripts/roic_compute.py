# -*- coding: utf-8 -*-
"""★轮153 C:ROIC(护城河最硬的结果指标——真有护城河能长期维持高ROIC·没有的被竞争抹平)。
ROIC = NOPAT / 投入资本。NOPAT ≈ 营业利润×(1-有效税率)。投入资本 ≈ 股东权益+有息负债-现金。
★C-2 XBRL有无这些分项?能算就算·算不了如实报NK4(不估算)。
US→EDGAR XBRL;JP→EDINET XBRL(IFRS/JP-GAAP各取)。取最近共同FY算。★机器只算·质性留Opus5(G2)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD      # 复用 _get/cik_map/_series(EDGAR)
import edinet_moat_pull as ED    # 复用 _download_xbrl/_parse/_byyear(EDINET)

US_TAGS = {
    "营业利润": [("us-gaap", "OperatingIncomeLoss"), ("ifrs-full", "ProfitLossFromOperatingActivities")],
    "税前利润": [("us-gaap", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"),
              ("us-gaap", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"),
              ("ifrs-full", "ProfitLossBeforeTax")],
    "所得税": [("us-gaap", "IncomeTaxExpenseBenefit"), ("ifrs-full", "IncomeTaxExpenseContinuingOperations")],
    "股东权益": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "EquityAttributableToOwnersOfParent"), ("ifrs-full", "Equity")],
    # 有息负债components(各求和)
    "债务分项": [("us-gaap", "LongTermDebtNoncurrent"), ("us-gaap", "LongTermDebtCurrent"), ("us-gaap", "ShortTermBorrowings"),
              ("us-gaap", "LongTermDebt"), ("us-gaap", "DebtCurrent"),
              ("ifrs-full", "NoncurrentPortionOfNoncurrentBorrowings"), ("ifrs-full", "CurrentPortionOfNoncurrentBorrowings"),
              ("ifrs-full", "ShorttermBorrowings"), ("ifrs-full", "Borrowings")],
    "现金": [("us-gaap", "CashAndCashEquivalentsAtCarryingValue"), ("ifrs-full", "CashAndCashEquivalents"),
            ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")],
}
# US债务用求和(components)·单值项用_series
US_DEBT_COMPONENTS = ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "ShortTermBorrowings", "DebtCurrent",
                      "NoncurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings", "ShorttermBorrowings"]
JP_TAGS = {
    "IFRS": {"营业利润": ["OperatingProfitLossIFRS", "OperatingIncomeIFRS", "ProfitLossFromOperatingActivitiesIFRS"],
             "税前利润": ["ProfitLossBeforeTaxIFRSSummaryOfBusinessResults", "ProfitLossBeforeTaxIFRS", "ProfitBeforeTaxIFRS"],
             "所得税": ["IncomeTaxExpenseIFRS", "IncomeTaxesIFRS", "TaxExpenseIFRS"],
             "股东权益": ["EquityAttributableToOwnersOfParentIFRSSummaryOfBusinessResults", "EquityAttributableToOwnersOfParentIFRS"],
             # ★有息负债components(CL+NCL求和)
             "债务分项": ["BorrowingsCLIFRS", "BorrowingsNCLIFRS", "InterestBearingLiabilitiesCLIFRS", "InterestBearingLiabilitiesNCLIFRS",
                       "BondsAndBorrowingsCLIFRS", "BondsAndBorrowingsNCLIFRS"],
             "现金": ["CashAndCashEquivalentsIFRS"]},
    "JPGAAP": {"营业利润": ["OperatingIncome"], "税前利润": ["OrdinaryIncome", "IncomeBeforeIncomeTaxes"],
               "所得税": ["IncomeTaxes", "IncomeTaxesCurrent"], "股东权益": ["NetAssets", "ShareholdersEquity"],
               "债务分项": ["ShortTermLoansPayable", "LongTermLoansPayable", "BondsPayable", "CurrentPortionOfLongTermLoansPayable",
                        "CurrentPortionOfBonds", "CommercialPapersLiabilities"],
               "现金": ["CashAndDeposits", "CashAndCashEquivalents"]},
}


def _us_series(cik, tags, instant=False):
    ser, _ = MD._series(cik, tags, instant=instant)
    return MD._byfy(ser)


def _us_debt_sum(cik):
    """有息负债=各component求和(按fy)。返回{fy:sum}·有值的fy才计。"""
    comp = {}
    for tag in US_DEBT_COMPONENTS:
        tx = "ifrs-full" if tag in ("NoncurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings", "ShorttermBorrowings") else "us-gaap"
        s = _us_series(cik, [(tx, tag)], instant=True)
        for y, v in s.items():
            comp.setdefault(y, 0.0)
            comp[y] += (v or 0)
    return comp


def roic_us(cik):
    op = _us_series(cik, US_TAGS["营业利润"]); pre = _us_series(cik, US_TAGS["税前利润"])
    tax = _us_series(cik, US_TAGS["所得税"]); eq = _us_series(cik, US_TAGS["股东权益"], True)
    debt = _us_debt_sum(cik); cash = _us_series(cik, US_TAGS["现金"], True)
    # ★取【营业利润+权益+有息负债】三项俱全的最近FY(某些公司最新年清偿了债务只在前年披露)
    yrs = sorted(set(op) & set(eq) & set(debt))
    if not yrs:
        if not (set(op) & set(eq)):
            return {"ROIC": "NK4", "缺": "营业利润或股东权益取不到"}
        return {"ROIC": "NK4", "缺": "有息负债分项(无标准debt标签)"}
    y = yrs[-1]
    tr = (tax[y] / pre[y]) if (y in tax and pre.get(y)) else None
    if tr is None:
        return {"ROIC": "NK4", "FY": y, "缺": "有效税率(税前/所得税缺)"}
    nopat = op[y] * (1 - tr)
    ic = eq[y] + debt[y] - (cash.get(y, 0) or 0)
    if ic <= 0:
        return {"ROIC": "NK4", "FY": y, "缺": "投入资本≤0(异常)", "投入资本": round(ic)}
    return {"ROIC": round(nopat / ic, 4), "FY": y, "NOPAT": round(nopat), "投入资本": round(ic),
            "有效税率": round(tr, 4), "含现金": y in cash}


def roic_jp(doc_id, key):
    try:
        xml = ED._download_xbrl(doc_id, key)
    except Exception as e:
        return {"ROIC": "NK4", "缺": "XBRL下载失败:%s" % repr(e)[:60]}
    if not xml:
        return {"ROIC": "NK4", "缺": "XBRL空"}
    ctxs, facts = ED._parse(xml)
    std = ED._detect_std(facts)
    t = JP_TAGS[std]
    def by(k): return ED._byyear(facts, ctxs, t[k])
    def bysum(names):   # 债务components按year求和
        out = {}
        for f in facts:
            if f["tag"] in set(names) and "_" not in f["ctx"] and "Member" not in f["ctx"]:
                y = ctxs.get(f["ctx"])
                if y:
                    out[y] = out.get(y, 0.0) + (f["val"] or 0)
        return out
    op = by("营业利润"); eq = by("股东权益"); tax = by("所得税"); pre = by("税前利润")
    debt = bysum(t["债务分项"]); cash = by("现金")
    yrs = sorted(set(op) & set(eq) & set(debt))   # ★三项俱全的最近FY
    if not yrs:
        if not (set(op) & set(eq)):
            return {"ROIC": "NK4", "准则": std, "缺": "营业利润或权益取不到(%s)" % std}
        return {"ROIC": "NK4", "准则": std, "缺": "有息负债分项EDINET取不到"}
    y = yrs[-1]
    tr = (tax[y] / pre[y]) if (y in tax and pre.get(y)) else None
    if tr is None:
        return {"ROIC": "NK4", "准则": std, "FY": y, "缺": "有效税率(税前/所得税缺)"}
    ic = eq[y] + debt.get(y, 0) - cash.get(y, 0)
    if ic <= 0:
        return {"ROIC": "NK4", "准则": std, "FY": y, "缺": "投入资本≤0"}
    nopat = op[y] * (1 - tr)
    return {"ROIC": round(nopat / ic, 4), "准则": std, "FY": y, "NOPAT": round(nopat), "投入资本": round(ic), "有效税率": round(tr, 4)}


def _noop():
    pass


def build(dc):
    m = MD.cik_map()
    key = ED._key()
    res = []
    ok = 0
    for code, name, tk in MD.HOLDINGS:
        if tk is not None:
            cik = m.get(tk.upper())
            r = roic_us(cik) if cik else {"ROIC": "NK4", "缺": "无CIK"}
            src = "EDGAR"
        else:
            doc = next((d for c, n, d in ED.JP7 if c == code), None)
            r = roic_jp(doc, key) if doc else {"ROIC": "NK4", "缺": ("私司" if code == "US.SPCX" else "无docID")}
            src = "EDINET"
        if isinstance(r.get("ROIC"), (int, float)):
            ok += 1
        res.append({"代码": code, "名称": name, "源": src, "ROIC结果": r})
    out = {
        "_说明": "★轮153 C ROIC=NOPAT/投入资本。NOPAT=营业利润×(1-有效税率)·投入资本=股东权益+有息负债-现金。★分项取不到→NK4不估算。机器只算·质性留Opus5(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★ROIC算成只数(/20)": ok,
        "逐只": res,
    }
    (ROOT / f"data/opportunity/roic_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★ROIC算成 %d/20" % o["★ROIC算成只数(/20)"])
    for r in o["逐只"]:
        rr = r["ROIC结果"]
        v = rr.get("ROIC")
        print("  %-9s %-8s %s ROIC=%s %s" % (r["代码"], r["名称"], r["源"], v, ("缺:" + rr.get("缺", "") if v == "NK4" else "FY" + str(rr.get("FY", "")))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
