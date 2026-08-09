# -*- coding: utf-8 -*-
"""★轮150 E5 路径C【估值异常】(多路径入口最后一路·董事长定义·Code实现)。
定义(董事长):估值异常=同板块内估值显著低于同侪·且不是因为基本面恶化。
判据(结构化·§5.4):
  · PE_TTM 处该板块【同类型标的】后25%分位(P25以下)
  · 且 PE>0(排除亏损·负PE不是便宜是没盈利)
  · 且 市值≥20亿USD(守分层·小盘暂缓)
★A-2 同时标【为什么便宜】候选解释(不判定·只列可能):近期跌幅(异动数据) + 该板块③④判受益/受损(对照上层) + ★若板块受损→显式标『便宜可能是板块问题·非个股错杀』。
★A-3 路径C候选同过第2/3/4关(入口不免筛)。★A-4 标入口=C·带分位数值。
★Code只算分位+列候选解释·不判『是不是真便宜/该不该买』(G2·投资判断归Opus5)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CAP_MIN = 20e8

# ★classified 8板块 → ④方向(受益/受损)映射。★无直接对应的显式标『未明』(不编)。
BOARD_DIR = {
    "AI算力·AI芯片": "受益", "AI半导体设备": "受益", "AI存储": "受损",
    "AI云·数据中心": "受损(④『AI基础设施外延·冷却/数据中心/网络』)", "AI应用软件": "受益(④『AI软件应用』)",
    "电力·能源(AI耗电)": "★未明(④无直接对应板块·不编方向)",
    "机器人·自动化": "★未明(④无直接对应板块·不编方向)",
    "材料(半导体上游)": "★未明(④无直接对应板块·不编方向)",
}


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat))
    return g[-1] if g else None


def _pctile(sorted_vals, q):
    """线性插值分位(q∈[0,1])。sorted_vals升序。"""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx); hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _rank_pct(sorted_vals, v):
    """v 在 sorted_vals(升序)中的分位百分比(越小越便宜)。"""
    n = len(sorted_vals)
    below = sum(1 for x in sorted_vals if x < v)
    return round(100.0 * below / n) if n else None


def build(dc):
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    cls = _rj(_latest("data/universe/classified_*.json"))
    tg = _rj(_latest("data/universe/type_gate3_*.json"))
    snap = ff.get("snap", {}) or {}
    types = ff.get("types", {}) or {}
    gate3 = ff.get("gate3", {}) or {}
    # code→异动跌幅(路径B异动明细)
    anom = {y["code"]: y for y in tg.get("★C异动明细", [])}
    # board→members(大盘中盘·有PE)
    board_members = {}
    for b, v in (cls.get("★各板块归出", {}) or {}).items():
        codes = [c for c in v.get("全量code(供分层筛选·不进产品)", []) if c in types]
        board_members[b] = codes

    flagged = {}
    board_stats = {}
    for b, codes in board_members.items():
        # 分组:板块×类型 → PE>0 的 PE 列表
        for tp in ("成长股", "周期股"):
            grp = [(c, snap.get(c, {}).get("pe")) for c in codes if types.get(c, {}).get("type") == tp]
            pes = sorted(p for _, p in grp if isinstance(p, (int, float)) and p > 0)
            if len(pes) < 4:   # 样本<4不算分位(避免噪声)
                board_stats[f"{b}·{tp}"] = {"样本(PE>0)": len(pes), "结论": "样本<4·不算分位"}
                continue
            p25 = _pctile(pes, 0.25)
            board_stats[f"{b}·{tp}"] = {"样本(PE>0)": len(pes), "P25阈值": round(p25, 2),
                                       "中位": round(_pctile(pes, 0.5), 2)}
            for c, pe in grp:
                if not (isinstance(pe, (int, float)) and pe > 0):
                    continue
                cap = snap.get(c, {}).get("cap_usd")
                if pe <= p25 and cap is not None and cap >= CAP_MIN:
                    rank = _rank_pct(pes, pe)
                    y = anom.get(c)
                    board_d = BOARD_DIR.get(b, "★未明")
                    损 = board_d.startswith("受损")
                    rec = flagged.get(c, {"标的": c, "入口": "C·估值异常", "板块": [], "类型": tp,
                                          "PE_TTM": round(pe, 2), "市值USD": round(cap), "分位": []})
                    rec["板块"].append(b)
                    rec["分位"].append(f"{b}:PE在板块{tp}第P{rank}(后25%·阈值≤{round(p25,2)})")
                    # ★A-3 过第2/3/4关(入口不免筛)
                    g3 = gate3.get(c, {}).get("过第3关")
                    rec["★过关(入口不免筛)"] = {
                        "第2关_年线": "★待K线quota恢复", "流动性_60日均": "★待K线quota恢复",
                        "第3关_估值": ("过(成长PE·且P25低估侧)" if g3 else "★注:PE低但第3关口径待核") if tp == "成长股" else "N/A(周期股·第3关只跑成长)",
                        "第4关_护城河": "★NK4·待Opus5五维"}
                    flagged[c] = rec

    # ★受损=任一所属板块受损(不看迭代顺序)·列全部板块方向 + A-2为什么便宜候选解释
    for c, rec in flagged.items():
        dirs = {b: BOARD_DIR.get(b, "★未明") for b in rec["板块"]}
        损 = any(str(d).startswith("受损") for d in dirs.values())
        rec["★板块受损"] = 损
        y = anom.get(c)
        rec["★为什么便宜(候选解释·不判定G2)"] = {
            "①近期跌幅(异动数据)": (f"单日{y.get('chg1')}%/5日{y.get('chg5')}%→跌多了可能错杀" if y else "无异动记录(未入±8%/5日±15%)"),
            "②各所属板块③④方向(对照上层)": dirs,
            "③★若板块受损的提示": ("★便宜可能是【板块问题】·非个股错杀·须Opus5辨" if 损 else "所属板块均非受损→便宜更可能是个股层面·仍须Opus5辨"),
        }
    损cnt = sum(1 for r in flagged.values() if r["★板块受损"])
    out = {
        "_说明": "★轮150 E5路径C估值异常。同板块同类型PE后25%分位+PE>0+市值≥20亿。★标为什么便宜候选解释(不判定)·板块受损者显式标『便宜可能是板块问题』。★Code只算分位不判投资(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "判据": {"分位": "PE_TTM≤同板块同类型P25", "排负": "PE>0", "市值": "≥20亿USD", "入口": "C·带分位"},
        "★路径C候选数": len(flagged),
        "★其中板块受损数(便宜可能是板块问题)": 损cnt,
        "★路径C候选": list(flagged.values()),
        "板块×类型分位统计": board_stats,
        "★纪律": "A-3入口不免筛(过第2/3/4关·K线两关待quota)·A-4标入口C带分位·A-2列为什么便宜不判定(G2)",
    }
    (ROOT / f"data/universe/path_c_anomaly_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("[路径C估值异常] 候选 %d 只 · 其中板块受损 %d 只(便宜可能是板块问题)" % (o["★路径C候选数"], o["★其中板块受损数(便宜可能是板块问题)"]))
    for r in o["★路径C候选"][:12]:
        print("  %s PE%.1f 市值%.1f亿 %s | 板块%s %s" % (
            r["标的"], r["PE_TTM"], r["市值USD"] / 1e8, r["类型"], r["板块"],
            "★板块受损" if r["★板块受损"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
