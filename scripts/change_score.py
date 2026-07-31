#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变化驱动·四层分类得分（派工单甲·2026-07-21·尺总册G-13·F-07双轴/F-08分层）。
★只算不筛选·不出名单·不给买卖建议·不改尺·不自调参数·不合并成单一总分。
F-08 四层(同一指标只出现在一层·不重复计分)：
  基本面变化层(读PIT财报8xxx/11xxx)：利润/营收/OCF加速度·毛利率趋势·亏损收窄·由亏转盈
  市场先行层(kline vs 指数)：相对强度由负转正·1/3/6月相对强度斜率·放量突破
  市场确认层(earnings_price_move)：财报后跳空·财报后5/20日是否守住·财报后相对大盘
  行业扩散层：需全行业成员kline→本轮未算·如实标覆盖0(F-07④无法充分判定)·非0分
F-07 每层各出：得分/覆盖率/可信度;缺失不计0分;不同覆盖率不直接排名;禁得分×覆盖率合并。
capex未解→真自由现金流仍待查不采信。常识核对必做。
用法：python scripts/change_score.py --date 20260721
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
F = {"8xxx": {"rev": 8001, "gross": 8004, "net": 8037, "ocf": 8015},
     "11xxx": {"rev": 11001, "gross": 11004, "net": 11036, "ocf": 11014}}
IDX = {"US": "US.SPY", "JP": "JP.1329"}


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def sc_dir(x, span=60):
    """方向分:x>0好·映射到0~100(50中性)。"""
    return round(clamp(50 + max(min(x, span), -span) / span * 50), 1) if x is not None else None


def fy(stmt):
    return [r for r in (stmt or {}).get("report_list", []) if "FY" in r.get("period_text", "")]


def it(period, fid):
    for x in period.get("item_list", []):
        if x.get("field_id") == fid:
            return x.get("data"), x.get("yoy")
    return None, None


def layer_credibility(cov):
    return "高" if cov >= 0.75 else ("中" if cov >= 0.5 else "低→无法充分判定")


def load_pit(date):
    p = ROOT / "data" / "pit" / date / "statements.jsonl"
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    r = json.loads(line); out[r["code"]] = r
                except Exception:
                    pass
    return out


def fundamentals_layer(rec):
    """基本面变化层。返回(层dict, 四项覆盖dict[利润/营收/毛利率/OCF], 常识flags)。"""
    flags = []
    if not rec or not rec.get("income"):
        return {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→无法充分判定(无PIT财报)", "指标": {}}, {}, flags
    inc = rec["income"]; cf = rec.get("cashflow") or {}
    ifys = fy(inc); cfys = fy(cf)
    if not ifys:
        return {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→无法充分判定(无年报FY)", "指标": {}}, {}, flags
    ids = {x.get("field_id") for x in ifys[0].get("item_list", [])}
    sch = "8xxx" if 8001 in ids else ("11xxx" if 11001 in ids else None)
    if not sch:
        return {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→字段方案未识别", "指标": {}, "数据方案": None}, {}, flags
    m = F[sch]; p0 = ifys[0]; p1 = ifys[1] if len(ifys) >= 2 else None
    c0 = cfys[0] if cfys else None; c1 = cfys[1] if len(cfys) >= 2 else None

    def yac(a, b, fid):
        y0 = it(a, fid)[1]
        y1 = it(b, fid)[1] if b else None
        return y0, (round(y0 - y1, 2) if (y0 is not None and y1 is not None) else None)
    p_y, p_a = yac(p0, p1, m["net"])
    r_y, r_a = yac(p0, p1, m["rev"])
    o_y, o_a = (yac(c0, c1, m["ocf"]) if c0 else (None, None))

    def gm(p):
        g = it(p, m["gross"])[0]; rv = it(p, m["rev"])[0]
        return (g / rv * 100 if (g is not None and rv not in (None, 0)) else None)
    p2 = ifys[2] if len(ifys) >= 3 else None
    gm0 = gm(p0); gm1 = gm(p1) if p1 else None; gm2 = gm(p2) if p2 else None
    gm_pp = (round(gm0 - gm1, 2) if (gm0 is not None and gm1 is not None) else None)
    gm_pp_prev = (gm1 - gm2 if (gm1 is not None and gm2 is not None) else None)
    gm_accel = (round(gm_pp - gm_pp_prev, 2) if (gm_pp is not None and gm_pp_prev is not None) else None)  # 毛利率加速度(pp的变化)
    gm_trend = ("上行" if (gm_pp is not None and gm_pp > 0.3) else "下行" if (gm_pp is not None and gm_pp < -0.3) else ("走平" if gm_pp is not None else None))
    net0 = it(p0, m["net"])[0]; net1 = it(p1, m["net"])[0] if p1 else None
    turn = (net1 is not None and net0 is not None and net1 < 0 <= net0)
    narrow = (net1 is not None and net0 is not None and net1 < 0 and net0 < 0 and net0 > net1)
    # 常识核对 + 异常字段标注(问题3:同比绝对值>500%→异常·待查)
    anom_fields = {}
    if gm0 is not None and not (0 < gm0 < 100) and gm0 != 0.0:
        flags.append(f"毛利率{round(gm0,1)}%越界"); anom_fields["毛利率%"] = "越界·待查"
    if gm0 == 0.0:
        flags.append("毛利率=0.0疑假"); anom_fields["毛利率%"] = "=0.0疑假·待查"
    for lbl, key, y in [("营收同比", "营收同比%", r_y), ("利润同比", "利润同比%", p_y), ("OCF同比", "OCF同比%", o_y)]:
        if y is not None and abs(y) > 500:
            flags.append(f"{lbl}{round(y,0)}%>±500%·异常"); anom_fields[key] = f"{round(y,0)}%>±500%·异常·待查·打分已截尾"
    # 四项子分:优先用加速度·缺则退同比;★截尾(winsorize)防极端值扭曲(sc_dir 已 clamp·此处显式记)
    subs = {"利润": sc_dir(p_a if p_a is not None else p_y), "营收": sc_dir(r_a if r_a is not None else r_y),
            "毛利率": sc_dir(gm_pp), "OCF": sc_dir(o_a if o_a is not None else o_y)}
    avail = {k: v for k, v in subs.items() if v is not None}
    cov = round(len(avail) / 4, 2)
    score = round(sum(avail.values()) / len(avail), 1) if avail else None
    n_bars = len(avail)                                            # 有柱子(同比或加速度)的项数
    n_accel = sum(1 for x in (p_a, r_a, o_a, gm_pp) if x is not None)   # 有加速度的项数
    # ★可信度(问题2):同时看 柱子数 + 加速度数 + 是否有异常(暂行档·待架构师复核)
    if n_bars == 4 and n_accel >= 3 and not flags:
        cred = "高"
    elif n_bars >= 3 and n_accel >= 2:
        cred = "中"
    else:
        cred = "低→无法充分判定"
    layer = {"数据方案": sch, "得分": score, "数据覆盖率": cov, "有柱子数": n_bars, "有加速度数": n_accel,
             "结论可信度": cred,
             "指标": {"利润同比%": p_y, "利润加速度pp": p_a, "营收同比%": r_y, "营收加速度pp": r_a,
                    "毛利率%": (round(gm0, 2) if gm0 is not None else None), "毛利率同比pp": gm_pp, "毛利率加速度pp": gm_accel, "毛利率趋势": gm_trend,
                    "OCF同比%": o_y, "OCF加速度pp": o_a, "亏损收窄": narrow, "由亏转盈": turn},
             "异常字段": anom_fields}
    availmap = {"利润": p_y is not None, "营收": r_y is not None, "毛利率同比": gm_pp is not None, "OCF": o_y is not None,
                "有毛利科目": (it(p0, m["gross"])[0] is not None)}
    return layer, availmap, flags


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    pit = load_pit(d)
    try:
        cd = json.loads((SCREEN / "candidates_20260721.json").read_text(encoding="utf-8"))
        inbound = [c["code"] for c in cd.get("candidates", []) if c.get("conclusion") == "入围"]
    except Exception:
        inbound = list(pit.keys())

    # 行业(读 fin_score·入围各只真行业)
    industry = {}
    try:
        fs = json.loads((SCREEN / "fin_score_20260721.json").read_text(encoding="utf-8"))
        industry = {c: v.get("industry") for c, v in fs.get("scores", {}).items()}
    except Exception:
        pass
    # L2/L3 复用上次 candidates_v2(kline/earnings 一小时内不变·不重抓·省OpenD)
    prevL = {}
    pv = SCREEN / f"candidates_v2_{d}.json"
    if pv.exists():
        try:
            for c, v in json.loads(pv.read_text(encoding="utf-8")).get("cards", {}).items():
                prevL[c] = {"市场先行层": v.get("市场先行层"), "市场确认层": v.get("市场确认层")}
        except Exception:
            pass

    cards = {}; availmaps = {}
    for c in inbound:
        rec = pit.get(c)
        L1, avail1, flags = fundamentals_layer(rec)
        availmaps[c] = avail1
        L3 = (prevL.get(c) or {}).get("市场先行层") or {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→无法充分判定(无缓存)", "指标": {}}
        L2 = (prevL.get(c) or {}).get("市场确认层") or {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→无法充分判定(无缓存)", "指标": {}}
        L4 = {"得分": None, "数据覆盖率": 0.0, "结论可信度": "低→无法充分判定(本轮未算)",
              "说明": "需全行业成员kline算上涨广度/新高比例·成本高·本轮未算·下轮评估·不计0分"}
        cards[c] = {"code": c, "行业": industry.get(c), "★四层不合并总分": True, "基本面变化层": L1,
                    "市场先行层": L3, "市场确认层": L2, "行业扩散层": L4,
                    "常识核对": (flags or ["通过"]), "真自由现金流": "待查·capex未解出·不采信"}

    # 四项可得率(整体)
    def rate(field):
        return round(sum(1 for c in inbound if cards[c]["基本面变化层"].get("指标", {}).get(field) is not None) / len(inbound) * 100, 1)
    cov4 = {"利润": rate("利润同比%"), "营收": rate("营收同比%"), "毛利率同比": rate("毛利率同比pp"), "OCF": rate("OCF同比%")}
    # 加速度可得率
    cov_accel = {"利润加速度": rate("利润加速度pp"), "营收加速度": rate("营收加速度pp"), "OCF加速度": rate("OCF加速度pp"), "毛利率同比": rate("毛利率同比pp")}
    # ★毛利率可得率 by 行业 + 结构性NA(无营业成本科目)vs 数据缺失(董事长2026-07-21 问)
    from collections import defaultdict
    ind_stat = defaultdict(lambda: {"n": 0, "有毛利科目": 0, "毛利率同比可得": 0})
    for c in inbound:
        ind = industry.get(c) or "(未分类)"
        am = availmaps.get(c, {})
        ind_stat[ind]["n"] += 1
        if am.get("有毛利科目"):
            ind_stat[ind]["有毛利科目"] += 1
        if am.get("毛利率同比"):
            ind_stat[ind]["毛利率同比可得"] += 1
    结构性无毛利行业 = sorted([ind for ind, s in ind_stat.items() if s["n"] >= 2 and s["有毛利科目"] == 0])
    毛利率结构性NA数 = sum(1 for c in inbound if not availmaps.get(c, {}).get("有毛利科目"))
    毛利率数据缺失数 = sum(1 for c in inbound if availmaps.get(c, {}).get("有毛利科目") and not availmaps.get(c, {}).get("毛利率同比"))
    flagged = [c for c, v in cards.items() if v["常识核对"] and not v["常识核对"][0].startswith("通过")]

    毛利率覆盖分解 = {"总入围": len(inbound), "毛利率同比可得": sum(1 for c in inbound if availmaps.get(c, {}).get("毛利率同比")),
                 "结构性无营业成本科目(银行/保险/地产类·非缺失)": 毛利率结构性NA数,
                 "有科目但数据缺失(期数不足等)": 毛利率数据缺失数,
                 "结构性无毛利的行业": 结构性无毛利行业,
                 "_口径": "结构性NA(该行业无营业成本概念·8003/8004不存在)≠数据没取到·两者已分开·不混进同一覆盖率数字"}

    change_score = {"_说明": "变化驱动·基本面变化层四根柱子(利润/营收/毛利率/OCF·同比+加速度)·F-07缺失不计0·加速度需≥2个FY期(PIT已存16期)",
                    "入围": len(inbound), "四项同比可得率%": cov4, "加速度可得率%": cov_accel,
                    "毛利率覆盖分解_结构vs缺失": 毛利率覆盖分解,
                    "scores": {c: cards[c]["基本面变化层"] for c in inbound}}
    (SCREEN / f"change_score_{d}.json").write_text(json.dumps(change_score, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    v2 = {"_说明": "按四层分类得分重出候选·★不合并成单一总分(F-07⑤/本轮不做)·不同覆盖率不直接排名·每层各出 得分/覆盖率/可信度。"
                 "★可信度=柱子数+加速度数+异常综合(问题2);异常值>±500%已标并截尾(问题3);capex未解→真FCF待查;行业扩散层未算(覆盖0·非0分)。",
          "date": d, "入围": len(inbound), "四项同比可得率%": cov4, "加速度可得率%": cov_accel,
          "毛利率覆盖分解_结构vs缺失": 毛利率覆盖分解, "常识核对待查": flagged, "cards": cards}
    (SCREEN / f"candidates_v2_{d}.json").write_text(json.dumps(v2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 可信度分布
    from collections import Counter
    cred_dist = Counter(cards[c]["基本面变化层"].get("结论可信度", "")[:1] for c in inbound)
    print("wrote change_score + candidates_v2")
    print("四项同比可得率:", cov4, "· 加速度可得率:", cov_accel)
    print("基本面变化层可信度分布(高/中/低):", dict(cred_dist))
    print("毛利率覆盖分解:", {k: v for k, v in 毛利率覆盖分解.items() if not k.startswith("_") and k != "结构性无毛利的行业"})
    print("常识核对待查:", len(flagged), "只")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
