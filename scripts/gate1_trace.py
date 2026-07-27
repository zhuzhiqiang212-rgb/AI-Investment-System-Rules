#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第1关逐关轨迹 + 反向回归测试（派工单B3/B4·2026-07-22·右栏_过滤标准筛选规则）。
★第1关=硬性一票否决:不在【今天激活的板块】=否决(哪怕再便宜再优质)。方向自上而下·不得跳关。
输入 data/market/sector_activation_20260722.json(激活清单)。逐只输出:激活板块→第1关→第2关(财务四柱)→第3关→状态。
★时间戳必须晚于激活文件(否则倒推)。★行业→激活板块crosswalk为Code反推·须架构师核·未映射行业保守判否决。
B4回归:金矿(黄金未激活)必须第1关被挡;礼来LLY(AI受益·医疗健康已激活)必须进第1关受检。任一不成立=漏斗未通过。
用法:python scripts/gate1_trace.py"""
import json, sys, time, os, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"

# ── 行业(OpenD INDUSTRY)→激活板块 crosswalk（★Code反推·须架构师核）──
CROSSWALK = {
    "半导体": "AI算力·AI芯片", "半导体设备与材料": "AI半导体设备",
    "软件基础设施": "AI软件应用", "应用软件": "AI软件应用", "信息技术服务": "AI软件应用",
    "一般药品制造商": "AI受益·医疗健康", "专业与通用药品制造商": "AI受益·医疗健康", "生物技术": "AI受益·医疗健康",
    "诊断与研究": "AI受益·医疗健康", "医疗计划": "AI受益·医疗健康", "医疗分销": "AI受益·医疗健康",
    "独立电力生产商": "AI电力/能源", "批发业": "高股息/价值·综合商社",
    "科技仪器": "AI基础设施外延·冷却/数据中心/网络", "通讯设备": "AI基础设施外延·冷却/数据中心/网络",
    "计算机硬件": "AI基础设施外延·冷却/数据中心/网络",
    # 架构师2026-07-22补映射:安全/国防(第18格·激活)
    "航空航天与国防": "安全/国防·军工/太空/网络安全",
    # 能源误杀补映射到已激活板块
    "铀": "AI电力/能源", "太阳能": "AI电力/能源",
    "多元化公用事业": "公用事业·传统水电气", "受监管天然气": "公用事业·传统水电气",
    # 未激活(明确)
    "黄金": "黄金/贵金属", "有色金属": "黄金/贵金属", "其他工业金属与采矿": "黄金/贵金属",
    "受监管电力": "公用事业·传统水电气",
    "金融数据与证券交易所": "加密/稳定币",   # COIN类·驱动=流动性
    "多元化银行": "保险/金融价值", "地区银行": "保险/金融价值", "资本市场": "保险/金融价值",
    "资产管理": "保险/金融价值", "信贷": "保险/金融价值",
    "多元化保险": "保险/金融价值", "财产和意外伤害保险": "保险/金融价值", "人寿保险": "保险/金融价值",
    "再保险": "保险/金融价值", "保险经纪": "保险/金融价值",
}
DRIVER_OVERRIDE = {"US.MSTR": "加密/稳定币", "US.COIN": "加密/稳定币", "US.CRCL": "加密/稳定币"}  # 流动性驱动·非按行业


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds")


def _latest(dirp, pat):
    """★N1(裁定2026-07-27):默认取最新一份·不再写死日期文件名(7/29后写死会读作废清单)。"""
    import glob as _glob
    cands = sorted(_glob.glob(str(dirp / pat)))
    return Path(cands[-1]) if cands else None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import argparse as _ap
    _p = _ap.ArgumentParser(); _p.add_argument("--date", default=None)
    _args, _ = _p.parse_known_args()
    # ★N1:激活清单单一源·默认取最新sector_activation(或--date指定)·不写死07-22
    if _args.date:
        actf = ROOT / "data" / "market" / f"sector_activation_{_args.date}.json"
    else:
        actf = _latest(ROOT / "data" / "market", "sector_activation_*.json")
    if not actf or not actf.exists():
        print("⚠缺 sector_activation·须架构师出激活清单再跑第1关"); return
    act = json.loads(actf.read_text(encoding="utf-8"))
    act_mtime = os.path.getmtime(actf)
    active = {b["板块"]: b for b in act["板块"]}
    active_set = {k for k, b in active.items() if b.get("激活") is True}

    _fsf = _latest(S, "fin_score_*.json")
    fs = json.loads(_fsf.read_text(encoding="utf-8"))
    industry = {c: v.get("industry") for c, v in fs["scores"].items()}
    try:
        _csf = _latest(S, "change_score_*.json")
        cs = json.loads(_csf.read_text(encoding="utf-8"))["scores"]
    except Exception:
        cs = {}
    # 待检集 = 432入围 + 明确点名 LLY(漏筛案·若不在则手工补行业)
    universe = dict(industry)
    if "US.LLY" not in universe:
        universe["US.LLY"] = "一般药品制造商"

    def sector_of(code, ind):
        if code in DRIVER_OVERRIDE:
            return DRIVER_OVERRIDE[code], "驱动覆盖(流动性)"
        if ind in CROSSWALK:
            return CROSSWALK[ind], "crosswalk"
        return None, "未映射"

    trace = {}
    for c, ind in universe.items():
        sec, how = sector_of(c, ind)
        if sec is None:
            g1, g1why = "否决", f"行业『{ind}』未映射到任何激活板块·保守否决(须架构师补映射)"
        elif sec in active_set:
            g1, g1why = "过关", f"在激活板块『{sec}』"
        else:
            st = active.get(sec, {}).get("激活")
            g1, g1why = "否决", f"板块『{sec}』{'未激活' if st is False else '未核(null)'}·一票否决"
        # 第2关 财务四柱(用变化驱动·仅过第1关者展示·但都算)
        c2 = cs.get(c, {})
        four = c2.get("指标", {})
        g2 = None
        if g1 == "过关":
            has = sum(1 for k in ["利润同比%", "营收同比%", "毛利率同比pp", "OCF同比%"] if four.get(k) is not None)
            g2 = f"财务四柱可得{has}/4·变化证据得分{c2.get('得分')}·可信度{c2.get('结论可信度')}" if c2 else "无变化驱动数据·待算"
        trace[c] = {"code": c, "行业": ind, "映射激活板块": sec, "映射方式": how,
                    "第1关": g1, "第1关依据": g1why,
                    "第2关_财务四柱": (g2 if g1 == "过关" else "—(第1关已否决·不进第2关)"),
                    "第3关_估值": ("待算(读valuation)" if g1 == "过关" else "—"),
                    "状态": ("受检(过第1关·进后续关)" if g1 == "过关" else "出局(第1关一票否决)")}

    # 统计
    passed = [c for c, t in trace.items() if t["第1关"] == "过关"]
    vetoed = [c for c, t in trace.items() if t["第1关"] == "否决"]
    unmapped = [c for c, t in trace.items() if t["映射激活板块"] is None]

    # ── B4 反向回归 ──
    gold = [c for c, ind in universe.items() if ind == "黄金"]
    gold_blocked = all(trace[c]["第1关"] == "否决" for c in gold) and len(gold) > 0
    lly_in = ("US.LLY" in trace and trace["US.LLY"]["第1关"] == "过关")
    regression_pass = gold_blocked and lly_in
    b4 = {
        "金矿必须被第1关挡住": {"金矿只数": len(gold), "全部否决": gold_blocked,
                       "样例": [{"code": c, "第1关": trace[c]["第1关"], "板块": trace[c]["映射激活板块"]} for c in gold[:5]]},
        "礼来LLY必须进第1关受检": {"LLY第1关": trace.get("US.LLY", {}).get("第1关"), "进受检": lly_in,
                          "板块": trace.get("US.LLY", {}).get("映射激活板块")},
        "回归测试结论": ("漏斗通过回归测试（金矿被挡+礼来进受检）" if regression_pass else "★漏斗未通过回归测试"),
    }

    doc = {
        "_说明": "第1关逐关轨迹+反向回归(B3/B4)。第1关=不在激活板块一票否决·方向自上而下·不跳关。",
        "生成时间": now(), "激活文件": actf.name,
        "激活文件mtime": datetime.datetime.fromtimestamp(act_mtime).isoformat(timespec="seconds"),
        "时间戳晚于激活文件": (datetime.datetime.now().timestamp() > act_mtime),
        "★倒推自检": ("通过·本输出晚于激活文件" if datetime.datetime.now().timestamp() > act_mtime else "★失败·早于激活文件=倒推"),
        "crosswalk来源": "★Code反推(OpenD INDUSTRY→架构师激活板块)·须架构师核·未映射行业保守判否决(第1关一票否决的安全默认)",
        "★2026-07-22架构师补映射已实施": ["航空航天与国防→安全/国防", "铀/太阳能→AI电力/能源", "多元化公用事业/受监管天然气→公用事业"],
        "★电气设备(军工相关)未映射_原因": "架构师要求映射『电气设备(军工相关的)』但 OpenD 行业名『电气设备』含半导体/工业设备(非军工)·无法从行业名区分军工·本轮保持原判(否决)·请架构师给『军工相关电气设备』的具体代码名单·我按名单加(432中电气设备共18只+电气设备及零件4只)",
        "维持否决(不扩大·架构师2026-07-22确认)": ["油气全系列(勘探/炼制/中游/综合/设备服务)", "铜铝钢/金属加工", "农业投入品/农产品", "餐厅/糖果/包装食品", "服装", "货运/铁路/物流"],
        "激活板块": sorted(active_set), "未激活/未核板块": sorted(set(active) - active_set),
        "统计": {"受检总数": len(universe), "过第1关": len(passed), "第1关否决": len(vetoed),
               "其中未映射行业(保守否决)": len(unmapped)},
        "B4反向回归测试": b4,
        "过第1关名单": sorted(passed),
        "逐只轨迹": trace,
    }
    p = S / "gate1_trace_20260722.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"))
    print("激活板块:", sorted(active_set))
    print("受检", len(universe), "→ 过第1关", len(passed), "· 否决", len(vetoed), "(未映射保守否决", len(unmapped), ")")
    print("时间戳晚于激活文件:", doc["时间戳晚于激活文件"], "·倒推自检:", doc["★倒推自检"])
    print("B4-金矿被挡:", gold_blocked, f"({len(gold)}只黄金)", "· B4-LLY进受检:", lly_in)
    print("★回归结论:", b4["回归测试结论"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
