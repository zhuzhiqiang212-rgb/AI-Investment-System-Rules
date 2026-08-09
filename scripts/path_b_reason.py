# -*- coding: utf-8 -*-
"""★轮157 A:路径B异动【原因线索】(结构性补——不知原因就给动作=第一三共犯过的错·不能留在机制里)。
每异动标的补:①同板块其他标的是否同向异动(★机器算板块内同向比例→区分【板块性】vs【个股特有】·不需判断) ②财报/公告日期是否落异动窗口 ③新闻(Yahoo search·若不可归因标原因未知)。
★A-3 取不到→标『原因未知』不编。★A-4 个股特有且原因未知→『★原因未知·不可据此行动』。★机器只算线索·因果判断留Opus5(G2)。"""
import sys, json, ssl, statistics, urllib.request, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}
SIG = 8.0   # 同向异动阈值(5日±8%)


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def to_yahoo(code):
    mk, sym = code.split(".", 1)
    if mk == "US":
        return sym
    if mk == "JP":
        return sym + ".T"
    if mk == "HK":
        return (sym.lstrip("0") or "0").zfill(4) + ".HK"
    return None


def chg5(code):
    """近5交易日涨跌%。取不到→None。"""
    sym = to_yahoo(code)
    if not sym:
        return None
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d"
        j = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15, context=CTX).read())
        cl = [c for c in j["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c is not None]
        if len(cl) < 6:
            return None
        return round((cl[-1] - cl[-6]) / cl[-6] * 100, 2)
    except Exception:
        return None


def build(dc):
    tg = _rj(_latest("data/universe/type_gate3_*.json"))
    cls = _rj(_latest("data/universe/classified_*.json"))
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    anom = tg.get("★C异动明细", []) or []
    # code→boards
    bd = {}
    for b, v in (cls.get("★各板块归出", {}) or {}).items():
        for c in v.get("全量code(供分层筛选·不进产品)", []) or []:
            bd.setdefault(c, []).append(b)
    # board→大盘中盘成员
    bigmid = set(c for c, v in (ff.get("snap", {}) or {}).items() if v.get("tier") in ("大盘", "中盘"))
    board_members = {}
    for b, v in (cls.get("★各板块归出", {}) or {}).items():
        board_members[b] = [c for c in v.get("全量code(供分层筛选·不进产品)", []) if c in bigmid]
    # ④板块方向(受益/受损·参照)
    lp = _rj(_latest("data/market/layer_pipeline_*.json"))
    l4 = next((x for x in lp.get("七层", []) if x["层"][0] == "④"), {})
    dir4 = {o.get("板块"): o.get("方向(机器初判枚举)") for o in l4.get("output", [])}

    # 异动股涉及的板块 → 算板块内5日同向比例(缓存)
    involved = set()
    for a in anom:
        for b in bd.get(a["code"], []):
            involved.add(b)
    board_stat = {}
    for b in involved:
        mem = board_members.get(b, [])
        moves = []
        for c in mem[:60]:   # 上限60只/板块(控Yahoo调用)
            v = chg5(c); time.sleep(0.2)
            if v is not None:
                moves.append(v)
        if len(moves) >= 4:
            down = sum(1 for m in moves if m <= -SIG); up = sum(1 for m in moves if m >= SIG)
            board_stat[b] = {"样本": len(moves), "中位5日%": round(statistics.median(moves), 2),
                             "下跌≥8%占比": round(down / len(moves), 3), "上涨≥8%占比": round(up / len(moves), 3)}
        else:
            board_stat[b] = {"样本": len(moves), "结论": "样本<4·无法算板块性"}

    rows = []
    for a in anom:
        code = a["code"]; c5 = a.get("chg5")
        boards = bd.get(code, [])
        # ★板块性 vs 个股特有(机器算·不判断)
        cls_reason = "个股特有(须查具体原因)"
        board_ctx = []
        peer_share = 0.0
        for b in boards:
            bs = board_stat.get(b, {})
            board_ctx.append({"板块": b, "④方向": dir4.get(b, "★未明"), **bs})
            if "下跌≥8%占比" in bs:
                share = bs["下跌≥8%占比"] if (c5 is not None and c5 < 0) else bs["上涨≥8%占比"]
                peer_share = max(peer_share, share)
        if peer_share >= 0.4:
            cls_reason = "★板块性·非个股特有(同板块≥40%同向异动)"
        elif peer_share > 0:
            cls_reason = "个股特有偏多(同板块同向<40%·主要是它自己)"
        rows.append({
            "标的": code, "5日%": c5, "板块": boards, "板块内同向比例(max)": round(peer_share, 3),
            "★板块性/个股特有": cls_reason,
            "板块上下文": board_ctx,
            "财报公告落窗口内": "★未接公告日历(EDINET/EDGAR年报6月·多不在近5日窗口)·标待接",
            "新闻线索": "★Yahoo search返通用市场新闻非个股可归因→原因未知(不编)",
            "★原因状态": ("板块性(板块共振)" if cls_reason.startswith("★板块性") else "★个股特有·原因未知·不可据此行动"),
        })
    out = {
        "_说明": "★轮157 路径B异动原因线索。★同板块同向比例=机器算(不判断)·区分板块性/个股特有。★新闻不可归因/公告未接→原因未知不编。★个股特有且原因未知→不可据此行动。机器只算·因果判断留Opus5(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "异动数": len(rows),
        "板块性": sum(1 for r in rows if r["★原因状态"].startswith("板块性")),
        "个股特有原因未知": sum(1 for r in rows if "不可据此行动" in r["★原因状态"]),
        "逐只": rows,
        "板块5日统计": board_stat,
    }
    (ROOT / f"data/universe/path_b_reason_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("异动 %d · 板块性 %d · 个股特有原因未知 %d" % (o["异动数"], o["板块性"], o["个股特有原因未知"]))
    for r in o["逐只"]:
        print("  %-9s 5日%s%% 同向比例%s → %s" % (r["标的"], r["5日%"], r["板块内同向比例(max)"], r["★板块性/个股特有"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
