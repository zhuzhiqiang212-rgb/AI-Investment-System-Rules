# -*- coding: utf-8 -*-
"""尺B(41号)·控股型/净资产驱动标的估值尺。适用:normal_eps=null 或 双口径差>30%。
三层法(取代『在多个NAV口径里挑一个』):
 第一层·硬 = Σ(已上市持股市价×比例) − 抵押负债 ÷ 发行股数 = 每股可验证下限(★股数取权威源·禁市值反推)
 第二层·软 = 未上市资产【只给区间·禁取中值】
 第三层·判断 = 当日价 ÷ 第一层下限 = R → 按区间给动作
★第一层数据缺失→标『待取数』列缺项·禁退回挑口径。Code只实现尺·不写投资结论。
输入:data/valuation/holdco_inputs_{date}.json;输出:data/valuation/ruler_b_{code}_{date}.json。"""
import json, argparse, pathlib
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent

def layer1(spec):
    """第一层每股下限。需:发行股数(权威·禁反推)+各已上市持股(市价×比例)+抵押负债。缺任一→待取数。"""
    missing = []
    shares = spec.get("发行股数_权威源")
    if not shares or spec.get("发行股数_来源") in (None, "", "市值反推"):
        missing.append("发行股数(权威源·禁市值反推)")
    listed = spec.get("已上市持股", [])
    total = 0.0; terms = []
    for h in listed:
        mv, ratio = h.get("市值"), h.get("持股比例")
        if mv is None or ratio is None:
            missing.append("已上市持股[%s]的市值或比例" % h.get("名", "?"))
        else:
            v = mv * ratio; total += v
            terms.append("%s 市值%.4g×比例%.2f=%.4g" % (h.get("名", "?"), mv, ratio, v))
    debt = spec.get("抵押负债")
    if debt is None:
        missing.append("以这些股票为抵押的负债")
    if missing:
        return None, missing, terms
    per = (total - debt) / shares
    return per, [], terms + ["减抵押负债%.4g" % debt, "÷发行股数%.4g" % shares]

def build_one(spec):
    per_low, missing, terms = layer1(spec)
    res = {"标的": spec["code"], "名称": spec.get("name", ""), "尺": "B·控股型/净资产驱动估值尺(41号)",
           "适用判据": spec.get("适用理由", "normal_eps=null 或 双口径差>30%"),
           "第一层·硬(每股可验证下限)": {"算式项": terms, "每股下限": (round(per_low) if per_low else None),
                              "数据来源要求": "★股数必须权威源·禁市值反推;持股市价用当日公开价;负债用公司披露"},
           "第二层·软(未上市资产·只给区间禁取中值)": spec.get("第二层未上市资产区间", {"下限": None, "上限": None, "构成": "待取", "★注": "禁取中值当单一答案"}),
           "第三层·判断(R=当日价÷第一层下限)": None,
           "生成": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")}
    if missing:
        res["★待取数"] = {"缺项": missing, "处置": "★标待取数·不退回『在两个NAV口径里挑一个』(B3/B4④)·取到即可算第一层与R"}
        res["第三层·判断(R=当日价÷第一层下限)"] = "待第一层数据取齐后算"
    else:
        px = spec["当日价"]; R = px / per_low
        lo = spec.get("第二层未上市资产区间", {}).get("下限占比", 0)
        hi = spec.get("第二层未上市资产区间", {}).get("上限占比", 0)
        zone = ("★未上市资产等于免费送→强买入区(R<1.0)" if R < 1.0 else
                ("合理偏低(1.0≤R<1+第二层下限占比)" if R < 1 + lo else
                 ("贵(R>1+第二层上限占比)" if R > 1 + hi else "区间内·中性")))
        res["第三层·判断(R=当日价÷第一层下限)"] = {"当日价": px, "第一层下限": round(per_low), "R": round(R, 3), "所处区间": zone}
    return res

def build(date):
    src = ROOT / "data" / "valuation" / f"holdco_inputs_{date}.json"
    if not src.exists():
        return [], "无 holdco_inputs_%s.json" % date
    specs = json.loads(src.read_text(encoding="utf-8")).get("holdcos", [])
    out = []
    for s in specs:
        r = build_one(s)
        (ROOT / "data" / "valuation").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "valuation" / f"ruler_b_{s['code'].replace('.', '_')}_{date}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(r)
    return out, None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d")); a = ap.parse_args()
    res, note = build(a.date)
    if note: print(note)
    for r in res:
        print("尺B · %s %s" % (r["标的"], r["名称"]))
        if "★待取数" in r:
            print("  ★待取数·缺:", r["★待取数"]["缺项"])
            print("  处置:", r["★待取数"]["处置"][:60])
        else:
            print("  第一层每股下限=", r["第一层·硬(每股可验证下限)"]["每股下限"], "· 第三层:", r["第三层·判断(R=当日价÷第一层下限)"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
