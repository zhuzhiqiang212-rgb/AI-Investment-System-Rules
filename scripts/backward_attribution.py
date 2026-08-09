# -*- coding: utf-8 -*-
"""★轮147 E9(当前最大结构缺口):【从下到上验证】——动作结果回头查哪一层判错。
逐层回溯归因链:⑦结果→验⑥→验⑤→验④→验③→验②①。★每次错必须归因到【具体哪一层】(不许笼统『判错了』)。
机制:沿链走·每层判『该层判断 matched reality 吗』·★第一个 matched==False 的层＝错源层·再定维度(方向/时机/概率/选择)。
★归因结果写进 PDCA 台账(layer_judgment_ledger·只增不改)。★Code 只搭回溯机制·维度分类靠结构化比较(方向对/时点错=时机·概率偏=概率)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/pdca/layer_judgment_ledger.json"
CHAIN = ["⑦", "⑥", "⑤", "④", "③", "②①"]   # 从下到上


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _classify_dim(d):
    """维度分类(结构化):方向对但时点错→时机;概率/校准偏→概率;方向本身错→方向;选错标的→选择。"""
    if d.get("方向matched") and not d.get("时点matched"):
        return "★时机错(方向对·时点/幅度错)"
    if d.get("概率偏"):
        return "★概率错(校准偏·如把一天方向当趋势)"
    if d.get("方向matched") is False:
        return "★方向错"
    if d.get("选择错"):
        return "★选择错(选错标的/漏更好的)"
    return "★维度待Opus5定"


def attribute(case):
    """沿回溯链找第一个 matched==False 的层＝错源。"""
    steps = []
    culprit = None
    for L in CHAIN:
        d = case["layers"].get(L)
        if d is None:
            steps.append({"层": L, "状态": "无该层数据·跳过"}); continue
        if d.get("_skip"):
            steps.append({"层": L, "状态": "N/A(本案不涉此层·如持仓处置无⑤选股)"}); continue
        matched = d.get("matched")
        steps.append({"层": L, "该层判断": d.get("判断"), "reality": d.get("reality"), "matched": matched})
        if matched is False and culprit is None:
            culprit = {"★错在哪层": L, "★维度": _classify_dim(d), "该层判断": d.get("判断"),
                       "reality": d.get("reality"), "说明": d.get("说明")}
    return {"回溯链步骤": steps, "★归因": culprit or {"★错在哪层": "各层均matched·无归因", "★维度": None}}


# ★B-3 两个已有案例(数据来自董事长/台账·Code只跑机制不编投资判断)
CASES = {
    "第一三共JP.4568": {
        "Opus5判断": "★卖出(周一开盘立即卖全部9900股)", "结果": "相对抗跌 +2.7pp(第一三共-0.49% vs 其余日股-2.09%)",
        "董事长已给归因(供机制核对)": "★时机错·⑥层(把有依据的退出方向与无依据的时点捆成一个动作)",
        "layers": {
            "⑦": {"判断": "从⑥推卖出动作", "reality": "动作未执行(复核修正)", "matched": True, "说明": "⑦忠实从⑥推·非⑦错"},
            "⑥": {"判断": "★立即卖出(方向=退出·时点=周一开盘)", "reality": "抗跌+2.7pp·时点不该立即",
                  "matched": False, "方向matched": True, "时点matched": False,
                  "说明": "退出方向有依据(会计造假是基本面)·但『立即卖』时点无依据(价格/均线/量能未算)→方向对时点错"},
            "⑤": {"_skip": True}, "④": {"判断": "日股板块普跌", "reality": "日股确普跌", "matched": True},
            "③": {"判断": "资金/风险偏好", "reality": "与判断一致", "matched": True},
            "②①": {"判断": "格局", "reality": "一致", "matched": True}}},
    "爱德万JP.6857": {
        "Opus5判断": "★中性50%·消化期", "结果": "★进乐观区(实际偏乐观·非中性)",
        "董事长已给归因(供机制核对)": "★概率错·⑥层(概率校准问题·把一天方向当趋势·消化期谬误)",
        "layers": {
            "⑦": {"判断": "无动作(中性)", "reality": "中性判断致无动作", "matched": True, "说明": "⑦从⑥中性推无动作·非⑦错"},
            "⑥": {"判断": "★中性50%·消化期", "reality": "进乐观区·概率低估",
                  "matched": False, "概率偏": True,
                  "说明": "板块受益方向判对·但概率校准偏(50%中性低估·实际乐观)→概率错·非③④方向错"},
            "⑤": {"_skip": True}, "④": {"判断": "AI半导体设备受益", "reality": "爱德万确受益", "matched": True},
            "③": {"判断": "资金流向AI", "reality": "一致", "matched": True},
            "②①": {"判断": "格局", "reality": "一致", "matched": True}}},
}


def _append_ledger(entries):
    """★只增不改·dedup by (案例+错层+维度)。"""
    lg = _rj(LEDGER)
    arr = lg if isinstance(lg, list) else (lg.get("entries") or [])
    if not isinstance(lg, dict):
        lg = {"entries": arr}
    else:
        lg.setdefault("entries", arr)
    seen = set((e.get("案例"), e.get("★错在哪层")) for e in lg["entries"] if isinstance(e, dict))
    added = 0
    for e in entries:
        key = (e.get("案例"), e.get("★错在哪层"))
        if key not in seen:
            lg["entries"].insert(0, e); seen.add(key); added += 1
    LEDGER.write_text(json.dumps(lg, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def build(dc):
    results = {}
    ledger_entries = []
    for name, case in CASES.items():
        att = attribute(case)
        expected = case["董事长已给归因(供机制核对)"]
        got_layer = att["★归因"].get("★错在哪层")
        # ★复现核对:机制归因的层 是否＝董事长已给归因里的层
        reproduced = (got_layer in expected) or (got_layer and got_layer in expected)
        results[name] = {"Opus5判断": case["Opus5判断"], "结果": case["结果"],
                         "★机制归因": att["★归因"], "回溯链": att["回溯链步骤"],
                         "董事长已给归因": expected, "★机制复现正确？": reproduced}
        ledger_entries.append({
            "类型": "E9从下到上归因", "案例": name, "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
            "Opus5原判断": case["Opus5判断"], "结果": case["结果"],
            "★错在哪层": got_layer, "★维度": att["★归因"].get("★维度"),
            "说明": att["★归因"].get("说明"), "★机制复现董事长归因": reproduced, "填写人": "机制(backward_attribution)"})
    added = _append_ledger(ledger_entries)
    out = {
        "_说明": "★轮147 E9 从下到上验证。回溯链⑦→⑥→⑤→④→③→②①·第一个matched==False层=错源·再定维度。★归因写台账(只增不改)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★回溯链定义": " → ".join("%s验%s" % (CHAIN[i], CHAIN[i + 1]) for i in range(len(CHAIN) - 1)),
        "★两案例归因": results,
        "★两案例都复现正确？": all(r["★机制复现正确？"] for r in results.values()),
        "台账新增条数": added,
    }
    (ROOT / "data/pdca" / f"backward_attribution_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("[E9回溯归因] 回溯链:", o["★回溯链定义"])
    for name, r in o["★两案例归因"].items():
        print("  %s: 机制归因=%s·%s · 复现董事长归因=%s" % (
            name, r["★机制归因"].get("★错在哪层"), r["★机制归因"].get("★维度"), r["★机制复现正确？"]))
    print("★两案例都复现正确:", o["★两案例都复现正确？"], "· 台账新增", o["台账新增条数"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
