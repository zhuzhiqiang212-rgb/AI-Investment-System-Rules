# -*- coding: utf-8 -*-
"""★轮110 NP2:决策资格硬闸(GPT第一关+最终决策对象)。两道结构化校验(守§5.4·靠字段不靠文本关键词)：
A. 第一关事实完整性：①层 worldview 总命中=0(事实未确证进入) → ★下游无资格出【确定性交易动作】·
   产品只能输出「输入不完整·今日决策暂停更新·沿用上一轮判断(醒目标注)」。判定靠 worldview.总命中/★零命中分类(结构化)。
B. 最终决策对象/版本覆盖：同一标的 opus5_content『今天做什么』(定性·可能旧日沿用) 与 production.action(量化当日) 冲突·
   且无 decisions_{dc} 唯一决定表 reconcile → ★两套动作并存·FAIL(修最终决策对象与版本覆盖逻辑)。
★本闸一上·当日①层0命中的册会被判「无资格出确定性动作」——那是对的(NP2-4)。"""
import sys, json, re, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _act_class(text):
    """把动作文本归成枚举:卖/买/等(结构化·供冲突判定)。确定性动作=卖/买。"""
    t = str(text or "")
    if re.search(r"卖出|清仓|减仓|处置", t):
        return "卖"
    if re.search(r"买入|建仓|加仓", t):
        return "买"
    if re.search(r"不买入|不动|维持|观望|不加不减|受检", t) or t.strip() in ("等", "守", "持有"):
        return "等"
    return "等"


def check(date):
    dc = date.replace("-", "")
    fails, notes = [], []
    # ── A. 第一关事实完整性(结构化:worldview 总命中/★零命中分类) ──
    wv = _rj(ROOT / "data/market" / f"worldview_{dc}.json")
    st = _rj(ROOT / "data/market" / f"strategy_{dc}.json")
    wv_hit = wv.get("总命中"); wv_z = wv.get("★零命中分类(NK2·全局)", "?")
    st_hit = st.get("总命中")
    first_gate_pass = isinstance(wv_hit, int) and wv_hit > 0
    if first_gate_pass:
        notes.append("第一关(事实完整性)PASS：①层总命中=%s(有实质事实进入)" % wv_hit)
    else:
        notes.append("第一关(事实完整性)未过：①层总命中=%s·零命中分类『%s』(事实未确证进入)" % (wv_hit, wv_z))

    # ── B. 最终决策对象/版本覆盖:opus5『今天做什么』 vs production.action 冲突且无决定表 ──
    op = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    op_carry = any(k.startswith("_") and "沿用" in k for k in op)  # 是否08-02沿用
    op_act = {}
    for x in op.get("三_逐只判断", []):
        m = re.search(r"([A-Z]{2}\.[0-9A-Z]+)", str(x.get("标的", "")))
        if m:
            op_act[m.group(1)] = _act_class(x.get("今天做什么"))
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    pr_act = {h.get("symbol"): _act_class(h.get("action")) for h in prod.get("holdings", [])}
    dec = _rj(ROOT / "data/pdca" / f"decisions_{dc}.json").get("decisions", {})
    conflicts = []
    for sym in set(op_act) & set(pr_act):
        a1, a2 = op_act[sym], pr_act[sym]
        if a1 != a2 and (a1 in ("卖", "买") or a2 in ("卖", "买")):  # 至少一方是确定性动作
            reconciled = sym in dec  # 唯一决定表是否收敛
            conflicts.append((sym, a1, a2, reconciled))
    unreconciled = [c for c in conflicts if not c[3]]
    if unreconciled:
        for sym, a1, a2, _ in unreconciled:
            fails.append("NP1-B 两套动作并存·无最终决策对象：%s 定性层(opus5『今天做什么』%s%s) vs 量化层(production.action %s)冲突·decisions_%s 无该只收敛→版本覆盖逻辑缺失·FAIL" % (
                sym, a1, "·08-02沿用" if op_carry else "", a2, dc))
    else:
        notes.append("最终决策对象：opus5×production 无未收敛冲突(或有decisions收敛)")

    # ── 合判:第一关未过 但产品/数据里有确定性动作 → 无资格却出了动作(GPT根因) ──
    #   ★并集(非merge覆盖):任一来源(opus5或production)出确定性动作即算(否则pr_act的『等』会盖掉opus5的『卖』)。
    determinate_actions = {}
    for s in set(op_act) | set(pr_act):
        if op_act.get(s) in ("卖", "买"):
            determinate_actions[s] = op_act[s]
        elif pr_act.get(s) in ("卖", "买"):
            determinate_actions[s] = pr_act[s]
    if not first_gate_pass and determinate_actions:
        fails.append("NP2 无资格却出确定性动作：第一关(①层事实完整性)未过(总命中%s)·但存在确定性交易动作 %s——★下游应改输出「输入不完整·今日决策暂停更新·沿用上一轮判断(醒目标注)」·不得出确定性交易结论→FAIL" % (
            wv_hit, list(determinate_actions.keys())))
        notes.append("★本册应判：【无资格出确定性动作·输入不完整·决策暂停更新·沿用上一轮(醒目标注)】(NP2-2/NP2-4)")
    return fails, notes, {"第一关pass": first_gate_pass, "wv总命中": wv_hit, "冲突": conflicts,
                          "确定性动作": determinate_actions, "opus5沿用": op_carry}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, notes, info = check(a.date)
    for n in notes:
        print("  ·", n)
    if fails:
        print("[决策资格闸 FAIL] %d 条——★本册无资格出确定性交易动作：" % len(fails))
        for f in fails:
            print("  ✗", f)
        return 6
    print("[决策资格闸 PASS] 第一关事实完整性过 + 无未收敛动作冲突")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
