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

# 通用五维评分[分, 理由]·★Code据公开事实初判·须理解岗核(非公用标的走这套)
MOAT = {
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
    "US.WDC": {"名称": "Western Digital(存储/HDD)",
               "品牌": [1, "存储品牌中等"], "网络效应": [0, "无"],
               "成本": [1, "HDD双寡头规模(WDC/希捷)"], "转换成本": [0, "存储近商品·低转换"], "专利": [1, "HDD/NAND专利"],
               "★风险注": "存储为周期性商品·护城河薄·须理解岗核周期位置"},
}
DIMS = ["品牌", "网络效应", "成本", "转换成本", "专利"]

# ── 公用事业专用护城河评法（架构师《护城河分析框架.html》增补·2026-07-22）──
# 受监管公用(D/PEG)改走公用五维·纠正通用五维对其系统性低估(通用五维无『监管特许』维)。
UTIL_DIMS = ["监管特许", "高效规模", "受监管回报", "资产壁垒", "需求刚性"]
UTIL_CODES = {"US.D", "US.PEG"}
# 公③受监管回报:缺各州具体allowed ROE/rate base → 标待理解岗核·不估算放行·不计分(None)
UTIL_MOAT = {
    "US.D": {"名称": "Dominion(受监管电力·公用专用评法)",
             "监管特许": [2, "州公用委授予的排他特许经营区·居民法定无法更换供电商=垄断牌照"],
             "高效规模": [2, "输配电网自然垄断·一张网供全域·无经济空间容第二张网"],
             "受监管回报": [None, "★待理解岗核各州rate case(allowed ROE×rate base)·缺具体口径·不估算放行·暂不计分"],
             "资产壁垒": [2, "电厂/输配电重资产·数百亿级沉没成本·新进入者近乎不可能"],
             "需求刚性": [2, "电力刚需·需求无弹性·经济周期免疫(收息防御属性来源)"]},
    "US.PEG": {"名称": "PSEG(受监管电力·公用专用评法)",
               "监管特许": [2, "NJ公用委排他特许经营区·用户法定无法更换供电商=垄断牌照"],
               "高效规模": [2, "输配电网自然垄断·一网供全域·无空间容第二张网"],
               "受监管回报": [None, "★待理解岗核NJ rate case(allowed ROE×rate base)·缺具体口径·不估算放行·暂不计分"],
               "资产壁垒": [2, "输配电重资产·巨额沉没成本·极高进入壁垒"],
               "需求刚性": [2, "电力刚需·需求无弹性·抗周期"]},
}
UTIL_CEIL = "★天花板注:公用宽护城河=收息防御型·非成长——护城河极宽(垄断牌照)但超额回报被监管allowed ROE封顶·涨幅有天花板·定位=防御/收息·不是成长股。"
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

    def score_word(v):
        return "待核" if v is None else ("宽" if v == 2 else "窄" if v == 1 else "无")

    rows = {}
    for c in POOL7:
        is_util = c in UTIL_CODES
        m = UTIL_MOAT[c] if is_util else MOAT[c]
        dims = UTIL_DIMS if is_util else DIMS
        dimscore = {dim: {"分": m[dim][0], "宽窄无": score_word(m[dim][0]), "理由": m[dim][1]} for dim in dims}
        scored = [m[dim][0] for dim in dims if m[dim][0] is not None]
        total = sum(scored)
        pending = [dim for dim in dims if m[dim][0] is None]
        g3c = g3rows.get(c, {})
        g3v = g3c.get("第3关估值", {})
        cheap = g3v.get("结论", "")
        moat_block = {
            "评法": ("公用事业专用五维(监管特许/高效规模/受监管回报/资产壁垒/需求刚性)" if is_util
                   else "通用五维(品牌/网络效应/成本/转换成本/专利)"),
            "五维": dimscore, "总分": total,
            "计分说明": (f"③受监管回报待理解岗核·不计分;其余{len(scored)}维计分={total}" if pending else f"五维全计={total}"),
            "档": band(total),
            "宽+便宜=最优质?": ("★是(宽护城河+便宜)" if (band(total) == "宽护城河" and cheap.startswith("便宜"))
                           else f"否(护城河{band(total)}·估值{cheap})"),
        }
        if is_util:
            moat_block["★天花板注"] = UTIL_CEIL
            moat_block["★待核维"] = pending
        rows[c] = {
            "code": c, "名称": m["名称"],
            "逐关轨迹": {
                "第1关_激活板块": g3c.get("逐关轨迹", {}).get("第1关_激活板块"),
                "第2关_象限": g3c.get("逐关轨迹", {}).get("第2关_象限"),
                "第3关_估值": cheap,
                "第4关_护城河": band(total),
            },
            "第4关护城河": moat_block,
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
        "_说明": "第4关护城河·7只(第3关便宜/合理过关)。非公用走通用五维(品牌/网络/成本/转换/专利);受监管公用(D/PEG)走公用专用五维(监管特许/高效规模/受监管回报/资产壁垒/需求刚性)。宽7-10/窄4-6/无0-3。",
        "★★诚实声明": "护城河=定性分析(理解岗/架构师职责)。本表为Code据公开事实初判·每维附理由·须理解岗/架构师逐维核改·非深度护城河研究。",
        "★公用专用评法(架构师《护城河分析框架.html》增补·2026-07-22)": "受监管公用(D/PEG)由通用五维系统性低估(通用五维无『监管特许』维)→改走公用五维·D/PEG档从『无护城河』纠为『宽护城河』。★天花板注:公用宽护城河=收息防御型·非成长·超额回报被监管allowed ROE封顶。★③受监管回报缺各州具体allowed ROE/rate base→待理解岗核·不估算放行·暂不计分。",
        "date": d, "generated_at": gen, "评法": "通用五维/公用五维各 宽2/窄1/无0·总分7-10宽/4-6窄/0-3无(公用③待核不计分·由其余4维定档)",
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
