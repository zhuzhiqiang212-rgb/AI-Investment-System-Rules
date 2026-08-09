# -*- coding: utf-8 -*-
"""★轮92 KA1:对「被风险压死」的候选跑完整估值·验证简易估值上行数字站不站得住。
简易估值=板块中位PE×当前EPS(B级)·可能高估(value/cyclical股放进high-PE格)。完整估值需【共识forward EPS/穿周期EPS】——
★免密钥源(OpenD snapshot)只给当前EPS+TTM PE+forward PE(pe_ratio)·无共识forward EPS·如实标。
可及的验证:①归类business正确性(股名是否真属该格)②本股自身PE(pe_ttm)vs板块中位PE→简易估值是否被拉高
③用本股forward PE(pe_ratio)×当前EPS 作『更接地气估值』对照。
KA1-2 对照表(简易上行vs接地气上行)。KA1-3 分类:完整仍≥20%=真机会·大幅缩水=方法偏差/归类错。
输出 data/opportunity/ka1_full_valuation_{date}.json。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# 格business关键词(判归类是否business-correct·股名匹配)
CELL_BIZ = {
    "半导体存储（DRAM/NAND）": ["存储", "内存", "闪存", "铠侠", "memory", "NAND", "DRAM"],
    "半导体测试": ["测试", "试験"], "半导体设备（前道/后道）": ["电子", "设备", "Electron", "Disco", "Lasertec", "Screen", "斯库林"],
    "半导体材料": ["化学", "材料", "硅", "揖斐", "wafer"], "代工": ["积电", "Foundr", "代工", "GlobalFoundries"],
    "AI算力租赁（新型云）": ["云", "算力", "数据中心", "cloud", "CoreWeave", "Nebius"],
    "AI服务器/硬件": ["服务器", "硬件", "戴尔", "Dell", "Vertiv", "超微", "SMCI"],
    "AI电力/能源": ["电力", "能源", "电网", "核电", "发电"], "日本金融/保险": ["银行", "保险", "证券", "金融"],
    "日本自动化/机器人": ["机器人", "自动化", "发那科", "电机"], "医药（ADC/肿瘤）": ["医药", "制药", "生物", "第一三共"],
}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    ja1 = _rj(ROOT / "data/opportunity" / f"buildable_analysis_{dc}.json")
    cp = _rj(ROOT / "data/opportunity" / f"candidate_pool_{dh}.json")
    # 被压死的(可建≈0·上行不低)——取ja1逐只里可建<0.5%且上行≥10%
    blocked = [r for r in ja1.get("逐只", []) if r["②可建权重pct"] < 0.5 and r["①上行pct"] >= 10]
    codes = [r["code"] for r in blocked]
    import universe_to_candidate_pool as U
    names, _ = U._fetch_names(codes, dc)
    snap, _ = U._fetch_snapshot(codes, dc)
    # ★LA2修:板块中位PE用candidate_pool【简易估值实际用的】中位(全格·非被压死子集)+格候选数(小样本污染检测)
    import re as _re
    from collections import Counter
    cell_med, cell_n = {}, Counter()
    for c in cp.get("candidates", []):
        cell_n[c["sector_cell"]] += 1
        m = _re.search(r"板块中位PE\(([\d.]+)\)", str((c.get("fair_value", {}) or {}).get("method", "")))
        if m:
            cell_med[c["sector_cell"]] = float(m.group(1))
    rows = []
    real_opp, artifact = [], []
    for r in blocked:
        code = r["code"]; s = snap.get(code, {}) or {}
        nm = names.get(code, "?"); cell = r["sector_cell"]
        eps = s.get("eps"); pe_ttm = s.get("pe_ttm"); pe_fwd = s.get("pe_ttm")  # OpenD无共识forward·用ttm
        px = s.get("price"); med = cell_med.get(cell)
        simple_up = r["①上行pct"]
        # ① 归类business正确性
        biz_ok = any(k.lower() in nm.lower() for k in CELL_BIZ.get(cell, []))
        # ③ 接地气估值:用本股自身pe_ttm×EPS=当前价→上行≈0(即本股按自身盈利已被市场定价);
        #    简易估值上行高 ⟺ 本股pe_ttm << 板块中位PE(被板块中位拉高)
        pe_gap = (med - pe_ttm) if (isinstance(med, (int, float)) and isinstance(pe_ttm, (int, float))) else None
        # 判定:归类错 或 本股PE远低于板块中位(value/cyclical被拉高) → 简易上行是artifact
        ncell = cell_n.get(cell, 0)
        if not biz_ok:
            verdict = "归类错(股名非该格业务)→简易上行是artifact"; artifact.append(code)
        elif ncell < 3:
            verdict = "★格候选仅%d只·板块中位PE(%s)是小样本(易被单个极贵peer污染)→上行不可信·artifact(LA2)" % (ncell, round(med, 1) if med else "?"); artifact.append(code)
        elif pe_gap is not None and pe_ttm is not None and pe_ttm > 0 and med and (med / pe_ttm) > 1.5:
            verdict = "本股PE(%.0f)远低于板块中位(%.0f)·简易估值被板块中位拉高→上行多为方法偏差" % (pe_ttm, med); artifact.append(code)
        elif pe_ttm is not None and pe_ttm < 0:
            verdict = "本股亏损(PE<0)·简易估值不适用→artifact"; artifact.append(code)
        else:
            verdict = "★简易上行较可信(归类对+格样本足+PE与板块中位相近)·完整估值(共识forward EPS)免密钥无·待确认"; real_opp.append(code)
        rows.append({"code": code, "股名": nm, "格": cell, "格候选数": ncell, "简易估值上行pct": simple_up,
                     "本股PE_TTM": pe_ttm, "板块中位PE(实际用的)": round(med, 1) if med else None,
                     "归类business对": biz_ok, "★判定": verdict})
    return {
        "_说明": "★轮92 KA1 对被压死候选跑完整估值验证。★完整估值需共识forward EPS/穿周期EPS·免密钥源(OpenD)只给当前EPS+TTM PE·无共识forward→完整估值受限·如实标。可及验证:归类正确性+本股PE vs板块中位PE(简易估值被拉高=artifact)。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "被压死候选数": len(blocked),
        "★KA1-3分类": {"疑真实被压死的机会(简易上行较可信·待完整估值确认)": real_opp,
                    "疑方法偏差/归类错(简易上行是artifact)": artifact},
        "★完整估值数据源限制": "共识forward EPS/穿周期多年EPS 免密钥源(OpenD/Yahoo chart)不提供→无法对scan-discovered新标的做真完整估值·只能交叉验证识别artifact·真完整估值需付费共识源(Bloomberg/Refinitiv)或逐只IR",
        "对照逐只(KA1-2)": rows,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data/opportunity" / f"ka1_full_valuation_{a.date.replace('-','')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[ka1_full_valuation] %s · 被压死%d只 · 乱码%d" % (a.date, out["被压死候选数"], b.count(b"\xef\xbf\xbd")))
    for r in out["对照逐只(KA1-2)"]:
        print("  %s %s %s(格%s只) 上行%d%% PE%s vs中位%s → %s" % (
            r["code"], str(r["股名"])[:10], r["格"][:6], r.get("格候选数"), r["简易估值上行pct"], r["本股PE_TTM"], r.get("板块中位PE(实际用的)"), r["★判定"][:36]))
    c = out["★KA1-3分类"]
    print("  ★真机会(待完整估值确认):", len(c["疑真实被压死的机会(简易上行较可信·待完整估值确认)"]),
          "· 方法偏差/归类错:", len(c["疑方法偏差/归类错(简易上行是artifact)"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
