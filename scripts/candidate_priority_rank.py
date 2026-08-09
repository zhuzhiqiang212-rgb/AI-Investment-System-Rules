# -*- coding: utf-8 -*-
"""★轮151 E7候选优先级排序(★供Opus5决定护城河先评谁·护城河是质性·做不完全部)。
★Code只按【结构化字段】排序(可复核·§5.4)·不判『哪只更好』(投资判断归Opus5·G2)。
排序依据(董事长定·全结构化):
  ①★被几条路径同时命中(多路径命中数·最能说明优先级) ②是否过第3关(成长PE)
  ③★路径B异动幅度(5日跌越多越可能错杀·负值优先) ④★路径C的PE分位(越低越可能错杀)
  ⑤市值分层(大盘优先)。
★B-2 特别标多路径命中(A+C/B+C/A+B+C)。★B-4 板块受损者单独分组(便宜可能是板块问题·非个股错杀)。"""
import sys, json, re, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data/opportunity/candidate_pool.json"


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _paths(entry):
    s = set()
    for x in entry.get("入口路径", []):
        x = str(x)
        if x.startswith("A"): s.add("A")
        elif x.startswith("B"): s.add("B")
        elif x.startswith("C"): s.add("C")
    return s


def build(dc):
    pool = _rj(POOL).get("★候选池", {}) or {}
    pc = _rj(_latest("data/universe/path_c_anomaly_*.json"))
    tg = _rj(_latest("data/universe/type_gate3_*.json"))
    # 路径C:code→(最低PE分位, 板块受损)
    pcm = {}
    for r in pc.get("★路径C候选", []):
        ps = [int(m) for s in r.get("分位", []) for m in re.findall(r"第P(\d+)", str(s))]
        pcm[r["标的"]] = {"最低PE分位": min(ps) if ps else None, "★板块受损": bool(r.get("★板块受损")), "PE": r.get("PE_TTM")}
    # 异动:code→5日幅度
    anom = {y["code"]: y.get("chg5") for y in tg.get("★C异动明细", [])}

    rows = []
    for code, e in pool.items():
        ps = _paths(e)
        g = e.get("各关结果", {}) or {}
        # ★P0-5:改位置锚定判定·不用子串("不过"含"过"曾被误判为过·有交易安全风险)。
        #   结果取值集:"过(...)"=PASS · "★不过(...)"/"★明显贵.../不追"/"N/A(...)"=NOT。lstrip★空格后 startswith 可靠区分过/不过。
        _g3r = str((g.get("第3关_估值", {}) or {}).get("结果", "")).lstrip("★ ")
        g3 = _g3r.startswith("过") or _g3r.startswith("通过")
        tier = (g.get("市值分层", {}) or {}).get("结果") or "?"
        pcc = pcm.get(code, {})
        chg5 = anom.get(code)
        rows.append({
            "标的": code, "命中路径": sorted(ps), "★命中数": len(ps),
            "过第3关": g3, "市值分层": tier,
            "路径C_PE分位": pcc.get("最低PE分位"), "PE_TTM": pcc.get("PE"),
            "路径B_5日异动%": chg5, "★板块受损": pcc.get("★板块受损", False),
            "类型": (g.get("类型分类", {}) or {}).get("结果"),
        })

    # ★排序key(全结构化·可复核):命中数↓ · 过第3关 · 异动跌幅↑(负先) · PE分位↑(低先) · 大盘先
    def key(r):
        chg = r["路径B_5日异动%"]
        pcp = r["路径C_PE分位"]
        return (
            -r["★命中数"],
            0 if r["过第3关"] else 1,
            (chg if isinstance(chg, (int, float)) else 999),      # 跌越多越前
            (pcp if isinstance(pcp, (int, float)) else 999),      # PE分位越低越前
            0 if r["市值分层"] == "大盘" else 1,
            r["标的"],
        )
    rows.sort(key=key)
    for i, r in enumerate(rows):
        r["排名"] = i + 1

    multi = [r for r in rows if r["★命中数"] >= 2]
    combo = {}
    for r in multi:
        combo["+".join(r["命中路径"])] = combo.get("+".join(r["命中路径"]), 0) + 1
    top30 = rows[:30]
    top30_损 = [r for r in top30 if r["★板块受损"]]
    top30_净 = [r for r in top30 if not r["★板块受损"]]

    out = {
        "_说明": "★轮151 E7候选优先级排序。★Code按结构化字段排(可复核)·不判哪只更好(G2)。供Opus5决定护城河先评谁。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "候选池总数": len(rows),
        "★排序依据(结构化)": "命中路径数↓ → 过第3关 → 5日异动跌幅↑(负先) → 路径C PE分位↑(低先) → 大盘优先",
        "★多路径命中(≥2条)总数": len(multi),
        "★多路径命中组合分布": combo,
        "★Top30_板块非受损(个股层面优先)": top30_净,
        "★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)": top30_损,
        "全量排序": rows,
    }
    (ROOT / f"data/opportunity/candidate_priority_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("候选池 %d · 多路径命中(≥2) %d · 组合 %s" % (o["候选池总数"], o["★多路径命中(≥2条)总数"], o["★多路径命中组合分布"]))
    print("=== Top30 排序(结构化·%s) ===" % o["★排序依据(结构化)"])
    for r in (o["★Top30_板块非受损(个股层面优先)"] + o["★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)"]):
        print("  #%-2d %-10s 路径%s 命中%d 过3关%s PE分位%s 异动5日%s 市值%s %s" % (
            r["排名"], r["标的"], "".join(r["命中路径"]), r["★命中数"], "√" if r["过第3关"] else "×",
            r["路径C_PE分位"], r["路径B_5日异动%"], r["市值分层"], "★板块受损" if r["★板块受损"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
