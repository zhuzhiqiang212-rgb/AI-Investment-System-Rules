# -*- coding: utf-8 -*-
"""★★★轮200 · 漏斗加固【攻击测试】——证明 GPT V7 退回要求的 9 条结果。
每条=①攻击/绕过尝试必须被拦 + ②合规必须放行(不误杀)。★对真实产物做实际解析+攻击(证明9)。
输出 data/funnel/attack_test_results_20260805.json(真实输入输出·供GPT代码级复验)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dup_count_gate as dg
import triage_gate as tg
import l2_anchor_pe as la


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def run(date="2026-08-05"):
    dc = date.replace("-", "")
    anchor_file = ROOT / "data/funnel" / f"L2_anchor_pe_{dc}.json"
    triage_file = ROOT / "data/funnel" / f"L2_triage_{dc}.json"
    evid_file = ROOT / "data/funnel" / f"dup_gate_test_evidence_{dc}.json"
    an = _rj(anchor_file); tr = _rj(triage_file); ev = _rj(evid_file)
    rows = an.get("全189逐只", [])
    anchor_recs = an.get("★锚点记录(六项留痕·A-3)", [])
    R = []

    def rec(no, name, passed, detail):
        R.append({"结果": no, "证明": name, "通过": bool(passed), "细节": detail})

    # 证明1:三年高不影响任何排序结果——扰动参考_空间④/三年高·rank_by_space2输出不变
    base = [dict(r) for r in rows]
    top_base = [r["代码"] for r in la.rank_by_space2(base, 30)]
    pert = []
    for i, r in enumerate(rows):
        rr = dict(r)
        rr["参考_空间④(仅参考·不排序)"] = 999.0 - i   # 极端扰动
        rr["参考列_三年最高价(★不作排序锚点·C-1)"] = 1e9 - i
        pert.append(rr)
    top_pert = [r["代码"] for r in la.rank_by_space2(pert, 30)]
    rec(1, "三年高不影响任何排序结果", top_base == top_pert,
        {"扰动前后top30代码序列一致": top_base == top_pert, "top5": top_base[:5]})

    # 证明2:拆分记录不能绕过事实/驱动重复(★含A-2:换个事实ID但内容指纹同也拦)
    a2a = dg.check(dg._attack_fact_split()); a2b = dg.check(dg._sample_sndk_split()); a2c = dg.check(dg._attack_fact_relabel())
    rec(2, "拆分记录不能绕过事实或驱动重复检查", (not a2a["pass"]) and (not a2b["pass"]) and (not a2c["pass"]),
        {"同事实拆2证据ID被拦": not a2a["pass"], "SNDK拆分被拦": not a2b["pass"],
         "★A-2换事实ID+改措辞(内容指纹同)被拦": not a2c["pass"], "命中": a2c["命中判定"]})

    # 证明3:自报独立不能关闭强闸
    a3 = dg.check(dg._attack_selfreport_false())
    rec(3, "自报独立性不能关闭强闸", not a3["pass"],
        {"三驱动全自报独立=False仍被拦": not a3["pass"], "命中": a3["命中判定"]})

    # 证明4:不同锚点不会身份混淆(★A-3:任一身份属性不同即须不同id)+ 真实产物anchor_id唯一
    a4 = dg.check_anchors(dg._attack_anchor_collision())
    a4b = dg.check_anchors(dg._attack_anchor_attr_change())   # ★仅『异常值处理』不同
    real_ids = [a.get("anchor_id") for a in anchor_recs]
    real_unique = len(real_ids) == len(set(real_ids))
    rec(4, "不同锚点不会身份混淆", (not a4["pass_期间与字段"]) and (not a4b["pass_期间与字段"]) and real_unique,
        {"多属性不同复用id被判碰撞": not a4["pass_期间与字段"],
         "★A-3仅异常值处理不同也判碰撞": not a4b["pass_期间与字段"], "真实产物anchor_id全唯一": real_unique})

    # 证明5:锚点失效覆盖全部关联标的(含list漏登记但rows引用·★A-4多条记录双向核对)
    anc, rws = dg._attack_invalidate_leak()
    inv = dg.invalidate_anchor(anc, "AID1", rows=rws)
    anc2, rws2 = dg._attack_multi_record_invalidate()
    inv2 = dg.invalidate_anchor(anc2, "MULTI", rows=rws2)
    multi_ok = set(inv2["须同时重算的标的"]) == {"US.R1", "US.R2", "US.R3", "US.R4"} and ("US.R4" in inv2["★仅rows引用有(登记表漏登记)"])
    rec(5, "锚点失效能够覆盖全部关联标的", ("US.LEAK" in inv["须同时重算的标的"]) and multi_ok,
        {"覆盖list漏登记但rows引用的US.LEAK": "US.LEAK" in inv["须同时重算的标的"],
         "★A-4多条记录并全+双向核对(R1-R4全覆盖·R4标出登记漏)": multi_ok, "multi只数": inv2["只数"]})

    # 证明6:未知或冲突期间不会通过
    a6u = dg.check_anchors(dg._attack_anchor_unknown_period())
    a6c = dg.check_anchors(dg._sample_anchor_period_bad())
    rec(6, "未知或冲突期间不会通过", (not a6u["pass_期间与字段"]) and (not a6c["pass_期间与字段"]),
        {"未知期间被拦": not a6u["pass_期间与字段"], "冲突期间(TTMvs预测年)被拦": not a6c["pass_期间与字段"]})

    # 证明7:★轮203 A/B档不可用(无验证器·自报标志被忽略)+ C档只格式检查不给合格
    t7 = tg.enforce(tg._attack_A_selfreport_verified() + tg._attack_B_selfreport_verified()
                    + tg._attack_C_abcdef() + tg._attack_C_random())
    rA = next(x for x in t7["逐只"] if x["代码"] == "US.SRV")
    rB = next(x for x in t7["逐只"] if x["代码"] == "US.SRB")
    rAbc = next(x for x in t7["逐只"] if x["代码"] == "US.ABC")
    checks7 = {
        "A档自报已联网核验→台账未合格降C": rA["判定档"] == "C" and rA["明细"].get("验证器台账合格") is False,
        "B档自报已联网核验→台账未合格降C": rB["判定档"] == "C" and rB["明细"].get("验证器台账合格") is False,
        "C档abc def不获『合格』(只格式通过+内容未验证)": rAbc.get("C档内容有效性", "").startswith("未验证") and rAbc.get("C档格式检查") == "通过",
    }
    rec(7, "A/B档凭验证器台账开放(删自报标志·假域名未核不开放)+C档只格式检查不给合格", all(checks7.values()), checks7)

    # 证明8:数量一致——★从【完整记录】独立计数(rerun_dataset:189全量+30分档全量·非预填)
    ds = _rj(ROOT / "data/funnel" / f"rerun_dataset_{dc}.json")
    r189 = ds.get("rows_189", []); triC = ds.get("triage_C_records", [])
    n_space2 = sum(1 for r in r189 if r.get("空间②") is not None)
    t8 = tg.enforce(triC)
    checks8 = {
        "完整排序记录条数==189": len(r189) == 189,
        "有空间②条数==C-3(93)": n_space2 == ds.get("C3_用②数") == 93,
        "分档记录条数==30": len(triC) == 30,
        "30条全判C·格式检查全通过(内容一律未验证)": t8["各档最终数量"] == {"A": 0, "B": 0, "C": 30} and not t8["C档格式不通过清单"],
        "top30==按空间②排序前30(可独立复算)": [x["代码"] for x in la.rank_by_space2([{"代码": r["代码"], "空间②": r["空间②"]} for r in r189], 30)] == [t["代码"] for t in triC],
    }
    rec(8, "全部文件/记录数量/说明一致(★完整记录独立计数)", all(checks8.values()), checks8)

    # 证明9:★诚实命名——【复跑所需记录集】(排序189/分档30/锚点20)完整解析+攻击测试(★非全字段原始产物)
    import adversarial_test as adv
    advR = adv.battery()
    a9 = dg.check(dg._attack_missing_field())
    bypass = sum(1 for x in advR if not x["拦住"])   # ★对抗BYPASS计数(轮202:全BLOCK→0)
    parse_ok = {
        "L2_anchor_pe可解析": bool(an), "rerun_dataset可解析": bool(ds),
        "真实锚点过闸": dg.check_anchors(anchor_recs).get("pass_期间与字段", False) if anchor_recs else False,
        "缺字段攻击硬FAIL": not a9["pass"],
        "对抗全部攻击拦截(BYPASS=0)": bypass == 0,
    }
    rec(9, "复跑所需记录集(排序189/分档30/锚点20)完整解析+攻击测试(★非全字段原始产物·全字段在L2_anchor_pe.json)",
        all(parse_ok.values()), {**parse_ok, "对抗BYPASS数": bypass})

    # ★★★轮202 A-2/轮203:总裁定硬编码——任一BYPASS或任一结果未过 → 绝不『全过』
    allpass_9 = all(x["通过"] for x in R)
    layer1_pass = allpass_9 and bypass == 0
    总裁定 = "不通过(对抗存在%d条BYPASS)" % bypass if bypass > 0 else ("离线复跑模式通过·对抗0BYPASS" if allpass_9 else "不通过(有结果未过)")
    out = {"date": date, "_说明": "★轮203攻击测试·9条结果+总裁定硬编码+★四层结论(第②层未通过)。",
           "★9条全过": allpass_9, "对抗BYPASS数": bypass,
           "★★★总裁定(硬编码·有BYPASS则不通过)": 总裁定,
           "★★★四层结论": adv.four_layers(layer1_pass),
           "逐条": R}
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / f"attack_test_results_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="2026-08-05"); a = ap.parse_args()
    o = run(a.date)
    print("═══ 轮203 漏斗攻击测试 · 9条+总裁定硬编码+四层 ═══")
    for x in o["逐条"]:
        print("%s 结果%d · %s" % ("PASS" if x["通过"] else "FAIL", x["结果"], x["证明"]))
    print("对抗BYPASS数：%d" % o["对抗BYPASS数"])
    print("★★★总裁定：%s" % o["★★★总裁定(硬编码·有BYPASS则不通过)"])
    print("★★★四层结论：")
    for k, v in o["★★★四层结论"].items():
        print("   %s：%s" % (k, v))
    return 0 if (o["★9条全过"] and o["对抗BYPASS数"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
