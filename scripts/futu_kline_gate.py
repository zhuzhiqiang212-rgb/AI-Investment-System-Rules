# -*- coding: utf-8 -*-
"""★轮158 C:富途QFQ K线重跑第2关(富途本土源·request_history_kline其实可用·3元组解包)。
对大盘中盘496跑K线两关(60日均成交额USD门槛+站上200日年线)·与Yahoo版(189)对比·★以富途QFQ为准。
★富途 request_history_kline 返回3元组(ret,data,page_req_key)·turnover为本币成交额。"""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data/logs/futu_kline_progress.txt"
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


def build(dc):
    from futu import OpenQuoteContext, KLType, AuType
    LOG.write_text("", encoding="utf-8")
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    fx = _rj(_latest("data/universe/tier_filter_*.json")).get("FX", {"US": 1.0, "JP": 156.554, "HK": 7.8422})
    yk = _rj(_latest("data/universe/yahoo_kline_gate_*.json"))
    snap = ff.get("snap", {}) or {}
    types = ff.get("types", {}) or {}
    gate3 = ff.get("gate3", {}) or {}
    targets = [c for c, v in snap.items() if v.get("tier") in ("大盘", "中盘") and not c.startswith("KR.")]
    _log(f"大盘中盘目标 {len(targets)}只·富途QFQ K线两关")
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    res = {}
    done = 0
    try:
        for code in targets:
            ok = None
            for att in range(3):
                try:
                    ret = ctx.request_history_kline(code, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=250)
                    r, d = ret[0], ret[1]
                    if r == 0 and len(d) >= 60:
                        ok = d; break
                    time.sleep(0.5)
                except Exception:
                    time.sleep(0.5)
            done += 1
            if ok is None:
                res[code] = {"pass2": None, "原因": "NK4·富途K线取不到"}
            else:
                closes = list(ok["close"]); tos = list(ok["turnover"])
                mk = code.split(".")[0]
                avg60 = sum(tos[-60:]) / min(60, len(tos))
                avg60u = avg60 / fx.get(mk, 1.0)
                ma200 = sum(closes[-200:]) / min(200, len(closes))
                price = closes[-1]
                tier = snap[code]["tier"]
                thr = TO_LARGE if tier == "大盘" else TO_MID
                g1 = avg60u >= thr; g2 = price > ma200
                res[code] = {"pass2": bool(g1 and g2), "g1流动性": bool(g1), "g2年线": bool(g2),
                             "avg60成交额USD": round(avg60u), "ma200": round(ma200, 2), "price": round(price, 2), "源": "富途QFQ"}
            if done % 50 == 0:
                _log(f"  {done}/{len(targets)}·过两关{sum(1 for v in res.values() if v.get('pass2'))}·NK4 {sum(1 for v in res.values() if v.get('pass2') is None)}")
            time.sleep(0.1)
    finally:
        ctx.close()
    pass2 = set(c for c, v in res.items() if v.get("pass2"))
    nk4 = [c for c, v in res.items() if v.get("pass2") is None]
    # 对比Yahoo版
    ypass = set(c for c, v in (yk.get("逐只K线两关", {}) or {}).items() if v.get("pass2"))
    only_futu = sorted(pass2 - ypass)
    only_yahoo = sorted(ypass - pass2)
    both = pass2 & ypass
    # 富途版准数
    g_pass2 = [c for c in pass2 if types.get(c, {}).get("type") == "成长股"]
    g3_pass = [c for c in g_pass2 if gate3.get(c, {}).get("过第3关")]
    out = {
        "_说明": "★轮158 富途QFQ K线两关(本土源·以此为准)。对比Yahoo版(189)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "数据源": "富途OpenD QFQ(本土源·以此为准)",
        "大盘中盘_base": len(targets),
        "★富途版过两关N": len(pass2),
        "富途NK4(取不到)": len(nk4),
        "★对比Yahoo版": {"Yahoo过两关": len(ypass), "富途过两关": len(pass2),
                      "两版都过": len(both), "仅富途过": len(only_futu), "仅Yahoo过": len(only_yahoo),
                      "仅富途样例": only_futu[:15], "仅Yahoo样例": only_yahoo[:15]},
        "★富途版准数": {"过两关": len(pass2), "成长股": len(g_pass2), "成长股过第3关": len(g3_pass)},
        "逐只K线两关": res,
    }
    (ROOT / f"data/universe/futu_kline_gate_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"★★富途版过两关{len(pass2)} vs Yahoo{len(ypass)}·都过{len(both)}·仅富途{len(only_futu)}·仅Yahoo{len(only_yahoo)}")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    build(a.date.replace("-", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
