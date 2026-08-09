# -*- coding: utf-8 -*-
"""★轮152 B:护城河客观数据(第一批=现有持仓20只·供Opus5五维打分托底·★机器只取数不判质性G2)。
取(近3年·对应通用五维·非公用事业):
  · 毛利率 =(营收-营业成本)/营收        —— 成本优势
  · ROE = 净利/股东权益                   —— ★护城河结果指标(真有护城河才长期维持高回报)
  · 研发费用率 = 研发费/营收              —— 无形资产/专利
  · 营收增速稳定性 = 近3年营收YoY增速标准差 —— 转换成本(间接)
  · 市占率 —— ★财报无·标NK4(不估算)
数据源:SEC EDGAR XBRL companyconcept(keyless·US-GAAP + IFRS·覆盖美股 + 有20-F的日股ADR)。
★取不到→标NK4·不估算·不用别的指标代替(董事长铁律)。★ROIC需NOPAT/投入资本口径复杂→标NK4待接·不硬凑。"""
import sys, json, time, urllib.request, statistics
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "AI-Investment-System zhuzhiqiang212@gmail.com"}
CONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/{tx}/{tag}.json"
TICKERS = "https://www.sec.gov/files/company_tickers.json"

# 20持仓 → EDGAR查询ticker(日股用其US ADR·20-F申报者;无US申报者标NK4)
HOLDINGS = [
    ("JP.4568", "第一三共", None), ("US.NVDA", "英伟达", "NVDA"), ("US.MSFT", "微软", "MSFT"),
    ("US.MSTR", "MSTR", "MSTR"), ("US.COIN", "Coinbase", "COIN"), ("JP.9984", "软银", None),
    ("JP.8766", "东京海上", None), ("JP.6758", "索尼", "SONY"), ("JP.6857", "爱德万", None),
    ("JP.7203", "丰田", "TM"), ("JP.8001", "伊藤忠", None), ("JP.7832", "万代", None),
    ("JP.7974", "任天堂", None), ("US.AVGO", "博通", "AVGO"), ("US.CRCL", "Circle", "CRCL"),
    ("US.SNDK", "闪迪", "SNDK"), ("US.TSM", "台积电", "TSM"), ("US.META", "META", "META"),
    ("US.IBKR", "IBKR", "IBKR"), ("US.SPCX", "SpaceX", None),
]
TAGS = {
    "营收": [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"), ("us-gaap", "Revenues"),
            ("us-gaap", "RevenuesNetOfInterestExpense"), ("us-gaap", "SalesRevenueNet"), ("ifrs-full", "Revenue")],
    "营业成本": [("us-gaap", "CostOfRevenue"), ("us-gaap", "CostOfGoodsAndServicesSold"), ("ifrs-full", "CostOfSales")],
    "净利": [("us-gaap", "NetIncomeLoss"), ("ifrs-full", "ProfitLoss")],
    "股东权益": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "Equity")],
    "研发费": [("us-gaap", "ResearchAndDevelopmentExpense"), ("ifrs-full", "ResearchAndDevelopmentExpense")],
}


def _get(url):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read())
    except Exception:
        return None


def cik_map():
    d = _get(TICKERS)
    return {str(v["ticker"]).upper(): int(v["cik_str"]) for v in d.values()} if d else {}


_CF_CACHE = {}
COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def _companyfacts(cik):
    """★companyfacts(bulk·一次取全概念)。比companyconcept稳(concept端点对部分公司返空·AMKR/CTSH坑)。缓存per cik。"""
    if cik not in _CF_CACHE:
        _CF_CACHE[cik] = _get(COMPANYFACTS.format(cik=cik)) or {}
        time.sleep(0.15)
    return _CF_CACHE[cik]


def _series(cik, tags, instant=False):
    """取年度序列(10-K/20-F)。★从companyfacts(bulk)取·合并所有备选标签(公司跨年换标签·合并才到最新年)。instant=时点值(权益)。"""
    facts = _companyfacts(cik)
    allf = facts.get("facts") or {}
    uniq = {}
    used = []
    for tx, tag in tags:
        d = (allf.get(tx) or {}).get(tag)
        if not d:
            continue
        hit = False
        for unit, vals in (d.get("units") or {}).items():
            for x in vals:
                if str(x.get("form")) not in ("10-K", "20-F"):
                    continue
                if x.get("fp") not in (None, "FY"):
                    continue
                try:
                    if instant:
                        datetime.fromisoformat(x["end"]).date()
                    else:
                        s = datetime.fromisoformat(x["start"]).date(); e = datetime.fromisoformat(x["end"]).date()
                        if not (330 <= (e - s).days <= 400):
                            continue
                except Exception:
                    continue
                k = x["end"]
                if k not in uniq or str(x.get("filed")) > str(uniq[k]["filed"]):
                    uniq[k] = {"fy": x.get("fy"), "end": x.get("end"), "val": x.get("val"), "filed": x.get("filed"), "tag": f"{tx}:{tag}"}
                    hit = True
        if hit:
            used.append(f"{tx}:{tag}")
    return sorted(uniq.values(), key=lambda r: str(r["end"])), ("+".join(used) if used else "")


def _byfy(series):
    return {r["end"][:4]: r["val"] for r in series if r.get("val") is not None}


def pull_one(cik):
    data = {}
    for name, tags in TAGS.items():
        ser, tag = _series(cik, tags, instant=(name == "股东权益"))
        data[name] = {"byfy": _byfy(ser), "tag": tag}
    # 近3年公共fy(营收在的年)
    rev = data["营收"]["byfy"]; cogs = data["营业成本"]["byfy"]; ni = data["净利"]["byfy"]
    eq = data["股东权益"]["byfy"]; rd = data["研发费"]["byfy"]
    yrs = sorted(rev.keys())[-4:]   # 取4年→算3个YoY增速
    out = {"毛利率近3年": {}, "ROE近3年": {}, "研发费用率近3年": {}, "营收近4年": {}, "ROIC近3年": "NK4(需NOPAT/投入资本口径·不估算)", "市占率": "NK4(财报无·不估算)"}
    for y in yrs:
        out["营收近4年"][y] = rev.get(y)
        if y in cogs and rev.get(y):
            out["毛利率近3年"][y] = round((rev[y] - cogs[y]) / rev[y], 4)
        if y in ni and eq.get(y):
            out["ROE近3年"][y] = round(ni[y] / eq[y], 4)
        if y in rd and rev.get(y):
            out["研发费用率近3年"][y] = round(rd[y] / rev[y], 4)
    # 营收增速稳定性(YoY增速标准差)
    revseq = [rev[y] for y in yrs if rev.get(y)]
    growths = [(revseq[i] - revseq[i - 1]) / revseq[i - 1] for i in range(1, len(revseq)) if revseq[i - 1]]
    out["营收YoY增速"] = [round(g, 4) for g in growths]
    out["营收增速稳定性(增速标准差)"] = round(statistics.pstdev(growths), 4) if len(growths) >= 2 else "NK4(年数不足·不估算)"
    # 缺项标NK4
    for k4, src in [("毛利率近3年", "毛利率近3年"), ("ROE近3年", "ROE近3年"), ("研发费用率近3年", "研发费用率近3年")]:
        if not out[src]:
            out[src] = "NK4(EDGAR无此标签·不估算·不代替)"
    return out, {k: v["tag"] for k, v in data.items()}


def build(dc):
    m = cik_map()
    result = []
    got_stat = {"毛利率": 0, "ROE": 0, "研发费用率": 0, "营收增速稳定性": 0, "市占率": 0, "ROIC": 0}
    for code, name, tk in HOLDINGS:
        if tk is None:
            reason = ("私司无公开财报" if code == "US.SPCX" else "日股无US 20-F申报·EDINET XBRL逐值解析未建")
            result.append({"代码": code, "名称": name, "★状态": "NK4(全项待接)", "原因": reason,
                           "四项数据": "NK4·不估算"})
            continue
        cik = m.get(tk.upper())
        if not cik:
            result.append({"代码": code, "名称": name, "★状态": "NK4", "原因": f"EDGAR无{tk}的CIK", "四项数据": "NK4"})
            continue
        d, tags = pull_one(cik)
        # 统计取到项
        if isinstance(d["毛利率近3年"], dict) and d["毛利率近3年"]: got_stat["毛利率"] += 1
        if isinstance(d["ROE近3年"], dict) and d["ROE近3年"]: got_stat["ROE"] += 1
        if isinstance(d["研发费用率近3年"], dict) and d["研发费用率近3年"]: got_stat["研发费用率"] += 1
        if isinstance(d["营收增速稳定性(增速标准差)"], (int, float)): got_stat["营收增速稳定性"] += 1
        result.append({"代码": code, "名称": name, "★状态": "EDGAR取到(部分/全)", "CIK": cik,
                       "四项数据(近3年·对应通用五维)": d, "XBRL标签": tags})
    out = {
        "_说明": "★轮152 护城河客观数据(第一批20持仓)。★机器只取数(EDGAR XBRL)不判质性·五维打分由Opus5(G2)。★取不到标NK4·不估算·不代替。ROIC/市占率财报无→NK4。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "对应通用五维": {"毛利率": "成本优势", "ROE": "★护城河结果指标", "研发费用率": "无形资产/专利", "营收增速稳定性": "转换成本(间接)", "市占率": "NK4"},
        "★取到项统计(/共20只·美股+20-F日股)": got_stat,
        "逐只": result,
    }
    (ROOT / f"data/opportunity/moat_data_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★取到项统计(/20只):", json.dumps(o["★取到项统计(/共20只·美股+20-F日股)"], ensure_ascii=False))
    for r in o["逐只"]:
        if "四项数据(近3年·对应通用五维)" in r:
            d = r["四项数据(近3年·对应通用五维)"]
            gm = d["毛利率近3年"]; roe = d["ROE近3年"]
            gmv = (list(gm.values())[-1] if isinstance(gm, dict) and gm else "NK4")
            roev = (list(roe.values())[-1] if isinstance(roe, dict) and roe else "NK4")
            print("  %-9s %-8s 毛利率%s ROE%s 营收稳定性%s" % (r["代码"], r["名称"], gmv, roev, d["营收增速稳定性(增速标准差)"]))
        else:
            print("  %-9s %-8s ★%s(%s)" % (r["代码"], r["名称"], r["★状态"], r.get("原因", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
