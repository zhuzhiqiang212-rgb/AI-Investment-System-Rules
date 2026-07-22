#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第2关·财务四柱 + 四象限分池 + 市场确认三状态（派工单C2·2026-07-22）。
对象=gate1_trace过第1关的216只(第1关=激活板块一票否决·已过)。第2关财务扫描=「谁是龙头」工具·不淘汰。
四柱:净利润/营收/毛利率/经营现金流(OCF)·各看同比+加速度。
四象限(F-11·利润为主判据):①强者加速(主池)/②强者减速/③困境反转/④持续恶化(排除)。
市场确认(F-12):已确认/正在确认/未确认·★只标记不淘汰。
守5.5:field_id 8xxx/11xxx不混(逐只数据方案)·毛利率ANNUAL且0.0→null(change_score已做)·
       成交额60日均(硬准入在first_scan·此处四柱为财务)·小样本<10不下结论(行业rollup标注)·覆盖率单列不进总分。
★财务四柱数据源=最新PIT(20260721·财报季度值·非日频)·gate2组装日=20260722·如实标。
用法：python scripts/gate2_score.py --date 20260722 --fin-date 20260721"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def status_of(rel):
    """F-12三状态(同 pool_state.py·口径一致)。"""
    r3 = rel.get("3月"); r1 = rel.get("1月"); r6 = rel.get("6月")
    if r3 is None or r1 is None:
        return "状态数据不足", "缺相对大盘1或3月"
    if r3 > 0:
        return "已确认", "三月跑赢大盘"
    if (r6 is not None and r1 > r6) or (r1 > r3):
        return "正在确认", "三月仍跑输·但近期(1月)相对强度好于前期·在改善"
    return "未确认", "三月跑输·且近期相对强度未见好转"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--fin-date", default="20260721")
    a = ap.parse_args()
    d, fd = a.date, a.fin_date
    sys.stdout.reconfigure(encoding="utf-8")

    gate1 = json.loads((S / f"gate1_trace_{d}.json").read_text(encoding="utf-8"))
    passed = gate1["过第1关名单"]
    trace1 = gate1["逐只轨迹"]
    gen = now()
    g1_time = gate1.get("生成时间")
    after_g1 = (g1_time is not None and gen > g1_time)
    cs = json.loads((S / f"change_score_{fd}.json").read_text(encoding="utf-8"))["scores"]
    q = json.loads((S / f"quadrant_{fd}.json").read_text(encoding="utf-8"))["cards"]
    v2 = json.loads((S / f"candidates_v2_{fd}.json").read_text(encoding="utf-8"))["cards"]

    QNAME = {"①": "强者加速(主池)", "②": "强者减速", "③": "困境反转", "④": "持续恶化(排除)", "—": "无法判定(数据不足)"}
    rows = {}
    for c in passed:
        sc = cs.get(c, {}); ind = sc.get("指标", {})
        qc = q.get(c, {})
        rel = ((v2.get(c, {}).get("市场先行层", {}).get("指标", {}) or {}).get("相对大盘1/3/6月%")) or {}
        st, why = status_of(rel)
        four_have = sum(1 for k in ["利润同比%", "营收同比%", "毛利率同比pp", "OCF同比%"] if ind.get(k) is not None)
        # 毛利率覆盖性质(结构性无营业成本 vs 可得)
        gm = ind.get("毛利率%")
        gm_cov = ("可得" if gm is not None else "结构性无/数据缺失(见change_score毛利率覆盖分解)")
        rows[c] = {
            "code": c,
            "第1关": {"结果": "过", "激活板块": trace1.get(c, {}).get("映射激活板块"),
                    "依据": trace1.get(c, {}).get("第1关依据")},
            "第2关_财务四柱": {
                "净利润": {"同比%": ind.get("利润同比%"), "加速度pp": ind.get("利润加速度pp"),
                        "亏损收窄": ind.get("亏损收窄"), "由亏转盈": ind.get("由亏转盈")},
                "营收": {"同比%": ind.get("营收同比%"), "加速度pp": ind.get("营收加速度pp")},
                "毛利率": {"当前%": gm, "同比pp": ind.get("毛利率同比pp"), "加速度pp": ind.get("毛利率加速度pp"),
                        "趋势": ind.get("毛利率趋势"), "覆盖性质": gm_cov},
                "经营现金流OCF": {"同比%": ind.get("OCF同比%"), "加速度pp": ind.get("OCF加速度pp")},
                "四柱可得数(同比)": four_have,
                "数据方案": sc.get("数据方案"),
                "变化证据得分": sc.get("得分"),
                "数据覆盖率_单列不进总分": sc.get("数据覆盖率"),
                "结论可信度": sc.get("结论可信度"),
                "异常字段": sc.get("异常字段", {}),
            },
            "四象限_F11": {"主象限(利润为主判据)": qc.get("主象限(利润)"), "象限名": QNAME.get(qc.get("主象限(利润)")),
                       "四项象限": qc.get("四项象限"), "象限分歧": qc.get("象限分歧"),
                       "名称行业": qc.get("名称行业"), "常识核对": qc.get("常识核对")},
            "市场确认_F12": {"状态": st, "依据": why, "相对大盘1/3/6月%": rel,
                        "★口径": "只标记不淘汰(F-12)"},
        }

    # ── 四象限分池统计(216内)──
    quad = Counter(rows[c]["四象限_F11"]["主象限(利润为主判据)"] for c in passed)
    pool_main = [c for c in passed if rows[c]["四象限_F11"]["主象限(利润为主判据)"] == "①" and rows[c]["四象限_F11"]["象限分歧"] is False]
    # ①主池(真强者=①且分歧false)·②③④·无法判定
    def bucket(sym):
        return sorted([c for c in passed if rows[c]["四象限_F11"]["主象限(利润为主判据)"] == sym])
    pools = {
        "①强者加速(主池·②注:真主池=①且象限分歧false)": {"象限①总数": quad.get("①", 0),
                                          "其中分歧false(真主池)": len(pool_main), "真主池名单": pool_main},
        "②强者减速": {"数": quad.get("②", 0), "名单": bucket("②")},
        "③困境反转": {"数": quad.get("③", 0), "名单": bucket("③")},
        "④持续恶化(排除)": {"数": quad.get("④", 0), "名单": bucket("④")},
        "—无法判定(数据不足)": {"数": quad.get("—", 0), "名单": bucket("—")},
    }

    # ── 市场确认三状态分布(216内·只标记)──
    st_dist = Counter(rows[c]["市场确认_F12"]["状态"] for c in passed)

    # ── 行业rollup(小样本<10不下结论·守5.5)──
    by_ind = defaultdict(list)
    for c in passed:
        by_ind[rows[c]["四象限_F11"].get("名称行业") or "(未分类)"].append(c)
    ind_roll = []
    for ind, mem in sorted(by_ind.items(), key=lambda kv: -len(kv[1])):
        n = len(mem)
        acc = sum(1 for c in mem if rows[c]["四象限_F11"]["主象限(利润为主判据)"] == "①")
        ind_roll.append({"行业": ind, "216内只数": n, "象限①(加速)只数": acc,
                         "加速占比%": (round(acc / n * 100, 1) if n else None),
                         "★可下结论": (n >= 10), "备注": ("样本≥10·可看趋势" if n >= 10 else "★小样本<10·不下结论(仅记录)")})

    # 可信度分布
    conf = Counter(rows[c]["第2关_财务四柱"]["结论可信度"] for c in passed)

    doc = {
        "_说明": "第2关财务四柱+四象限分池(F-11)+市场确认三状态(F-12)。对象=过第1关216只。财务扫描=谁是龙头工具·不淘汰。",
        "组装日": d, "generated_at": gen,
        "★倒推自检_晚于gate1_trace": {"gate1_trace生成时间": g1_time, "gate2生成时间": gen,
                                "晚于gate1(顺序正确)": after_g1,
                                "结论": ("通过·第2关晚于第1关(顺序时间戳可核·GPT第4验法)" if after_g1 else "★失败·第2关早于/等于第1关=倒推·顺序不成立")},
        "★财务四柱数据源日": fd,
        "★数据日说明": f"四柱(净利/营收/毛利/OCF·同比+加速度)源自最新PIT {fd}(财报季度值·非日频·财报不逐日变)·gate2组装于{d}·如实标·非旧数据顶充完整产品(此为第2关筛选中间件·非五册验收成品)",
        "对象": f"过第1关{len(passed)}只(第1关=激活板块一票否决·已过·见gate1_trace_{d})",
        "守5.5核对": {
            "field_id_8xxx_11xxx不混": "逐只带『数据方案』标识(8xxx美股/IFRS·11xxx日股本土)",
            "毛利率ANNUAL且0.0转null": "已在change_score上游做(0.0→null·ANNUAL口径)",
            "成交额60日均": "硬准入(市值/60日均成交额/OCF>0)在first_scan2完成·第2关四柱为财务指标·不重复",
            "小样本<10不下结论": "行业rollup逐行标『可下结论』布尔·<10仅记录不下结论",
            "覆盖率单列不进总分": "『变化证据得分』与『数据覆盖率』分列·得分不乘覆盖率(F-07第⑤条)",
        },
        "四象限分池(216内)": pools,
        "市场确认三状态分布(216内·只标记不淘汰)": dict(st_dist),
        "结论可信度分布(216内)": dict(conf),
        "行业rollup(小样本<10不下结论)": ind_roll,
        "逐只轨迹(216)": rows,
    }
    p = S / f"gate2_score_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("generated_at:", gen, "· gate1:", g1_time, "· 晚于gate1(顺序):", after_g1)
    print(f"对象216只·四象限: ①{quad.get('①',0)}(真主池{len(pool_main)}) ②{quad.get('②',0)} ③{quad.get('③',0)} ④{quad.get('④',0)} —无法判定{quad.get('—',0)}")
    print("市场确认三状态(只标记):", dict(st_dist))
    print("可信度分布:", dict(conf))
    print("财务数据源日:", fd, "·组装日:", d, "(如实标·非旧顶充成品)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
