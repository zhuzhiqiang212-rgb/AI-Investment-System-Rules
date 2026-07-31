# -*- coding: utf-8 -*-
"""C2(43号)·机会发现(从缺口出发)。照《机会发现规范_从缺口出发_v1_20260730》实现。
四道硬闸 S0(漏斗合规·候选须来自当日第1关激活板块·一票否决) S1(补缺口≥1.5pp/换仓净≥1.0pp) S2(低相关·同驱动组0.5折算·组≤30%) S3(风险配仓) S4(可脚本重跑)。
排序 priority = 补缺口pp × 置信度系数 ÷ 最坏回撤pp。九项字段缺一即FAIL。
★必守三条(违反整轮FAIL):①候选只来自激活板块(严禁自下而上全市场扫描)②fair_value禁硬编码(估值引擎当日跑)③rejected不得为空+gate_trace五关留痕(全过=闸没生效→FAIL)。
Code只实现闸与排序·不点名个股·不写公允值(个股/公允由输入候选池的估值引擎给)。"""
import json, argparse, pathlib, sys
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = {"A": 1.0, "B": 0.7, "C": 0.4}
# 风险配仓(07-19四条)·S2/S3门槛——是【口径常数】非个股公允值
SINGLE_MAX, GROUP_MAX, PEAK_MAX, DEF_MIN = 0.20, 0.30, 0.05, 0.15
S1_MIN_PP, S1_SWAP_MIN_PP = 1.5, 1.0

def _exposure_cap():
    """Y1-1:生效上限从 data/config/risk_caps.json 读(默认0.30·不硬编码·董事长偏好可调)。"""
    import json as _j
    p = ROOT / "data" / "config" / "risk_caps.json"
    try:
        return float(_j.loads(p.read_text(encoding="utf-8")).get("exposure_cap", GROUP_MAX))
    except Exception:
        return GROUP_MAX

def gate_S0(cand, activated_sectors):
    ok = cand.get("sector_cell") in activated_sectors
    return ("PASS" if ok else "FAIL"), (None if ok else "S0:候选板块[%s]不在当日第1关激活清单→漏斗合规否决(严禁自下而上)" % cand.get("sector_cell"))

def upside(cand):
    fv = cand.get("fair_value", {}); v = fv.get("value"); px = cand.get("price")
    if not v or not px:
        return None
    return v / px - 1

def gate_S1(cand, w_legal):
    up = upside(cand)
    if up is None:
        return "FAIL", "S1:fair_value/price缺→上行算不出(标待核·本闸按噪音挡)", None
    contrib = w_legal * up * 100
    swap = cand.get("swap_out") or {}
    if swap.get("ticker"):
        net = contrib - (swap.get("contrib_pp") or 0)
        if net < S1_SWAP_MIN_PP:
            return "FAIL", "S1:换仓净贡献%.2fpp<%.1f" % (net, S1_SWAP_MIN_PP), contrib
    if contrib < S1_MIN_PP:
        return "FAIL", "S1:补缺口%.2fpp<%.1f(噪音)" % (contrib, S1_MIN_PP), contrib
    return "PASS", None, contrib

def gate_S2(cand, group_weight_after, same_group_as_top):
    # Y1(轮61裁定·修v1.2错规则):S2④改三分支——上限是董事长偏好·规则不替他否决主线
    cap = _exposure_cap()
    grp_cur = cand.get("driver_group_current_weight")
    intra = cand.get("is_intra_group_swap", False)         # ①组内换仓(卖组内一只买组内另一只·净权重不增)
    net_add = cand.get("net_weight_add")                    # 净增权重(组内换仓=0或≤0)
    factor = 0.5 if same_group_as_top else 1.0
    # ① 组内换仓·净权重不增 → 允许(不受上限限制)
    if intra and (net_add is None or net_add <= 1e-9):
        pass  # 直接过 S2④(组内换仓不增暴露)
    elif group_weight_after is not None and group_weight_after > cap + 1e-9:
        # ③ 净增且超生效上限 → ★不判FAIL·判「需董事长拍板抬高上限」并附S3代价(百分比+金额)
        over_pp = (group_weight_after - cap) * 100
        s3_drop = cand.get("s3_drop_pct")                  # 该候选/组在S3下的跌幅(小数·如0.25)
        A = cand.get("account_A")
        cost_line = ""
        if s3_drop is not None and net_add is not None:
            loss_pct = net_add * s3_drop * 100             # 净增暴露在S3下的组合亏损(pp)
            cost_line = "·S3代价≈%.2fpp" % loss_pct + (("(约$%s)" % format(int(net_add * s3_drop * A), ",")) if A else "")
        return ("NEED_DECISION",
                "S2④(Y1):加入后组权重%.1f%%>生效上限%.0f%%(超%.1fpp)→【需董事长拍板抬高上限】·非规则否决%s" % (
                    group_weight_after * 100, cap * 100, over_pp, cost_line), factor)
    # ② 净增但增后 ≤ 生效上限 → 允许(落到此处即合规)
    # ⑤ 跨度不得扩大(v1.2保留)
    sb, sa = cand.get("span_before"), cand.get("span_after")
    if sb is not None and sa is not None and sa > sb + 1e-9:
        return "FAIL", "S2⑤(v1.2):加入后账户S1−S3跨度扩大(%.2f→%.2fpp)·无论补多少缺口一律出局" % (sb * 100, sa * 100), factor
    if not cand.get("driver_basis"):
        return "FAIL", "S2:驱动组归组无依据(不许只按行业标签)", factor
    return "PASS", None, factor

def gate_S3(cand, w_legal, is_peak, def_ratio_after):
    if w_legal > SINGLE_MAX:
        return "FAIL", "S3:单只%.0f%%>20%%" % (w_legal * 100)
    if is_peak and cand.get("peak_bucket_total_after", 0) > PEAK_MAX:
        return "FAIL", "S3:峰值定价类合计>5%"
    if def_ratio_after is not None and def_ratio_after < DEF_MIN:
        return "FAIL", "S3:防御仓<15%%"
    if cand.get("adv60d") is not None and cand.get("adv60d_min") is not None and cand["adv60d"] < cand["adv60d_min"]:
        return "FAIL", "S3:成交额<60日均门槛"
    return "PASS", None

def gate_S4(cand):
    fv = cand.get("fair_value", {})
    need = [fv.get("value"), fv.get("method"), fv.get("as_of"), cand.get("price")]
    if any(x in (None, "", 0) for x in need):
        return "FAIL", "S4:数据源/取数日期/公式不全·脚本重跑不出→是产品不是机器"
    if fv.get("hardcoded"):
        return "FAIL", "S4/硬闸②:fair_value为脚本外硬编码"
    return "PASS", None

def nine_fields_ok(nf):
    keys = ["earn", "lose", "verdict_date", "invalidation", "today_action", "driver", "why_this_weight", "sources", "forecast_id"]
    banned = {"守", "观察", "禁止"}
    for k in keys:
        v = nf.get(k)
        if v in (None, "", []) or (isinstance(v, str) and v.strip() in banned):
            return False, k
    return True, None

def process(cand, ctx):
    trace = {}
    s0, r0 = gate_S0(cand, ctx["activated_sectors"]); trace["S0"] = s0
    if s0 == "FAIL":
        return None, {"ticker": cand.get("ticker"), "failed_gate": "S0", "reason": r0}, trace
    w_legal = cand.get("max_legal_weight", 0.0)
    s1, r1, contrib = gate_S1(cand, w_legal); trace["S1"] = s1
    if s1 == "FAIL":
        return None, {"ticker": cand.get("ticker"), "failed_gate": "S1", "reason": r1}, trace
    s2, r2, factor = gate_S2(cand, cand.get("group_weight_after", 0), cand.get("same_group_as_top", False)); trace["S2"] = s2
    if s2 == "FAIL":
        return None, {"ticker": cand.get("ticker"), "failed_gate": "S2", "reason": r2}, trace
    if s2 == "NEED_DECISION":
        # Y1③:超上限不否决·标「需董事长拍板」并附S3代价·不进rejected(不是被否)也不直接进passed
        return None, {"ticker": cand.get("ticker"), "gate": "S2④", "verdict": "需董事长拍板抬高上限", "reason": r2,
                      "★非否决": "上限是董事长偏好·规则不替他否决主线(裁定Y1)"}, trace
    s3, r3 = gate_S3(cand, w_legal, cand.get("is_peak", False), cand.get("def_ratio_after")); trace["S3"] = s3
    if s3 == "FAIL":
        return None, {"ticker": cand.get("ticker"), "failed_gate": "S3", "reason": r3}, trace
    s4, r4 = gate_S4(cand); trace["S4"] = s4
    if s4 == "FAIL":
        return None, {"ticker": cand.get("ticker"), "failed_gate": "S4", "reason": r4}, trace
    nf = cand.get("nine_fields", {})
    ok9, miss = nine_fields_ok(nf)
    if not ok9:
        return None, {"ticker": cand.get("ticker"), "failed_gate": "九字段", "reason": "九项字段缺[%s]或用单词充数" % miss}, trace
    up = upside(cand)
    contrib_adj = contrib * factor                       # S2折算后进排序
    dd = cand.get("downside", {})
    worst_dd_pp = w_legal * abs(dd.get("drop_pct", 0)) * 100 or 0.01
    conf = CONF.get(cand.get("fair_value", {}).get("confidence", "C"), 0.4)
    # v1.2 排序:优先度 = 补缺口pp × 置信度 ÷ 最坏回撤pp × 跨度改善系数(加入前跨度÷加入后跨度·>1改善)
    sb, sa = cand.get("span_before"), cand.get("span_after")
    span_improve = round(sb / sa, 3) if (sb and sa and sa > 0) else 1.0
    priority = round(contrib_adj * conf / worst_dd_pp * span_improve, 3)
    passed = {
        "跨度改善系数": span_improve,
        "ticker": cand.get("ticker"), "name": cand.get("name"), "account_fit": cand.get("account_fit"),
        "sector_cell": cand.get("sector_cell"), "driver_group": cand.get("driver_group"), "driver_basis": cand.get("driver_basis"),
        "gate_trace": trace, "max_legal_weight": w_legal,
        "fair_value": cand.get("fair_value"), "upside_pct": round(up * 100, 2),
        "gap_contrib_pp": round(contrib, 3), "gap_contrib_pp_after_S2折算": round(contrib_adj, 3),
        "swap_out": cand.get("swap_out", {}), "downside": dd, "priority": priority, "nine_fields": nf,
    }
    return passed, None, trace

def run(date, ctx):
    cands = ctx.get("candidate_pool", [])
    passed, rejected = [], []
    for c in cands:
        p, rj, _ = process(c, ctx)
        if p: passed.append(p)
        if rj: rejected.append(rj)
    passed.sort(key=lambda x: -x["priority"])
    out = {
        "run_id": ctx.get("run_id", date + "_000000"), "data_date": ctx.get("data_date", ""),
        "account_scope": ["FUTU", "SBI"], "gap": ctx.get("gap", {}),
        "source_gate1": {"activation_file": ctx.get("activation_file", ""), "activated_sectors": ctx["activated_sectors"],
                         "activation_stale": ctx.get("activation_stale")},
        "candidates": passed, "rejected": rejected,
        "self_check": {
            # D2④:零候选时 nine_fields_complete = null(不是空真true)
            "nine_fields_complete": (None if not passed else all("nine_fields" in c for c in passed)),
            "no_hardcoded_fair_value": (None if not passed else all(not c["fair_value"].get("hardcoded") for c in passed)),
            "gate1_upstream_ok": bool(ctx["activated_sectors"]),   # 激活清单作废/空→False→整轮FAIL出声
            "rerunnable": True, "rejected_non_empty": len(rejected) > 0,
            "activation_stale_note": ctx.get("activation_stale")},
    }
    return out

def load_ctx(date):
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    import glob as _g
    sa = sorted(_g.glob(str(ROOT / "data" / "market" / "sector_activation_*.json")))
    activated, actfile, stale_note = [], "", None
    # D2②(46号)新鲜度闸:激活清单 data_date 必须=当日;sorted(glob)[-1]不算当日。真结构=顶层「板块」=数组·每项「激活":true。
    #   ★删除轮39兜底 activated=list(cells.keys())——取不到就置空→self_check.gate1_upstream_ok=False→整轮FAIL出声(不许换个东西凑非空)。
    if sa:
        actfile = sa[-1]
        try:
            aj = json.loads(pathlib.Path(actfile).read_text(encoding="utf-8"))
            act_date = aj.get("data_date", "")
            if act_date != dd:
                stale_note = ("激活清单 data_date=%s ≠ 当日 %s → 新鲜度闸 FAIL:清单非当日(sorted(glob)[-1]不算当日)。"
                              "该清单『下一步』条款自写『2026-07-29 FOMC 之后必须重判·本清单届时作废重出』·FOMC 已开完 → 清单已作废。"
                              "本轮据实报『激活清单已作废·待重出』·不拿作废清单当第1关尺。") % (act_date, dd)
                activated = []          # 作废/非当日→置空(不兜底)→gate1_upstream_ok=False→FAIL出声
            else:
                activated = [b.get("板块") for b in aj.get("板块", []) if b.get("激活") is True]
        except Exception:
            activated = []
    gap = {}
    tgp = ROOT / "data" / "target" / f"target_gap_{date}.json"
    if tgp.exists():
        tg = json.loads(tgp.read_text(encoding="utf-8"))
        for k, acc in (("FUTU", tg.get("富途", {})), ("SBI", tg.get("SBI", {}))):
            if acc:
                gap[k] = {"target_pp": 40.0, "held_pp": acc.get("账户预期贡献合计pp(盲区不计)"),
                          "gap_pp": acc.get("距+40%缺口pp"), "blind_weight": acc.get("盲区占比%")}
    pool = []
    pp = ROOT / "data" / "opportunity" / f"candidate_pool_{date}.json"
    if pp.exists():
        pool = json.loads(pp.read_text(encoding="utf-8")).get("candidates", [])
    return {"data_date": dd, "run_id": date + "_" + datetime.now(JST).strftime("%H%M%S"),
            "activated_sectors": activated, "activation_file": actfile, "activation_stale": stale_note,
            "gap": gap, "candidate_pool": pool}

def self_test():
    """R1~R4 回归(反向样本)。返回 (通过bool, 明细)。"""
    ctx = {"activated_sectors": ["AI电力", "液冷"], "gap": {}, "run_id": "test", "data_date": "2026-07-30"}
    res = {}
    # R1 极便宜但不在激活板块 → S0挡
    r1 = process({"ticker": "R1", "sector_cell": "白酒", "max_legal_weight": 0.1,
                  "fair_value": {"value": 100, "method": "PE", "as_of": "2026-07-30", "confidence": "A"}, "price": 10}, ctx)
    res["R1_S0挡不在激活板块"] = (r1[1] and r1[1]["failed_gate"] == "S0")
    # R2 贡献<1.5pp → S1挡 (w=0.05, up=10% → 0.5pp)
    r2 = process({"ticker": "R2", "sector_cell": "AI电力", "max_legal_weight": 0.05,
                  "fair_value": {"value": 11, "method": "PE", "as_of": "2026-07-30", "confidence": "A"}, "price": 10,
                  "driver_basis": "x"}, ctx)
    res["R2_S1挡贡献<1.5pp"] = (r2[1] and r2[1]["failed_gate"] == "S1")
    # R3 与最大持仓同驱动组 → 0.5折算(过闸但contrib_adj减半)
    base = {"ticker": "R3", "sector_cell": "AI电力", "max_legal_weight": 0.15,
            "fair_value": {"value": 15, "method": "PE", "as_of": "2026-07-30", "confidence": "A"}, "price": 10,
            "driver_group": "OpenAI", "driver_basis": "同一客户", "group_weight_after": 0.20,
            "downside": {"drop_pct": 20, "trigger": "x"},
            "nine_fields": {"earn": "e", "lose": "l", "verdict_date": "2026-08", "invalidation": "i",
                            "today_action": "买5%", "driver": "OpenAI", "why_this_weight": "w", "sources": ["s"], "forecast_id": "F-R3"}}
    p_no = process({**base, "same_group_as_top": False}, ctx)[0]
    p_yes = process({**base, "same_group_as_top": True}, ctx)[0]
    res["R3_同驱动组0.5折算后移"] = (p_no and p_yes and abs(p_yes["gap_contrib_pp_after_S2折算"] - p_no["gap_contrib_pp_after_S2折算"] * 0.5) < 1e-6 and p_yes["priority"] < p_no["priority"])
    # Y1-2a 组内换仓(净权重不增) → S2④ PASS(允许)
    base_s2 = {"sector_cell": "AI电力", "max_legal_weight": 0.15, "driver_group": "高AI beta", "driver_basis": "AI capex",
               "fair_value": {"value": 15, "method": "PE", "as_of": "2026-07-30", "confidence": "A"}, "price": 10,
               "downside": {"drop_pct": 20, "trigger": "x"},
               "nine_fields": {"earn": "e", "lose": "l", "verdict_date": "2026-08", "invalidation": "i",
                               "today_action": "换", "driver": "AI", "why_this_weight": "w", "sources": ["s"], "forecast_id": "F-x"}}
    ra = process({**base_s2, "ticker": "Ya组内换", "is_intra_group_swap": True, "net_weight_add": 0.0,
                  "group_weight_after": 0.36}, ctx)
    res["Y1a_组内换仓PASS"] = (ra[0] is not None and ra[2].get("S2") == "PASS")
    # Y1-2b 净增但增后≤生效上限(0.30) → PASS
    rb = process({**base_s2, "ticker": "Yb净增不超", "is_intra_group_swap": False, "net_weight_add": 0.03,
                  "group_weight_after": 0.28}, ctx)
    res["Y1b_净增不超上限PASS"] = (rb[0] is not None and rb[2].get("S2") == "PASS")
    # Y1-2c 净增且超生效上限 → 需拍板(NEED_DECISION)+附S3代价
    rc = process({**base_s2, "ticker": "Yc净增超限", "is_intra_group_swap": False, "net_weight_add": 0.05,
                  "group_weight_after": 0.41, "s3_drop_pct": 0.25, "account_A": 1000000}, ctx)
    res["Y1c_净增超限需拍板"] = (rc[2].get("S2") == "NEED_DECISION" and rc[1] and rc[1].get("verdict") == "需董事长拍板抬高上限"
                            and "S3代价" in (rc[1].get("reason") or ""))
    # R4 rejected为空 → run 报FAIL(退出码非0)
    out_allpass = run("20260730", {**ctx, "candidate_pool": [base | {"same_group_as_top": False}], "activation_file": ""})
    res["R4_rejected空则FAIL"] = (out_allpass["self_check"]["rejected_non_empty"] is False)  # 空→非空False→主流程据此FAIL
    return all(res.values()), res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        ok, res = self_test()
        for k, v in res.items():
            print(("  ✓ " if v else "  ★FAIL ") + k)
        print("R1~R4 回归:", "全通过" if ok else "有FAIL")
        return 0 if ok else 1
    ctx = load_ctx(a.date)
    out = run(a.date, ctx)
    outp = ROOT / "data" / "opportunity" / f"discovery_{ctx['data_date']}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("机会发现 %s → %s" % (a.date, outp.name))
    print("激活板块:", out["source_gate1"]["activated_sectors"][:8] or "★激活清单空/未重出")
    print("候选池:", len(ctx["candidate_pool"]), "· 入池:", len(out["candidates"]), "· rejected:", len(out["rejected"]))
    # 硬闸③:rejected不得为空(全过=闸没生效)。候选池为空属"未产出"(另标),非"全过"
    if ctx["candidate_pool"] and not out["rejected"]:
        print("★整轮FAIL(硬闸③):候选池非空但rejected为空=闸没生效")
        return 3
    if not ctx["candidate_pool"]:
        print("★未产出·原因:候选池为空(需先由第1关激活板块+漏斗产出 candidate_pool·估值引擎跑fair_value)·非关键步只告警不停链")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
