# -*- coding: utf-8 -*-
"""★轮159 B:异动股财报数据(供Opus5判利好利空·★Code只给数据不判)。
对有公告的US异动·EDGAR companyfacts(bulk·轮156证稳)拉最新季报:营收/净利同比(vs去年同季)·毛利率。
★vs市场预期=NK4(EDGAR无consensus·不估算)。指引=NK4(非XBRL结构化·不估算)。★仍不判利好利空——给数据Opus5判(G2)。"""
import sys, json, time
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import moat_data_pull as MD
import yahoo_financials as YF

REV = [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"), ("us-gaap", "Revenues"), ("us-gaap", "SalesRevenueNet")]
NI = [("us-gaap", "NetIncomeLoss")]
COGS = [("us-gaap", "CostOfRevenue"), ("us-gaap", "CostOfGoodsAndServicesSold"), ("us-gaap", "CostOfGoodsAndServicesSoldExcludingDepreciationDepletionAndAmortization")]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _quarterly(cik, tags):
    """季度序列(10-Q/10-K·区间~90天)→[{end,val}]按end升序。合并备选标签。"""
    facts = MD._companyfacts(cik)
    allf = facts.get("facts") or {}
    uniq = {}
    for tx, tag in tags:
        d = (allf.get(tx) or {}).get(tag)
        if not d:
            continue
        for unit, vals in (d.get("units") or {}).items():
            for x in vals:
                if str(x.get("form")) not in ("10-Q", "10-K"):
                    continue
                s, e = x.get("start"), x.get("end")
                if not (s and e):
                    continue
                try:
                    dd = (date.fromisoformat(e) - date.fromisoformat(s)).days
                except Exception:
                    continue
                if not (80 <= dd <= 100):   # 单季~90天
                    continue
                k = e
                if k not in uniq or str(x.get("filed")) > str(uniq[k].get("filed", "")):
                    uniq[k] = {"end": e, "val": x.get("val"), "filed": x.get("filed")}
    return sorted(uniq.values(), key=lambda r: r["end"])


def _yoy(series):
    """最新季 vs 去年同季(end月份相同·约365天前)。返回(最新, 去年同季, 同比%)。"""
    if not series:
        return None, None, None
    latest = series[-1]
    le = date.fromisoformat(latest["end"])
    prior = None
    for r in series[:-1]:
        re_ = date.fromisoformat(r["end"])
        if 350 <= (le - re_).days <= 380 and re_.month == le.month:
            prior = r
    if prior and prior["val"]:
        yoy = round((latest["val"] - prior["val"]) / abs(prior["val"]) * 100, 1)
    else:
        yoy = None
    return latest, prior, yoy


def build(dc):
    ann = _rj(_latest("data/universe/announcements_*.json")).get("逐只公告", {}) or {}
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    # 有公告的US异动
    targets = [c for c, v in ann.items() if v.get("公告") and c.startswith("US.")]
    cikm = MD.cik_map()
    res = []
    for code in targets:
        sym = code.split(".")[1]
        cik = cikm.get(sym.upper())
        rec = {"代码": code, "公司全名": idm.get(code, {}).get("全名", "?"), "公告": [h["日期"] + " " + h["类型"] for h in ann[code]["公告"][:3]]}
        if not cik:
            rec["财报数据"] = "NK4(无CIK)"; res.append(rec); continue
        rq = _quarterly(cik, REV); nq = _quarterly(cik, NI); cq = _quarterly(cik, COGS)
        rl, rp, ryoy = _yoy(rq); nl, np_, nyoy = _yoy(nq)
        gm = None
        if rl and cq:
            cmatch = next((c for c in cq if c["end"] == rl["end"]), None)
            if cmatch and rl["val"]:
                gm = round((rl["val"] - cmatch["val"]) / rl["val"], 4)
        rec["财报数据(季·Code只给不判)"] = {
            "最新季末": rl["end"] if rl else "NK4",
            "营收_最新季": rl["val"] if rl else "NK4", "营收_去年同季": rp["val"] if rp else "NK4", "★营收同比%": ryoy if ryoy is not None else "NK4",
            "净利_最新季": nl["val"] if nl else "NK4", "净利_去年同季": np_["val"] if np_ else "NK4", "★净利同比%": nyoy if nyoy is not None else "NK4",
            "毛利率_最新季": gm if gm is not None else "NK4",
            "★vs市场预期(轮160·Yahoo consensus)": YF.get_consensus(code),
            "★指引变化": "见guidance文件(轮160·8-K EX-99.1提取)",
        }
        res.append(rec)
        time.sleep(0.1)
    got = sum(1 for r in res if isinstance(r.get("财报数据(季·Code只给不判)"), dict) and isinstance(r["财报数据(季·Code只给不判)"].get("★营收同比%"), (int, float)))
    out = {
        "_说明": "★轮159 异动股财报数据(有公告US异动)。EDGAR companyfacts季度·营收/净利同比+毛利率。★vs预期/指引=NK4不估算。★Code只给数据不判利好利空(G2·Opus5判)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "对象数": len(res), "营收同比取到": got,
        "逐只": res,
    }
    (ROOT / f"data/universe/anomaly_earnings_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("异动财报对象 %d · 营收同比取到 %d" % (o["对象数"], o["营收同比取到"]))
    for r in o["逐只"]:
        d = r.get("财报数据(季·Code只给不判)")
        if isinstance(d, dict):
            print("  %-9s %-24s 营收同比%s%% 净利同比%s%% 毛利率%s" % (
                r["代码"], r["公司全名"][:24], d["★营收同比%"], d["★净利同比%"], d["毛利率_最新季"]))
        else:
            print("  %-9s %s" % (r["代码"], d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
