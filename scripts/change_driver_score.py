#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变化驱动层：1根柱子→4根（派工单甲·2026-07-21·尺总册G-13·依据F-07双轴/F-08分层）。
★只算不筛选·不出名单·不给买卖建议·不改尺·不自调参数。
四项·每项都要【同比】和【加速度(同比的变化)】：利润/营收/毛利率/经营现金流。
数据源:优先读当日 PIT 存档 data/pit/{date}/statements.jsonl(8xxx+11xxx原样)·缺则跳过标缺失(不补0)。

F-07 双轴(五条铁律)：
 ①缺失数据不计0分(0会把没数据误判成表现差) ②不得把缺失权重静默转给市场确认
 ③不同覆盖率的股票总分不得直接排名 ④覆盖率不足→只进"无法充分判定"/观察池
 ⑤禁止"得分×覆盖率"合并。每张卡同时显示:变化证据得分/数据覆盖率/结论可信度。
F-08 分层(不重复计分)：本模块只产【基本面变化层】(利润加速度/营收加速度/毛利率趋势/OCF加速度/由亏转盈)。
capex 未解出→真自由现金流仍【待查·不采信】。常识核对必做。
用法：python scripts/change_driver_score.py --date 20260721
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"

# 反推映射(F-10·两套):8xxx=US_GAAP/IFRS·11xxx=JGAAP
F = {"8xxx": {"rev": 8001, "gross": 8004, "net": 8037, "ocf": 8015},
     "11xxx": {"rev": 11001, "gross": 11004, "net": 11036, "ocf": 11014}}


def scheme_of(std, item_ids):
    if 8001 in item_ids:
        return "8xxx"
    if 11001 in item_ids:
        return "11xxx"
    return None


def fy_periods(stmt):
    return [r for r in (stmt or {}).get("report_list", []) if "FY" in r.get("period_text", "")]


def get(period, fid):
    for it in period.get("item_list", []):
        if it.get("field_id") == fid:
            return it.get("data"), it.get("yoy")
    return None, None


def load_pit(date):
    p = ROOT / "data" / "pit" / date / "statements.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                out[r["code"]] = r
            except Exception:
                pass
    return out


def metric_score(yoy, accel):
    """单指标机械分(0~100)·仅用于同覆盖率档内参考·不跨档排名。
    象限:同比>0且加速>0(加速成长)高;同比>0加速<0(成长但减速)中上;
    同比<0加速>0(下滑但改善)中下;两负 低。"""
    if yoy is None:
        return None
    base = 50 + max(min(yoy, 60), -60) / 60 * 25            # 同比方向±25
    acc = 0 if accel is None else max(min(accel, 60), -60) / 60 * 25   # 加速度±25
    return round(max(0, min(100, base + acc)), 1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    pit = load_pit(d)
    # 入围池
    try:
        cd = json.loads((SCREEN / "candidates_20260721.json").read_text(encoding="utf-8"))
        inbound = [c["code"] for c in cd.get("candidates", []) if c.get("conclusion") == "入围"]
    except Exception:
        inbound = list(pit.keys())

    cards = {}
    for c in inbound:
        rec = pit.get(c)
        card = {"code": c, "数据方案": None, "变化证据得分": None, "数据覆盖率": None, "结论可信度": None,
                "F08层": "基本面变化层", "指标": {}, "常识核对": []}
        if not rec or (not rec.get("income") and not rec.get("cashflow")):
            card.update({"结论可信度": "无法充分判定(无PIT财报·未计0分)", "数据覆盖率": 0.0})
            cards[c] = card; continue
        inc = rec.get("income") or {}; cf = rec.get("cashflow") or {}
        fys = fy_periods(inc); cfys = fy_periods(cf)
        if not fys:
            card.update({"结论可信度": "无法充分判定(无年报FY)", "数据覆盖率": 0.0}); cards[c] = card; continue
        ids = {it.get("field_id") for it in fys[0].get("item_list", [])}
        sch = scheme_of(inc.get("accounting_standards"), ids)
        card["数据方案"] = sch
        if sch is None:
            card.update({"结论可信度": "无法充分判定(字段方案未识别)", "数据覆盖率": 0.0}); cards[c] = card; continue
        m = F[sch]
        # 取本期与上期FY
        p0 = fys[0]; p1 = fys[1] if len(fys) >= 2 else None
        cf0 = cfys[0] if cfys else None; cf1 = cfys[1] if len(cfys) >= 2 else None

        def yoy_and_accel(period_now, period_prev, fid):
            _, y0 = get(period_now, fid)
            y1 = get(period_prev, fid)[1] if period_prev else None
            accel = (round(y0 - y1, 2) if (y0 is not None and y1 is not None) else None)
            return y0, accel
        # 1 利润(净利)
        p_yoy, p_acc = yoy_and_accel(p0, p1, m["net"])
        # 2 营收
        r_yoy, r_acc = yoy_and_accel(p0, p1, m["rev"])
        # 3 毛利率(pp)+趋势:毛利率=gross/rev 各期
        def gm(period):
            g, _ = get(period, m["gross"]); rv, _ = get(period, m["rev"])
            return (g / rv * 100 if (g is not None and rv not in (None, 0)) else None)
        gm0 = gm(p0); gm1 = gm(p1) if p1 else None
        gm_pp = (round(gm0 - gm1, 2) if (gm0 is not None and gm1 is not None) else None)
        gm_series = [gm(p) for p in fys[:3]]
        gm_trend = ("上行" if (gm_pp is not None and gm_pp > 0.3) else ("下行" if (gm_pp is not None and gm_pp < -0.3) else ("走平" if gm_pp is not None else None)))
        # 4 OCF
        o_yoy, o_acc = (yoy_and_accel(cf0, cf1, m["ocf"]) if cf0 else (None, None))
        # 由亏转盈
        net0 = get(p0, m["net"])[0]; net1 = get(p1, m["net"])[0] if p1 else None
        turn = (net1 is not None and net0 is not None and net1 < 0 <= net0)

        # 常识核对
        flags = []
        if gm0 is not None and not (0 < gm0 < 100):
            flags.append(f"毛利率{round(gm0,1)}%越界·待查")
        if gm0 == 0.0:
            flags.append("毛利率=0.0·疑未取到·待查")
        if r_yoy is not None and abs(r_yoy) > 300:
            flags.append(f"营收同比{round(r_yoy,0)}%异常大·待查")

        subs = {"利润": metric_score(p_yoy, p_acc), "营收": metric_score(r_yoy, r_acc),
                "毛利率": metric_score(gm_pp, None) if gm_pp is not None else None, "OCF": metric_score(o_yoy, o_acc)}
        avail = [v for v in subs.values() if v is not None]
        cov = round(len(avail) / 4, 2)
        score = round(sum(avail) / len(avail), 1) if avail else None   # ★缺失不入分母·不计0(F-07①)
        cred = ("高" if cov >= 0.75 else ("中" if cov >= 0.5 else "低→无法充分判定/观察池"))
        card.update({
            "变化证据得分": score, "数据覆盖率": cov, "结论可信度": cred,
            "指标": {
                "利润同比%": p_yoy, "利润加速度(pp)": p_acc,
                "营收同比%": r_yoy, "营收加速度(pp)": r_acc,
                "毛利率%": (round(gm0, 2) if gm0 is not None else None), "毛利率同比(pp)": gm_pp, "毛利率趋势": gm_trend,
                "OCF同比%": o_yoy, "OCF加速度(pp)": o_acc, "由亏转盈": turn,
            },
            "真自由现金流": "待查·capex未解出·不采信",
            "常识核对": (flags or ["通过·数值在合理区间"]),
        })
        cards[c] = card

    # 汇总(★按覆盖率分档·不跨档排名·F-07③④)
    tiers = {"高(≥0.75)": [], "中(0.5-0.75)": [], "低/无法充分判定(<0.5)": []}
    for c, v in cards.items():
        cov = v.get("数据覆盖率") or 0
        (tiers["高(≥0.75)"] if cov >= 0.75 else tiers["中(0.5-0.75)"] if cov >= 0.5 else tiers["低/无法充分判定(<0.5)"]).append(c)
    flagged = [c for c, v in cards.items() if v.get("常识核对") and not v["常识核对"][0].startswith("通过")]

    doc = {
        "_说明": "变化驱动层·基本面变化层(4根柱子:利润/营收/毛利率/OCF·各同比+加速度+由亏转盈)。"
               "★F-07双轴:缺失不计0·覆盖率独立展示·不同覆盖率不直接排名·禁得分×覆盖率合并·低覆盖进无法充分判定。"
               "★F-08:本模块只此一层·不与市场确认/市场先行/行业扩散层重复计分。真自由现金流待查(capex未解)。",
        "数据源": f"data/pit/{d}/statements.jsonl(8xxx+11xxx原样·当日PIT)",
        "入围只数": len(inbound), "有PIT数据": sum(1 for v in cards.values() if v.get("数据方案")),
        "按覆盖率分档(不跨档排名)": {k: len(v) for k, v in tiers.items()},
        "分档明细": tiers,
        "常识核对待查": flagged,
        "cards": cards,
    }
    p = SCREEN / f"change_driver_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))
    print("入围", len(inbound), "· 有PIT数据", doc["有PIT数据"], "· 覆盖率分档", doc["按覆盖率分档(不跨档排名)"], "· 常识待查", len(flagged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
