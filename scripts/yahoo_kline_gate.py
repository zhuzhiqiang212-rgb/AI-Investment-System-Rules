# -*- coding: utf-8 -*-
"""★轮155 C:Yahoo K线补第2关(富途history_kline quota长期throttle→换源·轮137已证Yahoo韩股121根成功)。
对大盘中盘496只跑K线两关:①60日均成交额(close×volume→USD)门槛(大盘≥5000万/中盘≥8000万) ②站上200日年线(last>MA200)。
→ 过两关N → ★给轮149欠的准数:过两关N base 上·补标签后成长股/第3关净增(与轮145 71/30唯一可比的数)。
★数据源=Yahoo(非富途)·产物显式标源。★取不到→NK4·不估算。"""
import sys, json, time, urllib.request, ssl, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data/logs/yahoo_kline_progress.txt"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}
TO_LARGE = 5000e4
TO_MID = 8000e4


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _log(m):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def to_yahoo(code):
    mk, sym = code.split(".", 1)
    if mk == "US":
        return sym
    if mk == "JP":
        return sym + ".T"
    if mk == "HK":
        s = sym.lstrip("0") or "0"
        return s.zfill(4) + ".HK"
    return None


def yahoo_kline(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d"
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20, context=CTX)
        j = json.loads(r.read())
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        # ★轮157 C:用adjclose(前复权·与富途QFQ对齐·防拆股口径漂移)·无adjclose回退close
        adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
        closes = adj if adj else q["close"]
        rows = [(c, v) for c, v in zip(closes, q["volume"]) if c is not None and v is not None]
        return rows
    except Exception:
        return None


def build(dc):
    LOG.write_text("", encoding="utf-8")
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    fx = _rj(_latest("data/universe/tier_filter_*.json")).get("FX", {"US": 1.0, "JP": 156.554, "HK": 7.8422})
    snap = ff.get("snap", {}) or {}
    types = ff.get("types", {}) or {}
    gate3 = ff.get("gate3", {}) or {}
    targets = [c for c, v in snap.items() if v.get("tier") in ("大盘", "中盘")]
    _log(f"大盘中盘目标 {len(targets)}只·Yahoo K线两关")
    res = {}
    done = 0
    for code in targets:
        sym = to_yahoo(code)
        rows = yahoo_kline(sym) if sym else None
        done += 1
        if not rows or len(rows) < 60:
            res[code] = {"pass2": None, "原因": "NK4·Yahoo K线取不到/不足60根", "源": "Yahoo"}
        else:
            closes = [r[0] for r in rows]; vols = [r[1] for r in rows]
            mk = code.split(".")[0]
            turn_local = [closes[i] * vols[i] for i in range(len(rows))]
            avg60 = sum(turn_local[-60:]) / min(60, len(turn_local))
            avg60u = avg60 / fx.get(mk, 1.0)
            ma200 = sum(closes[-200:]) / min(200, len(closes))
            price = closes[-1]
            tier = snap[code]["tier"]
            thr = TO_LARGE if tier == "大盘" else TO_MID
            g1 = avg60u >= thr; g2 = price > ma200
            res[code] = {"pass2": bool(g1 and g2), "g1流动性": bool(g1), "g2年线": bool(g2),
                         "avg60成交额USD": round(avg60u), "门槛USD": thr, "ma200": round(ma200, 2), "price": round(price, 2), "源": "Yahoo"}
        if done % 40 == 0:
            _log(f"  进度 {done}/{len(targets)}·过两关{sum(1 for v in res.values() if v.get('pass2'))}·NK4 {sum(1 for v in res.values() if v.get('pass2') is None)}")
        time.sleep(0.25)
    pass2 = [c for c, v in res.items() if v.get("pass2")]
    nk4 = [c for c, v in res.items() if v.get("pass2") is None]
    _log(f"★Yahoo K线两关完成:过两关{len(pass2)}·未过{len(res)-len(pass2)-len(nk4)}·NK4 {len(nk4)}")

    # ★轮149准数:过两关N base 上·补标签后 成长股/第3关
    g_pass2 = [c for c in pass2 if types.get(c, {}).get("type") == "成长股"]
    g3_pass = [c for c in g_pass2 if gate3.get(c, {}).get("过第3关")]
    cyc = [c for c in pass2 if types.get(c, {}).get("type") == "周期股"]
    un = [c for c in pass2 if types.get(c, {}).get("type") == "未归类"]
    out = {
        "_说明": "★轮155 Yahoo K线补第2关(富途quota throttle换源)。K线两关:60日均成交额门槛+站上200日年线。★数据源=Yahoo非富途。取不到NK4不估算。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "数据源": "Yahoo Finance chart API(非富途·轮137已证可用)",
        "大盘中盘_base": len(targets),
        "★过两关N": len(pass2),
        "过两关_NK4(Yahoo取不到)": len(nk4),
        "★★轮149准数(过两关N base·补INDUSTRY标签后)": {
            "过两关N": len(pass2),
            "其中成长股": len(g_pass2), "其中周期股": len(cyc), "其中未归类": len(un),
            "成长股过第3关": len(g3_pass),
            "★与轮145可比": "轮145(过两关234 base·限流数据gap):成长71/未归类161/过第3关30 → ★本轮(过两关%d base·INDUSTRY补全后·Yahoo K线):成长%d/未归类%d/过第3关%d" % (len(pass2), len(g_pass2), len(un), len(g3_pass)),
        },
        "逐只K线两关": res,
        "过两关清单": pass2,
    }
    (ROOT / f"data/universe/yahoo_kline_gate_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"★★准数:过两关{len(pass2)}·成长{len(g_pass2)}·过第3关{len(g3_pass)}(vs轮145 234/71/30)")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    build(a.date.replace("-", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
