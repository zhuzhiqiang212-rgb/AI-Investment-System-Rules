# -*- coding: utf-8 -*-
"""★轮165 A/B:行业周期位置指标——库存周转天数(DIO) + capex 趋势(★Code只给数·周期位置由董事长判G2)。
DIO = 存货 ÷ 营业成本 × 天数(季~91/年365)。capex=资本开支。
US→EDGAR companyfacts季度(InventoryNet/CostOfRevenue/PaymentsToAcquirePPE·近8-12季)。
JP→EDINET有報年度(棚卸資産/売上原価/設備投資·current+prior·2年·★季度需四半期報告未接→标年度限制)。
★取不到NK4不估算。优先 AMKR / SCREEN(JP.7735) / 爱德万(JP.6857)。"""
import sys, json, time
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
import edinet_moat_pull as ED
import edinet_financials as EF

US_INV = [("us-gaap", "InventoryNet"), ("us-gaap", "InventoryFinishedGoodsNetOfReserves")]
US_COGS = [("us-gaap", "CostOfRevenue"), ("us-gaap", "CostOfGoodsAndServicesSold")]
US_CAPEX = [("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"), ("us-gaap", "PaymentsToAcquireProductiveAssets")]
PRIORITY = ["US.AMKR", "JP.7735", "JP.6857"]
# JP EDINET税目(IFRS/JP-GAAP)
JP_TAGS = {"IFRS": {"存货": ["InventoriesCAIFRS", "InventoriesIFRS", "Inventories"], "营业成本": ["CostOfSalesIFRS", "CostOfSales"],
                    "capex": ["PurchaseOfPropertyPlantAndEquipmentInvCFIFRS", "PaymentsToAcquirePropertyPlantAndEquipmentIFRS"]},
           "JPGAAP": {"存货": ["Inventories", "MerchandiseAndFinishedGoods"], "营业成本": ["CostOfSales"],
                      "capex": ["PurchaseOfPropertyPlantAndEquipmentInvCF", "PaymentsForPurchasesOfPropertyPlantAndEquipment"]}}


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _us_q(cik, tags, instant=False, ndays=(80, 100)):
    facts = MD._companyfacts(cik); allf = facts.get("facts") or {}
    uniq = {}
    for tx, tag in tags:
        d = (allf.get(tx) or {}).get(tag)
        if not d:
            continue
        for unit, vals in (d.get("units") or {}).items():
            for x in vals:
                if str(x.get("form")) not in ("10-Q", "10-K"):
                    continue
                try:
                    if instant:
                        date.fromisoformat(x["end"])
                    else:
                        s = date.fromisoformat(x["start"]); e = date.fromisoformat(x["end"])
                        if not (ndays[0] <= (e - s).days <= ndays[1]):
                            continue
                except Exception:
                    continue
                k = x["end"]
                if k not in uniq or str(x.get("filed")) > str(uniq[k].get("filed", "")):
                    uniq[k] = {"end": k, "val": x.get("val"), "filed": x.get("filed")}
    return sorted(uniq.values(), key=lambda r: r["end"])


def us_metrics(cik):
    inv = {r["end"]: r["val"] for r in _us_q(cik, US_INV, instant=True)}
    cogs = {r["end"]: r["val"] for r in _us_q(cik, US_COGS, instant=False)}
    capex = {r["end"]: r["val"] for r in _us_q(cik, US_CAPEX, instant=False)}
    ends = sorted(set(cogs) & set(inv))[-12:]
    dio = []
    for e in ends:
        if cogs.get(e):
            dio.append({"季末": e, "DIO天": round(inv[e] / cogs[e] * 91.25, 1), "存货": inv[e], "季COGS": cogs[e]})
    cx = [{"季末": e, "capex": capex[e]} for e in sorted(capex)[-12:]]
    return dio, cx


def jp_metrics(doc_id, key):
    try:
        xml = ED._download_xbrl(doc_id, key)
    except Exception:
        return None, None, None
    if not xml:
        return None, None, None
    ctxs, facts = ED._parse(xml); std = ED._detect_std(facts); t = JP_TAGS[std]
    def by(names):
        out = {}
        for f in facts:
            if f["tag"] in set(names) and "_" not in f["ctx"] and "Member" not in f["ctx"]:
                y = ctxs.get(f["ctx"])
                if y:
                    out[y] = f["val"]
        return out
    inv = by(t["存货"]); cogs = by(t["营业成本"]); capex = by(t["capex"])
    dio = []
    for y in sorted(set(inv) & set(cogs))[-4:]:
        if cogs.get(y):
            dio.append({"年": y, "DIO天": round(inv[y] / cogs[y] * 365, 1), "存货": inv[y], "年COGS": cogs[y]})
    # ★capex为现金流出(负值)→取绝对值(投资额·升=投资增加)
    cx = [{"年": y, "capex": abs(capex[y])} for y in sorted(capex)[-4:]] if capex else "NK4(设备投资税目取不到)"
    return dio, cx, std


def _trend(seq, key):
    vals = [s[key] for s in seq if isinstance(s.get(key), (int, float))]
    if len(vals) < 2:
        return "NK4(期数不足)"
    up = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
    down = len(vals) - 1 - up
    last_up = 0
    for i in range(len(vals) - 1, 0, -1):
        if vals[i] > vals[i - 1]:
            last_up += 1
        else:
            break
    last_down = 0
    for i in range(len(vals) - 1, 0, -1):
        if vals[i] < vals[i - 1]:
            last_down += 1
        else:
            break
    d = "升" if vals[-1] > vals[0] else ("降" if vals[-1] < vals[0] else "平")
    return {"首末": "%s→%s" % (round(vals[0], 1), round(vals[-1], 1)), "总体": d, "连升期数": last_up, "连降期数": last_down}


def build(dc):
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    cikm = MD.cik_map()
    key = ED._key()
    res = []
    for code in PRIORITY:
        rec = {"代码": code, "全名": idm.get(code, {}).get("全名", "?")}
        if code.startswith("US."):
            cik = cikm.get(code.split(".")[1].upper())
            if cik:
                dio, cx = us_metrics(cik)
                rec.update({"口径": "US EDGAR季度", "库存周转天数(DIO)": dio or "NK4",
                            "★DIO趋势": _trend(dio, "DIO天"), "capex": cx or "NK4", "★capex趋势": _trend(cx, "capex")})
            else:
                rec["数据"] = "NK4(无CIK)"
        else:
            doc = {"JP.7735": "S100YKTA", "JP.6857": "S100YKTA"}  # placeholder·从edinet_financials取真docID
            docid = _find_jp_doc(code, key)
            if docid:
                dio, cx, std = jp_metrics(docid, key)
                rec.update({"口径": "JP EDINET年度(%s·季度需四半期報告未接)" % std, "库存周转天数(DIO)": dio or "NK4",
                            "★DIO趋势": _trend(dio, "DIO天"), "capex": cx, "★capex趋势": (_trend(cx, "capex") if isinstance(cx, list) else cx)})
            else:
                rec["数据"] = "NK4(EDINET docID取不到)"
        # ★B 组合状态
        dt = rec.get("★DIO趋势"); ct = rec.get("★capex趋势")
        if isinstance(dt, dict) and isinstance(ct, dict):
            rec["★组合状态(Code只给·含义董事长判)"] = "capex%s + 库存%s" % (ct["总体"], dt["总体"])
        res.append(rec)
        time.sleep(0.1)
    out = {
        "_说明": "★轮165 行业周期位置指标(库存周转天数DIO + capex趋势)。★Code只给数值+升降趋势·★周期位置(见顶/见底)由董事长判(G2)。US=EDGAR季度·JP=EDINET年度(季度需四半期報告未接)。取不到NK4。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "优先3只": PRIORITY, "逐只": res,
    }
    (ROOT / f"data/universe/inventory_capex_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


_SEC = None


def _find_jp_doc(code, key):
    global _SEC
    if _SEC is None:
        try:
            _SEC = EF.build_secmap()
        except Exception:
            _SEC = {}
    edc = (_SEC.get(code.split(".")[1][:4], {}) or {}).get("edinet")
    if not edc:
        return None
    try:
        dd = EF.find_annual_doc(edc, key)
        return dd.get("docID") if isinstance(dd, dict) else None
    except Exception:
        return None


# ★JP docID缓存(持仓/焦点·避find_annual_doc慢扫)
JP_DOCID = {"JP.4568": "S100YEY0", "JP.9984": "S100YGH5", "JP.8766": "S100YLS8", "JP.6857": "S100YKTA",
            "JP.8001": "S100YA6H", "JP.7832": "S100YBXE", "JP.7974": "S100Y9NX", "JP.7735": "S100YKTA",
            "JP.7203": "S100Y8NY", "JP.6758": "S100YE2C"}


def build_all(dc, codes):
    """★轮166 B:批量DIO/capex(持仓+⑤候选)。US=EDGAR·JP=缓存docID·HK/无docID=NK4。返回组合计数。"""
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    cikm = MD.cik_map(); key = ED._key()
    res = []
    for code in codes:
        rec = {"代码": code, "全名": idm.get(code, {}).get("全名", "?"), "市场": code.split(".")[0]}
        dt = ct = None
        try:
            if code.startswith("US."):
                cik = cikm.get(code.split(".")[1].upper())
                if cik:
                    dio, cx = us_metrics(cik)
                    dt = _trend(dio, "DIO天") if dio else "NK4"; ct = _trend(cx, "capex") if cx else "NK4"
                else:
                    dt = ct = "NK4(无CIK)"
            elif code.startswith("JP.") and code in JP_DOCID:
                dio, cx, std = jp_metrics(JP_DOCID[code], key)
                dt = _trend(dio, "DIO天") if dio else "NK4"; ct = _trend(cx, "capex") if isinstance(cx, list) else "NK4"
            else:
                dt = ct = "NK4(HK/无docID·无keyless库存源)"
        except Exception as e:
            dt = ct = "NK4(异常%s)" % repr(e)[:30]
        combo = "NK4"
        if isinstance(dt, dict) and isinstance(ct, dict):
            combo = "capex%s+库存%s" % (ct["总体"], dt["总体"])
        rec.update({"DIO趋势": dt, "capex趋势": ct, "★组合状态": combo})
        res.append(rec)
        time.sleep(0.05)
    # 四组合计数
    from collections import Counter
    cc = Counter(r["★组合状态"] for r in res)
    danger = [r for r in res if r["★组合状态"] == "capex升+库存升"]
    out = {
        "_说明": "★轮166 B 全持仓+⑤候选 DIO/capex组合。★capex升+库存升=最危险(产能开出需求已走弱)。US=EDGAR季度·JP=缓存docID年度·HK/无docID=NK4(无keyless库存源)。★Code只给组合·周期位置董事长判(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "对象数": len(res),
        "★四组合计数": {k: cc.get(k, 0) for k in ["capex升+库存降", "capex升+库存升", "capex降+库存降", "capex降+库存升"]},
        "★★capex升+库存升(最危险)": [{"代码": r["代码"], "全名": r["全名"]} for r in danger],
        "NK4数": cc.get("NK4", 0),
        "逐只": res,
    }
    (ROOT / f"data/universe/inventory_capex_all_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--all", action="store_true"); a = ap.parse_args()
    if a.all:
        import glob as _g
        hold = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758", "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK", "US.TSM", "US.META", "US.IBKR", "US.SPCX"]
        cls = _rj(_latest("data/universe/classified_*.json")); ff = _rj(_latest("data/universe/funnel_full_*.json"))
        types = ff["types"]; g3 = ff["gate3"]
        cand = set()
        for b in ["AI云·数据中心", "AI应用软件"]:
            for c in cls["★各板块归出"][b]["全量code(供分层筛选·不进产品)"]:
                if types.get(c, {}).get("type") == "成长股" and g3.get(c, {}).get("过第3关"):
                    cand.add(c)
        codes = list(dict.fromkeys(hold + sorted(cand)))
        o = build_all(a.date.replace("-", ""), codes)
        print("对象", o["对象数"], "· 四组合", o["★四组合计数"], "· 最危险(capex升+库存升)", len(o["★★capex升+库存升(最危险)"]), "· NK4", o["NK4数"])
        return 0
    o = build(a.date.replace("-", ""))
    for r in o["逐只"]:
        print("%s %s:" % (r["代码"], r["全名"][:18]))
        print("   DIO趋势:", r.get("★DIO趋势"))
        print("   capex趋势:", r.get("★capex趋势"), "· 组合:", r.get("★组合状态(Code只给·含义董事长判)", "NK4"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
