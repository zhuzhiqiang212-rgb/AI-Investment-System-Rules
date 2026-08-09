# -*- coding: utf-8 -*-
"""★轮149 E5候选池全量填充 + C类型标签补全（★活数据真跑版）。
★把漏斗逐码【全量】重算并写候选池(替代轮146只bootstrap样例~43只)。
链:classified全量code(US/JP/HK+KR手工·A股暂缓) → 市值分层(get_market_snapshot·大盘≥100亿/中盘20-100亿USD·小盘排除)
   → get_owner_plate补INDUSTRY(★C任务·批量·轮145只246/546→161未归类·本轮补全)
   → 类型分类(无INDUSTRY=未归类/周期INDUSTRY关键词=周期/else成长·★成长周期口径待Opus5核G2)
   → 成长股第3关(成长PE 0<PE≤40·用snapshot的PE_TTM)。
★K线两关(60日均成交额+200日年线):request_history_kline 历史K线quota已throttle(单只阻塞>50s·同轮140-143限流墙)→本轮【交白卷】·标『待K线quota恢复』·不假报。
★市值/PE/INDUSTRY 皆 get_market_snapshot / get_owner_plate 快调可得(实测秒级)→全量真跑。"""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data/logs/funnel_full_progress.txt"

CAP_LARGE = 100e8
CAP_MID = 20e8
CYCLICAL_KW = ["存储", "半导体设备", "存储器", "memory", "内存"]  # ★周期INDUSTRY关键词·口径待Opus5核(G2)


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _log(m):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _latest(pat):
    g = sorted(ROOT.glob(pat))
    return g[-1] if g else None


def load_universe(dc):
    f = ROOT / f"data/universe/classified_{dc}.json"
    if not f.exists():
        f = _latest("data/universe/classified_*.json")  # ★非当日接最近有效(§5.4·非当日≠作废)
    c = _rj(f)
    codes = set()
    for k, v in (c.get("★各板块归出", {}) or {}).items():
        codes |= set(v.get("全量code(供分层筛选·不进产品)", []) or [])
    keep = [x for x in codes if x.split(".")[0] in ("US", "JP", "HK")]  # A股暂缓·韩股无富途快照另处理
    return sorted(set(keep)), ["KR.005930", "KR.000660"]


def classify_type(industries):
    if not industries:
        return "未归类", "★get_owner_plate未取到INDUSTRY→数据gap(非真未归类)"
    joined = " ".join(industries)
    for kw in CYCLICAL_KW:
        if kw.lower() in joined.lower():
            return "周期股", f"INDUSTRY含周期关键词『{kw}』(待Opus5核)"
    return "成长股", "有INDUSTRY且非周期关键词→成长(待Opus5核)"


def run(dc):
    from futu import OpenQuoteContext
    LOG.write_text("", encoding="utf-8")
    tf = ROOT / f"data/universe/tier_filter_{dc}.json"
    if not tf.exists():
        tf = _latest("data/universe/tier_filter_*.json")
    fx = _rj(tf).get("FX", {"US": 1.0, "JP": 156.554, "HK": 7.8422, "KR": 1427.55})
    uni, kr = load_universe(dc)
    _log(f"候选宇宙(US/JP/HK·A股暂缓): {len(uni)}只 + 韩股手工{len(kr)}")
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    snap = {}
    try:
        # 阶段1 市值分层 + PE(get_market_snapshot·★递归拆分:一只坏码/OTC只丢自己不连坐整批)
        def _snap_batch(batch, depth=0):
            if not batch:
                return
            r, d = ctx.get_market_snapshot(batch)
            if r == 0:
                for _, row in d.iterrows():
                    code = row["code"]; mk = code.split(".")[0]
                    cap = row.get("total_market_val")
                    capu = (cap / fx.get(mk, 1.0)) if cap else None
                    tier = None
                    if capu is not None:
                        tier = "大盘" if capu >= CAP_LARGE else ("中盘" if capu >= CAP_MID else "小盘排除")
                    snap[code] = {"cap_usd": capu, "tier": tier, "pe": row.get("pe_ttm_ratio"), "price": row.get("last_price")}
                return
            if len(batch) == 1:
                snap[batch[0]] = {"cap_usd": None, "tier": "无效/OTC剔除", "pe": None, "price": None, "_err": str(d)[:40]}
                return
            mid = len(batch) // 2   # ★拆半隔离坏码
            _snap_batch(batch[:mid], depth + 1); time.sleep(0.2)
            _snap_batch(batch[mid:], depth + 1)
        B = 100
        for i in range(0, len(uni), B):
            _snap_batch(uni[i:i + B])
            time.sleep(0.6)
            _log(f"  市值分层 {min(i+B,len(uni))}/{len(uni)}·已取{len(snap)}")
        n_large = sum(1 for v in snap.values() if v["tier"] == "大盘")
        n_mid = sum(1 for v in snap.values() if v["tier"] == "中盘")
        n_small = sum(1 for v in snap.values() if v["tier"] == "小盘排除")
        _log(f"★市值分层完成:大盘{n_large}·中盘{n_mid}·小盘排除{n_small}·缺{len(uni)-len(snap)}")
        big_mid = [c for c, v in snap.items() if v["tier"] in ("大盘", "中盘")]

        # 阶段2 get_owner_plate 补INDUSTRY(★C·批量) → 类型分类
        types = {}
        B2 = 100
        for i in range(0, len(big_mid), B2):
            batch = big_mid[i:i + B2]
            got = {}
            for att in range(5):
                r, d = ctx.get_owner_plate(batch)
                if r == 0:
                    for _, row in d.iterrows():
                        if row.get("plate_type") == "INDUSTRY":
                            got.setdefault(row["code"], []).append(row["plate_name"])
                    break
                _log(f"  owner_plate批{i}失败att{att}:{str(d)[:50]}"); time.sleep(3.6)
            for code in batch:
                inds = got.get(code, [])
                t, why = classify_type(inds)
                types[code] = {"industry": inds, "type": t, "依据": why}
            time.sleep(1.0)
            _log(f"  类型分类(补INDUSTRY) {min(i+B2,len(big_mid))}/{len(big_mid)}")
        # 韩股手工
        for c in kr:
            types[c] = {"industry": ["AI存储(手工·Yahoo)"], "type": "成长股", "依据": "韩股手工(Opus5轮139)"}
        n_growth = sum(1 for v in types.values() if v["type"] == "成长股")
        n_cyc = sum(1 for v in types.values() if v["type"] == "周期股")
        n_un = sum(1 for v in types.values() if v["type"] == "未归类")
        _log(f"★类型分类完成(补INDUSTRY后):成长{n_growth}·周期{n_cyc}·未归类{n_un}")

        # 阶段3 成长股第3关(成长PE 0<PE≤40·用snapshot PE)
        gate3 = {}
        for code, v in types.items():
            if v["type"] != "成长股":
                continue
            pe = snap.get(code, {}).get("pe")
            gate3[code] = {"pe": pe, "过第3关": bool(pe is not None and 0 < pe <= 40)}
        n_g3run = len(gate3); n_g3pass = sum(1 for v in gate3.values() if v["过第3关"])
        _log(f"★成长股第3关:成长股{n_g3run}只跑·过{n_g3pass}只")

        final = {
            "_说明": "★轮149 全量漏斗真跑。市值分层+INDUSTRY补全+类型分类+成长股第3关=活数据真跑;★K线两关(流动性+年线)因history_kline quota throttle本轮交白卷·标待。",
            "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
            "宇宙_n": len(uni) + len(kr),
            "snap": snap, "types": types, "gate3": gate3,
            "★K线两关": "★白卷·request_history_kline quota throttle(单只>50s)·待quota恢复重跑",
            "汇总": {"大盘": n_large, "中盘": n_mid, "小盘排除": n_small,
                   "大盘中盘_base": len(big_mid), "成长股": n_growth, "周期股": n_cyc, "未归类": n_un,
                   "成长股跑第3关": n_g3run, "过第3关": n_g3pass},
        }
        (ROOT / f"data/universe/funnel_full_{dc}.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
        _log(f"★★全量漏斗(K线除外)落盘 funnel_full_{dc}.json")
        return final
    finally:
        ctx.close()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    run(a.date.replace("-", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
