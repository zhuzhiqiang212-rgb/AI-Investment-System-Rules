#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第4关·护城河五维（派工单任务C·E1·2026-07-22）·给第3关便宜/合理过关的7只(D/GSK/HII/INCY/KLAC/PEG/WDC)。
五维:品牌/网络效应/成本/转换成本/专利·每维 宽2/窄1/无0。总分:7-10宽护城河·4-6窄·0-3无。宽+便宜=最优质机会。
★★重要诚实声明:护城河=定性分析(理解岗/架构师职责)。本表为Code据公开事实初判·每维附理由·须理解岗/架构师逐维核改·非深度护城河研究。
带逐关轨迹(第1→2→3→4关)+generated_at+倒推自检(晚于gate3)+json.load自检。
用法：python scripts/gate4_moat.py --date 20260722"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))

# 五维评分[分, 理由]·★Code据公开事实初判·须理解岗核
MOAT = {
    "US.D": {"名称": "Dominion(受监管电力)",
             "品牌": [0, "公用事业无品牌溢价"], "网络效应": [0, "无"],
             "成本": [1, "规模发电·但受监管回报封顶"], "转换成本": [2, "地理垄断·居民无法更换供电商"], "专利": [0, "无"],
             "★框架注": "受监管公用真护城河=监管特许经营权/垄断牌照·本五维无此维→系统性低估·此处以『转换成本』代偿·须架构师定公用专用评法"},
    "US.GSK": {"名称": "GSK(制药)",
               "品牌": [1, "制药品牌中等·处方药靠疗效非品牌"], "网络效应": [0, "无"],
               "成本": [1, "全球规模制造/分销"], "转换成本": [1, "处方粘性·医生开药习惯"], "专利": [2, "专利药是制药核心护城河(疫苗/HIV/呼吸管线)"]},
    "US.HII": {"名称": "Huntington Ingalls(军工造船)",
               "品牌": [1, "国防承包品牌/信誉"], "网络效应": [0, "无"],
               "成本": [1, "造船规模"], "转换成本": [2, "美海军唯一航母建造商+两大核潜艇厂之一·监管准入极高·近垄断政府供应"], "专利": [1, "国防技术/机密工艺"]},
    "US.INCY": {"名称": "Incyte(生物制药)",
                "品牌": [0, "biotech无消费品牌"], "网络效应": [0, "无"],
                "成本": [0, "非成本驱动"], "转换成本": [1, "Jakafi处方粘性"], "专利": [2, "专利是核心·但高度依赖单品Jakafi(专利悬崖风险)"],
                "★风险注": "护城河集中于单品Jakafi专利·到期悬崖风险高·须理解岗核管线接续"},
    "US.KLAC": {"名称": "KLA(半导体量测/过程控制)",
                "品牌": [1, "半导体设备高端品牌"], "网络效应": [1, "装机基础+工艺数据积累"],
                "成本": [1, "规模"], "转换成本": [2, "设备嵌入fab产线·工艺know-how·极高转换"], "专利": [2, "过程控制量测技术专利·细分近垄断(份额~50%+)"]},
    "US.PEG": {"名称": "PSEG(受监管电力)",
               "品牌": [0, "公用无品牌溢价"], "网络效应": [0, "无"],
               "成本": [1, "规模·受监管回报"], "转换成本": [2, "地理垄断·用户无法更换供电商"], "专利": [0, "无"],
               "★框架注": "同D·受监管公用真护城河=监管特许经营权·五维无此维→低估·须架构师定公用专用评法"},
    "US.WDC": {"名称": "Western Digital(存储/HDD)",
               "品牌": [1, "存储品牌中等"], "网络效应": [0, "无"],
               "成本": [1, "HDD双寡头规模(WDC/希捷)"], "转换成本": [0, "存储近商品·低转换"], "专利": [1, "HDD/NAND专利"],
               "★风险注": "存储为周期性商品·护城河薄·须理解岗核周期位置"},
}
DIMS = ["品牌", "网络效应", "成本", "转换成本", "专利"]
POOL7 = ["US.D", "US.GSK", "US.HII", "US.INCY", "US.KLAC", "US.PEG", "US.WDC"]


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def band(t):
    return "宽护城河" if t >= 7 else ("窄护城河" if t >= 4 else "无护城河")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260722"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    gen = now()
    g3 = json.loads((S / f"gate3_valuation_{d}.json").read_text(encoding="utf-8"))
    g3_time = g3.get("generated_at")
    after_g3 = (g3_time is not None and gen > g3_time)
    g3rows = g3["逐只(15)"]

    rows = {}
    for c in POOL7:
        m = MOAT[c]
        dimscore = {dim: {"分": m[dim][0], "宽窄无": ("宽" if m[dim][0] == 2 else "窄" if m[dim][0] == 1 else "无"), "理由": m[dim][1]} for dim in DIMS}
        total = sum(m[dim][0] for dim in DIMS)
        g3c = g3rows.get(c, {})
        g3v = g3c.get("第3关估值", {})
        cheap = g3v.get("结论", "")
        rows[c] = {
            "code": c, "名称": m["名称"],
            "逐关轨迹": {
                "第1关_激活板块": g3c.get("逐关轨迹", {}).get("第1关_激活板块"),
                "第2关_象限": g3c.get("逐关轨迹", {}).get("第2关_象限"),
                "第3关_估值": cheap,
                "第4关_护城河": band(total),
            },
            "第4关护城河": {
                "五维": dimscore, "总分": total, "档": band(total),
                "宽+便宜=最优质?": ("★是(宽护城河+便宜)" if (band(total) == "宽护城河" and cheap.startswith("便宜"))
                               else f"否(护城河{band(total)}·估值{cheap})"),
            },
            "框架/风险注": {k: m[k] for k in m if k.startswith("★")},
        }

    # 汇总
    summary = [{"code": c, "名称": rows[c]["名称"], "护城河总分": rows[c]["第4关护城河"]["总分"],
                "档": rows[c]["第4关护城河"]["档"], "第3关估值": rows[c]["逐关轨迹"]["第3关_估值"]}
               for c in POOL7]
    summary.sort(key=lambda x: -x["护城河总分"])
    wide = [x["code"] for x in summary if x["档"] == "宽护城河"]
    best = [x for x in summary if x["档"] == "宽护城河" and str(x["第3关估值"]).startswith("便宜")]

    doc = {
        "_说明": "第4关护城河五维·7只(第3关便宜/合理过关)。宽7-10/窄4-6/无0-3。宽+便宜=最优质机会。",
        "★★诚实声明": "护城河=定性分析(理解岗/架构师职责)。本表为Code据公开事实初判·每维附理由·须理解岗/架构师逐维核改·非深度护城河研究。公用(D/PEG)五维系统性低估其监管特许护城河·已标框架注。",
        "date": d, "generated_at": gen, "评法": "五维各 宽2/窄1/无0·总分7-10宽/4-6窄/0-3无",
        "★倒推自检_晚于gate3": {"gate3生成时间": g3_time, "gate4生成时间": gen, "晚于gate3(顺序正确)": after_g3,
                          "结论": ("通过·第4关晚于第3关" if after_g3 else "★失败·倒推")},
        "汇总(按护城河总分降序)": summary,
        "宽护城河": wide,
        "宽+便宜=最优质机会": ([x["code"] for x in best] if best else "★本7只中无『宽护城河且便宜』完美组合(KLAC宽但估值合理·GSK便宜但护城河窄)·最接近见汇总"),
        "逐只(7)": rows,
    }
    p = S / f"gate4_moat_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("generated_at:", gen, "· 晚于gate3:", after_g3)
    for x in summary:
        print(f"  {x['code'].ljust(9)} {str(x['名称'])[:22].ljust(22)} 护城河{x['护城河总分']}分·{x['档']} · 估值{x['第3关估值']}")
    print("宽护城河:", wide, "· 宽+便宜最优质:", ([x["code"] for x in best] or "无完美组合"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
