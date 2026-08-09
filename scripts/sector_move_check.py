# -*- coding: utf-8 -*-
"""★轮161 A(最高优先):④层「受益/受损」判定 vs 板块实际5日涨跌·用数据核④可不可信。
每板块(大盘中盘成员)算:5日涨跌中位数 + 分布(涨/跌/跌超10%/涨超10%只数)。
★结论二选一(数据说话):④判受益但板块中位在跌→④判定有问题(报);板块中位在涨只个别跌→个股特有。★Code只给数据+机器一致性核·因果/尺是否要改由Opus5/董事长(G2)。"""
import sys, json, ssl, statistics, urllib.request, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}
# classified 8板块 → ④方向(轮150)
BOARD_DIR = {"AI算力·AI芯片": "受益", "AI半导体设备": "受益", "AI存储": "受损",
             "AI云·数据中心": "受损", "AI应用软件": "受益",
             "电力·能源(AI耗电)": "★未明", "机器人·自动化": "★未明", "材料(半导体上游)": "★未明"}


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
    sym = to_yahoo(code)
    if not sym:
        return None
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d"
        j = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15, context=CTX).read())
        adj = j["chart"]["result"][0]["indicators"].get("adjclose", [{}])[0].get("adjclose")
        cl = [c for c in (adj or j["chart"]["result"][0]["indicators"]["quote"][0]["close"]) if c is not None]
        if len(cl) < 6:
            return None
        return round((cl[-1] - cl[-6]) / cl[-6] * 100, 2)
    except Exception:
        return None


def build(dc):
    cls = _rj(_latest("data/universe/classified_*.json"))
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    bigmid = set(c for c, v in (ff.get("snap", {}) or {}).items() if v.get("tier") in ("大盘", "中盘"))
    rows = []
    for b, direction in BOARD_DIR.items():
        codes = [c for c in (cls.get("★各板块归出", {}) or {}).get(b, {}).get("全量code(供分层筛选·不进产品)", []) if c in bigmid]
        moves = []
        for c in codes[:70]:
            v = chg5(c); time.sleep(0.18)
            if v is not None:
                moves.append(v)
        if len(moves) < 4:
            rows.append({"板块": b, "④方向": direction, "样本": len(moves), "结论": "样本<4·不评"}); continue
        med = round(statistics.median(moves), 2)
        up = sum(1 for m in moves if m > 0); down = sum(1 for m in moves if m < 0)
        up10 = sum(1 for m in moves if m >= 10); down10 = sum(1 for m in moves if m <= -10)
        # ★机器一致性核(不改尺·只报是否矛盾)
        if direction == "受益":
            consist = "★一致(受益·板块中位涨)" if med > 0 else "★★矛盾(④判受益但板块中位在跌)→须Opus5/董事长核④"
        elif direction == "受损":
            consist = "★一致(受损·板块中位跌)" if med < 0 else "★★矛盾(④判受损但板块中位在涨)→须核④"
        else:
            consist = "④未标方向·仅报分布"
        rows.append({"板块": b, "④方向": direction, "样本": len(moves), "★5日中位%": med,
                     "涨": up, "跌": down, "涨超10%": up10, "跌超10%": down10,
                     "★④判定vs实际": consist})
    矛盾 = [r for r in rows if "矛盾" in str(r.get("★④判定vs实际", ""))]
    out = {
        "_说明": "★轮161 ④层受益/受损 vs 板块实际5日涨跌。★机器只算中位+分布+一致性核·不改尺(④判定是否要改由Opus5/董事长·G2)。数据源Yahoo adjclose。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★④判定与实际矛盾的板块数": len(矛盾),
        "★矛盾板块": [r["板块"] for r in 矛盾],
        "逐板块": rows,
    }
    (ROOT / f"data/market/sector_move_check_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★④判定与实际矛盾板块数:", o["★④判定与实际矛盾的板块数"], o["★矛盾板块"])
    for r in o["逐板块"]:
        if "★5日中位%" in r:
            print("  %-16s ④%s 中位%s%% 涨%d/跌%d 跌超10%%:%d → %s" % (
                r["板块"], r["④方向"], r["★5日中位%"], r["涨"], r["跌"], r["跌超10%"], r["★④判定vs实际"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
