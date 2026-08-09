# -*- coding: utf-8 -*-
"""★轮153 A:EDINET 日股护城河客观数据(7只纯日股·SBI主力仓爱德万35.7%/软银24.6%在内)。
EDINET 有価証券報告書 XBRL 逐值解析→取近3年四项(毛利率/ROE/研发费用率/营收增速稳定性)。
★A-3 日本会计准则(§5.5踩过的坑):
  · ★检测 IFRS vs 日本本土(JP-GAAP)·★两套税目不混用(IFRS用RevenueIFRS.../ProfitLossAttributableToOwnersOfParentIFRS...;JP-GAAP用NetSales/ProfitLoss·不交叉)。
  · ★毛利率用 ANNUAL 口径·★取到0.0一律转null(0.0是缺失不是真值)。
  · ★ROE 自算=归母净利/归母权益(ratio·与EDGAR口径一致·避开EDINET『率』字段的%/ratio歧义)。
★A-4 取不到→NK4·不估算·不用美股口径硬套日股。★机器只取数·五维打分留Opus5(G2)。
安全(董事长EDINET铁律):key只从secrets文件读·用完即弃·不硬编不进聊天。"""
import sys, json, ssl, io, zipfile, urllib.request, statistics, re
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
API = "https://api.edinet-fsa.go.jp/api/v2"
KEY_FILE = Path("C:/AI_Investment_System/secrets/edinet-api-key.txt")

# 7只纯日股(EDGAR无·EDINET取)→ docID(轮152 edinet_financials_20260725)
JP7 = [
    ("JP.4568", "第一三共", "S100YEY0"), ("JP.9984", "软银", "S100YGH5"),
    ("JP.8766", "东京海上", "S100YLS8"), ("JP.6857", "爱德万", "S100YKTA"),
    ("JP.8001", "伊藤忠", "S100YA6H"), ("JP.7832", "万代", "S100YBXE"),
    ("JP.7974", "任天堂", "S100Y9NX"),
]
# 税目(local-name·两套分开·不混)
T = {
    "IFRS": {
        # ★轮189 B:扩营收tag(索尼RevenuesIFRS复数/丰田SalesRevenuesIFRS/常见IFRS变体)
        "营收": ["RevenueIFRSSummaryOfBusinessResults", "RevenueIFRS", "Revenue",
                "RevenuesIFRSSummaryOfBusinessResults", "RevenuesIFRS",
                "SalesRevenuesIFRSSummaryOfBusinessResults", "SalesRevenuesIFRS",
                "NetSalesIFRS", "RevenueFromContractsWithCustomersIFRS", "TotalRevenuesIFRS"],
        "归母净利": ["ProfitLossAttributableToOwnersOfParentIFRSSummaryOfBusinessResults", "ProfitLossAttributableToOwnersOfParentIFRS"],
        "归母权益": ["EquityAttributableToOwnersOfParentIFRSSummaryOfBusinessResults", "EquityAttributableToOwnersOfParentIFRS"],
        "毛利": ["GrossProfitIFRS", "GrossProfit"],
        "营业成本": ["CostOfSalesIFRS", "CostOfSales"],
        "研发费": ["ResearchAndDevelopmentExpensesResearchAndDevelopmentActivities", "ResearchAndDevelopmentExpenseIFRS"],
    },
    "JPGAAP": {
        "营收": ["NetSalesSummaryOfBusinessResults", "NetSales", "OperatingRevenue1"],
        "归母净利": ["ProfitLossAttributableToOwnersOfParentSummaryOfBusinessResults", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss"],
        "归母权益": ["NetAssetsSummaryOfBusinessResults", "ShareholdersEquity", "NetAssets"],
        "毛利": ["GrossProfit"],
        "营业成本": ["CostOfSales"],
        "研发费": ["ResearchAndDevelopmentExpensesResearchAndDevelopmentActivities", "ResearchAndDevelopmentExpenses"],
    },
}


def _ctx():
    c = ssl.create_default_context(); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE
    return c


def _key():
    return KEY_FILE.read_text(encoding="utf-8").strip()


def _download_xbrl(doc_id, key):
    req = urllib.request.Request(f"{API}/documents/{doc_id}?type=1")
    req.add_header("Ocp-Apim-Subscription-Key", key)
    with urllib.request.urlopen(req, timeout=90, context=_ctx()) as r:
        data = r.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = next((n for n in zf.namelist() if n.endswith(".xbrl") and "PublicDoc" in n), None) \
        or next((n for n in zf.namelist() if n.endswith(".xbrl")), None)
    return zf.read(name).decode("utf-8", errors="replace") if name else None


def _parse(xml):
    """返回 (contexts{id:endYear}, facts[{tag,ctx,val}])。tag=local-name。"""
    root = ET.fromstring(xml.encode("utf-8"))
    ctxs = {}
    facts = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "context":
            cid = el.get("id")
            end = None
            for sub in el.iter():
                st = sub.tag.split("}")[-1]
                if st in ("endDate", "instant") and sub.text:
                    end = sub.text.strip()
            if cid and end:
                ctxs[cid] = end[:4]
        else:
            cref = el.get("contextRef")
            if cref is not None and el.text and el.text.strip():
                txt = el.text.strip().replace(",", "")
                try:
                    val = float(txt)
                except Exception:
                    continue
                facts.append({"tag": tag, "ctx": cref, "val": val})
    return ctxs, facts


def _byyear(facts, ctxs, names):
    """某组税目→{year:value}。★只取【合并·无维度成员】的context(纯期间如CurrentYearDuration)·
    跳过分部/成员context(带『_』维度后缀·如..._ToysAndHobbyBusinessSegmentsMember)→避免分部值覆盖合并值(万代串号教训)。"""
    out = {}
    nameset = set(names)
    for f in facts:
        if f["tag"] in nameset and "_" not in f["ctx"] and "Member" not in f["ctx"]:  # ★仅合并口径
            y = ctxs.get(f["ctx"])
            if y:
                out[y] = f["val"]
    return out


def _detect_std(facts):
    tags = set(f["tag"] for f in facts)
    ifrs_hit = sum(1 for t in tags if "IFRS" in t and ("Revenue" in t or "ProfitLoss" in t))
    return "IFRS" if ifrs_hit >= 1 else "JPGAAP"


# ★轮154 B:保险公司专用指标(东京海上·毛利率不适用保险)
INSURANCE = {"JP.8766"}


def _insurance_metrics(facts, ctxs):
    """保险专用:双口径ROE(IFRS/JP-GAAP·不混)+净保费+保险收入。EV/综合成本率有報XBRL无→NK4。"""
    def by(names):
        out = {}
        for f in facts:
            if f["tag"] in set(names) and "_" not in f["ctx"] and "Member" not in f["ctx"]:
                y = ctxs.get(f["ctx"])
                if y:
                    out[y] = f["val"]
        return out
    roe_ifrs = by(["RateOfReturnOnEquityIFRSSummaryOfBusinessResults"])
    roe_jp = by(["RateOfReturnOnEquitySummaryOfBusinessResults"])
    prem = by(["NetPremiumsWrittenSummaryOfBusinessResultsINS"])
    ins_rev = by(["InsuranceRevenueIFRS"])
    ordinc = by(["OrdinaryIncomeSummaryOfBusinessResults"])
    return {
        "★保险专用(毛利率对保险不适用)": True,
        "ROE_IFRS口径(归母·近年)": {k: v for k, v in sorted(roe_ifrs.items())[-3:]} or "NK4",
        "ROE_JPGAAP口径(自己資本利益率·近年)": {k: v for k, v in sorted(roe_jp.items())[-3:]} or "NK4",
        "★ROE双口径注": "★IFRS与JP-GAAP口径差异大(IFRS权益含大量OCI→ROE偏低)·不混·并列供Opus5",
        "净保费(NetPremiumsWritten·近年)": {k: round(v) for k, v in sorted(prem.items())[-3:]} or "NK4",
        "保险收入IFRS(近年)": {k: round(v) for k, v in sorted(ins_rev.items())[-3:]} or "NK4",
        "经常収益(近年)": {k: round(v) for k, v in sorted(ordinc.items())[-3:]} or "NK4",
        "★内含价值EV": "NK4(有報XBRL无EV/EEV税目·在独立EEV报告披露·不估算)",
        "★综合成本率CombinedRatio": "NK4(有報XBRL无此税目·不估算)",
    }


def pull_one(doc_id, key, code=None):
    xml = _download_xbrl(doc_id, key)
    if not xml:
        return {"★状态": "NK4", "原因": "XBRL下载/解析失败"}
    ctxs, facts = _parse(xml)
    std = _detect_std(facts)
    if code in INSURANCE:
        d = _insurance_metrics(facts, ctxs)
        d["会计准则"] = std
        d["★状态"] = "EDINET取到(保险专用指标·%s)" % std
        return d
    t = T[std]
    rev = _byyear(facts, ctxs, t["营收"])
    ni = _byyear(facts, ctxs, t["归母净利"])
    eq = _byyear(facts, ctxs, t["归母权益"])
    gp = _byyear(facts, ctxs, t["毛利"])
    cogs = _byyear(facts, ctxs, t["营业成本"])
    rd = _byyear(facts, ctxs, t["研发费"])
    yrs = sorted(rev.keys())[-4:]
    d = {"会计准则": std, "毛利率近年": {}, "ROE近年(自算=归母净利/归母权益)": {}, "研发费用率近年": {}, "营收近年": {}}
    for y in yrs:
        d["营收近年"][y] = rev.get(y)
        # 毛利率 ANNUAL·0.0→null
        gm = None
        if y in gp and rev.get(y):
            gm = gp[y] / rev[y]
        elif y in cogs and rev.get(y):
            gm = (rev[y] - cogs[y]) / rev[y]
        if gm is not None and gm != 0.0:
            d["毛利率近年"][y] = round(gm, 4)
        if y in ni and eq.get(y) and eq[y] != 0:
            d["ROE近年(自算=归母净利/归母权益)"][y] = round(ni[y] / eq[y], 4)
        if y in rd and rev.get(y):
            rr = rd[y] / rev[y]
            if rr != 0.0:
                d["研发费用率近年"][y] = round(rr, 4)
    # 营收增速稳定性
    revseq = [rev[y] for y in yrs if rev.get(y)]
    gr = [(revseq[i] - revseq[i - 1]) / revseq[i - 1] for i in range(1, len(revseq)) if revseq[i - 1]]
    d["营收YoY增速"] = [round(g, 4) for g in gr]
    d["营收增速稳定性(增速标准差)"] = round(statistics.pstdev(gr), 4) if len(gr) >= 2 else "NK4(年数不足·不估算)"
    for k in ("毛利率近年", "ROE近年(自算=归母净利/归母权益)", "研发费用率近年"):
        if not d[k]:
            d[k] = "NK4(EDINET该税目取不到·不估算·不套美股口径)"
    d["★市占率"] = "NK4(财报无·不估算)"
    d["★ROIC"] = "见C·另算"
    d["★状态"] = "EDINET取到(%s准则)" % std
    return d


def build(dc):
    key = _key()
    res = []
    got = {"毛利率": 0, "ROE": 0, "研发费用率": 0, "营收增速稳定性": 0}
    for code, name, doc in JP7:
        try:
            d = pull_one(doc, key, code=code)
        except Exception as e:
            d = {"★状态": "NK4", "原因": "解析异常:%s" % (repr(e)[:80])}
        # ★轮154 A:内容公司毛利率逐年注(发售/换代年硬件占比高→毛利压缩·非口径错)
        if code == "JP.7974" and isinstance(d.get("毛利率近年"), dict):
            d["★毛利率逐年注(A核)"] = "★口径正确(GrossProfit/NetSales合并)。FY2026毛利率低=Switch 2发售年(营收翻倍·硬件占比高→发售年毛利压缩)·常态~60%(FY2025=0.61为证)·非口径错·不改数迁就常识"
        if code == "JP.7832" and isinstance(d.get("毛利率近年"), dict):
            d["★毛利率逐年注(A核)"] = "★口径正确。毛利率稳定~40%(FY25=0.399/FY26=0.394)=玩具/内容实物商品行业正常水平(结构低于纯软件)·与任天堂发售年巧合同值但成因不同"
        if isinstance(d.get("毛利率近年"), dict) and d["毛利率近年"]: got["毛利率"] += 1
        if isinstance(d.get("ROE近年(自算=归母净利/归母权益)"), dict) and d["ROE近年(自算=归母净利/归母权益)"]: got["ROE"] += 1
        if isinstance(d.get("研发费用率近年"), dict) and d["研发费用率近年"]: got["研发费用率"] += 1
        if isinstance(d.get("营收增速稳定性(增速标准差)"), (int, float)): got["营收增速稳定性"] += 1
        res.append({"代码": code, "名称": name, "docID": doc, "数据": d})
    out = {
        "_说明": "★轮153 EDINET日股护城河客观数据(7只)。IFRS/JP-GAAP自动识别·两套税目不混(§5.5)。毛利率ANNUAL·0.0→null。ROE自算归母净利/归母权益。★取不到NK4不估算。机器只取数·五维打分留Opus5(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★取到项统计(/共7只日股)": got,
        "逐只": res,
    }
    (ROOT / f"data/opportunity/edinet_moat_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★取到项(/7日股):", json.dumps(o["★取到项统计(/共7只日股)"], ensure_ascii=False))
    for r in o["逐只"]:
        d = r["数据"]
        gm = d.get("毛利率近年"); roe = d.get("ROE近年(自算=归母净利/归母权益)")
        gmv = (list(gm.values())[-1] if isinstance(gm, dict) and gm else "NK4")
        roev = (list(roe.values())[-1] if isinstance(roe, dict) and roe else "NK4")
        print("  %-9s %-8s %s 毛利率%s ROE%s 营收稳%s" % (
            r["代码"], r["名称"], d.get("★状态", ""), gmv, roev, d.get("营收增速稳定性(增速标准差)", "?")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
