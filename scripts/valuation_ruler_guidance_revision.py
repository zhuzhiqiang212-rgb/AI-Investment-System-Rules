# -*- coding: utf-8 -*-
"""尺A(41号)·利润指引大幅变动时的重估尺。触发:全年净利指引较上次变动≥15%(上下调同触发)。
算法:P_base=P0×(E1/E0);折扣档由『净利增速 vs 营收增速×1.5』判;四档公允值全部并列。
★个股结论由本脚本按财报事实【算出】·不硬编码任何公允值。Code只实现尺·不写投资结论。
输入:data/valuation/guidance_events_{date}.json(每条=一次财报指引事件的事实:E0/E1/P0/当日价/净利增速/营收增速/需求端证据/辅助扣减)。
输出:data/valuation/ruler_a_{code}_{date}.json(四档公允+采用档+上行+失效条件)。"""
import json, argparse, pathlib
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent
TRIGGER_PCT = 15.0

def base_tier(net_growth, rev_growth, demand_capex):
    """主判据:利润率是否扩张(净利增速 vs 营收增速×1.5)。返回(基准折扣%, 结构判定)。"""
    if net_growth > rev_growth * 1.5:
        struct = "利润率显著扩张·结构性成分为主"
        base = 100 if demand_capex else 90            # 100%仅当结构性扩张 且 需求端有买方capex计划
        return base, struct
    if abs(net_growth - rev_growth) <= max(3.0, rev_growth * 0.15):
        return 80, "纯量增·周期性为主"
    if net_growth < rev_growth:
        return 70, "利润率在压缩·疑似峰值"
    return 80, "介于量增与扩张之间·按周期档"

def compute(ev):
    E0, E1, P0 = float(ev["E0_旧净利指引"]), float(ev["E1_新净利指引"]), float(ev["P0_触发前收盘价"])
    px = float(ev["当日价"])
    guide_chg = (E1 / E0 - 1) * 100
    triggered = abs(guide_chg) >= TRIGGER_PCT
    P_base = P0 * (E1 / E0)
    base, struct = base_tier(float(ev["净利增速pct"]), float(ev["营收增速pct"]), bool(ev.get("需求端买方capex证据", False)))
    aux = ev.get("辅助扣减", [])                        # 每条−5%·下限60%
    adopt = max(60, base - 5 * len(aux))
    tiers = {}
    for d in (100, 90, 80, 70):
        fair = round(P_base * d / 100)
        tiers[str(d) + "%"] = {"公允值": fair, "上行pct": round((fair / px - 1) * 100, 1)}
    adopt_fair = round(P_base * adopt / 100)
    return {
        "标的": ev["code"], "名称": ev.get("name", ""), "触发日": ev.get("date", ""),
        "触发判定": {"指引变动pct": round(guide_chg, 1), "阈值pct": TRIGGER_PCT, "已触发": triggered},
        "输入(财报事实)": {"E0_旧净利指引": E0, "E1_新净利指引": E1, "P0_触发前收盘价": P0, "当日价": px,
                     "净利增速pct": ev["净利增速pct"], "营收增速pct": ev["营收增速pct"],
                     "需求端买方capex证据": ev.get("需求端买方capex证据", False), "辅助扣减": aux},
        "P_base(倒推价·免疫股数错误)": round(P_base),
        "主判据": {"结构判定": struct, "基准折扣pct": base,
                 "辅助扣减": {"条目": aux, "合计pct": -5 * len(aux), "下限": 60}, "采用折扣pct": adopt},
        "★四档公允值全部并列": tiers,
        "采用档": {"折扣pct": adopt, "公允值": adopt_fair, "上行pct": round((adopt_fair / px - 1) * 100, 1)},
        "★标注": "折扣档是判断·不是计算(A4);四档公允值由本尺按财报事实算出·非硬编码",
        "失效条件": "若下季净利增速回落至营收增速以下→折扣档须下调(A4主判据反面);指引再变动≥15%→重新触发本尺",
        "生成": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"), "尺": "A·利润指引大幅变动重估尺(41号)",
    }

def build(date):
    src = ROOT / "data" / "valuation" / f"guidance_events_{date}.json"
    if not src.exists():
        return [], "无 guidance_events_%s.json(当日无≥15%指引变动事件)" % date
    events = json.loads(src.read_text(encoding="utf-8")).get("events", [])
    out = []
    for ev in events:
        ev["date"] = date
        r = compute(ev)
        if r["触发判定"]["已触发"]:
            (ROOT / "data" / "valuation").mkdir(parents=True, exist_ok=True)
            (ROOT / "data" / "valuation" / f"ruler_a_{ev['code'].replace('.', '_')}_{date}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            out.append(r)
    return out, None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d")); a = ap.parse_args()
    res, note = build(a.date)
    if note: print(note)
    for r in res:
        print("尺A · %s %s · 指引变动%+.1f%% · P_base=¥%d · 采用%d%%" % (
            r["标的"], r["名称"], r["触发判定"]["指引变动pct"], r["P_base(倒推价·免疫股数错误)"], r["主判据"]["采用折扣pct"]))
        print("  ★四档公允:", {k: v["公允值"] for k, v in r["★四档公允值全部并列"].items()})
        print("  采用档公允=¥%d · 上行%+.1f%%(对当日¥%.0f)" % (
            r["采用档"]["公允值"], r["采用档"]["上行pct"], r["输入(财报事实)"]["当日价"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
