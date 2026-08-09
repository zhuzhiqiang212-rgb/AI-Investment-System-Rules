# -*- coding: utf-8 -*-
"""★轮86 DB2:⑤机会池第4关护城河 + 第5关个股深度 + 量能标准。
 DB2-1 第4关护城河五维(★含公用事业专用评法:监管特许/高效规模/受监管回报/资产壁垒/需求刚性)→data/opportunity/moat_{date}.json
        每维宽/窄/无 + 一句依据·依据追不到标『待接』不编。
 DB2-2 第5关个股深度四项(财报要点/管线或产品线/管理层变动/竞争格局)→data/opportunity/deep_dive_{code}.json·缺项标待接。
 DB2-3 量能标准:放量突破=当日量≥60日均量×1.5(★B级经验值·用60日均量非当日近似)。
评估集:候选池为空(第1关激活清单作废)→本轮以当前20持仓为可评估集(第4/5关脚本对持仓演示·候选moat待激活清单重出)。"""
import sys, json, argparse, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
FRAME = "护城河分析框架.html"
FIVE_DIM = ["监管特许", "高效规模", "受监管回报", "资产壁垒", "需求刚性"]


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _series(sym, dc):
    """60日量:从 prices_daily / daily_scan 序列。无则待接。"""
    pj = _rj(ROOT / "data/market" / f"prices_daily_{dc}.json")
    arr = (pj.get(sym) or {}).get("volume") if isinstance(pj.get(sym), dict) else None
    return arr


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    holds = prod.get("holdings", [])
    # ── DB2-1 第4关护城河五维 ──
    moat_rows = []
    for h in holds:
        sym, nm = h.get("symbol"), h.get("name")
        mval = h.get("moat")   # production的moat结论(可能是文本/dict)
        base = str(mval) if mval else ""
        dims = {}
        for d in FIVE_DIM:
            # 依据追不到→待接(不编)。production无逐维数据→标待接·仅有总moat结论时记为参考。
            dims[d] = {"档": "待接", "依据": ("总moat结论参考：%s" % base[:40]) if base else "待接(production无逐维护城河数据·需moat_analysis五维源)"}
        moat_rows.append({"代码": sym, "名称": nm, "总moat结论": base[:60] or "待接",
                          "五维(监管特许/高效规模/受监管回报/资产壁垒/需求刚性)": dims,
                          "★说明": "逐维宽/窄/无待接moat_analysis五维源·不编"})
    moat_out = {
        "_说明": "★轮86 DB2-1 第4关护城河五维(含公用事业专用评法)。每维宽/窄/无+依据·追不到标待接不编。框架:%s。" % FRAME,
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "框架文件": FRAME, "五维定义": FIVE_DIM,
        "评估集": "候选池为空(第1关激活清单作废)→以当前20持仓为可评估集",
        "逐只": moat_rows,
        "★逐维数据源状态": "待接(production仅有总moat结论·无逐维宽窄无+依据·需moat_analysis扩五维输出)",
    }
    # ── DB2-2 第5关个股深度四项 ──
    D = ROOT / "data" / "opportunity"; D.mkdir(parents=True, exist_ok=True)
    dd_made = []
    for h in holds:
        sym, nm = h.get("symbol"), h.get("name")
        dd = {
            "_说明": "★轮86 DB2-2 第5关个股深度(最小可用集四项)。缺项标待接。",
            "代码": sym, "名称": nm, "date": dh,
            "财报要点": "待接(需edgar_financials/EDINET逐只要点提取·本轮未接)",
            "管线或产品线": "待接(需逐只业务线数据源)",
            "管理层变动": "待接(需公司公告/新闻逐只筛)",
            "竞争格局": h.get("one_line_reason", "")[:60] or "待接",
        }
        p = D / ("deep_dive_%s.json" % str(sym).replace(".", "_"))
        p.write_text(json.dumps(dd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        dd_made.append(sym)
    # ── DB2-3 量能标准 ──
    volume_std = {
        "_说明": "★轮86 DB2-3 量能标准。★用60日均量非当日近似。",
        "放量突破阈值": "当日量 ≥ 60日均量 × 1.5",
        "等级": "B级(经验值)",
        "60日均量数据源状态": "prices_daily序列(若有volume)·否则待接",
    }
    mp = D / f"moat_{dc}.json"
    mp.write_text(json.dumps(moat_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    vp = D / f"volume_standard_{dc}.json"
    vp.write_text(json.dumps(volume_std, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return moat_out, dd_made, volume_std


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    moat, dd, vol = build(a.date)
    print("[opportunity_gate45] %s · 第4关护城河五维:%d只 · 第5关深度:%d只 · 量能阈值:%s" % (
        a.date, len(moat["逐只"]), len(dd), vol["放量突破阈值"]))
    print("  ★逐维/深度多为待接(不编)·数据源:%s" % moat["★逐维数据源状态"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
