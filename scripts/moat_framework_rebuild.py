# -*- coding: utf-8 -*-
"""★轮153 B:护城河框架重建(纠A-2:公用事业专用评法误用到全部20只)。
B-1 五维改【通用】:品牌/网络效应/成本/转换成本/无形资产专利。
B-2 公用事业专用评法(监管特许/高效规模/受监管回报/资产壁垒/需求刚性)★只对公用事业标的启用·当前20只无一是公用事业→全用通用。
B-3 ★结构只搭·五维打分留Opus5(G2·机器不判质性)→每维『档=待Opus5打分』·不代填分。
B-4 评估集刷新:第一批20持仓(校准)+第二批候选池(501只·Top30优先)·非『候选池为空』。
★每只挂【客观数据托底】(moat_data EDGAR + edinet_moat·近3年毛利率/ROE/研发率/营收稳定性/ROIC/市占率·取不到NK4)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GEN_DIMS = ["品牌", "网络效应", "成本", "转换成本", "无形资产专利"]
UTIL_DIMS = ["监管特许", "高效规模", "受监管回报", "资产壁垒", "需求刚性"]
# 20持仓(与moat/持仓一致)·is_util:当前无一公用事业→全False
HOLDINGS = [
    ("JP.4568", "第一三共"), ("US.NVDA", "英伟达"), ("US.MSFT", "微软"), ("US.MSTR", "MSTR"),
    ("US.COIN", "Coinbase"), ("JP.9984", "软银"), ("JP.8766", "东京海上"), ("JP.6758", "索尼"),
    ("JP.6857", "爱德万"), ("JP.7203", "丰田"), ("JP.8001", "伊藤忠"), ("JP.7832", "万代"),
    ("JP.7974", "任天堂"), ("US.AVGO", "博通"), ("US.CRCL", "Circle"), ("US.SNDK", "闪迪"),
    ("US.TSM", "台积电"), ("US.META", "META"), ("US.IBKR", "IBKR"), ("US.SPCX", "SpaceX"),
]
UTILITY = set()  # ★公用事业标的集合(当前空·20只无一是)


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _objective(code):
    """并 moat_data(EDGAR·US) + edinet_moat(JP) 的客观托底数据。取不到→NK4。"""
    ed = _rj(_latest("data/opportunity/moat_data_*.json"))
    jp = _rj(_latest("data/opportunity/edinet_moat_*.json"))
    for r in ed.get("逐只", []):
        if r["代码"] == code and "四项数据(近3年·对应通用五维)" in r:
            d = r["四项数据(近3年·对应通用五维)"]
            return {"源": "EDGAR", "毛利率": d.get("毛利率近3年"), "ROE": d.get("ROE近3年"),
                    "研发费用率": d.get("研发费用率近3年"), "营收增速稳定性": d.get("营收增速稳定性(增速标准差)"),
                    "ROIC": d.get("ROIC近3年"), "市占率": d.get("市占率")}
    for r in jp.get("逐只", []):
        if r["代码"] == code:
            d = r["数据"]
            return {"源": "EDINET", "会计准则": d.get("会计准则"), "毛利率": d.get("毛利率近年"),
                    "ROE": d.get("ROE近年(自算=归母净利/归母权益)"), "研发费用率": d.get("研发费用率近年"),
                    "营收增速稳定性": d.get("营收增速稳定性(增速标准差)"), "ROIC": d.get("★ROIC"), "市占率": d.get("★市占率")}
    return {"源": "NK4", "毛利率": "NK4", "ROE": "NK4", "研发费用率": "NK4", "营收增速稳定性": "NK4", "ROIC": "NK4", "市占率": "NK4"}


def build(dc):
    cp = _rj(ROOT / "data/opportunity/candidate_pool.json")
    n_pool = cp.get("★候选池只数", 0)
    prio = _rj(_latest("data/opportunity/candidate_priority_*.json"))
    top30 = [r["标的"] for r in (prio.get("★Top30_板块非受损(个股层面优先)", []) + prio.get("★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)", []))]

    rows = []
    for code, name in HOLDINGS:
        is_util = code in UTILITY
        dims = UTIL_DIMS if is_util else GEN_DIMS
        rows.append({
            "代码": code, "名称": name,
            "评法": ("公用事业专用五维" if is_util else "通用五维(品牌/网络效应/成本/转换成本/无形资产专利)"),
            "五维(★结构·档=待Opus5打分·机器不判质性G2)": {d: {"档": "待Opus5打分", "依据": None} for d in dims},
            "★客观数据托底(机器取·供Opus5打分参考)": _objective(code),
        })
    out = {
        "_说明": "★轮153 B 护城河框架重建。★纠A-2:公用事业专用评法误用到全部20只→改通用五维(公用评法只对公用事业启用·当前20只无一是)。★结构只搭·打分留Opus5(G2)。每只挂客观数据托底(EDGAR/EDINET·取不到NK4)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "框架文件": "护城河分析框架.html",
        "★通用五维": GEN_DIMS,
        "★公用事业专用五维(仅公用事业启用)": UTIL_DIMS,
        "★当前公用事业标的": sorted(UTILITY) or "无(20只持仓无一公用事业→全用通用五维)",
        "★评估集(刷新·纠A-1)": {
            "第一批_校准": "现有持仓20只(先评·校准评分标准)",
            "第二批_候选": "候选池 %d 只(校准后评·按 candidate_priority Top30 优先)" % n_pool,
            "Top30优先": top30[:30],
            "★纠正": "原文件『候选池为空(第1关激活清单作废)』已过时(轮86)→候选池现%d只" % n_pool,
        },
        "逐只(20持仓·通用五维结构+客观托底)": rows,
    }
    (ROOT / f"data/opportunity/moat_framework_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★通用五维:", o["★通用五维"])
    print("★公用事业标的:", o["★当前公用事业标的"])
    print("★评估集:", o["★评估集(刷新·纠A-1)"]["第一批_校准"], "+", o["★评估集(刷新·纠A-1)"]["第二批_候选"])
    nu = sum(1 for r in o["逐只(20持仓·通用五维结构+客观托底)"] if "通用" in r["评法"])
    print("★20只用通用五维:", nu, "/ 20 · 用公用事业评法:", 20 - nu)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
