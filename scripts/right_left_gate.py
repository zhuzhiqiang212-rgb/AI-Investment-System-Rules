# -*- coding: utf-8 -*-
"""★轮147 E8/看板G21要素二:【右→左】印证——尺反过来检验左栏判断有没有偏离。
现状只有【左→右】(今日事实映射到尺·判印证/动摇);本闸补【右→左】:每条左栏判断必须声明依据哪把尺+与尺是否矛盾。
★A-3 禁止:左栏悄悄偏离右栏而不声明 → 闸 FAIL。★A-4 判定靠结构化字段(尺ID + 矛盾枚举)·不靠文本比对。
★矛盾时 Opus5 二选一:(a)修正判断 (b)提改尺【须董事长签字】·Code 只检测不裁。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RULERS = {"①世界观", "②国家战略", "③资金流动", "④板块地图", "⑤过滤五关", "⑥持仓档案"}
CONFLICT_ENUM = {"无矛盾", "★修正判断", "★提改尺"}   # ★轮338:退回轮337错误放松·严格枚举·只认这三个值(不认同义词·错的是填写方就退回改填)


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def check(dc):
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    slots = js.get("②~⑦层工单", {}) or {}
    fails, ok = [], []
    for k, s in slots.items():
        g = s.get("槽位", {}) or {}
        judged = g.get("本层判断")
        if not judged:
            continue   # 未填→E9的三态管·此闸只查已填判断是否声明尺依据
        # ★A-4 结构化判定(不靠文本)
        ruler = g.get("★依据右栏哪把尺(①~⑥·E8必填)")
        conflict = str(g.get("★与尺是否矛盾(E8枚举·必填)") or "")
        rec = {"层": k, "判断": str(judged)[:40], "依据尺": ruler, "与尺矛盾": conflict}
        # ★轮338(退回轮337错误放松·§5.4):严格结构化判定——不做关键词包含/前缀猜/同义词。
        #   依据尺【必须以 ①~⑥ 层号开头】(结构化前缀);与尺矛盾【必须完全等于】CONFLICT_ENUM 之一。
        #   ★错的是填写方就退回让Opus5改填(工单已印_允许值),★不放松闸迁就。
        if not ruler or ruler[0] not in "①②③④⑤⑥":
            fails.append({**rec, "★FAIL": "★左栏判断【依据右栏哪把尺 未以①~⑥层号开头】(未按结构化格式声明·A-3)→FAIL·须Opus5改填(见工单_允许值/_格式要求)"})
        elif conflict not in CONFLICT_ENUM:
            fails.append({**rec, "★FAIL": "★左栏判断【与尺是否矛盾 非合法枚举值】(实填=%r·须完全等于 无矛盾/★修正判断/★提改尺)→FAIL·须Opus5改填(见工单_允许值)" % conflict})
        elif conflict == "★提改尺" and not g.get("★改尺提案(仅当上项=提改尺·须董事长签字)"):
            fails.append({**rec, "★FAIL": "★声明【★提改尺】但缺改尺提案+董事长签字→FAIL(改尺须董事长签字·A-2)"})
        else:
            ok.append({**rec, "结论": "✓ 已声明尺依据+矛盾状态" + ("·无矛盾" if conflict == "无矛盾" else "·矛盾走修正/改尺已闭环")})
    # ⑥复核也查(第一三共)
    rc = (slots.get("⑥持仓比较", {}) or {}).get("★须复核既有判断(NV3)", [])
    for r in rc:
        cs = r.get("★复核槽位(Opus5填)", {}) or {}
        if cs.get("维持原判/修正/撤回"):
            ruler = cs.get("★依据右栏哪把尺(①~⑥·E8必填)")
            if not ruler:
                fails.append({"层": "⑥复核·" + str(r.get("标的")), "★FAIL": "★复核结论未声明依据哪把尺(悄悄偏离·A-3)→FAIL"})
    out = {
        "_说明": "★轮147 E8 右→左印证闸。每条左栏判断必须声明依据右栏哪把尺+与尺是否矛盾(结构化)。悄悄偏离→FAIL。改尺须董事长签字。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★闸结果": "FAIL" if fails else "PASS",
        "★已填判断数": len(ok) + len(fails), "FAIL数": len(fails),
        "★FAIL明细(悄悄偏离/未声明)": fails, "已声明合规": ok,
        "★判定依据": "★结构化判定(§5.4·轮338退回轮337放松)：依据尺=必须以①~⑥层号开头(结构化前缀·非关键词包含) + 与尺矛盾=必须完全等于枚举值{无矛盾/★修正判断/★提改尺}(非同义词/前缀猜)。★闸自述与实际一致：不做自由文本关键词匹配。",
    }
    (ROOT / "data/logs" / f"right_left_gate_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = check(a.date.replace("-", ""))
    print("[E8右→左闸] %s · 已填判断%d · FAIL%d" % (o["★闸结果"], o["★已填判断数"], o["FAIL数"]))
    for f in o["★FAIL明细(悄悄偏离/未声明)"]:
        print("  FAIL:", f.get("层"), "·", f.get("★FAIL"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
