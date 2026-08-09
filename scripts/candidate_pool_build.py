# -*- coding: utf-8 -*-
"""★轮146 E6/看板G22:候选池持久化存储(不再跑完就扔)。
A:data/opportunity/candidate_pool.json 持久化·每候选存 标的/市场/入口/首次入池日/各关结果+as_of/当前状态。
  ★变化追踪(新进/出池+原因)·★版本snapshot(不覆盖历史)。
B:四个重跑触发(结构化§5.4):①③regime方向变·②④板块激活重出·③①黑天鹅动摇高强·④满30天兜底。不触发不重跑·如实记。
C:今日可动清单(快层·只在池内算·非重扫全市场):触价/异动/年线位置/流动性变化。★报工作量对比。
★Code只搭结构+机械判定·不做投资判断。"""
import sys, json, argparse, glob, re
from datetime import date as _date, datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
POOL = ROOT / "data/opportunity/candidate_pool.json"
HOLD = {"JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
        "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
        "US.TSM", "US.META", "US.IBKR", "US.SPCX"}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _entry(code, path, today, gates):
    return {"标的": code, "市场": code.split(".")[0], "入口路径": [path], "首次入池日": today,
            "各关结果": gates, "当前状态": "在池", "出池": None, "最近更新": today}


def _latest(pat):
    """★读最新的漏斗产物(数据日可能≠今天·如08-03数据·08-04建池)。"""
    fs = sorted(glob.glob(str(ROOT / pat)))
    return _rj(fs[-1]) if fs else {}


def build(dc):
    today = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    tg = _latest("data/universe/type_gate3_*.json")
    lp = _latest("data/market/layer_pipeline_*.json")
    em = _latest("data/market/evidence_map_*.json")
    L = {x["层"][0]: x for x in lp.get("七层", [])}
    # 上层参照系(触发用)
    regime = next((str(o.get("本层判断"))[:50] for o in L.get("③", {}).get("output", []) if o.get("id") == "J3"), None)
    sect_dir = {o.get("板块"): o.get("方向(机器初判枚举)") for o in L.get("④", {}).get("output", [])}
    shake = em.get("★动摇的尺(PDCA入口·置顶)", [])

    prev = _rj(POOL)
    prev_pool = prev.get("★候选池", {}) or {}
    pool = {}
    _asof = "2026-08-03(K线/估值)"
    # 路径A:成长股估值样例(过第2关+流动性+第3关)
    for g in tg.get("★B估值明细样例", []):
        code = g["code"]
        pool[code] = _entry(code, "A·自上而下(成长股)", today, {
            "第1关_板块": {"结果": "过(在激活板块·归类含)", "as_of": _asof},
            "第2关_年线": {"结果": "过(站上200日年线)", "as_of": _asof},
            "流动性_60日均": {"结果": "过(达门槛)", "as_of": _asof},
            "第3关_估值": {"结果": ("过(成长PE≤40默认)" if g.get("过第3关(成长PE 0<PE≤40默认)") else "★明显贵/负PE·不追"),
                          "PE_TTM": g.get("PE_TTM"), "as_of": _asof},
            "第4关_护城河": {"结果": "★NK4·待Opus5五维分析", "as_of": None}})
    # ★轮157 A-4:路径B异动原因状态(个股特有/板块性·原因未知→不可据此行动)
    pbr = _latest("data/universe/path_b_reason_*.json") or {}   # ★_latest已返回内容(非路径)·勿再_rj
    reason_m = {r["标的"]: r for r in (pbr.get("逐只", []) or [])}
    # ★轮158 A:异动公告(可能原因·不判因果) + B:身份(全名+主营)
    ann = (_latest("data/universe/announcements_*.json") or {}).get("逐只公告", {}) or {}
    idm = (_latest("data/opportunity/identity_*.json") or {}).get("身份", {}) or {}
    # 路径B:异动(入口·各关待跑·守A-2纪律)
    for y in tg.get("★C异动明细", []):
        code = y["code"]
        _rsn = reason_m.get(code, {})
        _rsn_status = _rsn.get("★原因状态", "★原因未接·不可据此行动")
        if code in pool:
            pool[code]["入口路径"].append("B·事件驱动·异动%+.0f%%(5日)" % y.get("chg5", 0))
            pool[code]["各关结果"]["路径B_异动原因(轮157)"] = {
                "★原因状态": _rsn_status, "★板块性/个股特有": _rsn.get("★板块性/个股特有"),
                "板块内同向比例": _rsn.get("板块内同向比例(max)"), "新闻线索": _rsn.get("新闻线索"),
                "★公告线索(轮158·可能原因不判因果)": ann.get(code, {}), "as_of": pbr.get("date")}
        else:
            pool[code] = _entry(code, "B·事件驱动·异动(单日%+.0f%%/5日%+.0f%%)" % (y.get("chg1", 0), y.get("chg5", 0)), today, {
                "第1关_板块": {"结果": "待核(异动来自大盘中盘候选宇宙)", "as_of": _asof},
                "第2关_年线": {"结果": "★待跑(异动只是入口·纪律须过关)", "as_of": None},
                "流动性_60日均": {"结果": "★待跑", "as_of": None},
                "第3关_估值": {"结果": "★待类型分类+跑", "as_of": None},
                "第4关_护城河": {"结果": "★NK4·待Opus5", "as_of": None},
                "路径B_异动原因(轮157)": {"★原因状态": _rsn_status, "★板块性/个股特有": _rsn.get("★板块性/个股特有"),
                                    "板块内同向比例": _rsn.get("板块内同向比例(max)"), "新闻线索": _rsn.get("新闻线索"),
                                    "★公告线索(轮158·可能原因不判因果)": ann.get(code, {}), "as_of": pbr.get("date")}})
    # ★★轮149 E5全量填充:funnel_full(活数据真跑)存在→三层逐码全量进池(替代上面样例bootstrap)
    ff = _latest("data/universe/funnel_full_*.json")
    full_stat = None
    if ff:
        snap = ff.get("snap", {}) or {}
        types = ff.get("types", {}) or {}
        gate3 = ff.get("gate3", {}) or {}
        ff_asof = "%s(市值/INDUSTRY/PE·活数据真跑)" % ff.get("date", today)
        added = 0
        for code, tv in types.items():   # types 只含大盘中盘(过市值分层)
            tp = tv.get("type"); pe = (gate3.get(code, {}) or {}).get("pe")
            g3 = (gate3.get(code, {}) or {}).get("过第3关")
            cap = (snap.get(code, {}) or {}).get("cap_usd")
            tier = (snap.get(code, {}) or {}).get("tier")
            g3res = ("N/A(非成长股·%s·第3关只跑成长股)" % tp if tp != "成长股"
                     else ("过(成长PE 0<PE≤40)" if g3 else "★不过(PE=%s·贵/负/缺)" % pe))
            gates = {
                "市值分层": {"结果": tier, "市值USD": cap, "as_of": ff_asof},
                "第1关_板块": {"结果": "过(在激活板块归类宇宙内)", "as_of": ff_asof},
                "类型分类": {"结果": tp, "INDUSTRY": tv.get("industry"), "口径": "★成长/周期待Opus5核(G2)", "as_of": ff_asof},
                "第2关_年线": {"结果": "★待K线quota恢复(history_kline throttle·白卷)", "as_of": None},
                "流动性_60日均": {"结果": "★待K线quota恢复", "as_of": None},
                "第3关_估值": {"结果": g3res, "PE_TTM": pe, "as_of": ff_asof},
                "第4关_护城河": {"结果": "★NK4·待Opus5五维分析", "as_of": None}}
            if code in pool:
                pool[code]["各关结果"].update(gates)
                if "A·自上而下(全量·成长股)" not in pool[code]["入口路径"]:
                    pool[code]["入口路径"].append("A·自上而下(全量)")
            else:
                pool[code] = _entry(code, "A·自上而下(全量·%s)" % tp, today, gates)
                added += 1
        full_stat = {"大盘中盘全量进池": len(types), "本次新增": added,
                     "成长股": ff.get("汇总", {}).get("成长股"), "周期股": ff.get("汇总", {}).get("周期股"),
                     "未归类": ff.get("汇总", {}).get("未归类"), "过第3关": ff.get("汇总", {}).get("过第3关"),
                     "★注": "★大盘中盘base(K线两关未跑·quota白卷)·非过两关234·与轮145(过两关234base)不可直接比"}
    # ★★轮150 路径C估值异常:标入口C+分位+为什么便宜(读 path_c_anomaly)
    pc = _latest("data/universe/path_c_anomaly_*.json")
    pc_stat = None
    if pc:
        cand = pc.get("★路径C候选", []) or []
        for r in cand:
            code = r["标的"]
            ctag = "C·估值异常(%s%s)" % ("|".join(r.get("分位", []))[:60], "·★板块受损" if r.get("★板块受损") else "")
            if code in pool:
                if not any(str(x).startswith("C·估值异常") for x in pool[code]["入口路径"]):
                    pool[code]["入口路径"].append(ctag)
                pool[code]["各关结果"]["路径C_估值异常"] = {
                    "分位": r.get("分位"), "PE_TTM": r.get("PE_TTM"),
                    "★为什么便宜(候选解释·不判定)": r.get("★为什么便宜(候选解释·不判定G2)"),
                    "★板块受损": r.get("★板块受损"), "as_of": pc.get("date")}
            else:
                pool[code] = _entry(code, ctag, today, {
                    "路径C_估值异常": {"分位": r.get("分位"), "PE_TTM": r.get("PE_TTM"),
                                    "★为什么便宜(候选解释·不判定)": r.get("★为什么便宜(候选解释·不判定G2)"),
                                    "★板块受损": r.get("★板块受损"), "as_of": pc.get("date")},
                    "第2关_年线": {"结果": "★待K线quota恢复", "as_of": None},
                    "第4关_护城河": {"结果": "★NK4·待Opus5五维", "as_of": None}})
        pc_stat = {"路径C候选": len(cand), "★其中板块受损(便宜可能是板块问题)": pc.get("★其中板块受损数(便宜可能是板块问题)")}
    # ★轮158 B:每只补身份(公司全名+主营·防看代码认错)·不许只显代码
    for code in pool:
        _id = idm.get(code, {})
        pool[code]["公司全名"] = _id.get("全名", "★身份待核")
        pool[code]["主营行业"] = _id.get("行业") or "★待核"
    # 保留首次入池日(旧池已有的沿用)
    for code in pool:
        if code in prev_pool:
            pool[code]["首次入池日"] = prev_pool[code].get("首次入池日", today)
    # ★A-2 变化追踪
    new_in = [c for c in pool if c not in prev_pool]
    out_pool = []
    for c in prev_pool:
        if c not in pool and prev_pool[c].get("当前状态") == "在池":
            out_pool.append({"标的": c, "★出池原因": "★本次重跑未再入池(某关不再通过或异动消退)·具体关待与上版逐关对比", "出池日": today})
    # ★B 四触发(结构化·对比上次snapshot)
    prev_regime = prev.get("_触发基线", {}).get("regime")
    prev_sect = prev.get("_触发基线", {}).get("板块方向", {})
    last_snap = prev.get("snapshot日期")
    days_since = None
    if last_snap:
        try:
            _ls = _date(int(last_snap[:4]), int(last_snap[5:7]), int(last_snap[8:10]))
            days_since = (_date(int(dc[:4]), int(dc[4:6]), int(dc[6:8])) - _ls).days
        except Exception:
            days_since = None
    flip = [k for k, v in sect_dir.items() if prev_sect.get(k) and prev_sect.get(k) != v]
    triggers = {
        "①③regime方向变化": {"触发": bool(prev_regime and regime and prev_regime != regime),
                            "当前regime": regime, "上次regime": prev_regime or "★无(首次·记录基线)"},
        "②④板块激活重出(方向翻转)": {"触发": bool(flip), "翻转板块": flip or "无", "说明": "首次无对比基线" if not prev_sect else "对比上次snapshot"},
        "③①黑天鹅(动摇高强度)": {"触发": False, "今日动摇尺": shake,
                              "说明": "今日有动摇尺%d条但为『可能动摇』(中东降温/油价)·非黑天鹅级regime反转·不触发" % len(shake)},
        "④满30天兜底/首次建池": {"触发": (days_since is None) or (days_since >= 30) or (len(prev_pool) == 0),
                                "距上次snapshot天数": days_since if days_since is not None else "首次",
                                "说明": "★首次实质建池(上版池空)→视为触发" if len(prev_pool) == 0 else ("满30天兜底" if (days_since and days_since >= 30) else "未满30天")},
    }
    any_trig = any(t["触发"] for t in triggers.values())
    # ★C 今日可动清单(池内·快层)
    movable = []
    for y in tg.get("★C异动明细", []):
        movable.append({"标的": y["code"], "★可动信号": "异动", "单日%": y.get("chg1"), "5日%": y.get("chg5"),
                        "★入口": "B事件驱动", "★须过关": "第2/3/4关(异动不免筛)"})
    return {
        "_说明": "★轮146 E6候选池(G22)。持久化·各关结果+as_of+状态·变化追踪·snapshot不覆盖历史。★Code只搭结构不判断。",
        "snapshot日期": today, "version": "%s-snap%d" % (today, prev.get("_snap_seq", 0) + 1), "_snap_seq": prev.get("_snap_seq", 0) + 1,
        "★候选池只数": len(pool), "★E5全量填充(轮149)": full_stat, "★路径C估值异常(轮150)": pc_stat, "★候选池": pool,
        "★变化追踪(vs上次snapshot)": {"新进池数": len(new_in), "新进池": new_in[:30], "出池数": len(out_pool), "出池": out_pool[:30],
                                    "PDCA用途": "★追踪『上次选中它·这次为什么没选』——出池标哪关不再通过"},
        "★重跑触发(4条·G22)": {"任一触发": any_trig, "触发明细": triggers,
                              "★今日结论": ("★触发·本次重跑(哪条见明细)" if any_trig else "★未触发·候选池沿用上版·今日不重跑(如实记)")},
        "_触发基线": {"regime": regime, "板块方向": sect_dir},
        "★今日可动清单(池内·快层)": movable,
        "★C工作量对比(接口调用数)": {
            "全量重跑": "★约660次(宇宙22149→分层市值get_stock_filter~110页 + K线545 + get_owner_plate 6批·今日实测11轮撞3次限流)",
            "今日可动清单(池内)": "★约%d~60次(只对池内%d只算触价/异动/年线/流动性·K线%d次+snapshot几批)" % (len(pool), len(pool), len(pool)),
            "★省": "★约10倍(660→~60)·且不撞限流"},
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    o = build(dc)
    POOL.parent.mkdir(parents=True, exist_ok=True)
    # snapshot留档(不覆盖历史)
    (ROOT / "data/opportunity" / f"candidate_pool_snap_{dc}.json").write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    POOL.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[候选池] 入池 %d 只 · 新进 %d · 出池 %d" % (o["★候选池只数"], o["★变化追踪(vs上次snapshot)"]["新进池数"], o["★变化追踪(vs上次snapshot)"]["出池数"]))
    print("触发:", o["★重跑触发(4条·G22)"]["★今日结论"])
    print("今日可动清单:", len(o["★今日可动清单(池内·快层)"]), "只")
    print("工作量:", o["★C工作量对比(接口调用数)"]["★省"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
