# -*- coding: utf-8 -*-
"""★轮147 E8/看板G21要素二:【右→左】印证——尺反过来检验左栏判断有没有偏离。
现状只有【左→右】(今日事实映射到尺·判印证/动摇);本闸补【右→左】:每条左栏判断必须声明依据哪把尺+与尺是否矛盾。
★A-3 禁止:左栏悄悄偏离右栏而不声明 → 闸 FAIL。★A-4 判定靠结构化字段(尺ID + 矛盾枚举)·不靠文本比对。
★矛盾时 Opus5 二选一:(a)修正判断 (b)提改尺【须董事长签字】·Code 只检测不裁。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RULERS = {"①世界观", "②国家战略", "③资金流动", "④板块地图", "⑤过滤五关", "⑥持仓档案"}
CONFLICT_ENUM = {"无矛盾", "不矛盾", "★修正判断", "修正判断", "★提改尺", "提改尺"}   # ★轮337:补『不矛盾』≡『无矛盾』(同义·防同义词误FAIL)+去★前缀变体


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
        # ★轮337:识别尺依据更宽——层号前缀(①~⑥) 或 尺描述关键词含在文本里(如"过滤"/"板块地图")。防仅因格式(《尺名》vs 层号开头)误FAIL。
        _RULER_KW = ("世界观", "国家战略", "战略地图", "资金流动", "板块地图", "过滤", "护城河", "估值", "持仓档案", "预测锁定", "漂移", "风险配仓")
        _declared = bool(ruler) and (any(ruler.startswith(r[0]) for r in RULERS) or any(kw in str(ruler) for kw in _RULER_KW))
        if not _declared:
            fails.append({**rec, "★FAIL": "★左栏判断【未声明依据右栏哪把尺】(悄悄偏离·A-3)→FAIL·须Opus5补尺ID"})
        elif conflict not in CONFLICT_ENUM and not any(conflict.startswith(c[:2]) for c in CONFLICT_ENUM):
            fails.append({**rec, "★FAIL": "★左栏判断【未声明与尺是否矛盾】(悄悄偏离·A-3)→FAIL·须Opus5填枚举(无矛盾/修正/提改尺)"})
        elif "提改尺" in conflict and not g.get("★改尺提案(仅当上项=提改尺·须董事长签字)"):
            fails.append({**rec, "★FAIL": "★声明【提改尺】但缺改尺提案+董事长签字→FAIL(改尺须董事长签字·A-2)"})
        else:
            _noconf = conflict in ("无矛盾", "不矛盾")   # ★轮337:两者同义=不矛盾
            ok.append({**rec, "结论": "✓ 已声明尺依据+矛盾状态" + ("·无矛盾" if _noconf else "·矛盾走修正/改尺已闭环")})
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
        "★判定依据": "结构化字段(依据尺ID枚举 + 与尺矛盾枚举)·非文本比对(§5.4)",
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
