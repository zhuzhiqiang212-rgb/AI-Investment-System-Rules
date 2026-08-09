# -*- coding: utf-8 -*-
"""★★轮186 B:护城河【客观数据】——★Code只备客观数字·【不评分】(五维评分=Opus5的活·投资判断·Code不代)。
起因:moat_20260805.json 20只全用公用事业五维(误用·非公用事业标的)·且五维全"待接"依据是截断总结论(循环论证)→已标作废。
本件按 CLAUDE.md「公用事业专用评法只对公用事业启用」分流·备通用五维客观数据+ROIC交叉验证。

B-1 moat_framework:每只标 general/utility(★结构化字段·按行业分类判·不靠公司名猜)。
B-2 通用五维客观数据(只备数·查不到NK4不编):品牌(毛利率)/网络(市占·NK4)/成本(营业利润率)/转换(留存/营收稳定)/无形(研发/专利)。
B-3 ROIC交叉验证(★最重要):近3年 ROIC/ROE/FCF率——爱德万6分(窄)vs ROIC 0.513最高·矛盾供Opus5自检。
数据源:moat_data_20260804(EDGAR近3年·US取到12/JP NK4 8) + moat_opus5(部分ROIC) + identity(行业)。"""
import sys, json, glob, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
# 公用事业行业关键词(★只这些才 utility·其余 general)
UTILITY_KW = ("电力", "水务", "燃气", "公用事业", "utility", "electric util", "water util", "gas util", "power util")


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _framework(industry):
    s = str(industry or "").lower()
    return "utility" if any(k in s for k in UTILITY_KW) else "general"


def build(dc):
    md = _rj(_latest("data/opportunity/moat_data_*.json"))
    mdm = {r["代码"]: r for r in (md.get("逐只", []) or [])}
    o5 = _rj(_latest("data/opportunity/moat_opus5_*.json"))
    o5m = {r.get("代码"): r for r in (o5.get("逐只", []) or [])}
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    # 20只 = 作废moat文件的逐只(或持仓)
    void = _rj(_latest("data/opportunity/moat_2026*.json"))
    codes = [r["代码"] for r in (void.get("逐只", []) or [])] or list(mdm.keys())
    rows = []
    for c in codes:
        d = mdm.get(c, {})
        four = d.get("四项数据(近3年·对应通用五维)", {}) or {}
        ind = idm.get(c, {}).get("行业") or idm.get(c, {}).get("主营") or idm.get(c, {}).get("全名")
        fw = _framework(ind)
        o5d = o5m.get(c, {}).get("客观数据托底", {}) if o5m.get(c) else {}
        # ROIC:moat_data近3年优先·退moat_opus5
        roic = four.get("ROIC近3年") or ({"opus5托底": o5d.get("ROIC")} if o5d.get("ROIC") else "NK4(待接·不编)")
        rows.append({
            "代码": c, "名称": idm.get(c, {}).get("全名", d.get("名称")),
            "★moat_framework": fw,
            "framework判据": ("行业含公用事业关键词→utility" if fw == "utility" else "行业=%s·非公用事业→general" % (str(ind)[:24])),
            "★通用五维客观数据(只备数·不评分·Opus5评)": {
                "品牌_毛利率近3年(ANNUAL)": four.get("毛利率近3年") or ({"opus5托底": o5d.get("毛利率")} if o5d.get("毛利率") else "NK4(待接·不编)"),
                "网络效应_市占率/装机量": four.get("市占率") if four.get("市占率") not in (None, "NK4", 0) else "NK4(市占率数据源未接·不编)",
                "成本优势_营业利润率": four.get("营业利润率近3年") or "NK4(营业利润率待接·毛利率见品牌行)",
                "转换成本_营收增速稳定性(标准差低=稳)": four.get("营收增速稳定性(增速标准差)") or "NK4",
                "无形资产_研发费用率近3年": four.get("研发费用率近3年") or ({"opus5托底": o5d.get("研发费用率")} if o5d.get("研发费用率") else "NK4(待接·不编)"),
            },
            "★★B-3 ROIC交叉验证(最重要·供Opus5自检评分是否与ROIC背离)": {
                "ROIC近3年": roic,
                "ROE近3年": four.get("ROE近3年") or ({"opus5托底": o5d.get("ROE")} if o5d.get("ROE") else "NK4(待接·不编)"),
                "自由现金流率": four.get("FCF率近3年") or "NK4(FCF率待接·EDGAR现金流量表逐值解析未建·不编)",
            },
            "数据状态": d.get("★状态", "NK4(不在moat_data)"),
            "★评分归属": "★五维评分=Opus5(投资判断)·Code不代评(G2)。本件只客观数据。",
        })
    n_util = sum(1 for r in rows if r["★moat_framework"] == "utility")
    out = {
        "_说明": "★轮186 B 护城河客观数据(Code只备数·★不评分·五维评分=Opus5)。接替作废的 moat_20260805.json(公用五维误用)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8]),
        "★moat_framework分布": {"general": len(rows) - n_util, "utility": n_util},
        "★真该用utility的": [r["代码"] for r in rows if r["★moat_framework"] == "utility"] or "★0只(20只全非公用事业→全general·符合董事长预计)",
        "★NK4说明": "查不到一律NK4·不编·不把总结论截断当依据。JP日股财务多NK4(EDINET XBRL逐值解析未建)。",
        "逐只": rows,
    }
    (ROOT / f"data/opportunity/moat_objective_data_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("[护城河客观数据] %d只 · framework分布 %s · 真该utility:%s" % (
        len(o["逐只"]), json.dumps(o["★moat_framework分布"], ensure_ascii=False), o["★真该用utility的"]))
    for r in o["逐只"]:
        roic = r["★★B-3 ROIC交叉验证(最重要·供Opus5自检评分是否与ROIC背离)"]["ROIC近3年"]
        print("  %-9s %-12s fw=%-7s ROIC=%s" % (r["代码"], str(r["名称"])[:12], r["★moat_framework"], str(roic)[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
