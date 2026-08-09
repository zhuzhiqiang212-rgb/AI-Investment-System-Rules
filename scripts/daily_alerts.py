# -*- coding: utf-8 -*-
"""★轮130 A/B:今日提醒清单生成器(D4巡检前两类 + PDCA见分晓到期检测)。
A·C类【机器取不到·需人工补】= 新鲜度未达标/源滞后 + macro_flow NK4未接项 + 账户接不通项。
A·D类【触价检测】= exec_params 到价三档(短) vs 现价 → 触目标/触低吸/触止损。
B·见分晓到期 = 扫 locked_predictions_registry 的 PDCA核对日 → 到期/临近7日 → 提醒核对记分(★不代记分·G2)。
★Code只检测与提醒·不做投资判断。输出 data/logs/daily_alerts_{date}.json + 供册1顶部/册4的HTML。"""
import sys, json, argparse, re
from datetime import date as _date, datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _today(dc):
    return _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))


def c_class(dc):
    """C类:机器取不到·需人工补。源新鲜度/NK4/账户接不通。"""
    out = []
    for lf, lbl in (("worldview", "①世界观新闻"), ("strategy", "②国家战略新闻")):
        j = _rj(ROOT / "data/market" / f"{lf}_{dc}.json")
        if j.get("★新鲜度达标(取到当日事实·bool)") is False:
            lag = j.get("★A类滞后天数(PA3)") or j.get("★A类滞后天数(PB3)")
            out.append({"类": "C·源新鲜度", "项": lbl, "缺": "A类未取到当日事实·最新滞后%s天" % lag,
                        "需人工补": "接当日权威源 或 董事长确认无重大事件", "严重度": "中"})
    mf = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    for x in (mf.get("核心指标", []) or []):
        if x.get("接通") is False or x.get("当日值") is None:
            # ★甲A2(轮332):不印 Python True/False·解矛盾(接通True但值缺=源接通当日无值)。
            _conn = x.get("接通")
            _st = ("源已接通但当日无值" if (_conn is True and x.get("当日值") is None)
                   else ("未接通" if _conn is False else "当日值缺"))
            out.append({"类": "C·宏观NK4", "项": x.get("指标"), "缺": _st,
                        "需人工补": "接数据源 或 手工报当日值", "严重度": "低"})
    cl = _rj(ROOT / "data/accounts" / f"all_accounts_closure_{dc}.json")
    for it in (cl.get("四_接不通项(如实标·原因·预计·NK1-4·不删整块)", []) or []):
        out.append({"类": "C·账户接不通", "项": it.get("项"), "缺": it.get("原因"),
                    "需人工补": it.get("预计"), "严重度": "中"})
    return out


def d_class(dc):
    """D类:触价检测。exec_params 到价三档(短) vs 现价 → 触目标/低吸/止损。"""
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    out = []
    for p in ep.get("三只", []):
        px = (p.get("现价") or {}).get("值")
        band = (p.get("到价三档") or {}).get("未来3日(短·技术swing·MA20+ATR)") or {}
        if not isinstance(px, (int, float)) or not band:
            continue
        tgt = ((band.get("目标价") or {}).get("值")); low = ((band.get("低吸价") or {}).get("值")); stop = ((band.get("止损价") or {}).get("值"))
        hit = None
        if isinstance(stop, (int, float)) and px <= stop:
            hit = ("★触止损", "现价%.2f ≤ 止损%.2f" % (px, stop), "高")
        elif isinstance(low, (int, float)) and px <= low:
            hit = ("触低吸", "现价%.2f ≤ 低吸%.2f" % (px, low), "中")
        elif isinstance(tgt, (int, float)) and px >= tgt:
            hit = ("触目标", "现价%.2f ≥ 目标%.2f" % (px, tgt), "中")
        if hit:
            out.append({"类": "D·触价", "标的": p.get("symbol"), "名称": p.get("name"), "触发": hit[0],
                        "算式": hit[1], "严重度": hit[2], "现价as_of": (p.get("现价") or {}).get("as_of"),
                        "★提醒": "触价是机器信号·是否动作由 Opus5 判(G2)"})
    return out


def b_verdict_due(dc, near_days=7):
    """B:见分晓到期检测。扫 locked_predictions_registry PDCA核对日→到期/临近。★不代记分。"""
    reg = _rj(ROOT / "data/pdca/locked_predictions_registry.json")
    preds = reg.get("已登记预测", []) if isinstance(reg, dict) else []
    today = _today(dc)
    due, near, overdue_cnt = [], [], 0
    for p in preds:
        st = str(p.get("状态") or "")
        if "待评" not in st:   # 只看已锁定待评(未核对)
            continue
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(p.get("PDCA核对日") or ""))
        if not m:
            continue
        vd = _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        dleft = (vd - today).days
        rec = {"标的": p.get("标的"), "尺度": p.get("尺度"), "核对日": vd.isoformat(), "剩余天数": dleft,
               "预判": str(p.get("预判") or "")[:40], "★须核对": "该预测到期·须核对结果并记分(★记分是Opus5的判断·Code不代·G2)"}
        if dleft <= 0:
            rec["状态"] = "★已到期未核对"; due.append(rec); overdue_cnt += 1
        elif dleft <= near_days:
            rec["状态"] = "临近(%d日后到期)" % dleft; near.append(rec)
    return {"到期未核对": due, "临近": near, "★到期未核对累计": overdue_cnt}


def _prior_dc(pattern_dir, prefix, dc):
    """找 < dc 的最近一个日期文件(YYYYMMDD)。无→None。"""
    import glob as _g, re as _re
    ds = []
    for p in _g.glob(str(ROOT / pattern_dir / (prefix + "*.json"))):
        m = _re.search(r"(\d{8})\.json$", Path(p).name)
        if m and m.group(1) < dc:
            ds.append(m.group(1))
    return max(ds) if ds else None


def b_class_diff(dc):
    """★A类今昨diff:只报变化【事实】·不判意义(G2)。持仓涨跌异动/板块方向翻转/源健康变化/判断层状态/证据增减。"""
    out = []
    # 1 持仓涨跌异动 + 动作变化(production 今 vs 最近往日)
    pdc = _prior_dc("data/reports", "production_", dc)
    if pdc:
        cur = {h["symbol"]: h for h in _rj(ROOT / "data/reports" / f"production_{dc}.json").get("holdings", [])}
        prv = {h["symbol"]: h for h in _rj(ROOT / "data/reports" / f"production_{pdc}.json").get("holdings", [])}
        for s, h in cur.items():
            p = prv.get(s)
            if not p:
                out.append({"类": "B·持仓变化", "项": h.get("name"), "变化": "★新增持仓(昨无今有)", "基准日": pdc}); continue
            cp, pp = h.get("price"), p.get("price")
            if isinstance(cp, (int, float)) and isinstance(pp, (int, float)) and pp:
                chg = (cp - pp) / pp * 100
                if abs(chg) >= 3:
                    out.append({"类": "B·持仓涨跌异动", "项": h.get("name"), "变化": "价格 %+.1f%%(vs %s)" % (chg, pdc), "基准日": pdc})
            if h.get("action") != p.get("action"):
                out.append({"类": "B·动作变化", "项": h.get("name"), "变化": "动作 %s→%s" % (p.get("action"), h.get("action")), "基准日": pdc})
    # 2 板块方向翻转(sector_rotation 承接节点涨跌 sign flip)
    sdc = _prior_dc("data/market", "sector_rotation_", dc)
    if sdc:
        def _secmap(x):
            return {n.get("板块格"): n.get("当日涨跌pct") for n in (_rj(ROOT / "data/market" / f"sector_rotation_{x}.json").get("BC3-1_承接节点涨跌", []) or [])}
        cs, ps = _secmap(dc), _secmap(sdc)
        for k, cv in cs.items():
            pv = ps.get(k)
            if isinstance(cv, (int, float)) and isinstance(pv, (int, float)) and (cv > 0) != (pv > 0) and abs(cv) > 0.3:
                out.append({"类": "B·板块方向翻转", "项": k, "变化": "%+.2f%%→%+.2f%%(翻%s·vs %s)" % (pv, cv, "负" if cv < 0 else "正", sdc), "基准日": sdc})
    # 3 源健康变化(worldview 新鲜度达标/滞后)
    wdc = _prior_dc("data/market", "worldview_", dc)
    if wdc:
        cw = _rj(ROOT / "data/market" / f"worldview_{dc}.json"); pw = _rj(ROOT / "data/market" / f"worldview_{wdc}.json")
        cf, pf = cw.get("★新鲜度达标(取到当日事实·bool)"), pw.get("★新鲜度达标(取到当日事实·bool)")
        if cf != pf:
            out.append({"类": "B·源健康变化", "项": "①世界观新鲜度", "变化": "达标 %s→%s(vs %s)" % (pf, cf, wdc), "基准日": wdc})
    # 4/5 判断层状态 + 证据增减(需昨日 pipeline/evidence_map)
    edc = _prior_dc("data/market", "evidence_map_", dc)
    if edc:
        ce = set(e.get("id") for e in _rj(ROOT / "data/market" / f"evidence_map_{dc}.json").get("★全证据台账(带ID·插入序稳定)", []))
        pe = set(e.get("id") for e in _rj(ROOT / "data/market" / f"evidence_map_{edc}.json").get("★全证据台账(带ID·插入序稳定)", []))
        if len(ce) != len(pe):
            out.append({"类": "B·证据增减", "项": "①层证据条数", "变化": "%d→%d(vs %s)" % (len(pe), len(ce), edc), "基准日": edc})
    else:
        out.append({"类": "B·基线", "项": "判断层状态/证据增减diff", "变化": "★昨日无pipeline产物(evidence_map/layer_pipeline)·今日establishes基线·此两类diff明日起生效", "基准日": None})
    return out


def build(dc):
    c = c_class(dc); d = d_class(dc); b = b_verdict_due(dc); bdiff = b_class_diff(dc)
    # ★轮148 E10 A-4:四闭环到期检测→并入今日提醒清单
    try:
        import closed_loops as _cl
        loop_due = _cl.alerts_rows(dc)
    except Exception:
        loop_due = []
    # ★★轮175 C:外部资料未消化告警(显要位置·防08-03答疑类静默漏掉)
    try:
        import external_digest_status as _eds
        _ed_line, _ed_n, _ed_list = _eds.alert_line(dc)
    except Exception:
        _ed_line, _ed_n, _ed_list = ("外部资料消化状态未接", 0, [])
    # ★★轮176 C:闪迪SNDK 08/05财报=见分晓日(董事长持仓·07-30锁定预测检验点·挂BofA估值)
    try:
        import sbi_freshness_gate as _sfg
        _sf_line,_sf_stale,_sf=_sfg.alert_line(dc[:4]+"-"+dc[4:6]+"-"+dc[6:8]); _sbi_fresh={"告警":_sf_line,"stale":_sf_stale,"sbi_date":_sf.get("sbi_date")}
    except Exception:
        _sbi_fresh={"告警":"SBI新鲜度未接","stale":False}
    _sv = _rj(ROOT / "data/pdca/sndk_verdict_20260805.json")
    # ★★★轮186 A:见分晓日历(机器从registry读verdict_date·非Opus5口头)——今日到期+已过期未记分
    try:
        import verdict_calendar as _vc
        _vc_line, _vc_td, _vc_eu, _vc_o = _vc.alert_line(dc[:4] + "-" + dc[4:6] + "-" + dc[6:8])
    except Exception:
        _vc_line, _vc_td, _vc_eu, _vc_o = ("见分晓日历未接", 0, 0, {})
    out = {
        "_说明": "★轮130 今日提醒清单(D4巡检C/D类 + PDCA见分晓到期)。★轮148并入E10四闭环到期。★Code只检测提醒·不做投资判断(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), "生成时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "A_C类_机器取不到需人工补": c,
        "A_D类_触价检测": d,
        "A_B类今昨diff(只报变化事实·不判意义G2)": bdiff,
        "B_见分晓到期": b,
        "E_闭环到期(E10·该复盘本闭环)": loop_due,
        "★F_外部资料未消化(轮175·防静默漏)": {"未消化数": _ed_n, "告警": _ed_line, "未消化清单": _ed_list},
        "★G_闪迪见分晓(轮176·08-05财报·董事长持仓)": _sv if _sv else "无",
        "★I_SBI新鲜度(轮190·防静默用旧SBI)": _sbi_fresh,
        "★H_见分晓日历(轮186·机器从registry算·非Opus5口头)": {"告警": _vc_line, "今日到期数": _vc_td, "★已过期未记分数": _vc_eu,
                                                  "今日到期": _vc_o.get("★今日到期", []), "★已过期未记分": _vc_o.get("★★已过期未记分", [])},
        "汇总": {"C类项": len(c), "D类触价": len(d), "B类变化": len(bdiff), "到期未核对": len(b["到期未核对"]), "临近": len(b["临近"]), "闭环到期": len(loop_due), "★外部资料未消化": _ed_n},
    }
    (ROOT / "data/logs" / f"daily_alerts_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    o = build(dc)
    print("[今日提醒] C类%d · D类触价%d · 到期未核对%d · 临近%d" % (
        o["汇总"]["C类项"], o["汇总"]["D类触价"], o["汇总"]["到期未核对"], o["汇总"]["临近"]))
    for x in o["B_见分晓到期"]["临近"] + o["B_见分晓到期"]["到期未核对"]:
        print("  见分晓:", x["标的"], x["尺度"], x["核对日"], x["状态"])
    for x in o["A_D类_触价检测"]:
        print("  触价:", x["名称"], x["触发"], x["算式"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
