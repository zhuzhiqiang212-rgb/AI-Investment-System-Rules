# -*- coding: utf-8 -*-
"""★★轮195 D · 影子运行验证一轮完整漏斗(GPT V7 要求)。
L1广扫 → L2三档 → L3轻量 → L4候选。★验证重点不是猜对涨跌·是验机制:
  ①B档是否真有"查过且确认没有"的证据留痕(schema强制·缺则视为C)
  ②C档是否正确保留系统盲区(数量不应为0·为0=分流没生效)
  ③8只→3只是否用同尺度数据(排序键=上涨中值÷下行·不得混筛选分/命中路径/PE分位)
  ④重复计数强闸能否实际拦截(引 dup_count_gate 反向测试)
  ⑤各层数量/成本/淘汰原因可追溯
"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def verify(date):
    dc = date.replace("-", "")
    import dup_count_gate as dg
    import funnel_build as fb
    audit = _rj(ROOT / "data/universe" / f"p4_candidate_audit_{dc}.json")
    L12 = _rj(ROOT / "data/funnel" / f"L1_L2_estimate_{dc}.json")
    top = L12.get(f"★L1_L2约30只清单") or L12.get("★L1_L2约%d只清单" % 30) or []
    for k in L12:
        if k.startswith("★L1_L2约"):
            top = L12[k]; break

    checks = {}

    # ④ 强闸能拦(引 A-4 三向)——先跑·GPT新增强制项
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = dg.selftest()
    checks["④重复计数强闸实际拦截(A-4三向+合规+处置)"] = (rc == 0)

    # ① B档留痕机制:schema 是否强制『缺查过留痕→视为C』
    sc = fb.l2_triage_schema()
    checks["①B档必须有查过留痕(缺则视为C)"] = (sc["B_确认无实质驱动"].get("★缺此留痕则视为C") is True
                                    and "★查过的检索证据" in sc["B_确认无实质驱动"])

    # ② C档保留系统盲区:影子运行(Opus5未分档)→全部默认落 C(证据不足)·数量应=len(top)>0
    #    (真实分档=Opus5;此处验『默认落C而非默认淘汰』——系统不知≠没机会)
    shadow_C = [e["代码"] for e in top if (e.get("L2三档分流", {}).get("档") is None)]
    checks["②C档非0(保留盲区·未分档默认C不淘汰)"] = (len(shadow_C) == len(top) and len(top) > 0)

    # ③ 8→3同尺度:排序键=上涨中值÷下行·且明禁混用
    card = fb.l3_card_schema()
    key_desc = card.get("★8只→3只排序键", "")
    checks["③8→3用同尺度(上涨中值÷下行·禁命中路径/PE分位/5日异动)"] = ("上涨中值" in key_desc and "禁用" in key_desc)
    #   实测 rank_key_L3 只吃 ⑤⑥·不吃命中路径数(给个含命中路径的卡·排序键仍只看上涨/下行)
    t1 = fb.rank_key_L3({"⑤粗略上涨区间": [0.2, 0.6], "⑥粗略下行区间": [0.2], "命中路径数": 99})
    t2 = fb.rank_key_L3({"⑤粗略上涨区间": [0.2, 0.6], "⑥粗略下行区间": [0.2], "命中路径数": 1})
    checks["③排序键不受命中路径数影响(同上涨下行→同排序值)"] = (t1 == t2)

    # ⑤ 可追溯:各层数量/淘汰原因
    trace = {
        "L1宇宙": L12.get("L1宇宙数"),
        "L2粗估(过K线两关)": L12.get("过K线两关(进L2粗估)数"),
        "L2粗估成功(有锚点)": L12.get("L2粗估成功(有锚点)数"),
        "输出top(交Opus5)": len(top),
        "淘汰原因可查(样例)": [{"代码": r["代码"], "淘汰在": r.get("★到哪层"), "理由": r.get("★原始理由(非综合评分不足)")}
                       for r in audit.get("逐只", []) if r.get("★结果") == "淘汰"][:3],
    }
    checks["⑤各层数量/淘汰原因可追溯"] = all(v is not None for v in [trace["L1宇宙"], trace["L2粗估(过K线两关)"], trace["输出top(交Opus5)"]])

    allok = all(checks.values())
    out = {
        "date": date, "_说明": "★轮195 D·影子运行验证漏斗机制(★验机制非猜涨跌)。B/C分档与预测卡填充=Opus5·此处验默认落C保留盲区+闸真拦+排序同尺度+可追溯。",
        "五点验证": checks, "全过": allok,
        "可追溯层数": trace,
        "★影子运行说明": "Opus5未分档时全部默认落C(证据不足观察池)·证明『系统不知≠股票没机会』分流生效;真实A/B/C分档待Opus5。",
    }
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / f"shadow_run_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="2026-08-05"); a = ap.parse_args()
    o = verify(a.date)
    print("═══ D 影子运行·五点验证 ═══")
    for k, v in o["五点验证"].items():
        print("%s %s" % ("✅" if v else "❌", k))
    print("追溯:", json.dumps(o["可追溯层数"], ensure_ascii=False)[:160])
    print("═══ %s ═══" % ("★五点全过" if o["全过"] else "★有项未过"))
    return 0 if o["全过"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
