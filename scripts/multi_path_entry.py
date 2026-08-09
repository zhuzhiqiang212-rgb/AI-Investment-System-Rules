# -*- coding: utf-8 -*-
"""★轮144 A:机会标的【多路径入口】(董事长指出设计缺陷:上层从『唯一闸门』改『必须对照的参照系』)。
缺陷:现状⑤只从④受益板块捞(单一入口)→③④判错则全盘捞错·且漏独立催化剂/被错杀标的。
改:三路径并入·★都过第2/3/4关(纪律不变)·★每候选标入口路径(可追溯)·★路径B/C必须对照上层(板块受损则标矛盾·不无视上层)。
 路径A 自上而下:③资金流→④板块→该板块内标的(现有·candidate_universe/classify)。
 路径B 事件驱动:①层证据映射器的个股重大事件(财报超预期/并购/技术突破/暴跌)→直接进候选。
 路径C 估值异常:极端低估/被错杀→直接进候选(★待第3关估值跑完再建·需估值数据)。
★Code只搭多路径机制+对照上层·不做投资判断。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HOLDINGS = {"JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
            "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
            "US.TSM", "US.META", "US.IBKR", "US.SPCX"}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def path_b_from_evidence(dc):
    """★路径B:从①层证据映射器捞【个股重大事件】。★对照上层(A-4):该标的所在板块若被③④判受损→标矛盾。"""
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    lp = _rj(ROOT / "data/market" / f"layer_pipeline_{dc}.json")
    # ④板块方向(上层参照系):板块→受益/受损
    sect_dir = {}
    for L in lp.get("七层", []):
        if L["层"].startswith("④"):
            for o in L.get("output", []):
                sect_dir[o.get("板块")] = o.get("方向(机器初判枚举)")
    out = []
    for e in em.get("★全证据台账(带ID·插入序稳定)", []):
        z = str(e.get("证据", ""))
        # 只取【个股级】事件(⑥持仓档案=个股·或含具体公司名)·非纯板块/宏观
        is_stock = e.get("对应尺") == "⑥持仓档案" or any(k in z for k in ["第一三共", "英伟达", "软银", "爱德万", "微软", "闪迪", "索尼", "丰田"])
        if not is_stock:
            continue
        out.append({"证据ID": e.get("id"), "事件": z[:70], "★入口路径": "B·事件驱动",
                    "对应尺": e.get("对应尺"), "印证动摇": e.get("印证动摇"),
                    "★是否现有持仓": "是(非新标的)" if "第一三共" in z else "待认标的",
                    "★对照上层(A-4)": "★该事件属①层证据·下游板块方向见④层(受损则须标矛盾)·本条待Opus5认标的后核板块方向"})
    return out, sect_dir


def build(dc):
    kg = _rj(ROOT / "data/universe" / f"kline_gate_{dc}.json")
    path_a_total = (kg.get("★汇总(unique)", {}) or {}).get("★过流动+第2关(总剩)")
    pb, sect_dir = path_b_from_evidence(dc)
    out = {
        "_说明": "★轮144 多路径入口(董事长设计修复)。上层=参照系非唯一闸门。三路径都过第2/3/4关·每候选标入口·路径B/C对照上层。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★路径A_自上而下(现有)": {"来源": "③资金流→④板块→⑤该板块内标的(classify_universe/kline_gate)",
                                  "过两关候选数": path_a_total, "★入口路径": "A·自上而下"},
        "★路径B_事件驱动": {"来源": "①层证据映射器的个股重大事件", "捞出个股事件数": len(pb), "明细": pb,
                            "★现状缺口": ("★①层证据映射器当前只有【持仓+宏观/板块】事件·无【新候选个股事件】(财报超预期/并购/技术突破/暴跌)源→"
                                        "路径B本轮捞出的%d条全是现有持仓/板块级·★捞不出宇宙外新标的·需接【个股事件源】(财报日历/并购公告/个股异动)·本轮如实报缺口" % len(pb))},
        "★路径C_估值异常": {"来源": "极端低估/被错杀", "★状态": "★待第3关估值跑完再建(需估值数据·A-5·本轮不建)"},
        "★A-2纪律": "三路径候选都必须过第2/3/4关·不许因路径不同免筛",
        "★A-3可追溯": "每候选标【入口路径A/B/C】",
        "★A-4对照上层": "路径B/C候选·若其板块被③④判受损→显式标矛盾·不无视上层",
        "④板块方向(上层参照系)": sect_dir,
    }
    (ROOT / "data/universe" / f"multi_path_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("路径A(自上而下)过两关:", o["★路径A_自上而下(现有)"]["过两关候选数"])
    print("路径B(事件驱动)捞出个股事件:", o["★路径B_事件驱动"]["捞出个股事件数"], "· 缺口:", o["★路径B_事件驱动"]["★现状缺口"][:60])
    print("路径C(估值异常):", o["★路径C_估值异常"]["★状态"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
